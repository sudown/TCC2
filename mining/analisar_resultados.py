import csv
import pandas as pd

# --- CONFIGURAÇÃO ---
CSV_FILE = "resultados_com_validacao_total.csv"

def analyze():
    try:
        # Carrega os dados
        df = pd.read_csv(CSV_FILE)
        
        # Total de arquivos analisados (onde houve algum conflito em alguma ferramenta)
        total_arquivos = len(df)
        
        # 1. Contagem de Conflitos (Falsos Positivos)
        arquivos_com_conflito_diff3 = len(df[df['Diff3_Conflict'] > 0])
        arquivos_com_conflito_csdiff = len(df[df['CSDiff_Conflict'] > 0])
        
        # Casos onde o diff3 falhou, mas a nossa ferramenta resolveu 100% (Falsos Positivos Eliminados)
        resolvidos_pelo_csdiff = df[(df['Diff3_Conflict'] > 0) & (df['CSDiff_Conflict'] == 0)]
        total_resolvidos = len(resolvidos_pelo_csdiff)
        
        # 2. Análise de Sintaxe (A grande vitória da "Reversão Matemática")
        # Dentre os que a ferramenta resolveu sozinha, quantos compilaram perfeitamente?
        sucesso_sintatico = len(resolvidos_pelo_csdiff[resolvidos_pelo_csdiff['CSDiff_ParseOK'] == True])
        
        taxa_sucesso = (sucesso_sintatico / total_resolvidos * 100) if total_resolvidos > 0 else 0
        
        # 3. Comparação com o Desenvolvedor Humano
        iguais_ao_manual = len(resolvidos_pelo_csdiff[resolvidos_pelo_csdiff['CSDiff_Equals_Manual'] == True])

        # --- EXIBIÇÃO DOS RESULTADOS ---
        print("="*50)
        print(" 📊 RESULTADOS DA ANÁLISE: HASKELL-SEPMERGE")
        print("="*50)
        print(f"Total de arquivos analisados: {total_arquivos}")
        print("-" * 50)
        print("📌 RESOLUÇÃO DE CONFLITOS (Redução de Falsos Positivos):")
        print(f"  -> Arquivos com conflito no Diff3 nativo:  {arquivos_com_conflito_diff3}")
        print(f"  -> Arquivos com conflito no Haskell-Sep:   {arquivos_com_conflito_csdiff}")
        print(f"  ✅ Conflitos totalmente resolvidos:        {total_resolvidos} arquivos")
        print("-" * 50)
        print("🛠️  VALIDAÇÃO SINTÁTICA (Regra de Layout):")
        print(f"  -> Dos {total_resolvidos} arquivos resolvidos automaticamente:")
        print(f"  ✅ Compilaram com sucesso no GHC (ParseOK): {sucesso_sintatico} ({taxa_sucesso:.1f}%)")
        print(f"  🤝 Ficaram idênticos ao merge manual:       {iguais_ao_manual}")
        print("="*50)

        # 4. (Opcional) Exportar os casos de sucesso para inspecionar no VS Code
        if total_resolvidos > 0:
            resolvidos_pelo_csdiff.to_csv("casos_sucesso_absoluto.csv", index=False)
            print("\n💡 Dica: Os arquivos que a ferramenta resolveu com sucesso foram salvos em 'casos_sucesso_absoluto.csv'")

    except FileNotFoundError:
        print(f"[ERRO] Arquivo '{CSV_FILE}' não encontrado. Execute o orquestrador primeiro.")
    except Exception as e:
        print(f"[ERRO] Ocorreu um problema ao analisar os dados: {e}")

if __name__ == "__main__":
    analyze()