import os
import csv
import subprocess
import shutil
from git import Repo

# --- CONFIGURAÇÕES ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Certifique-se de usar o script v10 (o mais robusto)
CSDIFF_SCRIPT = os.path.join(SCRIPT_DIR, "../haskell/haskell-sep-mergeV10.sh") 

REPOS_DIR = os.path.join(SCRIPT_DIR, "repos_haskell")
RESULTS_FILE = "resultados_com_validacao_total.csv"

REPOS_TO_MINE = [
    "https://github.com/koalaman/shellcheck.git",
    "https://github.com/jgm/pandoc.git",
    "https://github.com/haskell/cabal.git",
    "https://github.com/commercialhaskell/stack.git"
]

def check_dependencies():
    print("--- Verificando Dependências ---")
    if not os.path.exists(CSDIFF_SCRIPT):
        print(f"[ERRO CRÍTICO] Script CSDiff não encontrado em: {CSDIFF_SCRIPT}")
        return False
    if shutil.which("diff3") is None:
        print("[ERRO CRÍTICO] 'diff3' não instalado.")
        return False
    if shutil.which("ghc") is None:
        print("[AVISO] 'ghc' não encontrado. Validação de sintaxe será ignorada.")
    return True

def setup():
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
    
    # Adicionada coluna Manual_ParseOK
    with open(RESULTS_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Repo", "MergeCommit", "File", 
            "Diff3_Conflict", "CSDiff_Conflict", 
            "CSDiff_Equals_Manual", 
            "Diff3_ParseOK", "CSDiff_ParseOK", "Manual_ParseOK"
        ])

def count_conflicts(filepath):
    try:
        with open(filepath, 'r', errors='ignore') as f:
            return f.read().count("<<<<<<<")
    except: return 0

def files_are_equal(file1, file2):
    try:
        with open(file1, "r", encoding='utf-8', errors='ignore') as f1, \
             open(file2, "r", encoding='utf-8', errors='ignore') as f2:
            return "".join(f1.read().split()) == "".join(f2.read().split())
    except: return False

def check_syntax(filepath):
    if shutil.which("ghc") is None: return True
    try:
        res = subprocess.run(["ghc", "-fno-code", "-v0", filepath], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0: return True
        err = res.stderr.lower()
        if any(e in err for e in ["parse error", "lexical error", "incorrect indentation", "unexpected"]):
            return False
        return True
    except: return True

def get_content_safe(tree, filepath):
    try: return tree[filepath].data_stream.read()
    except: return None

def process_repo(repo_url):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(REPOS_DIR, repo_name)
    
    print(f"\n--- Iniciando Repositório: {repo_name} ---")
    
    if not os.path.exists(repo_path):
        Repo.clone_from(repo_url, repo_path)
    
    repo = Repo(repo_path)
    merges = [c for c in repo.iter_commits() if len(c.parents) == 2]
    print(f" > Total de merges: {len(merges)}")

    # Sem limite de break para rodar tudo (ou descomente para testar)
    for i, commit in enumerate(merges):
        # if i >= 200: break 
        
        parent1 = commit.parents[0]
        parent2 = commit.parents[1]
        
        try:
            base = repo.merge_base(parent1, parent2)[0]
        except: continue
        
        diffs = parent1.diff(parent2)
        hs_files = [d for d in diffs if d.a_path.endswith(".hs")]
        
        for diff in hs_files:
            filename = diff.a_path
            
            base_blob = get_content_safe(base.tree, filename)
            left_blob = get_content_safe(parent1.tree, filename)
            right_blob = get_content_safe(parent2.tree, filename)
            
            if base_blob is None or left_blob is None or right_blob is None: continue

            if (base_blob == left_blob or base_blob == right_blob or left_blob == right_blob):
                continue

            try:
                manual_blob = get_content_safe(commit.tree, filename)
                if manual_blob is None: continue

                with open("temp_base.hs", "wb") as f: f.write(base_blob)
                with open("temp_left.hs", "wb") as f: f.write(left_blob)
                with open("temp_right.hs", "wb") as f: f.write(right_blob)
                with open("temp_manual.hs", "wb") as f: f.write(manual_blob)
                
                # Executa ferramentas
                subprocess.run(["diff3", "-m", "temp_left.hs", "temp_base.hs", "temp_right.hs"], 
                               stdout=open("out_diff3.hs", "w"), stderr=subprocess.DEVNULL)
                
                subprocess.run([CSDIFF_SCRIPT, "temp_base.hs", "temp_left.hs", "temp_right.hs"],
                               stdout=open("out_csdiff.hs", "w"), stderr=subprocess.DEVNULL)

                # Métricas
                c_diff3 = count_conflicts("out_diff3.hs")
                c_csdiff = count_conflicts("out_csdiff.hs")
                
                # Só analisamos se houve conflito em alguma ferramenta
                if c_diff3 > 0 or c_csdiff > 0:
                    eq_manual = files_are_equal("out_csdiff.hs", "temp_manual.hs")
                    
                    parse_diff3 = check_syntax("out_diff3.hs") if c_diff3 == 0 else False
                    parse_csdiff = check_syntax("out_csdiff.hs") if c_csdiff == 0 else False
                    
                    # --- NOVA VALIDAÇÃO: MANUAL ---
                    # Verificamos se o humano comitou código válido
                    parse_manual = check_syntax("temp_manual.hs")

                    with open(RESULTS_FILE, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([
                            repo_name, commit.hexsha[:7], filename, 
                            c_diff3, c_csdiff, 
                            eq_manual, 
                            parse_diff3, parse_csdiff, parse_manual
                        ])
                    
                    # Log de alerta se o humano errou (código quebrado no repo)
                    if not parse_manual:
                        print(f"   [ALERTA] Código Manual Inválido em {filename} ({commit.hexsha[:7]})")

            except Exception:
                continue

if __name__ == "__main__":
    if check_dependencies():
        setup()
        for url in REPOS_TO_MINE:
            process_repo(url)
        print(f"\nFim! Verifique '{RESULTS_FILE}'")