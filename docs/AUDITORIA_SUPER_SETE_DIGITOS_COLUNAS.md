# Auditoria Super Sete — Colunas × Dígitos 0–9 (sem dezenas)

**Data:** 2026-07-26  
**Fonte oficial:** [Super Sete — CAIXA](https://loterias.caixa.gov.br/Paginas/Super-Sete.aspx)  
**Evidência local:** concurso **877** = `0 | 0 | 5 | 5 | 1 | 7 | 3` (459/877 concursos contêm o dígito 0).

> Nota: o exemplo `1|2|5|5|1|7|3` do enunciado **não** corresponde ao 877 oficial na Caixa/banco; o oficial é o acima (com zeros).

---

## 1. Modelo oficial (validado)

| Item | Regra Caixa |
|------|-------------|
| Estrutura | **7 colunas** independentes |
| Por coluna | dígitos **0–9** (um na simples) |
| Resultado | 1 dígito/coluna; **repetição livre** |
| Aposta simples | 7 marcações (1/coluna) |
| Múltipla 8–14 | 1–2 por coluna |
| Múltipla 15–21 | 2–3 por coluna (máx. 21) |
| Premiação | acertos **por coluna** (3 a 7) |

**Não são dezenas:** nunca `01`…`09`, nem universo 01–60/80.

---

## 2. Inconsistências encontradas

### P1 — UI do Gerador por Dígitos formatava como dezena (causa do “0 some”)

**Arquivo:** `_shared/geradores_elite/static/construtor_digitos.js`  
`fmtDez(n) = String(n).padStart(2,'0')` → dígito **0** virava **`00`**, **5** virava **`05`**.

Impacto:
- Apostas geradas exibidas como dezenas;
- Usuário interpreta que o 0 “não existe” / não é o dígito da Caixa;
- Textos e labels falavam em “dezenas” / exemplos `09, 22, 34`.

### P2 — Textos de interface inadequados para SS

- Label “Dezenas / aposta”
- Hint “formam as dezenas (ex.: 09, 22, 34)”
- Select “7 dezenas”

### P3 — `digitos_da_dezena` com pad genérico

Com `pad_width=2`, valor `5` → `"05"` → dígitos `{0,5}` (infla o 0).  
SS usa `pad_width=1` nas specs; reforço defensivo aplicado.

### Já em conformidade (após plano anterior)

- Modelo C1–C7; `digitos()`; conferência posicional
- Gerador SS posicional (repetição livre, pool `{4}` → sete 4s)
- Concentração posicional; faixas 3–7; máx. 3/coluna
- Análise por posição `pad=1`, `distinct=False`
- Export Engine `export_is_columns` (sem zero à esquerda)

---

## 3. Correções aplicadas nesta revisão

1. `fmtDez` / labels JS respeitam `pad_width` + `positional` (SS → `"0"`, não `"00"`).
2. Template do gerador: textos de **colunas** e menção explícita ao dígito **0** (ex.: 877).
3. `digitos_da_dezena`: se `pad_width<=1`, retorna `[int(n)]`.
4. `_fmt_dezena` (Engine) e `fmtDezenas` (Análise Somas) alinhados ao pad da modalidade.
5. `ui_config` SS: `pad_width`, `export_is_columns`, `unidade_* = colunas`.
6. Cache JS `?v=12`.

---

## 4. Validações ainda recomendadas (próximas)

| Prioridade | Item |
|------------|------|
| Média | Validação formal de **apostas múltiplas** (8–21) em desdobramento/conversor |
| Baixa | Renomear campos internos `dezenas` → `digitos`/`colunas` em payloads SS (quebraria APIs; opcional) |
| Baixa | Revisar templates locais SS (`draw-dezenas-*` CSS) para nomenclatura “colunas” |

---

## 5. Como validar agora

1. Reiniciar Super Sete e hard-refresh no Gerador por Dígitos.
2. Pool com **0** marcado → gerar → deve aparecer `0` (não `00`) nas colunas.
3. Conferir aposta `0 0 5 5 1 7 3` no concurso **877** → **7 acertos**.
