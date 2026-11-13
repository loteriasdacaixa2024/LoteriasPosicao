# Simulador de globo e painel de cores

Módulo em `_shared/simulador_globo`. Nesta fase está ligado só no Dia de Sorte, pelo `extend_simulador_globo_app` em `AnalisePorPosicao--DiaDeSorte-Only/app.py`. O histórico vai para a tabela `simulacao_globo` do `instance/diadesorte.db`. Não há um segundo banco.

A página fica em `/simulador-globo/`, no menu Dados do Dia de Sorte, com três abas: Painel de Cores, Simulador de Sorteios e Histórico. Nesta fase a tela e o menu mostram só o Dia de Sorte: 31 dezenas, 7 números e 1 mês. As regras das outras modalidades continuam no código, cada uma com o próprio globo, e só entram na tela quando o Dia de Sorte estiver validado.

## Cores

A cor só acompanha o algarismo final. O resultado do sorteio é o número. A tabela está em `cores.py`:

| Final | Cor |
| --- | --- |
| 1 | Vermelha |
| 2 | Amarela |
| 3 | Verde |
| 4 | Marrom |
| 5 | Azul |
| 6 | Rosa |
| 7 | Preta |
| 8 | Cinza |
| 9 | Laranja |
| 0 | Branca |

A mesma regra vale para 00–99 e para os dígitos do Super Sete. Um ajuste de uma modalidade entra em `OVERRIDES_FINAL`, sem mudar as outras. Lotofácil e Dia de Sorte não ficam com a mesma quantidade em cada cor, porque o universo não é múltiplo de 10.

## Sorteio

O servidor sorteia com `secrets.SystemRandom`. Cada bola que ainda está na etapa tem a mesma chance. Não há repetição dentro da etapa e o resultado não usa o histórico oficial.

| Modalidade | Globo | O que sai |
| --- | --- | --- |
| Mega-Sena | 01–60 | 6 |
| Lotofácil | 01–25 | 15 |
| Quina | 01–80 | 5 |
| Lotomania | 00–99 | 20 |
| Timemania | 01–80 | 7 e, depois, 1 time |
| Dia de Sorte | 01–31 | 7 e, depois, 1 mês |
| Dupla Sena | 01–50 | dois sorteios de 6; o globo é recarregado |
| +Milionária | 01–50 | 6 e, depois, 2 trevos |
| Super Sete | 7 colunas de 0–9 | 1 dígito por coluna; o dígito pode repetir entre colunas |

O intervalo começa em 5 segundos e pode ir de 1 a 10. Pausar interrompe a próxima saída. Finalizar grava só as bolas que já saíram. Reiniciar abre outra simulação.

A animação usa Three.js r149, copiado em `static/vendor/three.min.js` (licença MIT). Se o navegador não abrir WebGL, o globo aparece em vista simplificada e a ordem do sorteio continua a mesma.

A simulação é experimental e educativa. Ela não representa o sorteio da Caixa.

## Uso

1. No Dia de Sorte, abra Dados e depois Simulador de Sorteios.
2. No painel, escolha outra modalidade para ver a distribuição. O simulador e o histórico continuam na modalidade da aplicação aberta.
3. Em Simulador de Sorteios: Preparar Bolas, Iniciar Sorteio, e use Pausar, Continuar, Reiniciar ou Finalizar Sorteio.
4. Em Histórico, Ver mostra o registro. Rever no globo só anima de novo, sem gravar outro sorteio.

Os testes estão em `test_simulador_globo.py`.
