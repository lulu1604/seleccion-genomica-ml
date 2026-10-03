"""
Proyecto: Selección genómica
Rama: f1-pubmed
Responsable: Chayna
................................
NOTA: la cifra que antes figuraba aquí estaba mal atribuida.
VanRaden (2008) trabajó sobre datos SIMULADOS (50,000 marcadores,
2,967 toros). Los 38,416 SNPs y los 3,576 toros Holstein son de
VanRaden et al. (2009), J. Dairy Sci. 92(1):16-24. Ya corregido en
docs/informe/informe.tex; no copiar cifras desde este archivo.

"""

import os
import re
import json
import time
import requests
import pandas as pd

RAW_DIR = 'data/raw/pubmed'
RESULTS_DIR = 'results'

KEYWORDS = ['milk', 'fat', 'yield', 'somatic cell']
TIMEOUT = 30  # segundos; sin esto el script se cuelga si PubMed no responde


def _cache_paths(gene):
    return (os.path.join(RAW_DIR, f'{gene}_ids.json'),
            os.path.join(RAW_DIR, f'{gene}.txt'))


def _read_cache(gene):
    """Devuelve (id_list, abstracts) desde data/raw/pubmed, o None si falta algo."""
    ids_path, txt_path = _cache_paths(gene)
    if not (os.path.exists(ids_path) and os.path.exists(txt_path)):
        return None
    with open(ids_path, encoding='utf-8') as f:
        id_list = json.load(f)
    with open(txt_path, encoding='utf-8') as f:
        abstracts = f.read()
    return id_list, abstracts


def _write_cache(gene, id_list, abstracts):
    os.makedirs(RAW_DIR, exist_ok=True)
    ids_path, txt_path = _cache_paths(gene)
    with open(ids_path, 'w', encoding='utf-8') as f:
        json.dump(id_list, f)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(abstracts)


def _download(gene):
    """Llama a PubMed y devuelve (id_list, abstracts). Lanza RequestException si falla."""
    # 1. Hacemos una búsqueda experta: El gen + vacas lecheras
    if gene == 'GEN_INVENTADO_QUE_NO_EXISTE':
        search_term = gene
    else:
        search_term = f"{gene} AND (bovine OR cattle OR dairy)"

    # Buscamos hasta 400 artículos (suficiente evidencia biológica)
    #El numero se puede cambiar
    #Pero se hicieron de¿diferentes pruebas, al parecer solo hay
    #379 articulos que hablan sobre el gen DGAT1
    url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={search_term}&retmode=json&retmax=400"

    time.sleep(1) # Pausa obligatoria para no saturar PubMed
    response = requests.get(url_search, timeout=TIMEOUT)
    response.raise_for_status()
    # Si PubMed devuelve una pagina de error en HTML, .json() revienta sin contexto
    try:
        data = response.json()
    except ValueError:
        raise requests.RequestException("la respuesta de esearch no es JSON valido")
    if not isinstance(data, dict) or 'esearchresult' not in data:
        raise requests.RequestException("la respuesta de esearch no trae 'esearchresult'")
    id_list = data['esearchresult'].get('idlist', [])

    # 2. Descargamos todos los textos reales de esos artículos
    abstracts = ""
    if id_list:
        ids_str = ','.join(id_list)
        url_fetch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=text&rettype=abstract"
        resp_fetch = requests.get(url_fetch, timeout=TIMEOUT)
        resp_fetch.raise_for_status()
        abstracts = resp_fetch.text

    return id_list, abstracts


def process_gene(gene, usar_cache=True):
    # OJO: 'gen' es la llave de cruce con results/snp_annot.csv (Ensembl, Ivan).
    # Siempre en MAYUSCULAS; no cambiar sin avisar a Ivan.
    gene = gene.strip().upper()

    cached = _read_cache(gene) if usar_cache else None
    if cached is not None:
        id_list, abstracts = cached
    else:
        try:
            id_list, abstracts = _download(gene)
        except requests.RequestException as e:
            print(f"ADVERTENCIA: PubMed fallo para el gen {gene} ({e}). "
                  f"Se deja la fila en ceros y se sigue con el siguiente gen.")
            return {'gen': gene, 'n_papers': 0, 'milk': 0, 'fat': 0,
                    'yield': 0, 'somatic_cell': 0}
        _write_cache(gene, id_list, abstracts)

    n_papers = len(id_list)
    # Convertimos todo a minúsculas para facilitar la búsqueda
    abstracts_text = abstracts.lower()

    # 3. Contamos las palabras clave exactas
    counts = {kw: 0 for kw in KEYWORDS}
    for kw in KEYWORDS:
        # \b asegura que busque la palabra exacta y no un fragmento
        counts[kw] = len(re.findall(rf'\b{kw}\b', abstracts_text))

    return {
        'gen': gene,
        'n_papers': n_papers,
        'milk': counts['milk'],
        'fat': counts['fat'],
        'yield': counts['yield'],
        'somatic_cell': counts['somatic cell']
    }

def main(genes=None):
    if genes is None:
        genes = ['DGAT1', 'GEN_INVENTADO_QUE_NO_EXISTE']
    results = []
    
    print("Iniciando busqueda en PubMed...")
    for g in genes:
        print(f"Buscando evidencias para: {g}...")
        results.append(process_gene(g))
        
    # Guardar en CSV respetando el contrato de tu rúbrica
    df = pd.DataFrame(results)
    df = df[['gen', 'n_papers', 'milk', 'fat', 'yield', 'somatic_cell']]
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    output_path = os.path.join(RESULTS_DIR, 'gene_evidence.csv')
    df.to_csv(output_path, index=False)
    
    print("\n" + "."*50)
    print("RESULTADOS DE LA BUSQUEDA EN PUBMED")
    print("."*50)
    for index, row in df.iterrows():
        print(f"Gen: {row['gen']}")
        print(f"Articulos encontrados: {row['n_papers']}")
        print(f"   Menciones en los textos:")
        print(f"   - Leche (milk): {row['milk']}")
        print(f"   - Grasa (fat):  {row['fat']}")
        print(f"   - Rendimiento (yield): {row['yield']}")
        print(f"   - Cel. somaticas (somatic_cell): {row['somatic_cell']}")
        print("-" * 50)

if __name__ == "__main__":
    main()

#Ver grafico, ya q' resume el rendimiento (correlación) de 6 modelos según el estudio 
#de Abdollahi-Arpanahi et al.