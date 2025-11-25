# SCRIPT PARA BUSCAR OS CONFLITOS PARA ANALISE
import os
import subprocess
from git import Repo

# CONFIGURAÇÕES
CSDIFF_SCRIPT = "../haskell/csdiff-hs-merge.sh"  # Seu script final
REPOS_DIR = "./repos_haskell"
OUTPUT_DIR = "./casos_estudo"

# Seus casos encontrados
CASOS_INTERESSANTES = [
    ("cabal", "6f19128", "cabal-install/Distribution/Client/CmdClean.hs")
]

# URLs dos repositórios para clone automático
REPO_URLS = {
    "cabal": "https://github.com/haskell/cabal",
    "shellcheck": "https://github.com/koalaman/shellcheck"
}

def ensure_repo_cloned(repo_name):
    """
    Garante que o repositório existe em REPOS_DIR.
    Se não existir, ele é clonado automaticamente.
    """
    repo_path = os.path.join(REPOS_DIR, repo_name)

    # Cria a pasta onde ficam os repositórios
    os.makedirs(REPOS_DIR, exist_ok=True)

    if os.path.exists(repo_path):
        print(f"   [OK] Repositório encontrado: {repo_path}")
        return repo_path

    # Verifica se temos URL para este repo
    if repo_name not in REPO_URLS:
        raise ValueError(f"URL não definida para o repositório: {repo_name}")

    repo_url = REPO_URLS[repo_name]
    print(f"   [CLONANDO] {repo_name} de {repo_url} ...")

    try:
        Repo.clone_from(repo_url, repo_path)
        print(f"   [OK] Clone concluído")
    except Exception as e:
        print(f"   [ERRO] Falha ao clonar {repo_name}: {e}")
        raise e

    return repo_path


def extract_cases():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for repo_name, commit_sha, filepath in CASOS_INTERESSANTES:
        merge_short = commit_sha[:7]
        print(f"--- Extraindo caso de merge: {merge_short} ({filepath}) ---")

        # Agora garantimos que o repositório existe (clonando se necessário)
        try:
            repo_path = ensure_repo_cloned(repo_name)
        except Exception:
            print("   [ERRO] Não foi possível obter o repositório.")
            continue

        # Abre o repositório
        repo = Repo(repo_path)

        try:
            merge_commit = repo.commit(commit_sha)
        except:
            print(f"   [ERRO] Commit {commit_sha} não encontrado no repo!")
            continue

        parent1 = merge_commit.parents[0]
        parent2 = merge_commit.parents[1]
        base_commit = repo.merge_base(parent1, parent2)[0]

        id_base = base_commit.hexsha[:7]
        id_left = parent1.hexsha[:7]
        id_right = parent2.hexsha[:7]
        id_manual = merge_short

        try:
            case_dir = os.path.join(OUTPUT_DIR, f"{repo_name}_{merge_short}")
            os.makedirs(case_dir, exist_ok=True)

            f_base = f"{case_dir}/base_{id_base}.hs"
            f_left = f"{case_dir}/left_{id_left}.hs"
            f_right = f"{case_dir}/right_{id_right}.hs"
            f_manual = f"{case_dir}/manual_{id_manual}.hs"
            f_merge_diff3 = f"{case_dir}/merge_diff3_{id_manual}.hs"
            f_merge_csdiff = f"{case_dir}/merge_csdiff_{id_manual}.hs"

            # Base, left e right
            with open(f_base, "wb") as f: f.write(base_commit.tree[filepath].data_stream.read())
            with open(f_left, "wb") as f: f.write(parent1.tree[filepath].data_stream.read())
            with open(f_right, "wb") as f: f.write(parent2.tree[filepath].data_stream.read())

            # Manual
            try:
                with open(f_manual, "wb") as f: f.write(merge_commit.tree[filepath].data_stream.read())
            except:
                print("   [AVISO] Manual não encontrado.")

            # diff3
            with open(f_merge_diff3, "w") as out:
                subprocess.run(["diff3", "-m", f_left, f_base, f_right],
                               stdout=out, stderr=subprocess.DEVNULL)

            # csdiff
            with open(f_merge_csdiff, "w") as out:
                subprocess.run([CSDIFF_SCRIPT, f_base, f_left, f_right], stdout=out)

            # info.txt
            if repo_name in REPO_URLS:
                base = REPO_URLS[repo_name]
                with open(f"{case_dir}/info.txt", "w") as f:
                    f.write(f"Repo: {repo_name}\n")
                    f.write(f"Arquivo: {filepath}\n\n")

                    f.write(f"Commit Merge (Manual): {merge_short}\n")
                    f.write(f"Link: {base}/commit/{commit_sha}\n\n")

                    f.write(f"Commit Base: {id_base}\n")
                    f.write(f"Link: {base}/commit/{base_commit.hexsha}\n\n")

                    f.write(f"Commit Left: {id_left}\n")
                    f.write(f"Link: {base}/commit/{parent1.hexsha}\n\n")

                    f.write(f"Commit Right: {id_right}\n")
                    f.write(f"Link: {base}/commit/{parent2.hexsha}\n")

            print(f"   -> Arquivos salvos em {case_dir}/")
            print(f"      Base: {id_base} | Left: {id_left} | Right: {id_right}")

        except Exception as e:
            print(f"   [ERRO] Falha geral na extração: {e}")


if __name__ == "__main__":
    extract_cases()
