# Auditoria — Impressão / Exportação (Gerador por Concentração)

**Data:** 2026-07-26  
**Evidência de origem:** Lotofácil (`localhost:5152`) — alerta `Falha: Failed to fetch`, console `POST .../api/concentracao/gerar` → 500 / `ERR_CONNECTION_REFUSED`, botão **Exportar TXT** desabilitado.  
**Referência de comportamento:** Dia de Sorte (módulo compartilhado `_shared/concentracao_acertos`).

---

## 1. Resumo executivo

O problema observado **não era um defeito isolado de CSS/HTML de impressão**. O fluxo de exportação depende de apostas geradas com sucesso; a API de geração da Lotofácil quebrava com **500**, o `fetch` falhava e o botão **Exportar TXT** permanecia desabilitado.

**Causa raiz (Lotofácil):** `ConcentracaoAcertosService._analise_geral()` chamava `AnaliseLotofacilService.analise_geral()`, método **inexistente** na Lotofácil (presente no Dia de Sorte e nas demais modalidades). Isso gerava exceção não tratada → HTTP 500 → `Failed to fetch`.

**Defeito transversal (todas as modalidades do módulo):** o botão **Exportar TXT** existia no template compartilhado, mas **não havia handler JavaScript** — mesmo após geração bem-sucedida (como no Dia de Sorte), o export nunca era habilitado nem baixava arquivo.

Correções aplicadas no núcleo compartilhado + `analise_geral` na Lotofácil; validação smoke por modalidade com pools realistas.

---

## 2. Modalidades analisadas

| Modalidade   | Módulo concentração | Porta típica | Analisada |
|--------------|---------------------|--------------|-----------|
| Dia de Sorte | Sim (referência)    | 5153         | Sim       |
| Lotofácil    | Sim (evidência)     | 5152         | Sim       |
| Quina        | Sim                 | 5155         | Sim       |
| Mega-Sena    | Sim                 | 5156         | Sim       |
| Timemania    | Sim                 | 5159         | Sim       |
| Lotomania    | Sim                 | 5154         | Sim       |
| Super Sete   | Sim                 | 5160         | Sim       |
| Dupla Sena   | Não cadastrado      | 5158         | Fora do escopo do módulo |
| +Milionária  | Não cadastrado      | 5157         | Fora do escopo do módulo |

Arquitetura: um único template/serviço (`_shared/concentracao_acertos`) parametrizado por `specs.py`.

---

## 3. Problemas encontrados

### P1 — Crítico (Lotofácil): 500 em `/api/concentracao/gerar`
- **Causa:** ausência de `AnaliseLotofacilService.analise_geral()`.
- **Efeito:** geração falha → export inacessível → alerta `Failed to fetch`.
- **Por que Dia de Sorte não falhava:** `AnaliseDiaDeSorteService.analise_geral()` já existia.

### P2 — Transversal: Exportar TXT sem wiring
- Template tinha o botão; JS não guardava apostas, não habilitava o botão e não fazia download.
- Afetava **todas** as modalidades do módulo, inclusive Dia de Sorte (gerar podia funcionar; export não).

### P3 — Preventivo (Timemania): classe de análise incorreta
- Spec apontava `AnaliseTimemaniaService`; classe real: `AnaliseTimemaniaSService`.

### P4 — Preventivo (Super Sete): quantidade fixa 10 no construtor
- `gerar_construcao` exigia sempre 10 apostas (`QTD_APOSTAS_FIXA`), ignorando a quantidade pedida.
- Estratégia A (pool 7 → C(7,7)=1) falhava sempre com quantidade padrão 10.

### P5 — UX: geração “sucesso” com 0 apostas após validação global
- Validador podia rejeitar 100% e ainda assim retornar `sucesso: true` com lista vazia → Exportar continuava inútil.

---

## 4. Correções realizadas

| # | Correção | Escopo |
|---|----------|--------|
| 1 | Implementar `analise_geral()` na Lotofácil (padrão Dia de Sorte: freq/atraso 01–25) | Lotofácil |
| 2 | `_analise_geral` tolerante; `_pool_resolvido` só consulta análise se pool não vier do cliente | Compartilhado |
| 3 | Corrigir `analise_class` Timemania → `AnaliseTimemaniaSService` | Specs |
| 4 | Rota `/api/concentracao/gerar`: capturar `Exception` → JSON 500 legível | Compartilhado |
| 5 | Wiring completo de **Exportar TXT** (estado, enable, download, limpar, mês DS) | Template compartilhado |
| 6 | `gerar_construcao` / `validar_estrategia` aceitam `quantidade` (default 10) | Construtor compartilhado |
| 7 | Concentração repassa `quantidade` ao construtor | Core concentração |
| 8 | Super Sete: quantidade padrão da gestão = 1 (Est. A) | Specs |
| 9 | Se validação zerar apostas → `sucesso: false` com mensagem clara | Serviço |

---

## 5. Arquivos modificados

1. `AnalisePorPosicao-Lotofacil-Only/services/analise_lotofacil_service.py`  
2. `_shared/concentracao_acertos/service.py`  
3. `_shared/concentracao_acertos/specs.py`  
4. `_shared/concentracao_acertos/routes_factory.py`  
5. `_shared/concentracao_acertos/templates/gerador_concentracao_acertos.html`  
6. `_shared/concentracao_acertos/core.py`  
7. `_shared/geradores_elite/construtor/construcoes_core.py`  
8. `docs/AUDITORIA_IMPRESSAO_CONCENTRACAO.md` (este relatório)

---

## 6. Justificativa técnica (por alteração)

1. **`analise_geral` Lotofácil** — Alinha o contrato esperado pelo serviço compartilhado ao padrão do Dia de Sorte; elimina o AttributeError/500.  
2. **`_analise_geral` / `_pool_resolvido`** — Com pool enviado pela UI (caso típico), evita dependência desnecessária da análise; falhas de análise não derrubam a geração.  
3. **Timemania class** — Corrige import dinâmico; sem isso Timemania quebraria ao sugerir pool sem seleção manual.  
4. **JSON 500 na rota** — Evita resposta HTML opaca que vira `Failed to fetch` no cliente.  
5. **Export JS** — Replica o padrão dos outros geradores (`gerador_por_posicao`, engine final): uma linha por aposta; Dia de Sorte inclui abreviação do mês.  
6–7. **`quantidade` no construtor** — Preserva default 10 para o Construtor de Construções; concentração passa a quantidade real (necessário no Super Sete).  
8. **Default Super Sete = 1** — Combina com o limite combinatório da Est. A.  
9. **Falha explícita se 0 válidas** — Impede falso sucesso e export “morto”.

---

## 7. Evidências de validação

Smoke test (processo isolado por modalidade, `ConcentracaoAcertosService.gerar` + formatação de linhas TXT):

| Modalidade   | `analise_geral` | Gerar (pool realista / qtd padrão) | Export (linhas TXT) | Notas |
|--------------|-----------------|------------------------------------|---------------------|-------|
| Dia de Sorte | OK              | OK (ex.: n=7–10)                   | OK (+ mês)          | Referência |
| Lotofácil    | OK (novo)       | OK com pool sugerido por freq      | OK                  | Pool 1–18 consecutivo pode ser 100% rejeitado pela validação global (comportamento do validador, não do print) |
| Quina        | OK              | OK                                 | OK                  | — |
| Mega-Sena    | OK              | OK                                 | OK                  | — |
| Timemania    | OK (class fix)  | OK                                 | OK                  | — |
| Lotomania    | OK              | OK                                 | OK                  | — |
| Super Sete   | OK              | OK (Est. A qtd=1; B/C com pool análise) | OK             | Default qtd ajustado |

**Padronização com Dia de Sorte:** mesmo template, mesmo serviço, mesmo fluxo gerar → habilitar export → TXT; única diferença funcional permanece `extra_mes` no Dia de Sorte (já existente).

---

## 8. Confirmação final por modalidade

| Modalidade   | Erro 500/`Failed to fetch` existia? | Causa | Correção aplicada? | Export alinhado ao Dia de Sorte? |
|--------------|-------------------------------------|-------|--------------------|----------------------------------|
| Lotofácil    | **Sim**                             | Sem `analise_geral` + export sem JS | **Sim**            | **Sim** |
| Dia de Sorte | Não (gerar OK); export incompleto   | Export sem handler                 | **Sim** (export)   | **Sim** (referência) |
| Quina        | Não (mesmo bug de export)           | Export sem handler                 | **Sim**            | **Sim** |
| Mega-Sena    | Idem                                | Idem                               | **Sim**            | **Sim** |
| Timemania    | Risco em pool automático + export   | Class errada + export              | **Sim**            | **Sim** |
| Lotomania    | Export incompleto                   | Export sem handler                 | **Sim**            | **Sim** |
| Super Sete   | Gerar Est.A falhava c/ qtd=10 + export | QTD fixa + export               | **Sim**            | **Sim** |

---

## 9. Como validar na UI

1. Reiniciar o app da modalidade (ex.: Lotofácil porta 5152) para carregar o código novo.  
2. Abrir **Geradores Elite → Gerador por Concentração**.  
3. Completar o pool (ou usar sugestão automática) → **Gerar apostas**.  
4. Confirmar lista de apostas e botão **Exportar TXT** habilitado.  
5. Baixar o `.txt` e conferir uma linha por aposta (no Dia de Sorte, com mês quando aplicável).

---

## 10. Escopo conscientemente não alterado

- Dupla Sena / +Milionária: sem módulo de concentração cadastrado — sem alteração.  
- Regras do `ValidadorGeradoresElite` (rejeição de jogos “muito consecutivos” etc.) — preservadas; apenas mensagem quando nenhuma aposta sobra.  
- Layout/CSS do gerador — sem mudança visual desnecessária.
