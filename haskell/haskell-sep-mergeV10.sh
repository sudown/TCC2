#!/usr/bin/env bash
#
# csdiff-hs-merge-v10.sh
#
# v10: "Idiomatic Haskell Layout"
# 1. Proteção de Tokens (v5) - Mantida.
# 2. Atribuição (=) é Horizontal - Mantido (v9).
# 3. CORREÇÃO CRÍTICA: Separadores Verticais (::, ->, =>) quebram linha, 
#    adicionam indentação (4 espaços), mas NÃO puxam a próxima linha.
#    Isso evita o erro de "engolir" a definição da função seguinte.
#

set -euo pipefail

MARKER=">>>>CSDIFF_MARK<<<<<"
MODE="FULL"

usage() { echo "Uso: $0 [--simple] BASE LEFT RIGHT"; exit 1; }

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --simple|--menos) MODE="SIMPLE"; shift ;;
        -*) usage ;;
        *) break ;;
    esac
done

if [ "$#" -ne 3 ]; then usage; fi
BASE_FILE=$1; LEFT_FILE=$2; RIGHT_FILE=$3

for f in "$BASE_FILE" "$LEFT_FILE" "$RIGHT_FILE"; do
    if [ ! -f "$f" ]; then echo "Erro: arquivo $f não encontrado"; exit 1; fi
done

tmp_base=$(mktemp); tmp_left=$(mktemp); tmp_right=$(mktemp); tmp_merged=$(mktemp)
cleanup() { rm -f "$tmp_base" "$tmp_left" "$tmp_right" "$tmp_merged"; }
trap cleanup EXIT

# ----------------------------------------------------------------------
# 1. PRÉ-PROCESSAMENTO (MANTIDO)
# ----------------------------------------------------------------------
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

        # PROTEÇÃO DE TOKENS
        gsub(/::/, "HSS_DOUBLE_COLON", code_part)
        gsub(/->/, "HSS_ARROW", code_part)
        gsub(/=>/, "HSS_FAT_ARROW", code_part)
        gsub(/<-/, "HSS_LEFT_ARROW", code_part)
        gsub(/@/,  "HSS_AT_SIGN", code_part)
        gsub(/==/, "HSS_EQUALITY", code_part)
        gsub(/>=/, "HSS_GTE", code_part)
        gsub(/<=/, "HSS_LTE", code_part)
        gsub(/\/=/, "HSS_NEQ", code_part)

        repl_base = "\n" mk "\n&\n" mk "\n"

        if (mode == "FULL") {
            gsub(/=/, repl_base, code_part)
            gsub(/,/, repl_base, code_part)
            gsub(/[|]/, repl_base, code_part)
            gsub(/\(/, repl_base, code_part)
            gsub(/\)/, repl_base, code_part)
        }

        r_dc = "\n" mk "\n::\n" mk "\n"; gsub(/HSS_DOUBLE_COLON/, r_dc, code_part)
        r_arr = "\n" mk "\n->\n" mk "\n"; gsub(/HSS_ARROW/, r_arr, code_part)
        r_fat = "\n" mk "\n=>\n" mk "\n"; gsub(/HSS_FAT_ARROW/, r_fat, code_part)
        r_larr = "\n" mk "\n<-\n" mk "\n"; gsub(/HSS_LEFT_ARROW/, r_larr, code_part)
        r_at = "\n" mk "\n@\n" mk "\n"; gsub(/HSS_AT_SIGN/, r_at, code_part)

        gsub(/HSS_EQUALITY/, "==", code_part)
        gsub(/HSS_GTE/, ">=", code_part)
        gsub(/HSS_LTE/, "<=", code_part)
        gsub(/HSS_NEQ/, "/=", code_part)

        print code_part comment_part
    }
    ' > "$out_file"
}

# ----------------------------------------------------------------------
# 2. PÓS-PROCESSAMENTO (V10 - CORREÇÃO DE FLUXO VERTICAL)
# ----------------------------------------------------------------------
postprocess_file() {
    in_file=$1
    tr -d '\r' < "$in_file" | \
    awk -v MARKER="$MARKER" 'MARKER == $0 { next } { print }' | \
    awk -v mode="$MODE" '
        function flush_prev() {
            if (has_prev) { print prev_line; has_prev=0; prev_line=""; }
        }
        BEGIN { has_prev=0; glue_next=0 }

        function get_sep_type(s) {
            clean_s = s
            gsub(/^[ \t]+|[ \t]+$/, "", clean_s)
            
            # VERT: Quebra linha e indenta (Estilo Haskell Idiomático)
            if (clean_s == "::" || clean_s == "->" || clean_s == "=>" || clean_s == "|" || clean_s == "<-") return "VERT"
            
            # HORIZ: Cola na linha anterior
            if (clean_s == "(" || clean_s == ")" || clean_s == "," || clean_s == "@" || clean_s == "=") return "HORIZ"
            
            return "NONE"
        }

        function get_glue_char(prev, curr) {
            if (curr ~ /^[,)]/) return ""
            if (prev ~ /[(]$/) return ""
            return " "
        }

        {
            line = $0

            if (line ~ /^[ \t]*$/) next

            if (line ~ /^<<<<<<<|^=======|^>>>>>>>/) {
                flush_prev()
                print line
                glue_next = 0
                next
            }

            sep_type = get_sep_type(line)

            if (sep_type != "NONE") {
                gsub(/^[ \t]+|[ \t]+$/, "", line) 

                if (sep_type == "HORIZ") {
                    if (has_prev) {
                        glue = get_glue_char(prev_line, line)
                        prev_line = prev_line glue line
                    } else {
                        prev_line = line
                    }
                    has_prev = 1
                    glue_next = 1 
                } 
                else if (sep_type == "VERT") {
                    # Quebra a linha anterior (flush)
                    flush_prev()
                    
                    # Inicia nova linha com 4 espaços (Haskell Style)
                    prev_line = "    " line
                    has_prev = 1
                    
                    # --- CORREÇÃO CRÍTICA v10 ---
                    # glue_next = 0: NÃO cola a próxima linha aqui.
                    # Deixa o tipo ou o retorno cair para a linha de baixo (também indentado ou não).
                    # Isso evita: "-> m (Maybe a) resolveOrWarn" na mesma linha.
                    glue_next = 0 
                }
                next
            }

            if (glue_next) {
                sub(/^[ \t]+/, "", line)
                glue = get_glue_char(prev_line, line)
                prev_line = prev_line glue line
                glue_next = 0 
                next
            }

            flush_prev()
            prev_line = line
            has_prev = 1
        }
        END { flush_prev() }
    '
}

# --- EXECUÇÃO ---
preprocess_file "$BASE_FILE" "$tmp_base"
preprocess_file "$LEFT_FILE" "$tmp_left"
preprocess_file "$RIGHT_FILE" "$tmp_right"

diff3 -m "$tmp_left" "$tmp_base" "$tmp_right" > "$tmp_merged" || :

postprocess_file "$tmp_merged"