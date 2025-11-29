import csv

# Nome do seu arquivo de resultados (verifique se é este mesmo)
INPUT_FILE = "resultados_experimento.csv"

def analyze():
    # Contadores
    total_conflicts_diff3 = 0
    total_conflicts_csdiff = 0
    
    files_with_conflict_diff3 = 0
    files_with_conflict_csdiff = 0
    
    # Casos de Sucesso (Diff3 tinha conflito, CSDiff zerou)
    fully_solved_scenarios = 0
    
    # Casos de Falso Negativo Potencial (CSDiff zerou, mas diferente do manual)
    # Requer que as colunas de comparação existam no CSV
    potential_false_negatives = 0

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            row_count = 0
            for row in reader:
                row_count += 1
                
                # Converte para int (trata possíveis erros de conversão)
                try:
                    d3 = int(row['Diff3_Conflict'])
                    cs = int(row['CSDiff_Conflict'])
                except ValueError:
                    continue # Pula linhas com erro de formatação

                # 1. Soma Total de Conflitos (QP1)
                total_conflicts_diff3 += d3
                total_conflicts_csdiff += cs
                
                # 2. Arquivos com Conflitos (QP2)
                if d3 > 0: files_with_conflict_diff3 += 1
                if cs > 0: files_with_conflict_csdiff += 1
                
                # 3. Cenários Resolvidos (QP2 / QP3)
                if d3 > 0 and cs == 0:
                    fully_solved_scenarios += 1
                
                # 4. Checagem de Falso Negativo (QP4)
                # Verifica se as colunas de comparação existem
                if 'CSDiff_Equals_Manual' in row:
                    eq_manual = row['CSDiff_Equals_Manual'] == 'True'
                    if d3 > 0 and cs == 0 and not eq_manual:
                        potential_false_negatives += 1

        # Cálculos de Variação
        var_conflicts = ((total_conflicts_csdiff - total_conflicts_diff3) / total_conflicts_diff3) * 100 if total_conflicts_diff3 > 0 else 0
        var_files = ((files_with_conflict_csdiff - files_with_conflict_diff3) / files_with_conflict_diff3) * 100 if files_with_conflict_diff3 > 0 else 0

        print("-" * 40)
        print(f"ANÁLISE DE {row_count} CENÁRIOS DE MERGE")
        print("-" * 40)
        print(f"1. Total de Conflitos (Blocos):")
        print(f"   Diff3:        {total_conflicts_diff3}")
        print(f"   Haskell-Sep:  {total_conflicts_csdiff}")
        print(f"   Variação:     {var_conflicts:+.2f}%")
        print("-" * 40)
        print(f"2. Arquivos com Conflitos (Cenários Pendentes):")
        print(f"   Diff3:        {files_with_conflict_diff3}")
        print(f"   Haskell-Sep:  {files_with_conflict_csdiff}")
        print(f"   Variação:     {var_files:+.2f}%")
        print("-" * 40)
        print(f"3. Sucessos Totais (Redução a 0): {fully_solved_scenarios}")
        print(f"4. Falsos Negativos (Alerta):     {potential_false_negatives}")
        print("-" * 40)

    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")

if __name__ == "__main__":
    analyze()