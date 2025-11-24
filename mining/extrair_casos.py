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
    ("cabal", "6f19128", "cabal-install/Distribution/Client/CmdClean.hs")    # Redução (2->1)
]

#Mapeamento para gerar links do GitHub (Ajuste se adicionar mais repos)
REPO_URLS = {
    "cabal": "https://github.com/haskell/cabal",
    "shellcheck": "https://github.com/koalaman/shellcheck"
}

def extract_cases():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for repo_name, commit_sha, filepath in CASOS_INTERESSANTES:
        merge_short = commit_sha[:7]
        print(f"--- Extraindo caso de merge: {merge_short} ({filepath}) ---")
        
        repo_path = os.path.join(REPOS_DIR, repo_name)
        if not os.path.exists(repo_path):
            print(f"   [ERRO] Repositório não encontrado em {repo_path}")
            continue

        repo = Repo(repo_path)
        merge_commit = repo.commit(commit_sha)
        
        # Identifica os pais e a base
        parent1 = merge_commit.parents[0] # Left
        parent2 = merge_commit.parents[1] # Right
        base_commit = repo.merge_base(parent1, parent2)[0]
        
        # Pega os Hashes Curtos REAIS de cada versão
        id_base = base_commit.hexsha[:7]
        id_left = parent1.hexsha[:7]
        id_right = parent2.hexsha[:7]
        id_manual = merge_short # O manual é o resultado do próprio merge commit

        try:
            # Mantemos a pasta com o nome do MERGE para agrupar
            case_dir = os.path.join(OUTPUT_DIR, f"{repo_name}_{merge_short}")
            if not os.path.exists(case_dir):
                os.makedirs(case_dir)

            # Definindo nomes com os IDs CORRETOS de cada versão
            f_base = f"{case_dir}/base_{id_base}.hs"
            f_left = f"{case_dir}/left_{id_left}.hs"
            f_right = f"{case_dir}/right_{id_right}.hs"
            f_manual = f"{case_dir}/manual_{id_manual}.hs"
            
            # Os resultados dos merges gerados levam o ID do merge pai
            f_merge_diff3 = f"{case_dir}/merge_diff3_{id_manual}.hs"
            f_merge_csdiff = f"{case_dir}/merge_csdiff_{id_manual}.hs"

            # 1. Extrai as 3 versões de entrada
            with open(f_base, "wb") as f: f.write(base_commit.tree[filepath].data_stream.read())
            with open(f_left, "wb") as f: f.write(parent1.tree[filepath].data_stream.read())
            with open(f_right, "wb") as f: f.write(parent2.tree[filepath].data_stream.read())
            
            # 2. Extrai o Manual (Gabarito)
            try:
                with open(f_manual, "wb") as f: f.write(merge_commit.tree[filepath].data_stream.read())
            except:
                print("   [AVISO] Manual não encontrado.")

            # 3. Gera os merges para comparação
            # Diff3
            with open(f_merge_diff3, "w") as out:
                subprocess.run(["diff3", "-m", f_left, f_base, f_right], 
                               stdout=out, stderr=subprocess.DEVNULL)

            # CSDiff
            with open(f_merge_csdiff, "w") as out:
                subprocess.run([CSDIFF_SCRIPT, f_base, f_left, f_right], stdout=out)
            
            # 4. Gera arquivo de informações detalhado
            if repo_name in REPO_URLS:
                base = REPO_URLS[repo_name]
                with open(f"{case_dir}/info.txt", "w") as f:
                    f.write(f"Repo: {repo_name}\n")
                    f.write(f"Arquivo: {filepath}\n\n")
                    
                    f.write(f"Commit Merge (Manual): {merge_short}\n")
                    f.write(f"Link: {base}/commit/{commit_sha}\n\n")
                    
                    f.write(f"Commit Base (Ancestral): {id_base}\n")
                    f.write(f"Link: {base}/commit/{base_commit.hexsha}\n\n")
                    
                    f.write(f"Commit Left (Local): {id_left}\n")
                    f.write(f"Link: {base}/commit/{parent1.hexsha}\n\n")
                    
                    f.write(f"Commit Right (Remoto): {id_right}\n")
                    f.write(f"Link: {base}/commit/{parent2.hexsha}\n")

            print(f"   -> Arquivos salvos em {case_dir}/")
            print(f"      Base: {id_base} | Left: {id_left} | Right: {id_right}")
            
        except Exception as e:
            print(f"   [ERRO] Falha geral na extração: {e}")

if __name__ == "__main__":
    extract_cases()