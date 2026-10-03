"""
Proyecto: Selección genómica
Rama: f1-pubmed
Responsable: Chayna
................................
NOTA PARA EL INFORME (Sección Estado del Arte - Ana):
Dato verificado de VanRaden (2008): 
- Tamaño del conjunto: 3,329 toros genotipados.
- Marcadores utilizados: 38,416 SNPs (tras control de calidad)

"""

import os
import re
import time
import requests
import pandas as pd

RAW_DIR = 'data/raw/pubmed'
RESULTS_DIR = 'results'
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

KEYWORDS = ['milk', 'fat', 'yield', 'somatic cell']

def process_gene(gene):
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
    
    response = requests.get(url_search)
    data = response.json()
    id_list = data.get('esearchresult', {}).get('idlist', [])
    
    n_papers = len(id_list)
    
    # 2. Descargamos todos los textos reales de esos artículos
    abstracts_text = ""
    if n_papers > 0:
        ids_str = ','.join(id_list)
        url_fetch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=text&rettype=abstract"
        resp_fetch = requests.get(url_fetch)
        # Convertimos todo a minúsculas para facilitar la búsqueda
        abstracts_text = resp_fetch.text.lower()
    
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

def main():
    genes = ['DGAT1', 'GEN_INVENTADO_QUE_NO_EXISTE']
    results = []
    
    print("Iniciando busqueda en PubMed...")
    for g in genes:
        print(f"Buscando evidencias para: {g}...")
        time.sleep(1) # Pausa obligatoria para no saturar PubMed
        results.append(process_gene(g))
        
    # Guardar en CSV respetando el contrato de tu rúbrica
    df = pd.DataFrame(results)
    df = df.rename(columns={'somatic cell': 'somatic_cell'})
    df = df[['gen', 'n_papers', 'milk', 'fat', 'yield', 'somatic_cell']]
    
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