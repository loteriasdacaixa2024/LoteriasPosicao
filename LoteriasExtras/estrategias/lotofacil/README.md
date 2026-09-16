# Lotofácil — Laboratório de Estratégias

Este é um aplicativo modular em Python para análise e geração de estratégias da Lotofácil.

## Estrutura do Projeto

- `app.py`: Servidor Flask e rotas da API.
- `config/`: Configurações de ambiente.
- `lotofacil/`: Núcleo matemático e estatístico.
    - `analyzer.py`: 6 camadas de análise estatística.
    - `db_manager.py`: Gerenciamento do banco de dados SQLite.
    - `strategies.py`: Algoritmos de geração baseados em critérios.
    - `ranking.py`: Sistema de avaliação de desempenho.
- `static/`: Identidade visual (Roxo Premium) e lógica client-side.
- `templates/`: Interface do usuário.

## Funcionalidades

1. **Análise Proativa**: 6 camadas (Frequência, Estrutura, Composição, Repetição, Padrões e Temporal).
2. **Estratégias Inteligentes**: 4 modelos de geração (Equilíbrio, Frequência, Atrasos e Estrutura).
3. **Simulação de Ranking**: Compare as estratégias por prêmios, acertos ou retorno financeiro.
4. **Exportação Robusta**: Suporte para geração em larga escala com download em TXT e CSV.

## Como Executar

1. Certifique-se de ter o Python instalado.
2. Instale as dependências: `pip install flask`.
3. Execute o aplicativo: `python app.py`.
4. Acesse no navegador: `http://localhost:5001`.

*Nota: Ao iniciar pela primeira vez sem dados, o sistema gera automaticamente 100 resultados de exemplo para demonstração das camadas estatísticas.*


Criado! Inseri perfeitamente o seu pedido dinâmico que funcionará hoje e sempre que você adicionar novas ferramentas no futuro:

Adicionei a função mestre 

renderStrategySummary()
 dentro do motor em JS que recalcula automaticamente e projeta um painel fixo de métricas dinâmico e autoexpandível (abaixo do alerta fixo principal e das guias de layout de estratégia).

O Resumo do Arsenal calculará com exatidão matemática:

O Total consolidado de Categorias base (Abas independentes, atualmente 8).
Quantas estratégias/algoritmos de fato residem e estão classificados como botões funcionais em cada uma daquelas abas base (ex: Estratégia 1: 1 est. | Estratégia 4: 2 est. | Estratégia 8: 1 est.)
Tudo somado a longo prazo para o Total Global com selos contadores coloridos da exata marca.

Dashboard Resumo do Arsenal
===>>>Se no futuro a Estratégia 4 possuir 3 modos de sub-estratégias dentro dela 



(incluindo o Botão dessa Base Inteligente que fizemos hoje), o sistema imediatamente reconhecerá em um milésimo de segundo e refletirá o número novo "3" nos blocos, atualizando o total grandioso do Laboratório.

Recarregue sua tela para visualizar o Dashboard Resumo do Arsenal implantado!