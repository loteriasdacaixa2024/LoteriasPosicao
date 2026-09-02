# Auditoria Completa — Gerador por Dígitos (pool 0–9)

**Data:** 2026-07-26  
**Foco:** lógica do pool de dígitos (0–9), filtros, algoritmo e mensagem de erro — **não** regras oficiais de modalidade.  
**Arquitetura:** motor único compartilhado em `_shared/geradores_elite/construtor/universes/`.

---

## 1. Diagnóstico completo

### Conclusão

A mensagem antiga:

> *"Não foi possível montar apostas com os filtros atuais."*

aparecia quando o motor **esgotava tentativas aleatórias** sem montar apostas. Em grande parte dos casos (incluindo a evidência Lotofácil: pool `{0,1,2,5,6,7}` + exigir **9** dígitos), o bloqueio era **matematicamente correto**: sob a regra estrita, a aposta só usa dígitos do pool, logo **nunca** pode ter mais dígitos distintos do que o tamanho do pool.

O problema não era o pool 0–9 estar errado, nem modalidade divergente: era **falta de diagnóstico** (mensagem genérica) e, em espaços pequenos, risco de **falso negativo** na busca aleatória.

### Causa da mensagem genérica

| Camada | Antes | Depois |
|--------|-------|--------|
| Filtros impossíveis | Busca falhava → frase genérica | `diagnosticar_filtros_digitos` bloqueia antes, com código/motivo/sugestões |
| Espaço C(n,k) ≤ 5000 | Amostragem aleatória | Enumeração + filtro (elimina falso negativo) |
| Busca grande esgotada | Frase genérica | Mensagem nomeando filtro (`exigir_qtd_digitos` / pool) |

A string genérica **não existe mais no código de runtime** (apenas citada neste relatório).

---

## 2. Pool de dígitos (0–9) — todas as modalidades

| Verificação | Resultado |
|-------------|-----------|
| Universo canônico | `DIGITOS_UNIVERSO = (0,1,2,3,4,5,6,7,8,9)` |
| Normalização | Aceita só 0–9; remove duplicatas; ordena |
| UI (volante) | Sempre renderiza `d = 0..9` (`construtor_digitos.js`) |
| Motor | Um único `ConstrutorDigitosService` para todas as keys |
| Dígito ignorado/duplicado por bug | Não encontrado |
| Modalidade com pool diferente | Nenhuma — só muda o **universo de dezenas** (1–25, 1–60, etc.) derivado do pool |

Specs usam o mesmo pool de dígitos; o que muda é `dezena_min`/`universo`/`pick_*`/`dezena_fmt_width` (Super Sete: width=1).

---

## 3. Modalidades analisadas

| Modalidade | key | Mesmo motor? | Pool 0–9? |
|------------|-----|--------------|-----------|
| Lotofácil | `lotofacil` | Sim | Sim |
| Dia de Sorte | `diadesorte` | Sim | Sim |
| Quina / Quina de São João | `quina` | Sim | Sim |
| Mega-Sena / Mega da Virada | `megasena` | Sim | Sim |
| Timemania | `timemania` | Sim | Sim |
| Lotomania | `lotomania` | Sim | Sim |
| Super Sete | `supersete` | Sim | Sim |
| Dupla Sena | `duplasena` | Sim | Sim |
| +Milionária | `maismilionaria` | Sim | Sim |

Não há implementação paralela do gerador por modalidade.

---

## 4. Filtros e conflitos tipificados

Códigos de diagnóstico:

| Código | Significado |
|--------|-------------|
| `pool_vazio` | Nenhum dígito 0–9 selecionado |
| `elegiveis_insuficientes` | Dezenas elegíveis &lt; dezenas/aposta |
| `exigir_maior_que_pool` | Exigir N &gt; tamanho do pool (caso da evidência) |
| `exigir_maior_que_capacidade` | N acima do teto teórico k×pad |
| `exigir_sem_combinacao` | Nenhuma C(n,k) tem exatamente N dígitos |
| `busca_esgotada` | Espaço grande; amostragem não achou (mensagem específica) |
| `validacao_global` | Apostas montadas, todas rejeitadas pelo validador global |

---

## 5. Algoritmo — melhorias desta auditoria

1. **Validação preventiva** antes de gerar.  
2. Se `C(n,k) ≤ 5000` → **enumera** combinações, aplica `exigir_qtd_digitos`, ordena por score — sem falso negativo.  
3. Se espaço maior → amostragem ponderada (como antes), com erro nomeado se falhar.  
4. UI: select «Exigir qtd dígitos» lista só 1…\|pool\| (sem opções cinza 7–10).

---

## 6. Inconsistências encontradas

| Item | Status |
|------|--------|
| Mensagem genérica | **Corrigida** (removida do runtime) |
| Falso negativo em espaços pequenos | **Corrigido** (enumeração) |
| Pool ≠ 0–9 em alguma modalidade | **Não** |
| Código duplicado por modalidade | **Não** (motor único) |
| Super Sete: exigir ≠ 7 com pick 7 | Comportamento esperado (`exigir_sem_combinacao` / validação) — diagnosticado |

---

## 7. Arquivos modificados (ciclo desta auditoria + anterior)

1. `_shared/geradores_elite/construtor/universes/__init__.py` — `DIGITOS_UNIVERSO`, `diagnosticar_filtros_digitos`  
2. `_shared/geradores_elite/construtor/universes/digitos_service.py` — gerar com diagnóstico + enumeração  
3. `_shared/geradores_elite/routes_factory.py` — `POST .../digitos/diagnosticar`  
4. `_shared/geradores_elite/static/construtor_digitos.js` — UI preventiva / select dinâmico  
5. `_shared/geradores_elite/templates/gerador_digitos_inteligente.html`  
6. `_shared/geradores_elite/templates/construtor_construcoes.html` (`?v=5`)  
7. `docs/AUDITORIA_GERADOR_DIGITOS.md` (este relatório)

---

## 8. Testes realizados (evidências)

### Helpers
- `DIGITOS_UNIVERSO == 0..9`
- Normalização remove fora de faixa e duplicatas
- Evidência Lotofácil → `exigir_maior_que_pool`
- Frase genérica antiga **ausente** nas respostas

### Por modalidade (gerar)

| Modalidade | 1 dígito | pool6+exig9 | pool 0–9 | Restritivo |
|------------|----------|-------------|----------|------------|
| Lotofácil | FAIL `elegiveis_insuficientes` | FAIL `exigir_maior_que_pool` | OK n=3 | FAIL `exigir_sem_combinacao`* |
| Dia de Sorte | FAIL elegíveis | FAIL exigir>pool | OK n=3 | OK n=2 |
| Quina | idem | idem | OK | OK |
| Mega-Sena | idem | idem | OK | OK |
| Timemania | idem | idem | OK | OK |
| Lotomania | FAIL elegíveis | FAIL elegíveis (50 dez.) | OK n=3 | FAIL elegíveis (pool curto) |
| Super Sete | FAIL elegíveis | FAIL elegíveis (6&lt;7) | OK | validação global** |
| Dupla Sena | FAIL elegíveis | FAIL exigir>pool | OK | OK |
| +Milionária | FAIL elegíveis | FAIL exigir>pool | OK | OK |

\* Lotofácil com pool 0–5 e exigir 4: nenhuma combinação de 15 dezenas tem exatamente 4 dígitos — diagnóstico correto.  
\*\* Super Sete: motor monta; validador global pode rejeitar o lote (mensagem `validacao_global`).

---

## 9. Confirmação final

- Todas as modalidades usam o **mesmo** pool 0–9 e o **mesmo** motor.  
- A mensagem genérica era **incompleta**, não um bug de regra de modalidade.  
- Conflitos de filtros agora são **preventivos** e **explicados**.  
- Regras específicas de cada loteria (pick/universo) **não foram alteradas**.  
- Recarregar a UI com `construtor_digitos.js?v=5` após reiniciar o app.
