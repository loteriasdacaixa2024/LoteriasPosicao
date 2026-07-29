# Fase 0 — Matriz Comparativa (Análises Inteligentes Dia de Sorte)

Gerado conforme o prompt profissional. Constantes DDS: **01–31**, **7 dezenas**, **mês da sorte**.

## Campos comuns (não duplicar no UI)

| Campo | A | B | C |
|-------|---|---|---|
| Concurso | ✓ | ✓ | — |
| Data | ✓ | ✓ | — |
| Dezenas | ✓ | ✓ | saída do Gerar |
| Quantidade de Dígitos (N) | ✓ | ✓ | chave do catálogo |

## Exclusivos

| Campo | Origem | Aba final |
|-------|--------|-----------|
| Dígitos (ordem) | A | 1 |
| Dígitos Ordenados | A | 1 / 4 |
| Combinações / volume | A / C | 1 (atalho) + 2 |
| Gerador Pro gcN | A / C | 1 (atalho) + 3 |
| Mês | B | 1 / 4 |
| Padrão Inicial / Final | B | 4 |
| Pares / Ímpares | B | 4 |
| Não Saíram | B | 4 |
| Catálogo C(10,N) | C | 2 |
| Geração Elite 3d–9d | B | 5 |

## Colunas unificadas (implementadas)

`concurso · data · dezenas · mes · digitos · digitos_ordenados · qtd_digitos · volume_combinacoes · padrao_inicial · padrao_final · pares/impares · nao_sairam · acoes`

## Relacionamentos

1. **Concurso** une Resultados ↔ Padrões  
2. **N = qtd_digitos** une Resultados ↔ indexN ↔ gcN ↔ Elite Nd  
3. **Conjunto de dígitos** abre a combinação certa no catálogo / gc / elite  

## Observação técnica

Os HTML `adaptar/index*` e `adaptar/gc*` ainda trazem títulos Mega Sena; a lógica foi **adaptada** para Dia de Sorte no serviço Python (`MAX_DEZENA=31`, `TAMANHO_JOGO=7`).
