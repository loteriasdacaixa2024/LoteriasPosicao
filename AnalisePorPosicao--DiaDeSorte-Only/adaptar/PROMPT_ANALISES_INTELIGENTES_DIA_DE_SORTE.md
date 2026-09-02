# PROMPT PROFISSIONAL — Análises Inteligentes Dia de Sorte (Unificação de Sistemas)

## 1. Objetivo

Unificar, dentro da aplicação local **Dia de Sorte**, três sistemas Netlify hoje separados, criando um **módulo único com abas**.

Não é para copiar tabelas nem layouts externos.

É para:

1. **Analisar** os arquivos HTML e as telas Netlify;
2. **Comparar** colunas, títulos e informações;
3. **Identificar** o que se repete e o que é exclusivo;
4. **Relacionar** os dados por concurso / quantidade de dígitos;
5. **Integrar** tudo no padrão visual e arquitetural do sistema atual;
6. **Permitir navegação inteligente** entre resultados, combinações (`indexN`), geradores (`gcN`) e Gerador Elite.

Resultado esperado: uma camada única de análise e geração de palpites baseada em relacionamento de dados — não páginas isoladas.

---

## 2. Contexto atual

### Workspace / projeto alvo

```text
D:\Loterias\LoteriasPosicao\AnalisePorPosicao--DiaDeSorte-Only
```

### Pasta de referência obrigatória (analisar antes de implementar)

```text
D:\Loterias\LoteriasPosicao\AnalisePorPosicao--DiaDeSorte-Only\adaptar
```

### Sistemas externos a unificar (todos principais)

| Sistema | URL | Print de referência |
|---------|-----|---------------------|
| A — Resultados & Dígitos | https://resultadosdigitosdiadesorte.netlify.app/ | `adaptar/agora (2).jpg` |
| B — Gerador Elite / Diário | https://geradorpalpitesdiariodiadesorte.netlify.app/ | `adaptar/agora (3).jpg` |
| C — Combinações / Geradores | https://geradoresdiadesorte.netlify.app/index8 | `adaptar/agora (1).jpg` |

> **Importante:** `geradoresdiadesorte` **entra e é um dos principais**. Não tratar como opcional.

### Aplicação local (destino da integração)

- Projeto Flask Dia de Sorte em `AnalisePorPosicao--DiaDeSorte-Only`
- Templates em `templates/`
- Rotas em `routes/`
- Menu/integrações já existentes via `_shared` / `menu.app_integration`
- Manter identidade visual, menus, componentes e arquitetura atuais
- **Não quebrar** funcionalidades existentes

---

## 3. Arquivos para análise (obrigatório antes de qualquer alteração)

### 3.1 Combinações por quantidade de dígitos

```text
adaptar/index1.html
adaptar/index2.html
adaptar/index3.html
adaptar/index4.html
adaptar/index5.html
adaptar/index6.html
adaptar/index7.html
adaptar/index8.html
adaptar/index9.html
adaptar/index10.html
```

Regra de navegação:

```text
N dígitos → indexN.html
Ex.: 6 dígitos → index6.html
     7 dígitos → index7.html
     8 dígitos → index8.html
```

### 3.2 Gerador Pro (nome real dos arquivos: **gc**, não cg)

```text
adaptar/gc3.html
adaptar/gc4.html
adaptar/gc5.html
adaptar/gc6.html
adaptar/gc7.html
adaptar/gc8.html
adaptar/gc9.html
adaptar/gc10.html
```

> Não existem `cg*.html` nesta pasta. Usar sempre **`gcN.html`**.

### 3.3 Arquivos auxiliares na mesma pasta

```text
adaptar/index-combinacoes-analise.html
adaptar/index-combinacoes-melhores.html
adaptar/index-combinacoes-todas.html
adaptar/index-pares-impares.html
adaptar/vizualizacao_tubular.html
```

Usar como referência de lógica / recursos complementares.  
**Não copiar layout** desses arquivos.

### 3.4 Prints das telas (barra de endereço visível)

```text
adaptar/agora (1).jpg   → geradoresdiadesorte (combinações index8)
adaptar/agora (2).jpg   → resultadosdigitosdiadesorte
adaptar/agora (3).jpg   → geradorpalpitesdiariodiadesorte
```

Prints extras (opcionais):

```text
adaptar/PrtScr capture_2.jpg
adaptar/PrtScr capture_3.jpg
adaptar/PrtScr capture_4.jpg
```

---

## 4. O que cada sistema oferece hoje (síntese dos prints)

### Sistema A — Resultados & Dígitos

Colunas / capacidades observadas:

- Concurso
- Data
- Dezenas
- Dígitos
- Dígitos Ordenados
- Quantidade de Dígitos
- Combinações
- Gerador Pro
- Exportações (XLS / HTML / TXT)
- Atualização automática / frequência de dígitos

### Sistema B — Gerador Elite / Diário

Capacidades observadas:

- Últimos concursos
- Análise detalhada dos concursos
- Gerador por padrões específicos
- Escolha de números (01–31)
- Bloqueio/liberação dos números do último sorteio
- Geração de jogos por estratégia

### Sistema C — Combinações / Geradores (`indexN` + `gcN`)

Capacidades observadas (ex.: index8):

- Lista de combinações de N dígitos
- Números válidos
- Combinações possíveis
- Filtros / busca
- Ações: **Usar** / **Gerar**
- Resumo estatístico por volume
- Ligação natural para `gcN` (geração)

---

## 5. Análise de relacionamento (obrigatória)

Antes de implementar, a IA deve produzir um mapa comparativo:

### 5.1 Colunas comuns (não duplicar no UI final)

Exemplos candidatos:

- Concurso
- Data
- Dezenas
- Quantidade de Dígitos

### 5.2 Exclusivas do Sistema A

- Dígitos
- Dígitos Ordenados
- Combinações (atalho / contagem)
- Gerador Pro (atalho)

### 5.3 Exclusivas do Sistema B / padrões

- Mês
- Padrão Inicial
- Padrão Final
- Dígitos Únicos
- Pares / Ímpares
- Não Saíram
- Geração Elite por quantidade de dígitos (3d…9d)

### 5.4 Exclusivas do Sistema C

- Catálogo de combinações por N dígitos (`indexN`)
- Volumes / estatísticas de combinações
- Geração via `gcN`

### 5.5 Chaves de relacionamento

Relacionar registros por:

1. **Concurso** (chave principal entre A e B)
2. **Quantidade de dígitos (N)** (chave entre A ↔ indexN ↔ gcN ↔ Elite Nd)
3. **Conjunto de dígitos** (quando aplicável, para abrir a combinação certa)

---

## 6. Arquitetura sugerida no sistema local

```text
MENU PRINCIPAL
└── Análises Inteligentes Dia de Sorte
       │
       ├── Aba 1 - Resultados & Dígitos
       │      Concurso
       │      Data
       │      Dezenas (ordem Caixa)
       │      Dígitos
       │      Dígitos Ordenados
       │      Quantidade de Dígitos
       │
       ├── Aba 2 - Combinações de Dígitos
       │      Quantidade de dígitos
       │      Quantidade de combinações possíveis
       │      Acesso automático:
       │          6 dígitos → index6
       │          7 dígitos → index7
       │          8 dígitos → index8
       │          ... até index10
       │
       ├── Aba 3 - Gerador Pro / gc
       │      gc3 … gc10
       │
       ├── Aba 4 - Padrões do Concurso
       │      Concurso
       │      Data
       │      Dezenas
       │      Mês
       │      Padrão Inicial
       │      Padrão Final
       │      Dígitos Únicos
       │      Quantidade de Dígitos
       │      Pares e Ímpares
       │      Não Saíram
       │
       └── Aba 5 - Gerador Elite de Palpites
              Geração por quantidade de dígitos:
              3d 4d 5d 6d 7d 8d 9d
```

### Posicionamento no menu

Preferência:

```text
ANÁLISES
  └── Análises Inteligentes Dia de Sorte
```

Avaliar também ligação com **Geradores Elite** (sem remover o que já existe lá).

---

## 7. Tabela inteligente unificada (visão consolidada)

Não criar três tabelas redundantes. Preferir uma visão inteligente com colunas:

| Coluna | Origem |
|--------|--------|
| Concurso | A / B |
| Data | A / B |
| Dezenas | A / B |
| Mês | B / padrões |
| Dígitos | A |
| Dígitos Ordenados | A |
| Quantidade Dígitos | A / B |
| Combinações | A / C |
| Não Saíram | B |
| Pares/Ímpares | B |
| Padrões | B |
| Ações | integração |

### Botões de ação (navegação obrigatória)

Para um concurso com **N dígitos** (ex.: N = 8):

```text
[Ver Combinações]  →  Aba 2 / conteúdo equivalente a index8
[Gerar gc8]        →  Aba 3 / conteúdo equivalente a gc8.html
[Gerador Elite]    →  Aba 5 (modo 8d)
```

Regras:

- N deve ser lido do registro (coluna Quantidade de Dígitos)
- Abrir automaticamente o `indexN` / `gcN` correspondente
- Se N < 3 para gc, informar indisponibilidade (não existem gc1/gc2 na pasta)

---

## 8. Regras de integração

1. **Não copiar** o visual Netlify (Tailwind isolado, tema dourado externo, etc.).
2. **Reaproveitar lógica** (cálculos, mapeamentos, combinações, geração).
3. Seguir **layout, CSS, menus e componentes** do app Flask atual.
4. **Não duplicar** colunas iguais em abas diferentes sem necessidade.
5. **Não sobrescrever** rotas/templates existentes sem necessidade.
6. Preferir extensão: nova rota + template + item de menu.
7. Dados oficiais devem continuar vindo da **base/API local** do Dia de Sorte sempre que possível.
8. Os HTML de `adaptar/` são **referência**, não destino final de produção.
9. Nome correto dos geradores: **`gcN`**, nunca `cgN` no código/documentação desta pasta.
10. `geradoresdiadesorte` é **principal** e deve ter aba/fluxo próprio (Combinações + Gerador Pro).

---

## 9. Requisitos do Gerador Elite (Aba 5)

Integrar a lógica do sistema B, adaptada ao app local:

- Geração por quantidade de dígitos: **3d … 9d**
- Uso de padrões / filtros quando disponíveis
- Compatibilidade com números 01–31 e mês da sorte
- Não gerar aleatoriamente sem critério: usar comportamento/padrão/dígitos selecionados
- Botão da tabela unificada deve abrir esta aba já no modo Nd correspondente

Avaliar, se fizer sentido no app atual, ligação complementar com:

```text
Geradores Elite → (nova aba ou atalho para Análises Inteligentes)
```

Sem remover funcionalidades já existentes em Geradores Elite.

---

## 10. Critérios para não duplicar informações

Antes de desenhar cada aba, classificar cada campo:

| Classificação | Ação |
|---------------|------|
| Comum | mostrar 1 vez na visão principal / tabela unificada |
| Exclusivo A | Aba 1 (e ação para C quando couber) |
| Exclusivo B | Aba 4 / Aba 5 |
| Exclusivo C | Aba 2 / Aba 3 |
| Derivado | calcular sob demanda (não armazenar redundante se já for calculável) |

Se a mesma informação aparecer em A e B com nomes diferentes, **unificar o título** no UI final.

---

## 11. Plano de trabalho obrigatório (ordem)

### Fase 0 — Inventário (sem alterar código)

1. Ler `index1..index10`, `gc3..gc10` e prints `agora (1|2|3).jpg`
2. Listar colunas/títulos de cada sistema
3. Produzir matriz: comum / exclusivo / relacionado
4. Propor nomes finais das colunas unificadas
5. Validar encaixe no menu ANÁLISES do app atual

### Fase 1 — Estrutura

1. Criar rota/módulo **Análises Inteligentes Dia de Sorte**
2. Criar shell com 5 abas
3. Ligar item no menu principal

### Fase 2 — Dados & relacionamentos

1. Alimentar Aba 1 com resultados/dígitos
2. Relacionar N dígitos → indexN / gcN
3. Montar Aba 4 (padrões)
4. Montar Aba 5 (Elite Nd)

### Fase 3 — Ações inteligentes

1. Botões Ver Combinações / Gerar gcN / Gerador Elite
2. Deep-link interno por concurso e por N

### Fase 4 — Polimento

1. Exportações (quando fizer sentido)
2. Responsividade / padrão visual local
3. Não regressão das rotas existentes

---

## 12. Resultado esperado

Ao final, o usuário deve conseguir, **em um único módulo do app local**:

1. Ver concursos com dígitos e padrões sem abrir 3 sites;
2. Clicar em um concurso de 8 dígitos e ir direto às combinações de 8;
3. Gerar via `gc8` sem sair do fluxo;
4. Abrir Gerador Elite já no modo 8d;
5. Evitar duplicidade de colunas e retrabalho;
6. Manter o visual/arquitetura do Dia de Sorte local.

---

## 13. Restrições explícitas

- Não alterar funcionalidades que já funcionam, salvo necessidade de integração.
- Não criar dependência obrigatória dos sites Netlify em produção (eles são referência).
- Não inventar colunas que não existam nos sistemas/arquivos analisados sem justificar.
- Não usar o nome `cg` para os arquivos desta pasta (`gc` é o correto).
- Não tratar `geradoresdiadesorte` como secundário.

---

## 14. Entregáveis da IA implementadora

1. Matriz comparativa (comum/exclusivo/relacionado)
2. Proposta final de colunas unificadas
3. Implementação do módulo com 5 abas
4. Navegação `indexN` / `gcN` / Elite Nd
5. Resumo do que foi reaproveitado vs. reescrito

---

## 15. Referências rápidas

### Pasta

```text
D:\Loterias\LoteriasPosicao\AnalisePorPosicao--DiaDeSorte-Only\adaptar
```

### Netlify (principais)

```text
https://resultadosdigitosdiadesorte.netlify.app/
https://geradorpalpitesdiariodiadesorte.netlify.app/
https://geradoresdiadesorte.netlify.app/index8
```

### Prints

```text
agora (1).jpg  → Combinações (geradoresdiadesorte)
agora (2).jpg  → Resultados & Dígitos
agora (3).jpg  → Gerador Elite / Diário
```

---

**Instrução final para a IA:**  
Comece pela Fase 0 (inventário e matriz). Só depois proponha a estrutura de rotas/templates e implemente. O sucesso não é “parecer com o Netlify”; é **unificar o relacionamento dos dados** no padrão do app local.
