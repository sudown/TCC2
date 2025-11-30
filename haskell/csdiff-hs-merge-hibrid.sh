#!/usr/bin/env bash
#
# csdiff-hs-merge-final.sh
#
# A VERSÃO DEFINITIVA.
# Combina a proteção de tokens da v12 com a lógica de reconstrução horizontal da v3.
# Garante a maior taxa de sucesso de compilação (ParseOK).
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
# 1. PRÉ-PROCESSAMENTO (PROTEGIDO - v12)
# Mantemos este porque evita bugs como "||" virar "| |" ou "=>" virar "= >"
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
        gsub(/\|\|/, "HSS_LOGICAL_OR", code_part)
        gsub(/&&/,   "HSS_LOGICAL_AND", code_part)

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
        gsub(/HSS_LOGICAL_OR/, "||", code_part)
        gsub(/HSS_LOGICAL_AND/, "&&", code_part)

        print code_part comment_part
    }
    ' > "$out_file"
}

# ----------------------------------------------------------------------
# 2. PÓS-PROCESSAMENTO (SIMPLES E ROBUSTO - v3/Recuperada)
# Essa lógica "achata" o código, garantindo que ele compile.
# ----------------------------------------------------------------------
postprocess_file() {
    in_file=$1
    tr -d '\r' < "$in_file" | \
    awk -v MARKER="$MARKER" 'MARKER == $0 { next } { print }' | \
    awk -v mode="$MODE" '
        function flush_prev() {
            if (has_prev) { print prev_line; has_prev=0; prev_line=""; }
        }
        BEGIN { has_prev=0; sep_pending=0; sep="" }

        function is_separator_line(s) {
            # Limpa espaços para verificar
            clean_s = s
            gsub(/^[ \t]+|[ \t]+$/, "", clean_s)
            
            if (clean_s == "::" || clean_s == "->" || clean_s == "=>" || clean_s == "<-" || clean_s == "@") return 1
            if (mode == "FULL") {
                if (clean_s == "=" || clean_s == "|" || clean_s == "," || clean_s == "(" || clean_s == ")") return 1
            }
            return 0
        }

        {
            line = $0

            # Ignora linhas em branco do diff3
            if (line ~ /^[ \t]*$/) next

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
                    # COLA O SEPARADOR E A LINHA ATUAL NA ANTERIOR
                    # Remove indentação excessiva da linha atual para colar bonito
                    sub(/^[ \t]+/, "", line)
                    # Remove espaços do separador também
                    gsub(/^[ \t]+|[ \t]+$/, "", sep)
                    
                    prev_line = prev_line " " sep " " line
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
                if (has_prev) { prev_line = prev_line " " sep } 
                else { prev_line = sep; has_prev = 1 }
            }
            flush_prev()
        }
    '
}

# --- EXECUÇÃO ---
preprocess_file "$BASE_FILE" "$tmp_base"
preprocess_file "$LEFT_FILE" "$tmp_left"
preprocess_file "$RIGHT_FILE" "$tmp_right"

diff3 -m "$tmp_left" "$tmp_base" "$tmp_right" > "$tmp_merged" || :

postprocess_file "$tmp_merged"