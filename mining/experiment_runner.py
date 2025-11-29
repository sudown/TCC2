
import os
import csv
import subprocess
import shutil
from git import Repo

# CONFIGURAÇÕES
CSDIFF_SCRIPT = "../haskell/csdiff-hs-merge.sh"
REPOS_DIR = "./repos_haskell" # Pasta onde os repos serão clonados
RESULTS_FILE = "resultados_experimento.csv"

# Lista de repositórios Haskell para testar (adicione mais aqui)
REPOS_TO_MINE = [
    "https://github.com/commercialhaskell/stack"
]

def setup():
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
    
    # Adicionamos colunas de comparação com o HUMANO (Manual)
    with open(RESULTS_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Repo", "MergeCommit", "File", 
            "Diff3_Conflict", "CSDiff_Conflict", 
            "CSDiff_Equals_Diff3", "CSDiff_Equals_Manual"
        ])

def count_conflicts(filepath):
    try:
        with open(filepath, 'r', errors='ignore') as f:
            return f.read().count("<<<<<<<")
    except:
        return 0

def files_are_equal(file1, file2):
    """
    Compara dois arquivos ignorando completamente espaços em branco,
    quebras de linha e tabulações. (Comparação 'Minificada')
    """
    try:
        with open(file1, "r", encoding='utf-8', errors='ignore') as f1, \
             open(file2, "r", encoding='utf-8', errors='ignore') as f2:
            
            # .read().split() quebra o texto em palavras (tokens), removendo todo whitespace
            # "".join(...) junta tudo numa tripa só de caracteres
            content1 = "".join(f1.read().split())
            content2 = "".join(f2.read().split())
            
            return content1 == content2
    except:
        return False

def process_repo(repo_url):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(REPOS_DIR, repo_name)
    
    print(f"--- Processando {repo_name} ---")
    
    if not os.path.exists(repo_path):
        Repo.clone_from(repo_url, repo_path)
    
    repo = Repo(repo_path)
    
    # Itera sobre commits de merge
    merges = [c for c in repo.iter_commits() if len(c.parents) == 2]
    print(f"Total de merges no histórico: {len(merges)}")

    count = 0
    scenarios_analyzed = 0
    
    for commit in merges:
        if scenarios_analyzed >= 10000: break # Limite de cenários úteis
        
        parent1 = commit.parents[0] # Left
        parent2 = commit.parents[1] # Right
        
        try:
            base = repo.merge_base(parent1, parent2)[0]
        except:
            continue # Pula se não achar base comum
        
        # Pega arquivos diferentes entre Left e Right
        diffs = parent1.diff(parent2)
        
        for diff in diffs:
            filename = diff.a_path
            if not filename.endswith(".hs"):
                continue
            
            try:
                # Obtém os Blobs (Objetos do Git) para comparar Hashes
                blob_left = parent1.tree[filename]
                blob_right = parent2.tree[filename]
                blob_base = base.tree[filename]
                
                # --- FILTRO DO ORIENTADOR (Non-trivial Merges) ---
                # Garante que as 3 versões são distintas entre si
                if (blob_base.hexsha == blob_left.hexsha or 
                    blob_base.hexsha == blob_right.hexsha or 
                    blob_left.hexsha == blob_right.hexsha):
                    continue # Pula merges triviais
                
                # Se passou aqui, é um cenário válido!
                scenarios_analyzed += 1
                
                # Extrai conteúdo
                base_content = blob_base.data_stream.read()
                left_content = blob_left.data_stream.read()
                right_content = blob_right.data_stream.read()
                manual_content = commit.tree[filename].data_stream.read()
                
                with open("temp_base.hs", "wb") as f: f.write(base_content)
                with open("temp_left.hs", "wb") as f: f.write(left_content)
                with open("temp_right.hs", "wb") as f: f.write(right_content)
                with open("temp_manual.hs", "wb") as f: f.write(manual_content)
                
                # Executa Diff3
                subprocess.run(["diff3", "-m", "temp_left.hs", "temp_base.hs", "temp_right.hs"], 
                               stdout=open("out_diff3.hs", "w"), stderr=subprocess.DEVNULL)
                
                # Executa Haskell-SepMerge (Ajuste a flag se necessário)
                subprocess.run([CSDIFF_SCRIPT, "temp_base.hs", "temp_left.hs", "temp_right.hs"], 
                               stdout=open("out_csdiff.hs", "w"), stderr=subprocess.DEVNULL)
                
                # Coleta Métricas
                c_diff3 = count_conflicts("out_diff3.hs")
                c_csdiff = count_conflicts("out_csdiff.hs")
                
                # Comparações (Usando a versão 'Minificada' que discutimos)
                eq_diff3 = files_are_equal("out_csdiff.hs", "out_diff3.hs")
                eq_manual = files_are_equal("out_csdiff.hs", "temp_manual.hs")

                if c_diff3 > 0:
                    with open(RESULTS_FILE, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([
                            repo_name, commit.hexsha[:7], filename, 
                            c_diff3, c_csdiff, 
                            eq_diff3, eq_manual
                        ])
                    
                    if c_csdiff < c_diff3:
                        print(f"  [REDUÇÃO] {filename}: {c_diff3} -> {c_csdiff}")
                    if c_csdiff == 0 and not eq_manual:
                        print(f"  [ALERTA FN] {filename}: Divergência do Manual")
            
            except Exception:
                # Arquivo não existe em uma das versões (adicionado/deletado)
                continue
        
        count += 1

if __name__ == "__main__":
    setup()
    for url in REPOS_TO_MINE:
        process_repo(url)
    print("\nFim! Verifique 'resultados_experimento.csv'")