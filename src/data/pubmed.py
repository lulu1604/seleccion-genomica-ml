import os
import re
import time
import json
import requests
import pandas as pd

# 1. Configuración inicial y creación de carpetas
RAW_DIR = 'data/raw/pubmed'
RESULTS_DIR = 'results'
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

KEYWORDS = ['milk', 'fat', 'yield', 'somatic cell']

def search_pubmed(gene):
    """Busca el gen en PubMed y devuelve una lista de IDs de artículos."""
    # Se añade 'bovine' o 'cattle' implícitamente si quisieran, pero nos apegamos a buscar el gen.
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={gene}&retmode=json&retmax=50"
    response = requests.get(url)
    data = response.json()
    return data.get('esearchresult', {}).get('idlist', [])

def fetch_abstracts(id_list):
    """Descarga los resúmenes dados una lista de IDs de PubMed."""
    if not id_list:
        return []
    
    ids_str = ','.join(id_list)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml&rettype=abstract"
    response = requests.get(url)
    
    # Extracción rudimentaria con Regex para no depender de librerías XML complejas
    abstracts = re.findall(r'<AbstractText.*?>(.*?)</AbstractText>', response.text, re.IGNORECASE | re.DOTALL)
    return abstracts

def process_gene(gene):
    """Procesa un gen completo: revisa caché, descarga, limpia y cuenta."""
    cache_file = os.path.join(RAW_DIR, f"{gene}_abstracts.json")
    
    # 2. Lógica de caché (no volver a llamar a la API si ya lo tenemos)
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            abstracts = json.load(f)
    else:
        # Respetar límite de consultas (máximo 3 por segundo en NCBI sin API key)
        time.sleep(0.4) 
        id_list = search_pubmed(gene)
        time.sleep(0.4)
        abstracts = fetch_abstracts(id_list)
        
        # Guardar crudos en caché
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(abstracts, f, ensure_ascii=False, indent=2)

    # 3. Limpiar texto y contar palabras clave
    counts = {kw: 0 for kw in KEYWORDS}
    
    for abstract in abstracts:
        # Minúsculas y quitar signos de puntuación
        clean_text = re.sub(r'[^\w\s]', '', abstract.lower())
        
        for kw in KEYWORDS:
            # Contar cuántas veces aparece la palabra clave en el resumen limpio
            # Usamos boundaries \b para buscar palabras exactas (ej. que no cuente 'fates' como 'fat')
            counts[kw] += len(re.findall(rf'\b{kw}\b', clean_text))
            
    return {
        'gen': gene,
        'n_papers': len(abstracts),
        'milk': counts['milk'],
        'fat': counts['fat'],
        'yield': counts['yield'],
        'somatic_cell': counts['somatic cell']
    }

def main():
    # El contrato dice que esto no debe romperse si hay genes raros.
    # DGAT1 es tu caso de prueba obligatorio.
    genes_to_test = ['DGAT1', 'GEN_INVENTADO_QUE_NO_EXISTE'] 
    
    results = []
    for gen in genes_to_test:
        print(f"Procesando gen: {gen}...")
        data = process_gene(gen)
        results.append(data)
        
    # 4. Guardar resultados respetando exactamente el contrato de columnas
    df = pd.DataFrame(results)
    
    # Renombrar 'somatic cell' a 'somatic_cell' para la columna del CSV
    df = df.rename(columns={'somatic cell': 'somatic_cell'})
    
    # Asegurar el orden exacto de las columnas
    column_order = ['gen', 'n_papers', 'milk', 'fat', 'yield', 'somatic_cell']
    df = df[column_order]
    
    output_path = os.path.join(RESULTS_DIR, 'gene_evidence.csv')
    df.to_csv(output_path, index=False)
    print(f"\exito! Archivo guardado en {output_path}")
    print(df.head())

if __name__ == "__main__":
    main()