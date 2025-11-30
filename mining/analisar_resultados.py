import csv

# --- CONFIGURAÇÃO ---
INPUT_FILE = "resultados_com_validacao_total-frank.csv"

def analyze():
    # Métricas Gerais
    total_conflicts_diff3 = 0
    total_conflicts_csdiff = 0
    files_diff3 = 0
    files_csdiff = 0
    
    # Análise de Sucesso (Casos Resolvidos)
    total_resolved = 0          # CSDiff zerou os conflitos
    resolved_syntax_ok = 0      # Zerou E compila (Sucesso Real)
    resolved_syntax_fail = 0    # Zerou MAS não compila (Erro de Layout)
    
    # Análise de Falsos Negativos (Divergência do Manual)
    divergences = 0             # Diferente do Manual
    divergences_syntax_ok = 0   # Diferente, mas compila (Provável mudança estética/semântica)
    
    # Validação do Manual (Controle de Qualidade)
    manual_broken = 0           # Quantos arquivos o próprio dev comitou quebrado

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row_count = 0
            
            for row in reader:
                row_count += 1
                try:
                    d3 = int(row['Diff3_Conflict'])
                    cs = int(row['CSDiff_Conflict'])
                except ValueError: continue

                # 1. Totais
                total_conflicts_diff3 += d3
                total_conflicts_csdiff += cs
                if d3 > 0: files_diff3 += 1
                if cs > 0: files_csdiff += 1
                
                # Leitura de Booleanos
                eq_manual = row['CSDiff_Equals_Manual'] == 'True'
                cs_parse = row['CSDiff_ParseOK'] == 'True'
                manual_parse = row.get('Manual_ParseOK', 'True') == 'True'

                if not manual_parse:
                    manual_broken += 1

                # 2. Análise de Sucessos (Diff3 falhou, CSDiff resolveu)
                if d3 > 0 and cs == 0:
                    total_resolved += 1
                    if cs_parse:
                        resolved_syntax_ok += 1
                    else:
                        resolved_syntax_fail += 1
                
                # 3. Análise de Falsos Negativos (Resolveu, mas diferente do manual)
                if d3 > 0 and cs == 0 and not eq_manual:
                    divergences += 1
                    if cs_parse:
                        divergences_syntax_ok += 1

        # Cálculos de Porcentagem
        var_conflicts = ((total_conflicts_csdiff - total_conflicts_diff3) / total_conflicts_diff3) * 100 if total_conflicts_diff3 else 0
        var_files = ((files_csdiff - files_diff3) / files_diff3) * 100 if files_diff3 else 0
        syntax_success_rate = (resolved_syntax_ok / total_resolved * 100) if total_resolved else 0

        print("=" * 60)
        print(f"RELATÓRIO FINAL (Versão hibrida --full) - {row_count} cenários")
        print("=" * 60)
        
        print(f"QP1 - GRANULARIDADE:")
        print(f"  Conflitos Diff3:       {total_conflicts_diff3}")
        print(f"  Conflitos HsSepMerge:  {total_conflicts_csdiff}")
        print(f"  Variação:              {var_conflicts:+.2f}%")
        print("-" * 60)
        
        print(f"QP2 - EFICÁCIA (Arquivos Pendentes):")
        print(f"  Arquivos Diff3:        {files_diff3}")
        print(f"  Arquivos HsSepMerge:   {files_csdiff}")
        print(f"  Variação:              {var_files:+.2f}%")
        print("-" * 60)
        
        print(f"QP3 - SUCESSO DE RESOLUÇÃO (0 Conflitos):")
        print(f"  Total Resolvido:       {total_resolved}")
        print(f"  ✅ Sintaxe Válida:      {resolved_syntax_ok} ({syntax_success_rate:.1f}%)")
        print(f"  ❌ Erro de Sintaxe:     {resolved_syntax_fail}")
        print("-" * 60)
        
        print(f"QP4 - ALERTAS DE FALSO NEGATIVO (Divergência):")
        print(f"  Total Divergente:      {divergences}")
        print(f"  ↳ Desses, compilam:    {divergences_syntax_ok}")
        print("-" * 60)
        
        print(f"CONTROLE:")
        print(f"  Manuais Quebrados:     {manual_broken}")
        print("=" * 60)

    except FileNotFoundError:
        print(f"Erro: Arquivo '{INPUT_FILE}' não encontrado.")

if __name__ == "__main__":
    analyze()