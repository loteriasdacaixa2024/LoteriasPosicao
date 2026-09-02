# -*- coding: utf-8 -*-
"""
Mês da Sorte — regras de seleção (referência rápida)

Arquivo canônico de código: diadesorte/mes_sorte_select.py

| Critério       | Como resolve                         | Aplicação no lote          |
|----------------|--------------------------------------|----------------------------|
| + Atrasado     | Maior atraso histórico               | Mesmo mês em todas         |
| + Frequente    | Maior frequência histórica           | Mesmo mês em todas         |
| Mês fixo 1–12  | Valor escolhido                      | Mesmo mês em todas         |
| + Aleatório    | Blocos 1–12 embaralhados             | 1 mês por aposta, equilibrado |

Bug corrigido (ago/2026):
  Antes, "aleatorio" era resolvido UMA vez (ex.: Dezembro) e repetido em
  todas as apostas/construções do export — aparentava concentração.
  Agora a distribuição é por aposta, sem favorecimento de nenhum mês.

Pontos de uso:
  - Construtor → Exportar .TXT (construção / sessão)
  - Construtor dígitos → export-txt
  - Ciclo de apostas → export / pós-geração
  - Select JS: geradores_elite/static/mes_sorte_select.js
"""
