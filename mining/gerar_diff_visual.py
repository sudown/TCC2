import pandas as pd
import os
import subprocess
import difflib
from git import Repo

# --- CONFIGURAÇÕES ---
CSV_FILE = "casos_sucesso_absoluto.csv"
REPOS_DIR = "./repos_haskell"
# Ajuste o caminho para o JAR se necessário, tal como fez no extrair_casos.py
HASKELL_SEPMERGE_JAR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../haskell-sepmerge/target/haskell-sepmerge.jar"))

def get_content_safe(tree, filepath):
    """Extrai o conteúdo do ficheiro a partir da árvore do Git."""
    try:
        # Lemos e descodificamos para texto, ignorando erros de encoding
        return tree[filepath].data_stream.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

def gerar_comparacoes_html():
    if not os.path.exists(CSV_FILE):
        print(f"[ERRO] Ficheiro '{CSV_FILE}' não encontrado.")
        return

    df = pd.read_csv(CSV_FILE)
    
    # Filtramos apenas os 5 casos em que a ferramenta teve sucesso, mas o código difere do manual
    casos_diferentes = df[(df['CSDiff_Equals_Manual'] == False)]
    
    pasta_saida = "comparacoes_visuais"
    os.makedirs(pasta_saida, exist_ok=True)

    print(f"A iniciar a geração de {len(casos_diferentes)} comparações visuais...\n")

    for index, row in casos_diferentes.iterrows():
        repo_name = row['Repo']
        commit_sha = row['MergeCommit']
        filename = row['File']
        
        print(f"[{index+1}/{len(casos_diferentes)}] A processar: {repo_name} | {commit_sha[:7]} | {filename}")
        
        repo_path = os.path.join(REPOS_DIR, repo_name)
        repo = Repo(repo_path)
        commit = repo.commit(commit_sha)
        
        # 1. Extrair a versão manual (resolvida pelo humano)
        manual_text = get_content_safe(commit.tree, filename)
        
        # 2. Reconstruir o cenário base, left e right
        parent1 = commit.parents[0]
        parent2 = commit.parents[1]
        base_commit = repo.merge_base(parent1, parent2)[0]
        
        base_text = get_content_safe(base_commit.tree, filename)
        left_text = get_content_safe(parent1.tree, filename)
        right_text = get_content_safe(parent2.tree, filename)
        
        if not all([manual_text, base_text, left_text, right_text]):
            print("  -> Ignorado: Falha ao extrair um dos blobs do Git.")
            continue
            
        # Guardar ficheiros temporários para o Java ler
        with open("temp_base.hs", "w", encoding="utf-8") as f: f.write(base_text)
        with open("temp_left.hs", "w", encoding="utf-8") as f: f.write(left_text)
        with open("temp_right.hs", "w", encoding="utf-8") as f: f.write(right_text)
        
        # 3. Executar o Haskell-SepMerge (a nossa ferramenta)
        resultado = subprocess.run(
            ["java", "-jar", HASKELL_SEPMERGE_JAR, "temp_base.hs", "temp_left.hs", "temp_right.hs"],
            capture_output=True, text=True
        )
        csdiff_text = resultado.stdout
        
        # 4. Gerar o ficheiro HTML com o Diff Lado a Lado
        # O parâmetro context=True com numlines=5 garante que vemos apenas o bloco alterado e 5 linhas acima/abaixo
        html_diff = difflib.HtmlDiff(wrapcolumn=90).make_file(
            csdiff_text.splitlines(), 
            manual_text.splitlines(),
            fromdesc=f"Haskell-SepMerge (Automático)",
            todesc=f"Merge Humano ({commit_sha[:7]})",
            context=True, numlines=5
        )
        
        nome_seguro = filename.replace("/", "_").replace("\\", "_")
        caminho_html = os.path.join(pasta_saida, f"{repo_name}_{commit_sha[:7]}_{nome_seguro}.html")
        
        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(html_diff)
            
        print(f"  -> Diff guardado em: {caminho_html}")

if __name__ == "__main__":
    gerar_comparacoes_html()