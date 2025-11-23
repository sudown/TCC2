#SCRIPT PARA BUSCAR OS CONFLITOS PARA ANALISE
import os
import subprocess
from git import Repo

# CONFIGURAÇÕES
CSDIFF_SCRIPT = "../haskell/csdiff-hs-merge.sh" # Seu script final
REPOS_DIR = "./repos_haskell"
OUTPUT_DIR = "./casos_estudo" # Onde vamos salvar os exemplos

# Os casos interessantes que você achou no CSV
# Formato: (RepoName, CommitHash, FilePath)
CASOS_INTERESSANTES = [
    ("shellcheck", "3fa5b7d", "src/ShellCheck/AnalyzerLib.hs"),       # Redução (2->1)
    ("shellcheck", "85066dd", "src/ShellCheck/Checks/ShellSupport.hs"), # Granularidade (1->2)
    ("shellcheck", "726a4e5", "ShellCheck/Analytics.hs")              # Redução (2->1)
]

def extract_cases():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for repo_name, commit_sha, filepath in CASOS_INTERESSANTES:
        print(f"--- Extraindo caso: {commit_sha} ({filepath}) ---")
        
        repo_path = os.path.join(REPOS_DIR, repo_name)
        repo = Repo(repo_path)
        commit = repo.commit(commit_sha)
        
        parent1 = commit.parents[0]
        parent2 = commit.parents[1]
        base = repo.merge_base(parent1, parent2)[0]
        
        try:
            # Extrai os conteúdos
            base_content = base.tree[filepath].data_stream.read()
            left_content = parent1.tree[filepath].data_stream.read()
            right_content = parent2.tree[filepath].data_stream.read()
            
            case_dir = os.path.join(OUTPUT_DIR, f"{repo_name}_{commit_sha}")
            if not os.path.exists(case_dir):
                os.makedirs(case_dir)
            
            # Salva os originais
            with open(f"{case_dir}/base.hs", "wb") as f: f.write(base_content)
            with open(f"{case_dir}/left.hs", "wb") as f: f.write(left_content)
            with open(f"{case_dir}/right.hs", "wb") as f: f.write(right_content)
            
            # Gera os merges para comparação visual
            # 1. Diff3
            with open(f"{case_dir}/merge_diff3.hs", "w") as out:
                subprocess.run(["diff3", "-m", 
                                f"{case_dir}/left.hs", 
                                f"{case_dir}/base.hs", 
                                f"{case_dir}/right.hs"], stdout=out, stderr=subprocess.DEVNULL)

            # 2. CSDiff (Seu script)
            with open(f"{case_dir}/merge_csdiff.hs", "w") as out:
                subprocess.run([CSDIFF_SCRIPT,
                                f"{case_dir}/base.hs", 
                                f"{case_dir}/left.hs", 
                                f"{case_dir}/right.hs"], stdout=out)
                                
            print(f"   -> Salvo em {case_dir}")
            
        except Exception as e:
            print(f"   [ERRO] Não foi possível extrair: {e}")

if __name__ == "__main__":
    extract_cases()