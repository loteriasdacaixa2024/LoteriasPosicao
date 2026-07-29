# Análises Gerais — Documentação Técnica

> Módulo de estudos exploratórios por abas — Dia de Sorte  
> Pacote técnico: `_shared/analise_estudos/`  
> URL: `/analise/analises-gerais/`

---

## 1. Objetivo

Concentrar análises que não pertencem diretamente aos módulos atuais em **um único hub com abas**, evitando proliferar itens no menu principal. Novas análises entram como plug-ins no registry, sem reorganizar a aplicação.

**Não confundir com:** `Análises Gerais — Central` (`/analises-gerais/` na porta 8083), que é o comparativo multimodal das 9 modalidades.

---

## 2. Arquitetura

### 2.1 Localização

| Aspecto | Valor |
|---------|-------|
| Blueprint | `analise_bp` (prefixo `/analise`) |
| Rota página | `/analise/analises-gerais/` |
| API base | `/analise/api/analises-gerais/` |
| Menu | Um item em `nav_config.py → diadesorte.analise_extras` |
| Domínio | Análise (não Geradores Elite) |

### 2.2 Estrutura de pacotes

```
_shared/analise_estudos/
├── registry.py              # Registro de abas (plug-in)
├── specs.py                 # Config por modalidade
├── base_service.py          # Carga de sorteios, janela, bases
├── service_factory.py
├── routes_factory.py
├── app_integration.py
├── core/
│   ├── classificacoes.py    # Definições PA, GE, TR, etc.
│   └── digitos.py           # Soma e conjunto de dígitos
├── abas/
│   ├── classificacao_numeros.py   # Aba 3 — implementada
│   ├── digitos_utilizados.py      # Aba 2
│   └── soma_digitos.py            # Aba 1
├── templates/
│   └── analise_estudos.html
└── static/
    └── analise_estudos.js
```

### 2.3 Padrão Registry de abas

Cada aba registra: `id`, `titulo`, `descricao`, `icone`, `ordem`, `service`.

Para adicionar Aba 4: criar `abas/nova_analise.py`, registrar em `registry.py` — sem alterar menu nem shell.

### 2.4 API

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/analises-gerais/meta` | Abas habilitadas + UI config |
| GET | `/api/analises-gerais/<aba_id>` | Payload da aba (`janela`, `base`) |
| GET | `/api/analises-gerais/<aba_id>/comparativo` | Vencedores × Acumulados (`janela`) |
| GET | `/api/analises-gerais/<aba_id>/export` | Download TXT/CSV (`janela`, `base`, `formato`, `comparativo`) |
| GET | `/api/analises-gerais/<aba_id>/concursos` | Lista resumida de concursos |

---

## 3. Abas

### Aba 1 — Soma dos Dígitos das Dezenas (`soma-digitos`)

Estuda a soma dos algarismos de cada dezena (ex.: 15 → 6) e agregados por concurso.

- Reutiliza `posicao_analise/core.py` (`soma_digitos`, `extrair_digitos`)
- Gráficos: Chart.js (histograma, evolução temporal)
- Status: implementação base

### Aba 2 — Dígitos Utilizados (`digitos-utilizados`)

Estuda o conjunto de dígitos 0–9 presentes em cada concurso.

- Reutiliza `analisar_concurso_geral()` de posição
- Co-ocorrência, frequência, atraso por dígito
- Gráficos: Chart.js
- Status: implementação base

### Aba 3 — Classificação dos Números (`classificacao-numeros`)

Contagem por concurso de grupos matemáticos e comportamentais.

**Grupo A (comportamento):** PA, IM, PR, FB, M3, MO, SQ, RT, MS

**Grupo B (estudos):** GE, M5, QP, P2, P3, TR, BX, MD, AL, CT, AM, SD

Definições centralizadas em `core/classificacoes.py`.

- Status: **implementada (v1)**

---

## 4. Filtros globais

| Filtro | Valores | Origem |
|--------|---------|--------|
| Janela | 10, 20, 31, 0 (todos) | Padrão comportamento |
| Base | geral, vencedores, acumulados | `SorteioDiaDeSorte.filtro_base()` |

---

## 5. Reaproveitamento

| Recurso | Origem |
|---------|--------|
| `soma_digitos`, `extrair_digitos` | `posicao_analise/core.py` |
| Primos, Fibonacci, M3, moldura | `comportamento/specs.py` |
| Panorama Top-3 | `comportamento/panorama_indicadores.py` |
| Coluna concurso + mês | `comportamento_col_concurso.js` |
| Bases estatísticas | `SorteioDiaDeSorte.ganhadores_7` |

---

## 6. Ordem de implementação

1. ✅ Shell + registry + Aba 3 (Classificação dos Números)
2. ✅ Abas 1 e 2 — KPIs, tabelas, Chart.js
3. ✅ Wiring: `app.py`, `analise_routes.py`, `nav_config.py`
4. ✅ Aba 2 fase 2 — co-ocorrência, atraso, top pares, insights
5. ✅ Aba 1 fase 2 — histograma, mapa 01–31, paridade, insights
6. ✅ Links cruzados entre abas e geradores/análises
7. ✅ Exportação TXT/CSV por aba (+ comparativo V×A)
8. ✅ Comparativo vencedores vs acumulados lado a lado

---

## 7. Decisões arquiteturais

1. Pacote `_shared/analise_estudos/` com registry de abas
2. Registro via `wire_analise_estudos(analise_bp, 'diadesorte')`
3. Um único item no menu Análise
4. Classificações em `core/classificacoes.py` (futuro Comportamento expandido)
5. Chart.js isolado neste módulo (Abas 1 e 2)
6. Central mantém nome diferenciado na UI
7. Fora de Geradores Elite

---

*Última atualização: exportação TXT/CSV e comparativo V×A nas 3 abas.*
