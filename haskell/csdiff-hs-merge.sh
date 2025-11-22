#!/usr/bin/env bash
#
# csdiff-hs-merge.sh
#
# Uso: 
#   ./csdiff-hs-merge.sh [--simple] BASE_FILE LEFT_FILE RIGHT_FILE
#
# Opções:
#   --simple   Usa apenas o conjunto básico de separadores (:: -> => <- @).
#              (O padrão é usar o conjunto completo, incluindo = | , ( ) )
#

set -euo pipefail

MARKER=">>>>CSDIFF_MARK<<<<<"
MODE="FULL"  # Padrão: conjunto completo de separadores

# --- Parsing de Argumentos ---
usage() {
    echo "Uso: $0 [--simple] BASE_FILE LEFT_FILE RIGHT_FILE" >&2
    echo "  --simple: Usa menos delimitadores (apenas :: -> => <- @)" >&2
    exit 1
}

# Processa flags antes dos arquivos
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --simple|--menos)
            MODE="SIMPLE"
            shift
            ;;
        -*)
            echo "Opção desconhecida: $1" >&2
            usage
            ;;
        *)
            break # Parar ao encontrar o primeiro argumento que não é flag (arquivo)
            ;;
    esac
done

# Verifica se restaram exatamente 3 argumentos (os arquivos)
if [ "$#" -ne 3 ]; then
    usage
fi

BASE_FILE=$1
LEFT_FILE=$2
RIGHT_FILE=$3

# Garante que os arquivos existem
for f in "$BASE_FILE" "$LEFT_FILE" "$RIGHT_FILE"; do
    if [ ! -f "$f" ]; then
        echo "Erro: arquivo não encontrado: $f" >&2
        exit 1
    fi
done

# Cria arquivos temporários
tmp_base=$(mktemp)
tmp_left=$(mktemp)
tmp_right=$(mktemp)
tmp_merged=$(mktemp)

cleanup() {
    rm -f "$tmp_base" "$tmp_left" "$tmp_right" "$tmp_merged"
}
trap cleanup EXIT

############################################
# Função: Pré-processamento
# (Adaptada para ler a variável 'mode')
############################################
preprocess_file() {
    in_file=$1
    out_file=$2

    tr -d '\r' < "$in_file" | \
    awk -v mk="$MARKER" -v mode="$MODE" '
    {
        line = $0
        comment_idx = index(line, "--")
        
        if (comment_idx > 0) {
            code_part = substr(line, 1, comment_idx - 1)
            comment_part = substr(line, comment_idx)
        } else {
            code_part = line
            comment_part = ""
        }

        repl = "\n" mk "\n&\n" mk "\n"
        
        # --- Separadores Básicos (Sempre ativos) ---
        gsub(/::/, repl, code_part)
        gsub(/->/, repl, code_part)
        gsub(/=>/, repl, code_part)
        gsub(/<-/, repl, code_part)
        gsub(/@/,  repl, code_part)
        
        # --- Separadores Estendidos (Apenas no modo FULL) ---
        if (mode == "FULL") {
            gsub(/=/,  repl, code_part)
            gsub(/,/,  repl, code_part)
            gsub(/[|]/, repl, code_part)
            gsub(/\(/,  repl, code_part)
            gsub(/\)/,  repl, code_part)
        }

        print code_part comment_part
    }
    ' > "$out_file"
}

############################################
# Função: Pós-processamento
# (Adaptada para ler a variável 'mode')
############################################
postprocess_file() {
    in_file=$1

    tr -d '\r' < "$in_file" | \
    awk -v MARKER="$MARKER" '
        MARKER == $0 { next }
        { print }
    ' | \
    awk -v mode="$MODE" '
        function flush_prev() {
            if (has_prev) {
                print prev_line
                has_prev = 0
                prev_line = ""
            }
        }

        BEGIN {
            has_prev = 0
            sep_pending = 0
            sep = ""
        }

        # Verifica se a linha é um separador válido com base no modo
        function is_separator_line(s) {
            # Básicos
            if (s == "::" || s == "->" || s == "=>" || s == "<-" || s == "@") return 1
            
            # Estendidos (apenas se FULL)
            if (mode == "FULL") {
                if (s == "=" || s == "|" || s == "," || s == "(" || s == ")") return 1
            }
            
            return 0
        }

        {
            line = $0

            if (!has_prev && !sep_pending) {
                if (is_separator_line(line)) {
                    sep = line
                    sep_pending = 1
                } else {
                    prev_line = line
                    has_prev = 1
                }
                next
            }

            if (sep_pending) {
                if (!has_prev) {
                    prev_line = sep line
                    has_prev = 1
                } else {
                    prev_line = prev_line sep line
                }
                sep = ""
                sep_pending = 0
                next
            }

            if (is_separator_line(line)) {
                sep = line
                sep_pending = 1
                next
            }

            flush_prev()
            prev_line = line
            has_prev = 1
        }

        END {
            if (sep_pending) {
                if (has_prev) {
                    prev_line = prev_line sep
                } else {
                    prev_line = sep
                    has_prev = 1
                }
            }
            flush_prev()
        }
    '
}

############################################
# Execução Principal
############################################
preprocess_file "$BASE_FILE" "$tmp_base"
preprocess_file "$LEFT_FILE" "$tmp_left"
preprocess_file "$RIGHT_FILE" "$tmp_right"

diff3 -m "$tmp_left" "$tmp_base" "$tmp_right" > "$tmp_merged" || {
    :
}

postprocess_file "$tmp_merged"