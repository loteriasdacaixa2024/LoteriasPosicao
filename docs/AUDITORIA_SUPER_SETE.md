# Auditoria Técnica — Adequação da Modalidade Super Sete

**Data:** 2026-07-26  
**Escopo:** somente leitura — nenhuma alteração de código foi feita.  
**Fonte primária:** [Super Sete — Portal Loterias CAIXA](https://loterias.caixa.gov.br/Paginas/Super-Sete.aspx)  
**Base histórica local:** `AnalisePorPosicao-SuperSete-Only/instance/supersete.db` (877 concursos).

---

## 1. Regras oficiais (Caixa) — resumo validado

Consultado o site oficial da Caixa:

| Item | Regra oficial |
|------|----------------|
| Volante | **7 colunas**, cada uma com dígitos **0–9** |
| Aposta simples | **1 número por coluna** (7 marcas) — R$ 3,00 |
| Apostas múltiplas | Até **21** marcas; 8–14 → máx. **2**/coluna; 15–21 → máx. **3**/coluna |
| Sorteio | **Um dígito por coluna** (7 prognósticos) |
| Premiação | Acertos de **3 a 7 colunas** (posição importa); 3 acertos = prêmio fixo R$ 6,00 |
| Sorteios | Seg / Qua / Sex a partir das 21h |
| Surpresinha / Teimosinha | Disponíveis (3, 6, 9 ou 12 concursos) |

**Consequências lógicas (não contraditas pelo regulamento):**

- Colunas são **independentes**.
- O **mesmo dígito pode sair em várias colunas** (ex.: `4-4-4-4-4-4-4`).
- Uma aposta simples válida pode ter **1 a 7 dígitos distintos** (nunca mais que 7).
- Apuração = comparação **coluna a coluna**, não interseção de conjuntos.

Espaço amostral do sorteio: \(10^7 = 10.000.000\) resultados possíveis (alinhado à probabilidade oficial “1 em 10.000.000” para 7 acertos na simples).

---

## 2. Evidência histórica (concursos reais no sistema)

Dos **877** concursos gravados:

| Dígitos distintos no resultado | Qtd | % |
|---|---:|---:|
| 1 | 0 | 0,00% |
| 2 | 0 | 0,00% |
| 3 | 19 | 2,17% |
| 4 | 131 | 14,94% |
| 5 | 413 | 47,09% |
| 6 | 256 | 29,19% |
| 7 | 58 | 6,61% |

- **93,4%** dos resultados oficiais têm **repetição** entre colunas (`distintos < 7`).
- **0** resultados inválidos (fora de 0–9 ou ≠ 7 colunas).
- Exemplos reais com 3 distintos: concurso **21** → `[7,8,7,9,9,8,8]`; **74** → `[4,2,2,4,8,8,4]`.
- Últimos: **877** → `[0,0,5,5,1,7,3]` (5 distintos); **874** → `[5,9,1,5,1,8,8]` (4 distintos).

Ausência histórica de 1–2 distintos **não** invalida essas apostas — são raras (\(P(\text{todos iguais}) = 10/10^7\)), mas **permitidas**.

---

## 3. O que está em conformidade

| Área | Evidência |
|------|-----------|
| Modelo `SorteioSuperSete` | Colunas C1–C7; trava “nunca ordenar”; `digitos()` posicional |
| Sync API Caixa | Grava `dezenasSorteadasOrdemSorteio` / `listaDezenas` na ordem |
| `catalogo_oficial.json` | 7×(0–9); simples 7; múltipla até 21; máx. 3/coluna |
| `modality_config` | `export_is_columns=True`, `loader=supersete_colunas` |
| Construtor SS (`construcoes_core_ss`) | 1 dígito/coluna; chave `tuple`; repetição livre |
| Conferência Construtor SS | Acertos posicionais |
| Engine Final — **geração** (`_montar_supersete`) | 1 dígito/coluna, sem unicidade global |
| Sniper / BetGenerator / Modelos locais | Geração por coluna |
| Análise por coluna | Frequência/atraso 0–9 por C1–C7 |
| Classificação intrasorte | Reconhece duplas/trincas (repetição) |
| Análise por Posição | `distinct=False` |
| Análises Gerais (grupo supersete) | Conta `len(set(cols))` como **métrica**, não como regra de validade |

---

## 4. Inconsistências encontradas (impacto)

### P1 — Crítico: Gerador Inteligente por Dígitos (motor compartilhado)

**Arquivos:**  
`_shared/geradores_elite/construtor/universes/digitos_service.py`  
`_shared/geradores_elite/construtor/universes/__init__.py`  
(rota exposta também para Super Sete)

**Problema:** gera via `combinations(elegiveis, k=7)` + `sorted(combo)`.

| Efeito | Gravidade |
|--------|-----------|
| Impede qualquer aposta com repetição | **Erro de regra** |
| Exige 7 dígitos distintos | Rejeita ~93% do padrão histórico |
| Destrói ordem de coluna | Incompatível com SS |
| Filtro `exigir_qtd_digitos` | Reforça lógica de “conjunto”, não de colunas |

**Impacto:** gerador produz apenas um subconjunto artificial (~6,6% do perfil histórico de distintos=7) e **nunca** reproduz resultados como o concurso 877.

---

### P1 — Crítico: Central de Conferências (contagem por conjunto)

**Arquivo:** `_shared/central_conferencias/folder_service.py` (`_analisar_aposta`)

Apesar de `dezenas_method: "digitos"` (lista ordenada), o fluxo faz:

```text
sorteadas = set(...)
acertos = |set(aposta) ∩ set(sorteio)|
```

**Prova com concurso real 877** `[0,0,5,5,1,7,3]`:

| Aposta | Acertos reais (coluna) | Contagem por `set` |
|--------|------------------------:|-------------------:|
| `[0,0,5,5,1,7,3]` (idêntica ao sorteio) | **7** | **5** |
| `[0,0,0,0,0,0,0]` | **2** | **1** |

Além disso, se `len(set(aposta)) < 7`, o código trata como “aposta incompleta” (`combos = []`) → **0 acertos** para sete iguais.

**Faixas incompletas** em `central_conferencias/config.py` (SS): só lista 7, 6 e 5 — faltam **4 e 3** (oficiais na Caixa).

---

### P1 — Crítico: Engine Final — conferência / backtest

**Arquivo:** `_shared/geradores_elite/engine_final_core.py` → `conferir_apostas_engine`

```text
sorteadas = set(...)
ac = svc._contar_acertos(dz, sorteadas)  # SS espera lista posicional
acertadas = set(dz) & sorteadas
```

A geração SS está correta; a **conferência** do Engine Final não.

---

### P1 — Alto: Concentração de Acertos

**Arquivos:**  
`_shared/concentracao_acertos/specs.py` (SS 0–9, pick 7)  
`SorteioSuperSete.dezenas()` → `set(self.digitos())`

Motor genérico de concentração + `dezenas()` colapsa repetidos → pool/otimização no estilo Mega-Sena.

---

### P2 — Médio: Limites de múltipla vs Caixa

| Local | Limite atual | Caixa |
|-------|-------------:|------:|
| Construtor `max_digitos_por_coluna` | **5** | **3** |
| Desdobramento (relatado na exploração) | até **4**/coluna | **3** |

O Construtor usa o teto como **pool de candidatos** (estratégia), não como volante oficial — mas o texto da UI sugere limite “por coluna” sem deixar claro que 4–5 **não** são jogáveis na lotérica sem desdobrar para ≤3.

`get_regras` / `pick_max=7` modela bem a **simples**; múltiplas oficiais (8–21) não estão no núcleo de regras consumido pelos geradores.

---

### P2 — Médio: `SorteioSuperSete.dezenas()`

Compatibilidade com motores compartilhados via `set` **quebra** SS onde for usado. Preferível: nunca alimentar motores de “conjunto” com SS, ou retornar lista posicional e criar adapters explícitos.

---

### P3 — Baixo / observação estatística

- Análise agregada “global” de dígitos (sem coluna) é útil como métrica, mas não substitui frequência **por coluna**.
- Filtros estratégicos do Sniper (`tipo_sorteio_alvo`, forçar par) **preferem** certos padrões — OK se forem opcionais e não validadores de legalidade.
- Módulo somas/dígitos: medir `qtd_digitos_distintos` está OK; **exigir** essa qtd como filtro de geração no motor de `combinations` é inadequado para SS.

---

## 5. Regras ausentes ou incompletas

1. Apuração oficial por **coluna** na Central de Conferências e no Engine Final (conferir).
2. Faixas de prêmio **3 e 4** acertos na Central.
3. Modelagem completa de **apostas múltiplas** (produto cartesiano por coluna, teto 3, tabela de preços Caixa).
4. Gerador por Dígitos **posicional** (7 pools independentes 0–9), se o produto for mantido no menu SS.
5. Validação “aposta jogável na lotérica” vs “pool de construção” (candidatos > 3/coluna).

---

## 6. Compatibilidade com concursos oficiais

| Pergunta | Resposta |
|----------|----------|
| Todos os 877 resultados cabem no modelo C1–C7 / 0–9? | **Sim** |
| Algum resultado oficial seria rejeitado pelo modelo posicional nativo? | **Não** |
| O Gerador por Dígitos (atual) poderia gerar o concurso 877? | **Não** (repetições + `combinations`) |
| A Central de Conferências acertaria 7 ao conferir o próprio resultado 877? | **Não** (contaria 5) |

---

## 7. Sugestões de melhoria (sem implementação nesta etapa)

1. **Bifurcar Super Sete** em todo motor compartilhado que usa `set` / `combinations` de dezenas.
2. Criar `contar_acertos_posicional(aposta, sorteio)` único e usá-lo em Conferências, Engine Final e Concentração.
3. Substituir ou ocultar o Gerador por Dígitos “estilo dezenas” no SS; ou reimplementar como **7 pools por coluna**.
4. Alinhar `max_digitos_por_coluna` do Construtor ao regulamento (3) **ou** rotular explicitamente como “candidatos de construção”.
5. Completar faixas 3–7 na Central.
6. Evitar `dezenas() → set` no modelo SS; expor só `digitos()`.

---

## 8. Plano de implementação priorizado (próximas etapas)

| Prioridade | Item | Impacto | Esforço |
|------------|------|---------|---------|
| **1** | Conferência posicional (Central + Engine Final) | Corrige prêmios/acertos falsos | Médio |
| **2** | Isolar/corrigir Gerador por Dígitos no SS | Apostas inválidas deixam de ser geradas | Alto |
| **3** | Concentração SS posicional + remover `dezenas()→set` | Estratégias deixam de colapsar repetidos | Alto |
| **4** | Faixas 3–4 na Central + testes com concursos reais (ex.: 21, 874, 877) | Premiação alinhada à Caixa | Baixo |
| **5** | Limites múltipla (máx. 3/coluna) e documentação UI | Conformidade volante | Baixo–médio |
| **6** | Suite de testes: sete iguais, 2–3 distintos, resultado oficial idêntico | Regressão contínua | Médio |

---

## 9. Conclusão

A base **posicional** do Super Sete (modelo, sync, análise por coluna, Construtor SS, geração Engine/Sniper) está **alinhada à Caixa**.

Os problemas graves concentram-se nos **módulos compartilhados** que ainda tratam a modalidade como **conjunto de dezenas distintas**. Isso:

- proíbe artificialmente repetições (proibidas **não** pela Caixa);
- conta acertos errados mesmo em apostas perfeitas;
- não reproduz a maioria dos resultados oficiais históricos.

## 10. Implementação (2026-07-26)

Autorizada e aplicada. Resumo:

| Item | Status |
|------|--------|
| Conferência posicional (Central + Engine Final) | Feito |
| Gerador por Dígitos SS (7 colunas, repetição livre) | Feito |
| Concentração posicional + `dezenas()` → lista | Feito |
| Faixas 3–4 na Central | Feito |
| Limite múltipla 3/coluna (Construtor + Desdobramento) | Feito |
| Testes `test_conformidade_ss.py` | TODAS OK |

Helper central: `_shared/configuracoes/acertos_posicionais.py`.
