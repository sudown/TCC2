
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
    "https://github.com/koalaman/shellcheck.git"
    #"https://github.com/haskell/cabal.git"
]

def setup():
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
    
    # Cabeçalho do CSV
    with open(RESULTS_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repo", "MergeCommit", "File", "Diff3_Conflict", "CSDiff_Conflict", "CSDiff_Differs_From_Diff3"])

def run_csdiff(base, left, right, output):
    try:
        subprocess.run([CSDIFF_SCRIPT, base, left, right], stdout=open(output, 'w'), check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def count_conflicts(filepath):
    """Conta quantos marcadores de conflito '<<<<<<<' existem no arquivo."""
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.read()
            return content.count("<<<<<<<")
    except:
        return 0

def process_repo(repo_url):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(REPOS_DIR, repo_name)
    
    print(f"--- Processando {repo_name} ---")
    
    if not os.path.exists(repo_path):
        Repo.clone_from(repo_url, repo_path)
    
    repo = Repo(repo_path)
    
    # Itera sobre commits de merge (com 2 pais)
    merges = [c for c in repo.iter_commits() if len(c.parents) == 2]
    print(f"Encontrados {len(merges)} merges.")

    for commit in merges[:1000]: # Limitado a 50 merges para teste
        parent1 = commit.parents[0] # Left (geralmente)
        parent2 = commit.parents[1] # Right (geralmente)
        base = repo.merge_base(parent1, parent2)[0]
        
        # Arquivos modificados
        diffs = parent1.diff(parent2)
        
        for diff in diffs:
            filename = diff.a_path
            if not filename.endswith(".hs"):
                continue
                
            try:
                # Extrai as 3 versões do arquivo
                base_content = base.tree[filename].data_stream.read()
                left_content = parent1.tree[filename].data_stream.read()
                right_content = parent2.tree[filename].data_stream.read()
                
                # Salva temporariamente
                with open("temp_base.hs", "wb") as f: f.write(base_content)
                with open("temp_left.hs", "wb") as f: f.write(left_content)
                with open("temp_right.hs", "wb") as f: f.write(right_content)
                
                # 1. Roda Diff3 Padrão
                subprocess.run(["diff3", "-m", "temp_left.hs", "temp_base.hs", "temp_right.hs"], 
                               stdout=open("out_diff3.hs", "w"), stderr=subprocess.DEVNULL)
                
                # 2. Roda CSDiff (Seu Script)
                # Nota: Usamos --simple ou não dependendo do que você quer testar.
                # Aqui estou chamando sem flag (modo FULL)
                subprocess.run([CSDIFF_SCRIPT, "temp_base.hs", "temp_left.hs", "temp_right.hs"], 
                               stdout=open("out_csdiff.hs", "w"), stderr=subprocess.DEVNULL)
                
                # Coleta Métricas
                conflicts_diff3 = count_conflicts("out_diff3.hs")
                conflicts_csdiff = count_conflicts("out_csdiff.hs")
                
                # Verifica se os arquivos finais são diferentes
                is_different = False
                with open("out_diff3.hs", "rb") as f1, open("out_csdiff.hs", "rb") as f2:
                    if f1.read() != f2.read():
                        is_different = True

                # Salva no CSV se houver conflito em algum deles
                if conflicts_diff3 > 0 or conflicts_csdiff > 0:
                    with open(RESULTS_FILE, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([repo_name, commit.hexsha[:7], filename, conflicts_diff3, conflicts_csdiff, is_different])
                        
                    print(f"  [DADOS] {filename}: Diff3={conflicts_diff3}, CSDiff={conflicts_csdiff}")

            except Exception as e:
                # Ignora erros de arquivo não encontrado ou binário
                continue

if __name__ == "__main__":
    setup()
    for url in REPOS_TO_MINE:
        process_repo(url)
    print("\nExperimento Finalizado! Verifique 'resultados_experimento.csv'")
