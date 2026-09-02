Menu (subitens)
Em Desdobramentos (dropdown):

Modalidade	Novo item	URL
Quina
Quina de São João
/desdobramento-especial/
Mega Sena
Mega da Virada
/desdobramento-especial/
Dupla Sena
Dupla de Páscoa
/desdobramento-especial/
Lotofácil
Lotofácil da Independência
/desdobramento-especial/
Na Mega, o item foi acrescentado ao menu que já tinha Des1 e Des2.

O que cada tela traz
Ciclo ativo (dezenas sorteadas/faltantes no volante)
Último concurso + sincronizar Caixa
Sugestões de colunas (quentes, atrasadas, balanceadas)
PAR / ÍMPAR só por colunas (cabeçalho do volante)
Meta de dezenas com preços da tabela Caixa
Garantias Bronze / Prata / Ouro / Diamante (jogos e total = aposta × jogos)
Volante adaptado:
Quina / Mega / Dupla: finais 1–0 (final10)
Lotofácil: 5 blocos de 5 (bloco5), aposta 6–10 dezenas (com aviso para 15+ usar o Desdobramento Inteligente)
Faixas por especial
Quina: 5–15 dez., até 28 jogos
Mega da Virada: 6–15 dez., até 15 jogos
Dupla de Páscoa: 6–15 dez., até 10 jogos
Lotofácil da Independência: 6–10 dez., até 10 jogos
Como testar
Reinicie cada servidor e abra com Ctrl+F5:

Quina: http://localhost:5155/desdobramento-especial/
Mega: http://localhost:5156/desdobramento-especial/
Dupla: http://localhost:5158/desdobramento-especial/
Lotofácil: http://localhost:5152/desdobramento-especial/


Código compartilhado em LoteriasPosicao/_shared/desdobramento_especial/ (motor, configs, template e rotas). A Quina deixou de usar o template local antigo e passou a usar o módulo compartilhado como as outras três.




# DIRETRIZ GLOBAL DO SISTEMA

Todas as análises desenvolvidas nas rotas 8033, 5151, 5152, 5153, 5154, 5155, 5156, 5157, 5158, 5159 e 5160 devem possuir capacidade opcional de geração inteligente de apostas.

## Conceito

Nenhuma análise deve ser apenas informativa.

Toda análise deve responder duas perguntas:

1. O que os dados mostram?
2. Como transformar esses dados em apostas?

## Nova Arquitetura

Cada análise deverá possuir dois modos:

### Modo Análise

Responsável por:

* Exibir estatísticas.
* Exibir tendências.
* Exibir padrões.
* Exibir gráficos.
* Exibir indicadores.

### Modo Gerar Apostas

Responsável por utilizar os dados calculados pela análise para criar apostas inteligentes.

## Botão Padrão

Adicionar em todas as análises:

[ Gerar Apostas com esta Estratégia ]

ou

[ Criar Jogos Baseados nesta Análise ]

## Funcionamento

Ao clicar no botão:

A IA deverá utilizar automaticamente os resultados já calculados pela análise atual.

Exemplos:

### Análise de Frequência

Gerar apostas privilegiando dezenas mais frequentes.

### Análise de Atraso

Gerar apostas privilegiando dezenas atrasadas.

### Análise de Ciclos

Gerar apostas privilegiando dezenas faltantes do ciclo.

### Análise Posicional

Gerar apostas respeitando padrões posicionais.

### Análise de Repetição

Gerar apostas reproduzindo padrões históricos de repetição.

### Análise de Linhas e Colunas

Gerar apostas respeitando distribuições históricas.

### Análise de Moldura

Gerar apostas respeitando padrões de moldura observados.

### Análise de Padrões

Gerar apostas reproduzindo os padrões encontrados.

## Modo Híbrido

Permitir combinar múltiplas análises.

Exemplo:

* Frequência 40%
* Atraso 20%
* Ciclo 20%
* Repetição 20%

O sistema deverá gerar apostas utilizando simultaneamente os critérios selecionados.

## Objetivo

Transformar o sistema em uma plataforma de decisão.



https://loterias.caixa.gov.br/Paginas/Locais-Sorte.aspx?modalidade=QUINA&concurso=6760&titulo=Quina
https://loterias.caixa.gov.br/Paginas/Locais-Sorte.aspx?modalidade=QUINA&concurso=6462&titulo=Quina
https://loterias.caixa.gov.br/Paginas/Locais-Sorte.aspx?modalidade=QUINA&concurso=6172&titulo=Quina
https://loterias.caixa.gov.br/Paginas/Locais-Sorte.aspx?modalidade=QUINA&concurso=6172&titulo=Quina
https://loterias.caixa.gov.br/Paginas/Locais-Sorte.aspx?modalidade=QUINA&concurso=5590&titulo=Quina