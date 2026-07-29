# Auditoria Global — Regras por Modalidade

**Data:** 2025-07-25  
**Escopo:** `D:\Loterias\LoteriasPosicao` (apps por modalidade + `_shared`)  
**Objetivo:** garantir que limites oficiais (universo, marcação, sorteadas, extras, preços) venham de configuração centralizada, sem hardcodes de uma modalidade “vazando” para outra.

---

## 1. Resumo da auditoria

Foi feita uma revisão técnica transversal dos parâmetros de negócio das loterias (universo, quantidade sorteada, min/max de marcação, extras, preços e defaults de UI/JS).

**Conclusão:** o sistema já possui várias fontes de verdade por módulo (`modality_config`, `catalogo_oficial.json`, specs de estudos/concentração/comportamento). Foi criada a fachada unificada `_shared/configuracoes/regras_modalidade.py` (`get_regras`) e corrigidos os hardcodes críticos que geravam regras incorretas (Timemania sorteadas, Mega marcação/preços, Lotomania 00–99, UI de geradores, textos/JS ainda amarrados ao Dia de Sorte).

**Nota oficial (conferida em 26/07/2026 no site da Caixa):** na Mega-Sena, *"marque de 6 a 20 números no volante"* — [Mega-Sena | CAIXA](https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx). A Lotofácil também permite até 20, mas no universo 01–25 e com marcação mínima 15.

Smoke-test de `get_regras` para as 9 modalidades: **OK**.

| Modalidade     | Universo | Sorteadas | Marcação | Extra        |
|----------------|----------|-----------|----------|--------------|
| Dia de Sorte   | 01–31    | 7         | 7–15     | Mês          |
| Quina          | 01–80    | 5         | 5–15     | —            |
| Mega-Sena      | 01–60    | 6         | **6–20** | —            |
| Lotofácil      | 01–25    | 15        | 15–20    | —            |
| Timemania      | 01–80    | **7**     | 10–10    | Time         |
| Lotomania      | **00–99**| 20        | 50–50    | —            |
| Super Sete     | 0–9 × 7  | 7         | 7–7      | Colunas      |
| Dupla Sena     | 01–50    | 6         | 6–15     | 2 sorteios   |
| +Milionária    | 01–50    | 6         | 6–12     | Trevo        |

---

## 2. Módulos analisados

- Configuração central (`_shared/configuracoes/`)
- Geradores Elite (`_shared/geradores_elite/`)
- Concentração de acertos
- Análises inteligentes / Resultados & Padrões
- Análise por posição, estudos, somas/dígitos
- Comportamento → Apostas / panorama
- Desdobramentos e ciclos (Lotomania, Timemania)
- Conferência de apostas (Mega-Sena)
- Menus / templates compartilhados
- Registries (`analises_gerais`, specs por feature)

---

## 3. Arquivos revisados (principais)

| Área | Arquivos |
|------|----------|
| Fonte unificada | `_shared/configuracoes/regras_modalidade.py`, `catalogo_oficial.json` |
| Engine geradores | `_shared/geradores_elite/modality_config.py` |
| Comportamento | `comportamento/specs.py`, `templates/comportamento_apostas_script.html`, `static/panorama_modos.js` |
| UI geradores | `templates/geradores_elite_index.html` |
| Concentração | `concentracao_acertos/core.py`, `specs.py`, `templates/gerador_concentracao_acertos.html` |
| Inteligentes | `analise_inteligentes_diadesorte/routes_factory.py`, `templates/analises_inteligentes.html`, `static/tubular.js` |
| Desdobramento | `_shared/desdobramento_service_factory.py`, apps Lotomania/Timemania |
| Ciclo Lotomania | `AnalisePorPosicao-Lotomania-Only/services/ciclo_service.py` |
| Conferência Mega | `AnalisePorPosicao-MegaSena-Only/services/conferencia_apostas_folder_service.py` |
| Registry | `_shared/analises_gerais/registry.py` |

---

## 4. Problemas encontrados

### Críticos (corrigidos)

1. **Timemania `sorteadas=10`** em configs de geradores/comportamento/registry — oficial é **7 sorteadas** e **10 marcadas**.
2. **Mega-Sena** — inicialmente o catálogo interno estava com max 15 (dado desatualizado). **Conferido no site oficial da Caixa (26/07/2026): marcação 6 a 20**. Configs e conferência alinhadas a 6–20 com tabela de preços até 20.
3. **Lotomania ciclo** usava `range(0, TOTAL+1)` com `TOTAL=100` → incluía dezena inválida **100**.
4. **Lotomania desdobramento** com `max_dezena=100` e factory assumindo `1..max` — universo é **00–99**.
5. **Índice Geradores Elite** exibia Concentração / Dígitos Inteligente só para `diadesorte`, apesar das rotas já existirem nas demais.
6. **Textos/UI Dia de Sorte** (31−7=24, faixas 21–31, tubular `<=31`) vazavam para outras modalidades.

### Médios / dívida técnica (parcialmente tratados ou documentados)

7. **Múltiplas fontes de regras** ainda coexistindo (`config.py`, `catalogo_oficial.json`, `modality_config.py`, specs por feature). A fachada `get_regras` unifica a leitura, mas nem todos os módulos já a consomem.
8. **Defaults JS** com fallback `31` / `7` / `20` quando `UI`/`CFG` não chegam — mitigados nos pontos críticos; ainda há fallbacks defensivos.
9. **Timemania desdobramento** texto “50 dezenas” (cópia Lotomania) — corrigido para 80.
10. **Otimizador** (`universo <= 31`) usa limiar heurístico de tamanho de universo (não é regra de modalidade, mas merece revisão futura).

### Fora do escopo / intencional

- Domínio **Mês da Sorte / cores dos meses** permanece específico do Dia de Sorte.
- Apps locais com constantes próprias (ex.: `NUM_SORT_DEZ = 7` na Timemania) quando já alinhados ao oficial.

---

## 5. Correções realizadas

| # | Correção |
|---|----------|
| 1 | Timemania: `sorteadas: 7` em `modality_config`, specs de comportamento e `analises_gerais/registry` |
| 2 | Mega conferência: `MAX_DEZENAS=15` e tabela de preços só até 15 |
| 3 | Lotomania ciclo: universo estrito `0..99` |
| 4 | Factory de desdobramento: parâmetro `dezena_min`; Lotomania `0..99` |
| 5 | `geradores_elite_index.html`: Concentração e Dígitos para Quina, Mega, LF, TM, LM, Super Sete (+ DS) |
| 6 | Inteligentes: contexto Jinja com `dezena_min/max`, `sorteadas`, `nao_sairam_qtd`; tubular lê `data-*` |
| 7 | Concentração: legendas/faixas de cor dinâmicas por `dezena_min/max` |
| 8 | Comportamento/panorama: fallbacks de universo e `alvoMax` alinhados a `CFG`/`pick_max` |
| 9 | Timemania UI ciclo: texto 80 dezenas (01–80) |
| 10 | Módulo `regras_modalidade.py` como API canônica para novos códigos |

---

## 6. Regras padronizadas (fonte canônica)

Para **código novo**, usar exclusivamente:

```python
from configuracoes.regras_modalidade import get_regras, universo_range, validar_tamanho_aposta, preco_aposta

r = get_regras("megasena")
# r["dezena_min"], r["dezena_max"], r["sorteadas"], r["pick_min"], r["pick_max"], r["extra"], r["precos_map"]
```

Ordem de merge em `get_regras`:

1. `catalogo_oficial.json` — regulamento / preços / marcação  
2. `geradores_elite.modality_config.MODALITIES` — universo tipado, pick, extra, loader  
3. `configuracoes.config.MODALITIES` — porta, metadados de app  

Specs de feature (`concentracao_acertos/specs`, `analise_estudos/specs`, `comportamento/specs`, etc.) devem continuar existindo para **parâmetros de análise** (pools, janelas, indicadores), mas os limites oficiais de volante/sorteio devem espelhar `get_regras` / `modality_config`.

---

## 7. Pontos que ainda necessitam revisão

1. **Migrar consumidores legados** para `get_regras` (evitar duplicar números nos specs).
2. **Templates/JS** com fallbacks Dia de Sorte remanescentes em telas pouco usadas (export filenames `tubular_diadesorte.*`, chaves `localStorage` `*_ds`).
3. **Super Sete** e **+Milionária**: validar ponta a ponta UI de coluna/trevo em todos os geradores (domínio diferente de “dezenas planas”).
4. **Conferências** das demais modalidades (além da Mega) — auditar `MAX_DEZENAS` / tabelas de preço locais.
5. **Import/export** e parsers de texto com regex `\d{1,2}` e teto 31 em scripts isolados.
6. **Testes automatizados** por modalidade (hoje smoke manual de `get_regras`; falta suite CI).

---

## 8. Recomendações para futuras implementações

1. **Uma modalidade nova** = atualizar `catalogo_oficial.json` + `modality_config.MODALITIES` (+ entry em `config.MODALITIES`); em seguida apenas specs de feature se houver parâmetros analíticos extras.
2. **Proibir literais** de universo/marcação em PRs de feature — revisão deve citar `get_regras` ou `modality_config`.
3. **UI sempre receber `CFG`/`data-*`** do backend; JS nunca assume 31/7/15 sem fallback documentado.
4. Distinguir claramente **sorteadas** (resultado) de **pick** (marcação no volante) — caso clássico Timemania 7 vs 10.
5. Não copiar pastas Dia de Sorte literalmente; replicar via `wire_*` / `extend_*` + specs.
6. Manter Mega em **marcação máxima 20** alinhada à Caixa ([Como jogar](https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx)).

---

## 9. Evidência de consistência (`get_regras`)

Execução local (PYTHONPATH=`_shared`):

- 9 modalidades listadas e validadas  
- Asserts: Timemania sorteadas=7 / pick=10; Mega pick_max=20 e aceita 16–20; Lotomania 0–99; Lotofácil aceita 20  

---

## 11. Conferência no site oficial da Caixa (26/07/2026)

Fontes: páginas `loterias.caixa.gov.br/Paginas/*.aspx` (Como jogar / Apostas / Tabelas).

| Modalidade | Página Caixa | Oficial (resumo) | Sistema (`get_regras`) | Status |
|------------|--------------|------------------|------------------------|--------|
| Mega-Sena | [Mega-Sena](https://loterias.caixa.gov.br/Paginas/Mega-Sena.aspx) | Marque **6 a 20** / 60; aposta mín. R$ 6 | pick 6–20 | **OK** (corrigido) |
| Lotofácil | [Lotofácil](https://loterias.caixa.gov.br/Paginas/Lotofacil.aspx) | **15 a 20** / 25; mín. R$ **3,50**; 15 sorteadas | pick 15–20 | **OK** (preços atualizados p/ R$ 3,50) |
| Quina | [Quina](https://loterias.caixa.gov.br/Paginas/Quina.aspx) | **5 a 15** / 80; mín. R$ 3; 5 sorteadas | pick 5–15 | **OK** |
| Dia de Sorte | [Dia de Sorte](https://loterias.caixa.gov.br/Paginas/Dia-de-Sorte.aspx) | **7 a 15** / 31 + 1 mês; 7+mês; mín. R$ 2,50 | pick 7–15 + mês | **OK** |
| Lotomania | [Lotomania](https://loterias.caixa.gov.br/Paginas/Lotomania.aspx) | Marque **50**; 20 sorteadas; prêmios 20…15 ou 0; R$ 3 | pick 50–50; univ. 00–99 | **OK** |
| Timemania | [Timemania](https://loterias.caixa.gov.br/Paginas/Timemania.aspx) | **10** números / 80 + Time; **7** sorteadas + Time; R$ 3,50 | pick 10; sort 7 + time | **OK** |
| Dupla Sena | [Dupla Sena](https://loterias.caixa.gov.br/Paginas/Dupla-Sena.aspx) | **6 a 15** / 50; **2 sorteios**/concurso | pick 6–15 + 2 sorteios | **OK** |
| +Milionária | [+Milionária](https://loterias.caixa.gov.br/Paginas/Mais-Milionaria.aspx) | Dezenas **6–12** / 50; trevos **2–6** / 6; mín. R$ 6 | pick 6–12; trevo default 2 | **Parcial** — trevos 2–6 documentados; engines ainda usam 2 como default |
| Super Sete | [Super Sete](https://loterias.caixa.gov.br/Paginas/Super-Sete.aspx) | 7 colunas 0–9; simples = 1/coluna; **múltiplas até 21** marcas (máx. 3/coluna) | pick 7–7 (modelo simples) | **Parcial** — múltiplas documentadas no catálogo; motor ainda modela aposta simples |

**Atenção:** nos cards “Outros jogos” da Caixa ainda aparece Mega “6 a 15” — texto cruzado **desatualizado**. A página própria da Mega-Sena manda **6 a 20**; usamos a página da modalidade.

### Ajustes feitos após esta conferência
- Lotofácil: tabela de preços reajustada (base R$ 3,50 → 15=3,50 … 20=54.264).
- +Milionária: `trevo_min/max` e `trevo_pick_min/max` no catálogo/`modality_config`.
- Super Sete: campos `marcacao_multipla_max`, `por_coluna_min/max` no catálogo (sem alterar `pick_max=7` do motor, para não quebrar geradores).
