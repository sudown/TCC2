#!/usr/bin/env bash
#
# csdiff-hs-merge.sh
#
# Uso:
#   csdiff-hs-merge.sh BASE_FILE LEFT_FILE RIGHT_FILE > MERGED_FILE
#
# Implementa:
#   1) Pré-processamento com separadores Haskell (::, ->, =>, <-, @)
#   2) Merge via diff3 -m
#   3) Pós-processamento (remoção de marcadores e "rejunte" das linhas)
#
# Requisitos:
#   - bash
#   - diff3
#   - awk, sed, tr, mktemp
#
# Observação:
#   - Lida com arquivos com final de linha CRLF (Windows) ou LF (Unix).
#   - Usa um marcador único pouco provável de aparecer em código.
#

set -euo pipefail

MARKER=">>>>CSDIFF_MARK<<<<<"

usage() {
    echo "Uso: $0 BASE_FILE LEFT_FILE RIGHT_FILE" >&2
    exit 1
}

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
# Função: normalizar EOL e aplicar marcadores
############################################
preprocess_file() {
    in_file=$1
    out_file=$2

    # 1) Normaliza CRLF -> LF removendo todos os '\r'
    #    (tr é POSIX e funciona bem nesse contexto)
    # 2) Insere marcadores e quebra de linha ao redor dos separadores Haskell:
    #       ::  ->  =>  <-  @
    #
    # Regra: SEPARADOR  =>  \nMARKER\nSEPARADOR\nMARKER\n
    #
    # A ordem dos padrões é importante para evitar conflitos de substring.
    # Usamos 'g' para pegar todas as ocorrências na linha.
    tr -d '\r' < "$in_file" | \
    sed -e "s/::/\n$MARKER\n::\n$MARKER\n/g" \
        -e "s/->/\n$MARKER\n->\n$MARKER\n/g" \
        -e "s/=>/\n$MARKER\n=>\n$MARKER\n/g" \
        -e "s/<-/\n$MARKER\n<-\n$MARKER\n/g" \
        -e "s/@/\n$MARKER\n@\n$MARKER\n/g" \
    > "$out_file"
}

############################################
# Função: remover marcadores e rejuntar linhas
############################################
postprocess_file() {
    in_file=$1

    # Estratégia:
    #   1) Garante normalização de '\r' novamente (caso diff3 tenha gerado algo estranho).
    #   2) "Cola" de volta as linhas que foram separadas pelos marcadores.
    #
    # Na etapa de pré-processamento, criamos trechos do tipo:
    #   ... texto anterior ...
    #   MARKER
    #   ::
    #   MARKER
    #   ... texto seguinte ...
    #
    # O que queremos ao final é:
    #   ...texto anterior...::...texto seguinte...
    #
    # Abordagem:
    #   - Usar awk em modo "acumulador de linhas".
    #   - Sempre que encontra uma linha com o MARKER:
    #       * ignora completamente essa linha (o marcador em si some).
    #   - Caso contrário, concatena a linha atual a um buffer,
    #     adicionando um '\n' normal entre linhas que não eram separadores.
    #
    # Como os separadores (::, ->, =>, <-, @) foram transformados em linhas próprias
    # entre marcadores, basta remover as linhas MARKER e concatenar todo o resto
    # em um fluxo de texto com quebras de linha normais preservadas.
    #
    # Mas para preservar as quebras de linha originais, a estratégia é:
    #   - Quando uma linha é gerada apenas por causa da lógica de separadores,
    #     ela está sempre cercada por marcadores.
    #   - Ao remover marcadores, linhas de separadores ficam em sequência direta
    #     com as linhas antes/depois na mesma "região" do merge.
    #
    # Implementação concreta:
    #   - Remove '\r'.
    #   - Percorre com awk, usando um registrador de estado simples para
    #     definir quando "rejuntar".
    #
    # Mais simples e robusto:
    #   - Remove completamente as linhas com MARKER.
    #   - Depois, junta linhas que consistam apenas em um dos separadores
    #     (::, ->, =>, <-, @) com a linha anterior (e eventualmente com a seguinte).
    #
    # Isso evita depender da posição exata do marcador e funciona bem
    # mesmo na presença de conflitos do diff3.

    tr -d '\r' < "$in_file" | \
    awk -v MARKER="$MARKER" '
        # Primeiro passo: descarta linhas que sejam exatamente o marcador
        MARKER == $0 { next }

        {
            print
        }
    ' | \
    awk '
        # Segundo passo: rejuntar separadores (linhas que são apenas ::, ->, =>, <- ou @)
        #
        # Estratégia:
        #   - Mantemos uma linha anterior em buffer.
        #   - Quando a linha atual é um separador puro:
        #       * salvamos o separador e marcamos que a próxima linha deve ser colada.
        #   - Quando a linha anterior era um texto normal e
        #     a linha atual é um separador, não imprimimos ainda.
        #   - Quando encontramos uma linha não vazia depois de um separador,
        #     colamos: prev_line + separador + current_line.
        #
        #   - Quebras de linha reais (linhas vazias ou começo de novo bloco) são preservadas.

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

        # Detecta se a linha é apenas um dos separadores
        function is_separator_line(s) {
            return (s == "::" || s == "->" || s == "=>" || s == "<-" || s == "@")
        }

        {
            line = $0

            # Se não temos nada pendente ainda
            if (!has_prev && !sep_pending) {
                if (is_separator_line(line)) {
                    # Separador no início absoluto do arquivo: apenas guarda
                    sep = line
                    sep_pending = 1
                } else {
                    prev_line = line
                    has_prev = 1
                }
                next
            }

            # Se há um separador pendente aguardando a próxima linha
            if (sep_pending) {
                if (!has_prev) {
                    # Não havia linha anterior, então a linha final é apenas sep + line
                    prev_line = sep line
                    has_prev = 1
                } else {
                    # Cola em cima da linha anterior
                    prev_line = prev_line sep line
                }
                sep = ""
                sep_pending = 0
                next
            }

            # Aqui temos uma linha anterior em prev_line
            if (is_separator_line(line)) {
                # Guarde o separador e espere a próxima linha para colar
                sep = line
                sep_pending = 1
                next
            }

            # Caso comum: nem separador, nem nada pendente
            flush_prev()
            prev_line = line
            has_prev = 1
        }

        END {
            # Se ainda houver um separador pendente sem nada depois,
            # agregue-o à última linha ou imprima sozinho.
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
# 1) Pré-processamento
############################################
preprocess_file "$BASE_FILE" "$tmp_base"
preprocess_file "$LEFT_FILE" "$tmp_left"
preprocess_file "$RIGHT_FILE" "$tmp_right"

############################################
# 2) Merge com diff3 -m
############################################
# diff3 espera a ordem: L R B ou L B R dependendo do uso.
# Para simular merge estilo Git (base, local, remota) usando diff3 clássico,
# usa-se normalmente:
#   diff3 -m LEFT BASE RIGHT
#
# A saída é enviada para tmp_merged.
diff3 -m "$tmp_left" "$tmp_base" "$tmp_right" > "$tmp_merged" || {
    # diff3 -m retorna código de erro em caso de conflitos, mas ainda produz saída.
    # Não tratamos como erro fatal: apenas seguimos com o pós-processamento.
    :
}

############################################
# 3) Pós-processamento
############################################
postprocess_file "$tmp_merged"
