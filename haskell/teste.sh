#!/bin/bash

# Script para gerar casos de teste para csdiff-hs-merge.sh
# Inclui teste da flag --simple

MERGE_SCRIPT="./csdiff-hs-merge.sh"

if [ ! -x "$MERGE_SCRIPT" ]; then
    echo "Erro: $MERGE_SCRIPT não encontrado ou não é executável."
    echo "Execute: chmod +x csdiff-hs-merge.sh"
    exit 1
fi

echo "=== Gerando Cenários de Teste (Com suporte a --simple) ==="

# ---------------------------------------------------------
# Cenário 4: Data Types (Testando '|') - Modo FULL
# ---------------------------------------------------------
echo "-> Cenário 4: Data Types (|) [Modo Padrão]"
echo "data Cor = Azul | Verde | Amarelo" > base4.hs
echo "data Cor = Azul | VerdeEscuro | Amarelo" > left4.hs
echo "data Cor = Azul | Verde | AmareloClaro" > right4.hs

$MERGE_SCRIPT base4.hs left4.hs right4.hs > merge4.hs
echo "   Resultado (Esperado: Merge feito nos campos):"
cat merge4.hs
echo ""

# ---------------------------------------------------------
# Cenário 5: Tuplas (Testando ',') - Modo FULL
# ---------------------------------------------------------
echo "-> Cenário 5: Tuplas (,) [Modo Padrão]"
echo "ponto = (10, 20, 30)" > base5.hs
echo "ponto = (15, 20, 30)" > left5.hs
echo "ponto = (10, 20, 35)" > right5.hs

$MERGE_SCRIPT base5.hs left5.hs right5.hs > merge5.hs
echo "   Resultado (Esperado: (15, 20, 35)):"
cat merge5.hs
echo ""

# ---------------------------------------------------------
# Cenário 6: Atribuição (Testando '=') - Modo FULL
# ---------------------------------------------------------
echo "-> Cenário 6: Atribuição (=) [Modo Padrão]"
echo "valorMax = 100" > base6.hs
echo "limite = 100" > left6.hs
echo "valorMax = 200" > right6.hs

$MERGE_SCRIPT base6.hs left6.hs right6.hs > merge6.hs
echo "   Resultado (Esperado: limite = 200):"
cat merge6.hs
echo ""

# ---------------------------------------------------------
# Cenário 7: Teste da flag --simple
# Situação: Alterações na mesma linha em uma tupla.
# Com --simple, ',' NÃO é um separador, então o diff3 verá a linha inteira mudada
# e provavelmente causará conflito (comportamento esperado do modo simples).
# ---------------------------------------------------------
echo "-> Cenário 7: Teste da flag --simple (Ignorando vírgulas)"
echo "   Usando arquivos do Cenário 5 (Tuplas)"

# Executa com a flag --simple
$MERGE_SCRIPT --simple base5.hs left5.hs right5.hs > merge7_simple.hs

echo "   Resultado com --simple:"
cat merge7_simple.hs
echo ""
echo "   [NOTA]: Se aparecerem marcadores de conflito (<<<<<<<), o teste passou."
echo "           Isso confirma que o script NÃO usou as vírgulas para separar as mudanças."

echo "=== Testes Concluídos ==="