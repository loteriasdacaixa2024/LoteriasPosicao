# Auditoria de Cores das Modalidades

## Fonte central

Tokens oficiais em `_shared/configuracoes/temas_modalidade.py`.  
Cada `templates/base.html` espelha esses valores em `:root`.  
Script de ressincronização: `_shared/configuracoes/_sync_base_temas.py`.

## Modalidades analisadas

| Modalidade | Primary | Accent | On-accent |
|---|---|---|---|
| Lotofácil (`lotofacil`) | `#672666` | `#930089` | `#ffffff` |
| Mega-Sena (`megasena`) | `#0a6b1a` | `#1ec83a` | `#ffffff` |
| Quina (`quina`) | `#6a0dad` | `#9b30e8` | `#ffffff` |
| Lotomania (`lotomania`) | `#c45c00` | `#f5820a` | `#ffffff` |
| Timemania (`timemania`) | `#8b3a00` | `#e07000` | `#ffffff` |
| Dia de Sorte (`diadesorte`) | `#c08b00` | `#e6a800` | `#1a0a00` |
| Super Sete (`supersete`) | `#708e25` | `#a9cf46` | `#1a2600` |
| Dupla Sena (`duplasena`) | `#8b0000` | `#d42020` | `#ffffff` |
| +Milionária (`maismilionaria`) | `#8b6914` | `#d4a017` | `#1a0a00` |

**Regra:** amarelo/ouro é exclusivo do **Dia de Sorte** (e dourado da **+Milionária**).  
Lotofácil usa roxo/magenta (`#672666` / `#930089`), nunca amarelo.

## Inconsistências encontradas (antes)

1. **Lotofácil** — `--accent` estava `#d4b31a` (ouro) em `base.html`; bolas/badges amarelas.
2. **Templates compartilhados** (Gerador por Dígitos, Construtor, Concentração, Posição, Repetição) usavam fallbacks hardcoded de Dia de Sorte (`#c08b00`, `#ffe082`, `#ffc107`, `btn-warning`).
3. Em Lotofácil, a mesma tela herdava visual amarelo apesar do navbar roxo.
4. Páginas Lotofácil locais (`modelos`, `sniper`, `conferencia`, `atrasos`, `analise_repeticao`) com `#d4b31a` / `btn-warning`.
5. Menu injetado (`nav_config._inject_analises_novas_nav`) usava ícones dourados fixos em todas as modalidades.

## Correções realizadas

### Centralização

- Consolidado `temas_modalidade.py` com tokens por modalidade.
- Sincronizados os 9 `base.html` (`--primary`, `--accent`, `--accent-light`, `--on-accent`, etc.).

### Templates compartilhados (todas as modalidades)

- `gerador_digitos_inteligente.html` — steps, pool, CTAs, badges via CSS vars; ícones sem `text-warning`.
- `construtor_construcoes.html` — cards/modos/dropzones sem amarelo fixo.
- `gerador_concentracao_acertos.html` + `analise_concentracao_acertos.html`.
- `geradores_elite_index.html` — botões outline na cor `--primary`.
- `posicao_analise` (`gerador_por_posicao`, `analise_por_posicao`) — bolas/matriz/hit via tema.
- `analise_repeticao` — volante/células/botões via tema.
- Removidos fallbacks `var(--primary, #c08b00)` em diversos HTML/CSS de `_shared`.

### Lotofácil (app local)

- `base.html` — accent roxo oficial.
- `modelos.html`, `sniper.html`, `conferencia.html`, `atrasos.html`, `analise_repeticao_concursos.html`.
- `ball_styles.py` — Lotofácil com `var(--accent)` + `var(--on-accent)` (texto branco).

### Menu

- Ícones de Somas/Dígitos e Concentração no inject compartilhado passam a usar o tema da modalidade.

## Evidência de identidade única

Qualquer tela que estende `base.html` e usa `var(--primary)` / `var(--accent)` segue a modalidade do app:

- Lotofácil → roxo  
- Mega-Sena → verde  
- Quina → violeta  
- Lotomania → laranja  
- Timemania → laranja (+ verde do time)  
- Dia de Sorte → amarelo/ouro (+ verde do mês)  
- Super Sete → verde-limão  
- Dupla Sena → vermelho  
- +Milionária → dourado (+ verde do trevo)

## Componentes auditados (escopo prioritário)

Geradores Elite, Construtor, Dígitos, Concentração, Análise por Posição, Repetição, Engine Final (bolas), navbar/`base.html`, badges de dezenas, CTAs, ícones de menu injetados.

## Pendências / fora do escopo imediato

- Telas **específicas do Dia de Sorte** (`gerador_especial`, `tubular.css`, etc.) mantêm amarelo de propósito.
- Alguns `btn-success` / azul Bootstrap em ações genéricas (sucesso/info) foram preservados — não são identidade de modalidade.
- Demais ícones semânticos do menu (verde “padrões”, azul “comportamental”) permanecem como categorias de UI.
- Pontuais `btn-warning` em fluxos de alerta/export de conferência (Bootstrap semântico).

## Como alterar identidade no futuro

1. Editar apenas `TEMAS` em `_shared/configuracoes/temas_modalidade.py`.
2. Rodar `python _shared/configuracoes/_sync_base_temas.py`.
3. Reiniciar o app da modalidade.
