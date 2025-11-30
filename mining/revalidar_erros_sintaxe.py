import os
import csv
import subprocess
import shutil
from git import Repo

# --- CONFIGURAÇÕES ---
# Aponte para a versão mais recente do seu script (ex: v10, v11 ou v12)
CSDIFF_SCRIPT = "./haskell-sep-merge.sh" 

# O arquivo de resultados da rodada anterior (que contém os erros)
INPUT_CSV = "resultados_com_validacao_total.csv"

# Onde salvar o relatório de "Antes vs Depois"
OUTPUT_CSV = "resultado_revalidacao.csv"

REPOS_DIR = "./repos_haskell"

def check_dependencies():
    if not os.path.exists(CSDIFF_SCRIPT):
        print(f"[ERRO] Script não encontrado: {CSDIFF_SCRIPT}")
        return False
    if shutil.which("ghc") is None:
        print("[ERRO] GHC necessário para validar sintaxe.")
        return False
    if not os.path.exists(INPUT_CSV):
        print(f"[ERRO] CSV de entrada não encontrado: {INPUT_CSV}")
        return False
    return True

def check_syntax(filepath):
    try:
        res = subprocess.run(["ghc", "-fno-code", "-v0", filepath], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0: return True
        err = res.stderr.lower()
        if any(e in err for e in ["parse error", "lexical error", "incorrect indentation", "unexpected"]):
            return False
        return True
    except: return True

def revalidate():
    print(f"Lendo falhas de: {INPUT_CSV}")
    print(f"Testando com script: {CSDIFF_SCRIPT}")
    print("-" * 60)

    # Prepara output
    with open(OUTPUT_CSV, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["Repo", "Commit", "File", "Old_ParseOK", "New_ParseOK", "Status"])
        
        with open(INPUT_CSV, 'r') as infile:
            reader = csv.DictReader(infile)
            
            count = 0
            fixed = 0
            
            for row in reader:
                # FILTRO: Casos onde a ferramenta disse que resolveu (0 conflitos)
                # mas gerou código quebrado (ParseOK=False), e o humano acertou (True).
                if (row['CSDiff_Conflict'] == '0' and 
                    row['CSDiff_ParseOK'] == 'False' and 
                    row['Manual_ParseOK'] == 'True'):
                    
                    repo_name = row['Repo']
                    commit_sha = row['MergeCommit']
                    filename = row['File']
                    
                    print(f"Processando: {repo_name} {commit_sha} - {filename}")
                    
                    # 1. Setup do Repositório
                    repo_path = os.path.join(REPOS_DIR, repo_name)
                    if not os.path.exists(repo_path):
                        print("  [SKIP] Repo não encontrado localmente.")
                        continue
                        
                    repo = Repo(repo_path)
                    
                    # 2. Extração dos Arquivos
                    # Precisamos achar o hash completo se o CSV só tiver o curto
                    try:
                        commit = repo.commit(commit_sha)
                        parent1 = commit.parents[0]
                        parent2 = commit.parents[1]
                        base = repo.merge_base(parent1, parent2)[0]
                        
                        base_blob = base.tree[filename].data_stream.read()
                        left_blob = parent1.tree[filename].data_stream.read()
                        right_blob = parent2.tree[filename].data_stream.read()
                        
                        with open("temp_base.hs", "wb") as f: f.write(base_blob)
                        with open("temp_left.hs", "wb") as f: f.write(left_blob)
                        with open("temp_right.hs", "wb") as f: f.write(right_blob)
                        
                        # 3. Executa a NOVA versão da ferramenta
                        subprocess.run([CSDIFF_SCRIPT, "temp_base.hs", "temp_left.hs", "temp_right.hs"], 
                                       stdout=open("out_revalidation.hs", "w"), stderr=subprocess.DEVNULL)
                        
                        # 4. Verifica Sintaxe
                        is_valid = check_syntax("out_revalidation.hs")
                        
                        status = "CORRIGIDO" if is_valid else "AINDA QUEBRADO"
                        if is_valid: fixed += 1
                        
                        print(f"  -> Resultado: {status}")
                        
                        writer.writerow([
                            repo_name, commit_sha, filename, 
                            "False", str(is_valid), status
                        ])
                        
                        count += 1
                        
                    except Exception as e:
                        print(f"  [ERRO] Falha ao processar: {e}")
                        continue

    print("-" * 60)
    print(f"Total reprocessado: {count}")
    print(f"Total corrigido pela nova versão: {fixed}")
    print(f"Relatório salvo em: {OUTPUT_CSV}")

if __name__ == "__main__":
    if check_dependencies():
        revalidate()