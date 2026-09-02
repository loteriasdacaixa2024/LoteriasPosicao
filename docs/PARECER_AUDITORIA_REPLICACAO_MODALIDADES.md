# Parecer Técnico — Auditoria de Replicação de Funcionalidades entre Modalidades

| Campo | Valor |
|-------|-------|
| **Escopo auditado** | `AnalisePorPosicao--DiaDeSorte-Only` (+ dependências em `_shared/`) |
| **Workspace** | `D:\Loterias\LoteriasPosicao` |
| **Data** | 25/07/2026 |
| **Tipo** | Auditoria somente-leitura (sem alteração de comportamento) |
| **Objetivo** | Identificar o que pode virar padrão do sistema e o que deve permanecer específico |

---

## 0. Resumo executivo

O Dia de Sorte (`AnalisePorPosicao--DiaDeSorte-Only`, porta **5153**) é hoje a **modalidade mais completa** do monólito. Não é um produto isolado: compartilha o esqueleto Flask das irmãs e concentra as **novas frentes de análise** em pacotes `_shared`, plugados primeiro nele.

**Achados principais:**

1. Já existe um padrão de apps por modalidade (`app.py` + `routes/` + `services/` + `models/` + `templates/` + `instance/`).
2. O motor reutilizável mais maduro é `_shared/posicao_analise` (specs por modalidade já cobrem 9 jogos).
3. Os módulos **mais novos** (estudos, soma de dígitos, concentração, análises inteligentes, meses) nasceram no Dia de Sorte e ainda **não foram habilitados** nas demais apps.
4. Elementos como **Mês da Sorte**, **ciclo de 31 dezenas**, **cores dos 12 meses** e o pacote `analise_inteligentes_diadesorte` são **exclusivos** (ou exigem análogo de domínio, ex.: Time do Coração na Timemania).
5. **Mega da Virada** e **Quina de São João** não são apps separados: são **concursos especiais** das séries Mega-Sena e Quina (já previstos em `config.py` / `catalogo_oficial.json`).

**Conclusão em uma frase:** o padrão do sistema deve ser o *motor compartilhado + spec/config por modalidade*; o que depende de Mês da Sorte, scoring de mês ou heurísticas DDS permanece específico.

---

## 1. Contexto da implementação auditada

### 1.1 Pasta auditada

```
D:\Loterias\LoteriasPosicao\AnalisePorPosicao--DiaDeSorte-Only
```

> Nota: a variante com hífen simples `AnalisePorPosicao-DiaDeSorte-Only` **não existe** neste workspace. O nome oficial no monólito usa hífen **duplo** (`--`).

### 1.2 Dependência crítica

Grande parte das funcionalidades “novas” **não vive só na pasta da modalidade**. Elas estão em:

```
D:\Loterias\LoteriasPosicao\_shared\
```

O `app.py` do Dia de Sorte faz o *wiring* desses pacotes. Replicar funcionalidade = **habilitar o mesmo `extend_*` / registry em outra app**, com **spec própria**, nunca copiar o app inteiro.

### 1.3 Apps irmãs já existentes

| Modalidade | Pasta | Porta |
|------------|-------|-------|
| Lotofácil | `AnalisePorPosicao-Lotofacil-Only` | 5152 |
| Dia de Sorte | `AnalisePorPosicao--DiaDeSorte-Only` | 5153 |
| Lotomania | `AnalisePorPosicao-Lotomania-Only` | 5154 |
| Quina | `AnalisePorPosicao-Quina-Only` | 5155 |
| Mega-Sena | `AnalisePorPosicao-MegaSena-Only` | 5156 |
| +Milionária | `AnalisePorPosicao-MaisMilionaria-Only` | 5157 |
| Dupla Sena | `AnalisePorPosicao-DuplaSena-Only` | 5158 |
| Timemania | `AnalisePorPosicao-Timemania-Only` | 5159 |
| Super Sete | `AnalisePorPosicao-SuperSete-Only` | 5160 |
| Central (hub) | `AnalisePorPosicao-Central` | 8083 |

---

## 2. Funcionalidades criadas / existentes no Dia de Sorte

Para cada item: **objetivo**, **arquivos**, **dependências**, **classificação de domínio**.

### 2.1 Núcleo da aplicação (esqueleto)

| # | Funcionalidade | Objetivo | Arquivos | Dependências | Domínio |
|---|----------------|----------|----------|--------------|---------|
| F01 | App Flask multimodalidade | Bootstrap, DB SQLite, blueprints, redirects | `app.py` | Flask, SQLAlchemy, `_shared/*` | **Semi-genérico** (padrão das irmãs; keys `diadesorte`/`diasorte` e porta 5153 são específicos) |
| F02 | Modelo de sorteio | Persistir concursos (7 dezenas + mês + ganhadores_7) | `models/sorteio_diadesorte.py`, `models/shared.py` | SQLAlchemy | **Específico DDS** (campos e mecânica) |
| F03 | Sync API Caixa | Buscar/atualizar sorteios oficiais | `services/api_diadesorte_service.py`, `sincronizar_diadesorte_completo.py`, `_shared/auto_sync.py` | API Caixa `/api/diadesorte/` | **Padrão com adaptação** (cada modalidade tem slug/parser) |
| F04 | Backfill mês / ganhadores | Completar histórico (`mes_*`, `ganhadores_7`) | `backfill_meses_diadesorte.py`, `backfill_ganhadores_diadesorte.py` | API + modelo | **Específico DDS** |
| F05 | Home / status / sync UI | Dashboard local da modalidade | `routes/index_routes.py`, `templates/index.html` | API service | **Genérico** (padrão UI) |

### 2.2 Análise estatística e posição

| # | Funcionalidade | Objetivo | Arquivos | Dependências | Domínio |
|---|----------------|----------|----------|--------------|---------|
| F06 | Análise geral (freq/atraso) | Frequência e atraso das 31 dezenas e 12 meses | `services/analise_diadesorte_service.py`, `routes/analise_routes.py`, `templates/analise.html` | Modelo + `_shared/diadesorte/meses_indicados` | **Específico nums**; padrão de tela **reutilizável** |
| F07 | Análise por posição | Estatísticas por ordem de sorteio (P1–P7) | `_shared/posicao_analise/*`, `services/analise_posicao_service.py`, `templates/analise_por_posicao.html`, `diadesorte/posicao_analise.py` | Spec `POSICAO_SPECS["diadesorte"]` | **Genérico** (motor); **adaptação** via spec |
| F08 | Gerador por posição | Gerar jogos a partir de perfis posicionais | `_shared/posicao_analise/gerador.py`, `templates/gerador_por_posicao.html`, `diadesorte/posicao_gerador.py` | posicao_analise + geradores_elite | **Genérico com adaptação** |
| F09 | Comparar / Repetição | Comparativos e repetição entre concursos | `_shared/analise_comparar`, `_shared/analise_repeticao` | Wiring em `app.py` | **Genérico** |
| F10 | Análises Gerais (hub de abas) | Estudos: soma dígitos, dígitos usados, classificações | `_shared/analise_estudos/*`, `docs/ANALISE_ESTUDOS.md` | Spec `ESTUDOS_MODALITIES` (hoje só `diadesorte`) | **Arquitetura genérica**; **rollout pendente** |
| F11 | Soma de dígitos (módulo dedicado) | Análise focada em soma dos algarismos | `_shared/analise_somas_digitos/*` | posicao_analise core | **Genérico com adaptação** (universo/pad) |
| F12 | Concentração de acertos | Estudo experimental de concentração | `_shared/concentracao_acertos/*`, `instance/concentracao_validacao_diadesorte.json` | Spec DDS | **Adaptável**; validação atual DDS |
| F13 | Análises inteligentes DDS | Resultados & padrões (tubular / heurísticas DDS) | `_shared/analise_inteligentes_diadesorte/*` | Modelo DDS | **Exclusivo DDS** (nome e domínio) |
| F14 | Ciclo de cobertura 31 | Ciclo até cobrir todas as dezenas 01–31 | `services/ciclo_service.py` | Modelo | **Exclusivo DDS** (lógica `== 31`); padrão “cobertura do universo” é adaptável |

### 2.3 Extra de domínio — Mês da Sorte

| # | Funcionalidade | Objetivo | Arquivos | Dependências | Domínio |
|---|----------------|----------|----------|--------------|---------|
| F15 | Cores dos meses | Personalizar CSS das 12 cores | `services/cores_meses_service.py`, `config_meses.json`, rota `/cores-meses.css` | — | **Exclusivo DDS** (análogo Timemania = times) |
| F16 | Meses indicados / MS | Indicadores e pool por eliminação do mês | `_shared/diadesorte/meses_indicados.py`, `_shared/diadesorte/meses_cores.py` | Modelo | **Exclusivo DDS** |
| F17 | Campo mês no modelo e UI | Exibir/gravar mês em sorteios, construtor, modelos | modelo + templates + migrations em `app.py` | API `nomeTimeCoracaoMesSorte` | **Exclusivo DDS** |

### 2.4 Modelos, desdobramento e geradores

| # | Funcionalidade | Objetivo | Arquivos | Dependências | Domínio |
|---|----------------|----------|----------|--------------|---------|
| F18 | Modelos 1–6 + backtest | 6 estratégias × 14 apostas (7 dez + 1 mês) | `services/modelos_service.py`, `routes/modelos_routes.py`, `templates/modelos.html` | Modelo + scoring mês | **Específico DDS** (estrutura adaptável) |
| F19 | Desdobramento | Fechamentos / distribuição de risco | `services/desdobramento_service.py`, `routes/desdobramento_routes.py`, `_shared/desdobramento_service_factory.py` | `max_dezena=31` | **Genérico com adaptação** |
| F20 | Geradores Elite | Engine, GC, construtor, comportamento | `_shared/geradores_elite/*`, `routes/geradores_elite_routes.py`, services comportamento/construtor | Specs por modalidade | **Genérico com adaptação** |
| F21 | Comportamento / estratégias | Panorama de indicadores (PA, IM, MS…) | `services/comportamento_*`, models relacionados | geradores_elite | **Adaptável**; indicador **MS exclusivo** |
| F22 | Conferência de apostas | Conferir jogos vs histórico / top freq | `routes/conferencia_routes.py`, `_shared/central_conferencias/*`, `templates/conferencia.html` | Keys `diasorte`/`diadesorte` | **Genérico com adaptação** |
| F23 | Configurações / bolão / perfil | Preço, cotas, catálogo oficial | `routes/config_routes.py`, `_shared/configuracoes/*` | `catalogo_oficial.json`, `config.py` | **Genérico** |
| F24 | Menu unificado | Nav por modalidade | `_shared/menu/*` | `nav_config` | **Genérico** |

### 2.5 Artefatos de produto / referência

| # | Item | Papel |
|---|------|-------|
| F25 | `diadesorte/Padrões-DiaDesorte.txt`, `Campos-DiadDeSorte.txt` | Spec de produto / sample API |
| F26 | `static/img/*`, `adaptar/MELHORIAS.txt` | Referências visuais e notas de UI |
| F27 | `docs/ANALISE_ESTUDOS.md` | Documentação técnica do hub de estudos |

---

## 3. Classificação A / B / C

### A) Pode ser replicado diretamente (ou quase — só wiring + key)

Lógica geral já parametrizada ou padrão de UI/infra:

| Item | Como replicar |
|------|----------------|
| Esqueleto Flask + blueprints | Já existe nas irmãs; manter padrão |
| Menu / configurações / catálogo | `_shared/menu`, `_shared/configuracoes` |
| Auto-sync + card de sync | `_shared/auto_sync` + service da modalidade |
| Central de conferências | `extend_app` / `register_conferencia_extras` com key correta |
| Análise comparar / repetição | `register_comparar` / `register_repeticao` |
| Análise por posição (motor) | `extend_posicao_app(app, '<key>')` — specs já existem |
| Geradores Elite (núcleo) | Blueprint factory + specs |
| Export TXT/CSV (padrão estudos/geradores) | Reaproveitar factories existentes |
| Hub Central (8083) | Já orquestra multimodalidade |

### B) Pode ser replicado com adaptação

Potencial alto, mas **obrigatório** respeitar regras da modalidade:

| Item | O que adaptar |
|------|----------------|
| **Análises Gerais (`analise_estudos`)** | Incluir entry em `ESTUDOS_MODALITIES`; ajustar `dezena_min/max`, `sorteadas`, janelas, `extra_mes`/`extra_time`; classificações (MS só DDS) |
| **Soma de dígitos** | Universo, padding, quantidade sorteada |
| **Concentração de acertos** | Critérios de pool, faixas de acerto, JSON de validação |
| **Desdobramento** | `max_dezena`, tamanho da aposta, fechamentos oficiais |
| **Modelos / backtest** | Nº de modelos, tamanho da aposta, scoring por faixa, presença de “extra” |
| **Ciclo de cobertura** | Trocar `31` pelo tamanho do universo (ex.: 60 Mega, 25 Lotofácil, 80 Quina) — **conceito** genérico, **implementação** hoje hardcoded DDS |
| **Frequência / atraso** | Pool e qtd sorteada |
| **Comportamento (indicadores)** | Remover/substituir MS; ajustar faixas BX/MD/AL ao universo |
| **Conferência Top-N** | Top = quantidade sorteada (5 Quina, 6 Mega, 15 Lotofácil…) |
| **Volante / matriz UI** | Layout por modalidade (Super Sete = colunas; Lotomania = 00–99) |
| **Concursos especiais** | Mega da Virada / Quina de São João: camada de série especial, não app novo |

#### Parâmetros obrigatórios por modalidade (referência)

| Modalidade | Universo | Sorteadas (padrão) | Marcação | Extra | Notas de replicação |
|------------|----------|--------------------|----------|-------|---------------------|
| Mega-Sena | 01–60 | 6 | 6–20 | — | Virada = concurso especial da mesma série |
| Mega da Virada | idem Mega | 6 | idem | edição especial | Não criar pasta própria; filtrar/rotular concurso especial |
| Lotofácil | 01–25 | 15 | 15–20 | — | Já madura; sniper próprio |
| Quina | 01–80 | 5 | 5–15 | — | São João = especial (ex. 7051 em `CONCURSOS_ESPECIAIS`) |
| Quina de São João | idem Quina | 5 | idem | edição especial | Idem Virada |
| Dia de Sorte | 01–31 | 7 | 7–15 | **Mês (1–12)** | Referência atual |
| Timemania | 01–80 | 7 (sorteio) / aposta 10 | 10 fixo | **Time do Coração** | Análogo do “extra” do mês |
| Lotomania | 00–99 | 20 | 50 fixo | — | Matriz e ranking distintos |
| Super Sete | 7×(0–9) | 7 colunas | 7 | — | Posição ≠ dezena; `distinct=False` |

### C) Exclusivo da modalidade (Dia de Sorte)

Não copiar para outras modalidades sem redesenho de domínio:

| Item | Motivo |
|------|--------|
| Mês da Sorte (campo, UI, prêmio, MS) | Mecânica inexistente nas demais (exceto análogo Time/Trevo) |
| `config_meses.json` / `CoresMesesService` / `/cores-meses.css` | Domínio 12 meses |
| `_shared/diadesorte/*` | Pacote nominal DDS |
| `analise_inteligentes_diadesorte` | Heurísticas e UI acopladas ao DDS |
| Backfills de mês | Só fazem sentido com campo mês |
| Scoring de modelos com peso de mês | Faixas 7+mês, 6+mês… |
| Hardcodes `31` / `12` / volante 4×10 do DDS | Constantes da mecânica |
| Inconsistência `diadesorte` vs `diasorte` nas keys | Dívida técnica a sanitizar no DDS, não propagar |

**Análogos legítimos (não cópia):**

- Timemania → **Time do Coração** (em vez de mês)
- +Milionária → **Trevos**
- Dupla Sena → **dois sorteios**

---

## 4. Avaliação de arquitetura

### 4.1 Estado atual

```
LoteriasPosicao/
├── _shared/                          # Motor e plug-ins (bom caminho)
│   ├── posicao_analise/specs.py      # Specs já multi-modalidade
│   ├── analise_estudos/specs.py      # Specs ainda só diadesorte
│   ├── geradores_elite/
│   ├── central_conferencias/
│   ├── configuracoes/                # MODALITIES + catalogo_oficial.json
│   └── diadesorte/                   # Domínio exclusivo
├── AnalisePorPosicao--DiaDeSorte-Only/
├── AnalisePorPosicao-MegaSena-Only/
├── AnalisePorPosicao-Lotofacil-Only/
├── ... (demais Only)
└── AnalisePorPosicao-Central/        # Hub / proxy
```

**Pontos fortes**

- Factories (`routes_factory`, `service_factory`, `extend_*`) já apontam para arquitetura modular.
- `PosicaoSpec` é o melhor exemplo de configuração por modalidade.
- Catálogo oficial centraliza regras comerciais/regulamentares.

**Pontos fracos / riscos**

- Novos módulos nascem com registry **só para DDS** (`ESTUDOS_MODALITIES`).
- Cada app ainda tem muito código local duplicável (services de análise/API).
- Keys duplicadas (`diadesorte` / `diasorte`).
- Nome de pasta com `--` diverge do padrão `-`.
- Replicação por *copy-paste* da pasta Only aumentaria divergência.

### 4.2 Arquitetura alvo recomendada

Não é necessário reescrever tudo. Evoluir o que já existe:

```
_shared/
  core/
    modality_registry.py          # carrega specs
  engines/
    posicao/                      # (já: posicao_analise)
    estudos/                      # (já: analise_estudos)
    digitos/
    concentracao/
    desdobramento/
    conferencias/
    geradores/
  modalities/
    diadesorte/
      configuracao.json           # universo, sorteadas, extras, janelas
      regras.py                   # ciclo, scoring, MS, faixas
      parsers_api.py
    megasena/
      configuracao.json
      regras.py
      especiais.py                # Virada
    quina/
      configuracao.json
      regras.py
      especiais.py                # São João
    lotofacil/
    timemania/                    # extra = time
    lotomania/
    supersete/                    # colunas, não dezenas
    ...
apps/   # ou manter pastas AnalisePorPosicao-*-Only
  <modalidade>/
    app.py                        # só wiring + DB path + porta
```

**Princípios**

1. **Motor compartilhado** — zero regras de negócio “soltas” nos templates.
2. **Config por modalidade** — JSON/dataclass: universo, n sorteadas, extras, faixas, API slug.
3. **Regras isoladas** — ciclo, scoring, extras em `regras.py` da modalidade.
4. **Carga dinâmica** — `extend_*(app, modality_key)` só se `tem_feature(key)`.
5. **Sem cópia cega** — novo módulo nasce com registry multi-key desde o dia 1.

### 4.3 Contrato mínimo de `configuracao.json` (proposta)

```json
{
  "key": "megasena",
  "nome": "Mega-Sena",
  "universo": { "min": 1, "max": 60, "pad": 2 },
  "sorteadas": 6,
  "marcacao": { "min": 6, "max": 15 },
  "posicoes": { "num": 6, "ordenadas": true, "distinct": true },
  "extras": [],
  "faixas_premio": [6, 5, 4],
  "api_slug": "megasena",
  "features": {
    "posicao_analise": true,
    "analise_estudos": true,
    "concentracao": true,
    "ciclo_cobertura": true,
    "extra_visual": false
  },
  "especiais": ["mega_da_virada"]
}
```

---

## 5. Ordem recomendada de implementação

Critério: maximizar reuso do que já está em `_shared`, minimizar risco de regra errada, respeitar complexidade do domínio.

| Ordem | Modalidade | Justificativa |
|------:|------------|---------------|
| 1 | **Quina** | Universo clássico (5/80); especial São João já catalogado; app enxuta |
| 2 | **Mega-Sena** | Similar à Quina; incluir **Mega da Virada** como filtro/série especial, não app |
| 3 | **Lotofácil** | App madura; habilitar estudos/dígitos/concentração sobre base existente |
| 4 | **Timemania** | Validar padrão de **extra** (Time ≈ Mês); 7 dezenas no sorteio |
| 5 | **Lotomania** | Universo 00–99 e 20 posições — stress no motor de posição/UI |
| 6 | **Super Sete** | Domínio por colunas (não conjunto de dezenas); exige cuidado no motor |
| 7 | **Dia de Sorte** | Já é referência — só refatorar para o registry comum **sem mudar comportamento** |
| — | Mega da Virada / Quina de São João | Tratar como **camada de concurso especial** dentro de Mega/Quina |

**Por feature (transversal), após Quina/Mega:**

1. Habilitar `analise_estudos` (adicionar specs)  
2. Habilitar `analise_somas_digitos`  
3. Habilitar `concentracao_acertos` (com validação própria)  
4. Generalizar `ciclo_service` → `ciclo_cobertura(universo_size)`  
5. **Não** portar `analise_inteligentes_diadesorte` sem redesign  

---

## 6. Cuidados e restrições (cumpridas nesta auditoria)

- Nenhuma funcionalidade existente foi alterada.
- Nenhuma regra do Dia de Sorte foi removida ou modificada.
- Nenhuma cópia automática de código foi executada.
- Este documento é **estratégia e inventário** — implementação futura deve ser modalidade a modalidade, com testes de regressão no DDS.

---

## 7. Conclusão técnica

### O que deve virar **padrão do sistema** de análise de loterias

1. **Esqueleto de app** (Flask + SQLite + blueprints + auto-sync + menu + config).  
2. **Motor de análise por posição** (`_shared/posicao_analise` + `PosicaoSpec`).  
3. **Hub de Análises Gerais** (`analise_estudos` com registry de abas) — após specs por modalidade.  
4. **Análises de dígitos / soma** (conceito matemático transversal).  
5. **Conferência / bolões / exportações**.  
6. **Geradores Elite + desdobramento** parametrizados.  
7. **Comparar / repetição / concentração** como features opt-in por config.  
8. **Catálogo oficial + `MODALITIES`** como fonte única de regras comerciais.  
9. **Tratamento de concursos especiais** (Virada, São João) no mesmo app da série.

### O que deve permanecer **específico de cada modalidade**

| Modalidade | Permanecer específico |
|------------|----------------------|
| **Dia de Sorte** | Mês da Sorte, cores dos meses, MS, ciclo 31, scoring 7+mês, `analise_inteligentes_diadesorte`, backfills de mês |
| **Timemania** | Time do Coração (e UI/cores de times, se houver) |
| **+Milionária** | Trevos |
| **Dupla Sena** | Dois sorteios |
| **Super Sete** | Colunas 0–9, ausência de “conjunto de dezenas” clássico |
| **Lotomania** | 50 fixas / 20 sorteadas / 00–99 |
| **Lotofácil / Quina / Mega** | Faixas, snipers/Des2 e fechamentos já próprios; especiais Virada/São João |
| **Todas** | Parser API, modelo ORM, DB `instance/`, porta, marca/CSS, preços e bolão do catálogo |

### Veredito final

> **Padrão do sistema** = motores compartilhados em `_shared` + configuração/regras por modalidade.  
> **Específico** = qualquer elemento de domínio (Mês, Time, Trevo, colunas Super Sete, especiais de calendário) e qualquer heurística nominalmente acoplada ao Dia de Sorte.  
> **Replicação segura** = habilitar features via registry/spec, nunca copiar a pasta `AnalisePorPosicao--DiaDeSorte-Only` como template cego.

---

## 8. Anexos

### A. Wiring atual do Dia de Sorte (`app.py`)

Pacotes `_shared` ativados hoje:

- `central_conferencias`
- `auto_sync`
- `analise_comparar` / `analise_repeticao`
- `menu` / `configuracoes`
- `posicao_analise`
- `concentracao_acertos`
- `analise_estudos`
- `analise_somas_digitos`
- `analise_inteligentes_diadesorte`
- `geradores_elite` (templates merge)

### B. Documentação interna útil

- `AnalisePorPosicao--DiaDeSorte-Only/docs/ANALISE_ESTUDOS.md` — arquitetura do hub de estudos  
- `_shared/configuracoes/catalogo_oficial.json` — regras oficiais por modalidade  
- `_shared/configuracoes/config.py` — portas, apostas, `CONCURSOS_ESPECIAIS`  
- `docs/PADROES/` — padrões visuais/API por modalidade  

### C. Glossário rápido

| Termo | Significado |
|-------|-------------|
| Spec | Config tipada por modalidade (ex.: `PosicaoSpec`) |
| Wiring | `extend_*` / `register_*` no `app.py` |
| Extra | Campo além das dezenas (mês, time, trevo) |
| Concurso especial | Edição paralela (Virada, São João) |
| Only | App Flask dedicada a uma modalidade |

---

*Fim do parecer. Próximo passo sugerido (fora do escopo desta auditoria): abrir um plano de rollout feature-a-feature começando por Quina e Mega-Sena, com checklist de regressão no Dia de Sorte.*
