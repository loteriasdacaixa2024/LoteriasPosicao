function openTab(event, tabName) {
    const contents = document.getElementsByClassName('tab-content');
    const buttons = document.getElementsByClassName('tab-btn');

    for (let content of contents) content.classList.remove('active');
    for (let btn of buttons) btn.classList.remove('active');

    document.getElementById(tabName).classList.add('active');
    if (event) event.currentTarget.classList.add('active');

    if (tabName === 'analise') {
        const activeSubBtn = document.querySelector('#analise .sub-tab-btn.active');
        if (!activeSubBtn) {
            document.querySelector('#analise .sub-tab-btn').click();
        }
        loadStats();
    }
}

function openSubTab(event, parentId, subTabId) {
    const container = document.getElementById(parentId);
    const contents = container.getElementsByClassName('sub-tab-content');
    const buttons = container.getElementsByClassName('sub-tab-btn');

    for (let content of contents) content.classList.remove('active');
    for (let btn of buttons) btn.classList.remove('active');

    document.getElementById(subTabId).classList.add('active');
    if (event) event.currentTarget.classList.add('active');

    // Trigger Visual Analysis when Layer 5 (Patterns) is selected
    if (subTabId === 'layer5') {
        initVisualAnalysis();
    }
}

function toggleCustomCount() {
    const select = document.getElementById('count-select');
    const input = document.getElementById('custom-count');
    input.style.display = (select.value === 'custom') ? 'inline-block' : 'none';
}

function toggleRankingHelp() {
    const box = document.getElementById('ranking-help');
    box.style.display = (box.style.display === 'none') ? 'block' : 'none';
}

function toggleStrategiesHelp() {
    const box = document.getElementById('strategies-help');
    box.style.display = (box.style.display === 'none') ? 'block' : 'none';
}

function toggleLayersHelp() {
    const box = document.getElementById('layers-help');
    box.style.display = (box.style.display === 'none') ? 'block' : 'none';
}

function selectStrategy(id) {
    const tabs = document.getElementsByClassName('strat-tab');
    for (let tab of tabs) {
        tab.classList.remove('active');
        if (parseInt(tab.dataset.id) === id) tab.classList.add('active');
    }
    document.getElementById('strategy-id').value = id;

    const info = document.getElementById('strategy-info');
    const content = {
        1: {
            title: "Estratégia 1 — Equilíbrio Estatístico",
            desc: "Esta estratégia gera jogos que seguem os padrões estatísticos mais comuns da Lotofácil.",
            rules: ["Proporção par/ímpar equilibrada", "Equilíbrio entre números baixos/altos", "Faixa de soma típica", "Distribuição equilibrada no volante"]
        },
        2: {
            title: "Estratégia 2 — Frequência Inteligente",
            desc: "Prioriza dezenas com maior frequência histórica, otimizando a combinação de números 'quentes'.",
            rules: ["Foco em números mais sorteados", "Inclusão controlada de números neutros", "Evita números excessivamente frios"]
        },
        3: {
            title: "Estratégia 3 — Atrasos Controlados",
            desc: "Foca em números que estão ligeiramente atrasados dentro de seu ciclo esperado.",
            rules: ["Identifica dezenas em fim de ciclo", "Prioriza números com atraso médio", "Evita dezenas em super atraso estatístico"]
        },
        4: {
            title: "Estratégia 4 — Modelo Híbrido",
            desc: "Combina frequência, atraso e equilíbrio estatístico em um modelo ponderado.",
            rules: ["Mix de dezenas quentes e frias", "Filtros estatísticos rigorosos", "Otimização de cobertura espacial"]
        },
        5: {
            title: "Estratégia 5 — Redução de Universo",
            desc: "Reduz o universo de 25 números para um subconjunto definido por você, aumentando as chances matemáticas.",
            rules: ["Geração restrita ao subconjunto selecionado", "Maior densidade de acertos no universo reduzido", "Flexibilidade total de escolha manual ou IA"]
        },
        6: {
            title: "Estratégia 6 — Fechamento Matemático",
            desc: "Desenvolve matrizes que garantem premiações mínimas caso as dezenas sorteadas estejam no seu grupo.",
            rules: ["Garantia de 13 ou 14 pontos (Wheeling)", "Otimização de custo/benefício no volume de jogos", "Estrutura lógica de alta performance"]
        },
        7: {
            title: "Estratégia 7 — Dezenas Fixas + Variáveis",
            desc: "Ideal para manter sua base de números favoritos enquanto o sistema busca as melhores dezenas complementares.",
            rules: ["Fixação de até 12 dezenas estratégicas", "Complementação via camadas de Inteligência Artificial", "Alta probabilidade de prêmios acumulados se as fixas saírem"]
        },
        8: {
            title: "Estratégia 8 — Filtro Prospectivo",
            desc: "Utiliza algoritmos de regressão para identificar dezenas próximas da quebra de ciclo estatístico.",
            rules: ["Foco em dezenas 'quentes' que devem retornar", "Análise de ciclo temporal dinâmico", "Equilíbrio de probabilidade prospectiva"]
        },
        9: {
            title: "Estratégia 9 — Topologia (Moldura/Centro)",
            desc: "Um gerador de combinações focado exclusivamente na proporção ideal geométrica do volante.",
            rules: ["Apenas jogos com 9 a 10 dezenas na moldura", "Isola os 9 números principais do miolo", "Garante o 'sweet spot' geométrico da Lotofácil"]
        },
        10: {
            title: "Estratégia 10 — Matriz de Afinidade",
            desc: "Analisa a probabilidade conjunta. Quais dezenas gostam de sair ao mesmo tempo? Esta estratégia prioriza essas amizades numéricas.",
            rules: ["Análise de pares combinados", "Machine Learning leve para identificar afinidades", "Jogos extremamente sinérgicos matematicamente"]
        },
        11: {
            title: "Estratégia 11 — Inversão de Frequência",
            desc: "Focada na 'fadiga' da dezena. Aposta no encerramento abrupto das sequências de dezenas excessivamente quentes.",
            rules: ["Corta dezenas super-quentes implacavelmente", "Evita armadilhas de repetição viciada", "Ideal para desviar do padrão geral (Zebras)"]
        }
    };

    const s = content[id];
    info.innerHTML = `
        <h4>${s.title}</h4>
        <p>${s.desc}</p>
        <ul>${s.rules.map(r => `<li>${r}</li>`).join('')}</ul>
    `;

    // Toggle Strategy Interfaces
    const strat4 = document.getElementById('strategy-4-interface');
    if (strat4) strat4.style.display = (id === 4) ? 'block' : 'none';
    document.getElementById('strategy-5-interface').style.display = (id === 5) ? 'block' : 'none';
    document.getElementById('strategy-6-interface').style.display = (id === 6) ? 'block' : 'none';
    document.getElementById('strategy-7-interface').style.display = (id === 7) ? 'block' : 'none';
    document.getElementById('strategy-8-interface').style.display = (id === 8) ? 'block' : 'none';

    if (id === 5) initUniverseGrid();
    if (id === 6) initWheelingGrid();
    if (id === 7) initFixedGrid();
    if (id === 8) loadTrendAnalysis();
}

let selectedUniverse = [];
let selectedWheeling = [];
let selectedFixed = [];

// --- INTELLIGENT BASE STRATEGY 4 LOGIC ---
let intelligentRotationIndex = 0;
let intelligentBaseArr = [];

async function generateIntelligentBase() {
    const limits = [5, 20, 50]; // Rotação Dinâmica: últimos 5, 20 ou 50 concursos.
    const limit = limits[intelligentRotationIndex % 3];
    intelligentRotationIndex++;

    document.getElementById('dyn-rotation-status').innerText = `Últimos ${limit} concursos`;

    try {
        const res = await fetch(`/api/history?limit=${limit}`);
        const history = await res.json();

        let freq = {};
        let atraso = {};
        for (let i = 1; i <= 25; i++) { freq[i] = 0; atraso[i] = -1; }

        // history is [most_recent, ..., oldest]
        history.forEach((draw, dIdx) => {
            const dezenas = draw.dezenas || draw.bolas || [];
            dezenas.forEach(n => {
                freq[n] = (freq[n] || 0) + 1;
                // Since 0 is most recent, the first time we see it is its actual delay
                if (atraso[n] === -1) atraso[n] = dIdx;
            });
        });

        for (let i = 1; i <= 25; i++) {
            if (atraso[i] === -1) atraso[i] = limit;
        }

        let scores = [];
        for (let i = 1; i <= 25; i++) {
            // (frequência * 0.6) + (atraso * 0.4) + leve aleatoriedade para variação entre empates
            const randomFactor = (Math.random() * 0.2) - 0.1;
            const s = (freq[i] * 0.6) + (atraso[i] * 0.4) + randomFactor;
            scores.push({ dez: i, score: s });
        }

        scores.sort((a, b) => b.score - a.score);

        const groupA = scores.slice(0, 8).map(x => x.dez);
        const groupB = scores.slice(8, 17).map(x => x.dez);
        const groupC = scores.slice(17, 25).map(x => x.dez);

        let base = [];
        let iA = 0, iB = 0, iC = 0;
        const pattern = ['A', 'B', 'A', 'C', 'B', 'A', 'C'];
        let pIdx = 0;

        while (base.length < 25) {
            let nextGroup = pattern[pIdx % pattern.length];
            pIdx++;

            if (nextGroup === 'A' && iA < groupA.length) {
                base.push(groupA[iA++]);
            } else if (nextGroup === 'B' && iB < groupB.length) {
                base.push(groupB[iB++]);
            } else if (nextGroup === 'C' && iC < groupC.length) {
                base.push(groupC[iC++]);
            } else {
                if (iA < groupA.length) base.push(groupA[iA++]);
                else if (iB < groupB.length) base.push(groupB[iB++]);
                else if (iC < groupC.length) base.push(groupC[iC++]);
            }
        }

        intelligentBaseArr = base;

        const grid = document.getElementById('intelligent-base-grid');
        grid.innerHTML = `<div style="font-family: monospace; font-size: 1.1rem; font-weight: bold; color: var(--primary); padding: 10px; background: #fdf2ff; border-radius: 8px; border: 1px dashed var(--primary); text-align: center; width: 100%; word-break: break-all;">` +
            base.map(n => n.toString().padStart(2, '0')).join(' - ') +
            `</div>`;

        document.getElementById('intelligent-base-box').style.display = 'block';
        document.getElementById('intelligent-game-selector').value = "0";
        renderIntelligentGame();

    } catch (e) {
        console.error(e);
        alert("Erro ao gerar base inteligente.");
    }
}

function renderIntelligentGame() {
    if (!intelligentBaseArr.length) return;
    const offset = parseInt(document.getElementById('intelligent-game-selector').value);

    // Janelas deslizantes: 15 dezenas com base no offset selecionado (0 a 10)
    const game = intelligentBaseArr.slice(offset, offset + 15);

    // Exibição do jogo ordenado
    document.getElementById('intelligent-game-view').innerHTML =
        game.sort((a, b) => a - b).map(n => n.toString().padStart(2, '0')).join(' - ');
}
// --- END INTELLIGENT BASE STRATEGY 4 LOGIC ---


function initWheelingGrid() {
    const grid = document.getElementById('wheeling-grid');
    if (grid.children.length > 0) return;

    for (let i = 1; i <= 25; i++) {
        const cell = document.createElement('div');
        cell.className = 'num-cell pointer';
        cell.innerText = i.toString().padStart(2, '0');
        cell.dataset.num = i;
        cell.onclick = () => toggleWheelingNumber(i);
        grid.appendChild(cell);
    }
}

function toggleWheelingNumber(num) {
    const type = document.getElementById('wheeling-type').value;
    const limit = parseInt(type.split('_')[0]);
    const idx = selectedWheeling.indexOf(num);

    if (idx > -1) {
        selectedWheeling.splice(idx, 1);
    } else {
        if (selectedWheeling.length >= limit) {
            alert(`Para este fechamento, selecione exatamente ${limit} números.`);
            return;
        }
        selectedWheeling.push(num);
    }
    renderWheelingSelection();
}

function renderWheelingSelection() {
    const cells = document.querySelectorAll('#wheeling-grid .num-cell');
    cells.forEach(cell => {
        const n = parseInt(cell.dataset.num);
        if (selectedWheeling.includes(n)) cell.classList.add('active');
        else cell.classList.remove('active');
    });
    const type = document.getElementById('wheeling-type').value;
    const limit = parseInt(type.split('_')[0]);
    document.getElementById('wheeling-status').innerText = `${selectedWheeling.length} / ${limit}`;
}

function initFixedGrid() {
    const grid = document.getElementById('fixed-grid');
    if (grid.children.length > 0) return;

    for (let i = 1; i <= 25; i++) {
        const cell = document.createElement('div');
        cell.className = 'num-cell pointer';
        cell.innerText = i.toString().padStart(2, '0');
        cell.dataset.num = i;
        cell.onclick = () => toggleFixedNumber(i);
        grid.appendChild(cell);
    }
}

function toggleFixedNumber(num) {
    const idx = selectedFixed.indexOf(num);
    if (idx > -1) {
        selectedFixed.splice(idx, 1);
    } else {
        if (selectedFixed.length >= 12) {
            alert("Limite máximo de 12 dezenas fixas atingido.");
            return;
        }
        selectedFixed.push(num);
    }
    renderFixedSelection();
}

function renderFixedSelection() {
    const cells = document.querySelectorAll('#fixed-grid .num-cell');
    cells.forEach(cell => {
        const n = parseInt(cell.dataset.num);
        if (selectedFixed.includes(n)) cell.classList.add('active');
        else cell.classList.remove('active');
    });
    document.getElementById('fixed-status').innerText = selectedFixed.length;
}

async function loadTrendAnalysis() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const trendDiv = document.getElementById('trend-numbers');

        // Logical "Trend": High Freq + Delay >= 3
        const freqTop = data.frequency.most_frequent.map(x => x[0]).slice(0, 15);
        const trends = freqTop.filter(n => data.temporal[n] >= 2);

        trendDiv.innerHTML = trends.map(n => `
            <div class="num-badge-premium" style="border-color: #f39c12; background: #fffdf5 !important;">
                <span class="num" style="color: #f39c12;">${n.toString().padStart(2, '0')}</span>
                <span class="label">Atraso: ${data.temporal[n]}</span>
            </div>
        `).join('') || "Nenhuma dezena em tendência crítica no momento.";
    } catch (e) {
        console.error(e);
    }
}

function updateUniverseLimit() {
    const limit = parseInt(document.getElementById('universe-size').value);
    document.getElementById('selection-status').innerText = `${selectedUniverse.length} / ${limit}`;

    // If current selection exceeds new limit, trim it
    if (selectedUniverse.length > limit) {
        selectedUniverse = selectedUniverse.slice(0, limit);
        renderUniverseSelection();
    }
}

function toggleUniverseNumber(num) {
    const limit = parseInt(document.getElementById('universe-size').value);
    const idx = selectedUniverse.indexOf(num);

    if (idx > -1) {
        selectedUniverse.splice(idx, 1);
    } else {
        if (selectedUniverse.length >= limit) {
            alert(`Você só pode selecionar até ${limit} números para este universo.`);
            return;
        }
        selectedUniverse.push(num);
    }
    renderUniverseSelection();
}

function renderUniverseSelection() {
    const cells = document.querySelectorAll('#universe-grid .num-cell');
    cells.forEach(cell => {
        const n = parseInt(cell.dataset.num);
        if (selectedUniverse.includes(n)) {
            cell.classList.add('active');
        } else {
            cell.classList.remove('active');
        }
    });
    const limit = parseInt(document.getElementById('universe-size').value);
    document.getElementById('selection-status').innerText = `${selectedUniverse.length} / ${limit}`;
    document.getElementById('selection-status').style.color = selectedUniverse.length === limit ? '#2e7d32' : 'var(--primary)';
}

async function suggestUniverse() {
    const limit = parseInt(document.getElementById('universe-size').value);
    const hybrid = document.getElementById('hybrid-mode').checked;

    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        let suggested = [];
        if (hybrid) {
            // LAYER 1: 60% top frequency
            const freq = data.frequency.most_frequent.map(x => x[0]);
            const topFreq = freq.slice(0, Math.floor(limit * 0.6));

            // LAYER 4 & 6: Repetition and Temporal (Pick some that didn't come out but are due)
            const delayed = Object.entries(data.temporal)
                .sort((a, b) => b[1] - a[1])
                .map(x => parseInt(x[0]));

            const pickedDelayed = delayed.slice(0, Math.ceil(limit * 0.2));

            // Combine and fill with rest of frequency to reach limit
            let combined = new Set([...topFreq, ...pickedDelayed]);

            let i = 0;
            while (combined.size < limit && i < freq.length) {
                combined.add(freq[i]);
                i++;
            }

            suggested = Array.from(combined).slice(0, limit);
        } else {
            // Simple frequency
            suggested = data.frequency.most_frequent.map(x => x[0]).slice(0, limit);
        }

        selectedUniverse = suggested.sort((a, b) => a - b);
        renderUniverseSelection();
    } catch (e) {
        console.error(e);
    }
}

function parseBrazilianNumber(val) {
    if (!val) return 0;
    return parseInt(val.toString().replace(/\./g, ''));
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        if (data.error) {
            console.error(data.error);
            await fetch('/api/debug/populate');
            loadStats();
            return;
        }

        renderFrequency(data.frequency);
        renderStructure(data.structure);
        renderComposition(data.composition);
        renderRepetition(data.repetition);
        renderPatterns(data.patterns);
        renderTemporal(data.temporal);

        // Update Insights in each layer
        updateAnalysisInsights(data.base_ranking);
    } catch (e) {
        console.error("Erro ao carregar estatísticas:", e);
    }
}

function updateAnalysisInsights(ranking) {
    if (!ranking || ranking.length === 0) return;

    const topStratName = ranking[0][0]; // "Estratégia X"
    const score = ranking[0][1].avg_hits.toFixed(2);

    // Highlighted strategy name
    const highlightedStrat = `<span style="font-size: 1.2rem; font-weight: 800; color: var(--primary); text-decoration: underline;">${topStratName}</span>`;

    const insightText = `💡 <b>Sugestão:</b> Com base nos dados acima, a ${highlightedStrat} está apresentando o melhor desempenho atual (Score: <b>${score}</b>). <b>Use a ${highlightedStrat} para gerar suas apostas!</b>`;

    // Apply to all 6 layers
    for (let i = 1; i <= 6; i++) {
        const el = document.getElementById(`insight-layer${i}`);
        if (el) el.innerHTML = insightText;
    }
}

function renderFrequency(data) {
    const topDiv = document.getElementById('freq-top');
    const chartDiv = document.getElementById('freq-chart');

    const top5 = data.most_frequent.slice(0, 5);
    topDiv.innerHTML = top5.map(x => `
        <div class="num-badge-premium">
            <span class="num">${x[0].toString().padStart(2, '0')}</span>
            <span class="label">${x[1]} Sorteios</span>
        </div>
    `).join('');

    const maxFreq = Math.max(...data.most_frequent.map(y => y[1]));
    chartDiv.innerHTML = data.most_frequent.slice(0, 10).map(x => `
        <div style="font-size: 0.85rem; display: flex; justify-content: space-between; margin-top: 10px;">
            <span>Dezena <b>${x[0].toString().padStart(2, '0')}</b></span>
            <span style="color: #666;">${x[1]}x</span>
        </div>
        <div class="stat-bar"><div class="stat-fill" style="width: ${(x[1] / maxFreq) * 100}%"></div></div>
    `).join('');
}

function renderStructure(data) {
    const gridLines = document.getElementById('volante-lines');
    const gridCols = document.getElementById('volante-cols');
    const detailsGrid = document.getElementById('line-details-grid');
    const patternsList = document.getElementById('line-patterns-list');

    if (!gridLines || !gridCols) return;

    gridLines.innerHTML = '';
    gridCols.innerHTML = '';

    const latestL = data.latest_lines;
    const latestC = data.latest_cols;

    for (let i = 1; i <= 25; i++) {
        // Line Cell
        const lineIdx = Math.floor((i - 1) / 5);
        const intensityL = (latestL[lineIdx] / 5);
        const cellL = document.createElement('div');
        cellL.className = 'num-cell';
        cellL.innerText = i.toString().padStart(2, '0');
        if (latestL[lineIdx] > 0) {
            cellL.classList.add('active');
            cellL.style.background = `rgba(103, 38, 102, ${0.2 + (intensityL * 0.8)})`;
            cellL.style.color = intensityL > 0.6 ? 'white' : 'inherit';
        }
        gridLines.appendChild(cellL);

        // Column Cell
        const colIdx = (i - 1) % 5;
        const intensityC = (latestC[colIdx] / 5);
        const cellC = document.createElement('div');
        cellC.className = 'num-cell';
        cellC.innerText = i.toString().padStart(2, '0');
        if (latestC[colIdx] > 0) {
            cellC.classList.add('active');
            cellC.style.background = `rgba(103, 38, 102, ${0.2 + (intensityC * 0.8)})`;
            cellC.style.color = intensityC > 0.6 ? 'white' : 'inherit';
        }
        gridCols.appendChild(cellC);
    }

    // Detailed Line Stats
    if (data.per_line_details && detailsGrid) {
        detailsGrid.innerHTML = data.per_line_details.map(d => `
            <div class="stat-item" style="text-align: left; padding: 12px; border: 1px solid #eee; border-radius: 8px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
                <p style="font-weight: 800; color: var(--primary); font-size: 0.8rem; margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; text-transform: uppercase;">Linha ${d.line}</p>
                <div style="font-size: 0.75rem; line-height: 1.6;">
                    <p>🔥 Top: <b style="color: #d32f2f;">${d.most_frequent.toString().padStart(2, '0')}</b></p>
                    <p>❄️ Frio: <b style="color: #1976d2;">${d.least_frequent.toString().padStart(2, '0')}</b></p>
                    <p>📊 Méd: <b>${d.avg_count.toFixed(1)}</b> dezenas</p>
                    <div style="margin-top: 5px; background: #fafafa; padding: 4px; border-radius: 4px; border: 1px solid #f0f0f0;">
                        <span style="font-size: 0.65rem; color: #888; display: block; text-transform: uppercase;">Sub-padrões TOP:</span>
                        <div style="font-weight: 700; color: var(--primary); font-size: 0.7rem;">
                            ${d.top_subsets.map(s => `[${s.join(',')}]`).join(' ')}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Predominant Patterns
    if (data.most_common_patterns && patternsList) {
        patternsList.innerHTML = data.most_common_patterns.map((p, idx) => `
            <div style="background: white; border: 2px solid ${idx === 0 ? 'var(--primary)' : '#eee'}; padding: 6px 14px; border-radius: 20px; font-weight: 800; font-size: 0.85rem; color: ${idx === 0 ? 'var(--primary)' : '#777'}; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1rem;">${idx === 0 ? '🥇' : idx === 1 ? '🥈' : '🥉'}</span> 
                [${p.join(', ')}]
            </div>
        `).join('');
    }
}

function renderComposition(data) {
    const stats = data.all_stats;
    const last = stats[stats.length - 1];
    const parityWinner = data.most_common_parity;

    // Summary Cards
    document.getElementById('comp-stats').innerHTML = `
        <div class="stat-item">
            <div class="section-title">Paridade Atual</div>
            <div style="font-size: 1.2rem;"><b>${last.pares}</b>P / <b>${last.impares}</b>I</div>
        </div>
        <div class="stat-item">
            <div class="section-title">Amplitude Atual</div>
            <div style="font-size: 1.2rem;"><b>${last.baixos}</b>B / <b>${last.altos}</b>A</div>
        </div>
        <div class="stat-item">
            <div class="section-title">Primos / Soma</div>
            <div style="font-size: 1.2rem; color: var(--primary);"><b>${last.primos}</b> Primos | <b>${last.soma}</b></div>
        </div>
    `;

    // NEW: Primes Winner List
    const primesList = document.getElementById('primes-winner-list');
    if (data.most_common_primes && primesList) {
        primesList.innerHTML = data.most_common_primes.map((p, idx) => `
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span>${idx + 1}º: ${p[0]} dezenas</span>
                <span style="color: #888;">${((p[1] / stats.length) * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    }

    // NEW: Sum Ranges Winner List
    const sumList = document.getElementById('sum-winner-list');
    if (data.most_common_sum_range && sumList) {
        sumList.innerHTML = data.most_common_sum_range.map((p, idx) => `
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span>${idx + 1}º: ${p[0]}</span>
                <span style="color: #888;">${((p[1] / stats.length) * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    }

    // Parity Dominance / Winner Pattern
    if (parityWinner) {
        const ratio = parityWinner[0]; // e.g., "7P / 8I"
        const freqRatio = ((parityWinner[1] / stats.length) * 100).toFixed(1);

        document.getElementById('winning-parity-ratio').innerText = ratio;
        document.getElementById('winning-parity-freq').innerText = `${freqRatio}% de ocorrência histórica`;

        // Description logic
        const pNum = parseInt(ratio.split('P')[0]);
        let desc = "Misto Equilibrado";
        if (pNum >= 10 || pNum <= 5) desc = "Dominância Forte";
        else if (pNum >= 9 || pNum <= 6) desc = "Tendência Misturada";

        document.getElementById('winning-parity-desc').innerText = desc;
    }

    // Parity Distribution List
    const distList = document.getElementById('parity-dist-list');
    if (data.parity_distribution && distList) {
        distList.innerHTML = data.parity_distribution.map((d, i) => {
            const pct = ((d[1] / stats.length) * 100).toFixed(1);
            return `
                <div style="background: white; border: 1px solid ${i === 0 ? 'var(--primary)' : '#ddd'}; padding: 5px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700;">
                    ${d[0]} <span style="font-size: 0.7rem; color: #888; margin-left: 5px;">${pct}%</span>
                </div>
            `;
        }).join('');
    }

    // Insight Layer 3
    const insight3 = document.getElementById('insight-layer3');
    if (insight3 && data.most_common_primes && data.most_common_sum_range) {
        const topPrimes = data.most_common_primes[0][0];
        const topSum = data.most_common_sum_range[0][0];
        insight3.innerHTML = `💡 <b>Dica de Ouro:</b> No histórico, o mais comum é saírem <b>${topPrimes}</b> números primos e a soma total ficar entre <b>${topSum}</b>. Jogos muito fora disso são raros!`;
    }
}

function renderRepetition(data) {
    const last = data[data.length - 1];
    document.getElementById('rep-stats').innerHTML = last;
}

function renderPatterns(data) {
    document.getElementById('pattern-stats').innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="section-title">Última Sequência</div>
                <div style="font-size: 2rem;"><b>${data.max_sequences[data.max_sequences.length - 1]}</b></div>
                <p class="small-note">Números contíguos</p>
            </div>
            <div class="stat-item">
                <div class="section-title">Média Histórica</div>
                <div style="font-size: 2rem;"><b>${data.avg_max_sequence.toFixed(1)}</b></div>
            </div>
        </div>
    `;

    // NEW: Ending Patterns
    const endsList = document.getElementById('ending-patterns-list');
    if (data.common_ending_patterns && endsList) {
        endsList.innerHTML = data.common_ending_patterns.map((p, idx) => `
            <div style="background: white; border: 1px solid #ddd; padding: 5px 12px; border-radius: 12px; font-size: 0.8rem;">
                <b style="color: var(--primary);">${p[0]}x</b> repetição final
            </div>
        `).join('');
    }

    const insight5 = document.getElementById('insight-layer5');
    if (insight5 && data.common_ending_patterns) {
        insight5.innerHTML = `💡 <b>Análise de Finais:</b> É extremamente comum que pelo menos <b>${data.common_ending_patterns[0][0]} dezenas</b> terminem com o mesmo dígito (ex: 04, 14, 24).`;
    }
}

function renderTemporal(data) {
    const sorting = Object.entries(data).sort((a, b) => b[1] - a[1]);
    document.getElementById('temporal-stats').innerHTML = `
        <div class="stats-grid">
            <div class="stat-item" style="border-bottom: 3px solid #d32f2f;">
                <div class="section-title">Dezena Mais Atrasada</div>
                <div style="font-size: 2.5rem; color: #d32f2f; font-weight: 900;">${sorting[0][0]}</div>
                <p>Ausente há <b>${sorting[0][1]}</b> concursos</p>
            </div>
            <div class="stat-item" style="border-bottom: 3px solid #2e7d32;">
                <div class="section-title">Fim de Ciclo Próximo</div>
                <div style="font-size: 2rem;"><b>~4</b></div>
                <p>Concursos Médios</p>
            </div>
        </div>
    `;

    // Calculate Cycle
    const cycleNumbers = Object.entries(data).filter(x => x[1] > 0).map(x => parseInt(x[0])).sort((a, b) => a - b);
    const missingInCycle = sorting.filter(x => x[1] > 0).map(x => parseInt(x[0]));
    const cycleProgress = ((25 - missingInCycle.length) / 25 * 100).toFixed(0);

    document.getElementById('cycle-progress').innerText = `${cycleProgress}%`;
    const cycleContainer = document.getElementById('cycle-numbers');

    if (missingInCycle.length === 0) {
        cycleContainer.innerHTML = "<p style='color:#2e7d32; font-weight:bold;'>O ciclo acaba de se fechar! Todas as dezenas foram sorteadas.</p>";
    } else {
        cycleContainer.innerHTML = missingInCycle.sort((a, b) => b - a).map(n => `
            <div class="num-badge-premium" style="min-width: 50px; padding: 5px; border-color: #f39c12;">
                <span class="num" style="font-size: 1.2rem; color: #f39c12;">${n.toString().padStart(2, '0')}</span>
                <span class="label">Há ${data[n]}x</span>
            </div>
        `).join('');
    }
}

async function generateGames() {
    const stratId = document.getElementById('strategy-id').value;
    const countSelect = document.getElementById('count-select').value;
    const customVal = document.getElementById('custom-count').value;
    const criterion = document.querySelector('input[name="rank-crit"]:checked').value;
    const sampleSize = parseInt(document.getElementById('ranking-sample').value) || 500;

    let count = (countSelect === 'custom') ? parseBrazilianNumber(customVal) : parseInt(countSelect);
    if (isNaN(count) || count <= 0) {
        alert("Por favor, insira uma quantidade válida.");
        return;
    }

    const warning = document.getElementById('warning-large');
    const gamesDisplay = document.getElementById('games-display');
    const stratTag = document.getElementById('active-strat-tag');
    const genBtn = event?.target || document.querySelector('.controls button');
    const originalText = genBtn.innerText;

    // Subtle feedback
    if (genBtn.tagName === 'BUTTON') {
        genBtn.disabled = true;
        genBtn.innerText = "Calculando...";
    }
    gamesDisplay.style.opacity = '0.7';

    if (count > 1000) {
        warning.style.display = 'block';
        gamesDisplay.innerHTML = "<em>Visualização desabilitada para grandes quantidades. Use o botão acima para baixar.</em>";
    } else {
        warning.style.display = 'none';
        gamesDisplay.innerHTML = "Gerando jogos estatísticos...";
    }

    if (stratId == 5 && selectedUniverse.length < 15) {
        alert("Selecione pelo menos 15 números para o universo reduzido.");
        return;
    }

    if (stratId == 7 && (selectedFixed.length < 5 || selectedFixed.length > 12)) {
        alert("Selecione entre 5 e 12 dezenas fixas.");
        return;
    }

    if (stratId == 6) {
        const type = document.getElementById('wheeling-type').value;
        const limit = parseInt(type.split('_')[0]);
        if (selectedWheeling.length !== limit) {
            alert(`Selecione exatamente ${limit} números para o fechamento.`);
            return;
        }
    }

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                strategy_id: parseInt(stratId),
                count: count,
                ranking_criterion: criterion,
                universe: selectedUniverse,
                fixed_numbers: selectedFixed,
                wheeling_numbers: selectedWheeling,
                wheeling_type: document.getElementById('wheeling-type') ? document.getElementById('wheeling-type').value : null,
                ranking_sample: sampleSize
            })
        });
        const data = await res.json();

        if (count <= 1000) {
            gamesDisplay.innerHTML = data.games.map((g, i) => `
                <div class="game-line" style="animation: fadeIn 0.3s ease-out forwards;">
                    <span class="game-num">${(i + 1)}</span>
                    <span class="game-content">${g.map(n => n.toString().padStart(2, '0')).join(' ')}</span>
                </div>
            `).join('');

            // Show which strategy was used
            stratTag.innerText = `Estratégia ${stratId}`;
            stratTag.style.display = 'inline-block';
            gamesDisplay.scrollTop = 0;
        }

        renderRanking(data.ranking, criterion);
    } catch (e) {
        console.error(e);
        gamesDisplay.innerHTML = "Erro ao gerar jogos.";
    } finally {
        if (genBtn.tagName === 'BUTTON') {
            genBtn.disabled = false;
            genBtn.innerText = originalText;
        }
        gamesDisplay.style.opacity = '1';
    }
}

function renderRanking(ranking, criterion) {
    const body = document.getElementById('ranking-body');
    body.innerHTML = '';

    const critNames = {
        'avg_hits': 'Média Acertos',
        'high_prizes': 'Prêmios 14/15',
        'financial_return': 'Lucro/Prejuízo'
    };

    ranking.forEach(([name, stats]) => {
        let val = stats[criterion];
        let color = "var(--primary)";
        if (criterion === 'financial_return') {
            color = val >= 0 ? "#2e7d32" : "#d32f2f";
            val = `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        }
        else if (criterion === 'avg_hits') val = val.toFixed(2);

        const row = `
            <tr>
                <td><b>${name}</b></td>
                <td style="font-size: 0.8rem; color: #777;">${critNames[criterion]}</td>
                <td style="color:${color}; font-weight:bold;">${val}</td>
            </tr>
        `;
        body.innerHTML += row;
    });
}

function downloadGames(format) {
    const stratId = document.getElementById('strategy-id').value;
    const countSelect = document.getElementById('count-select').value;
    const customVal = document.getElementById('custom-count').value;
    let count = (countSelect === 'custom') ? parseBrazilianNumber(customVal) : parseInt(countSelect);

    if (isNaN(count) || count <= 0) {
        alert("Quantidade inválida.");
        return;
    }

    fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            strategy_id: parseInt(stratId),
            count: count,
            format: format,
            universe: selectedUniverse,
            fixed_numbers: selectedFixed,
            wheeling_numbers: selectedWheeling,
            wheeling_type: document.getElementById('wheeling-type') ? document.getElementById('wheeling-type').value : null
        })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `lotofacil_jogos_${count}.${format}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        });
}

// --- ANÁLISE VISUAL ---
let visualConfig = null;
let historicalResults = [];
let simulatorGrids = [new Set()]; // Array of Sets for multiple grids
let visualViewMode = 'grid'; // 'grid' or 'horizontal'

function setViewMode(mode) {
    visualViewMode = mode;
    document.getElementById('btn-view-grid').classList.toggle('active', mode === 'grid');
    document.getElementById('btn-view-horizontal').classList.toggle('active', mode === 'horizontal');
    renderVisualGrids();
}

async function initVisualAnalysis() {
    if (!visualConfig) {
        try {
            const res = await fetch('/api/config');
            visualConfig = await res.json();
        } catch (e) {
            console.error("Erro ao carregar config de cores:", e);
        }
    }
    renderMultiSimulator();
    if (historicalResults.length === 0) {
        await loadVisualData();
    } else {
        renderVisualGrids();
    }
}

async function loadVisualData() {
    const limit = document.getElementById('visual-limit').value;
    try {
        const res = await fetch(`/api/history?limit=${limit}`);
        historicalResults = await res.json();
        renderVisualGrids();
    } catch (e) {
        console.error("Erro ao carregar histórico visual:", e);
    }
}

function addSimulatorGrid() {
    simulatorGrids.push(new Set());
    renderMultiSimulator();
}

function removeSimulatorGrid(index) {
    if (simulatorGrids.length <= 1) {
        simulatorGrids[0].clear();
    } else {
        simulatorGrids.splice(index, 1);
    }
    renderMultiSimulator();
}

function renderMultiSimulator() {
    const container = document.getElementById('simulator-container');
    if (!container) return;
    container.innerHTML = '';

    simulatorGrids.forEach((numbers, idx) => {
        const row = document.createElement('div');
        row.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 8px;
            background: #fff;
            border-bottom: 1px solid #eee;
        `;

        const info = document.createElement('div');
        info.style.cssText = `width: 140px; display: flex; align-items: center; gap: 8px;`;
        info.innerHTML = `
            <button onclick="removeSimulatorGrid(${idx})" style="background: #ff7675; color: white; border: none; border-radius: 4px; padding: 2px 6px; font-size: 10px; cursor: pointer;">✕</button>
            <span style="font-weight: 800; font-size: 0.75rem; color: #555;">APOSTA ${idx + 1} <span style="color: var(--primary); font-size: 0.65rem;">(${numbers.size}/15)</span></span>
        `;
        row.appendChild(info);

        const cellsContainer = document.createElement('div');
        cellsContainer.style.cssText = `display: flex; gap: 3px;`;

        for (let i = 1; i <= 25; i++) {
            const cell = document.createElement('div');
            const isActive = numbers.has(i);

            cell.style.cssText = `
                width: 28px; height: 28px; border-radius: 50%; border: 1px solid #ddd;
                display: flex; align-items: center; justify-content: center;
                font-size: 0.7rem; font-weight: 700; cursor: pointer;
                background: ${isActive ? (visualConfig ? visualConfig.lotofacil.cor_modalidade : 'var(--primary)') : '#f9f9f9'};
                color: ${isActive ? 'white' : '#bbb'};
                transition: all 0.2s;
            `;
            cell.innerText = i.toString().padStart(2, '0');
            cell.onclick = () => toggleSimulatorNum(idx, i);
            cellsContainer.appendChild(cell);
        }
        row.appendChild(cellsContainer);

        // --- MODO HÍBRIDO ---
        const isHibrido = document.getElementById('toggle-hibrido')?.checked;
        if (isHibrido && numbers.size > 0) {
            const statsPanel = document.createElement('div');
            statsPanel.className = 'hybrid-stats-panel';
            statsPanel.style.cssText = `
                margin-left: 15px;
                padding: 4px 10px;
                background: #f0f7ff;
                border: 1px solid #dae9f9;
                border-radius: 6px;
                font-size: 0.65rem;
                display: flex;
                gap: 12px;
                color: #555;
            `;

            const numsArray = Array.from(numbers);
            const pares = numsArray.filter(n => n % 2 === 0).length;
            const impares = numsArray.length - pares;

            // Repetidos do anterior
            let repeated = 0;
            if (historicalResults.length > 0) {
                const prev = historicalResults[0];
                const prevNums = [];
                for (let i = 1; i <= 15; i++) prevNums.push(prev[`dezena${i}`]);
                repeated = numsArray.filter(n => prevNums.includes(n)).length;
            }

            // Linhas
            const lines = [0, 0, 0, 0, 0];
            numsArray.forEach(n => lines[Math.floor((n - 1) / 5)]++);

            statsPanel.innerHTML = `
                <span>⚖️ <b>DISTR.:</b> ${pares}P / ${impares}I ${(pares >= 7 && pares <= 8) ? '✅' : '⚠️'}</span>
                <span>🔄 <b>REPET.:</b> ${repeated} ${(repeated >= 8 && repeated <= 10) ? '✅' : '⚠️'}</span>
                <span>📏 <b>LINHAS:</b> ${lines.join('|')}</span>
            `;
            row.appendChild(statsPanel);
        }

        container.appendChild(row);
    });
}

function toggleSimulatorNum(gridIdx, num) {
    const numbers = simulatorGrids[gridIdx];
    if (numbers.has(num)) {
        numbers.delete(num);
    } else {
        if (numbers.size >= 15) return;
        numbers.add(num);
    }
    renderMultiSimulator();
}

function downloadManualBets() {
    let content = "";
    let count = 0;
    simulatorGrids.forEach((numbers, idx) => {
        if (numbers.size > 0) {
            const arr = Array.from(numbers).sort((a, b) => a - b);
            content += arr.map(n => n.toString().padStart(2, '0')).join(' ') + "\n";
            count++;
        }
    });

    if (count === 0) {
        alert("Não há dezenas selecionadas para exportar.");
        return;
    }

    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lotofacil_apostas_manuais_${count}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function refreshVisualGrids() {
    renderVisualGrids();
}

function renderVisualGrids() {
    const container = document.getElementById('visual-historical-grids');
    if (!container) return;
    container.innerHTML = '';

    const showPares = document.getElementById('toggle-pares')?.checked || false;
    const showImpares = document.getElementById('toggle-impares')?.checked || false;
    const showRepetidos = document.getElementById('toggle-repetidos')?.checked || false;
    const showSequencias = document.getElementById('toggle-sequencias')?.checked || false;
    const showFinais = document.getElementById('toggle-finais')?.checked || false;

    historicalResults.forEach((res, idx) => {
        const dezenas = [];
        for (let i = 1; i <= 15; i++) dezenas.push(res[`dezena${i}`]);

        const prevDezenas = [];
        if (historicalResults[idx + 1]) {
            for (let i = 1; i <= 15; i++) prevDezenas.push(historicalResults[idx + 1][`dezena${i}`]);
        }

        // Sequences
        const sequences = new Set();
        if (showSequencias) {
            let currentSeq = [];
            const sortedDezenas = [...dezenas].sort((a, b) => a - b);
            for (let i = 0; i < sortedDezenas.length; i++) {
                if (currentSeq.length === 0 || sortedDezenas[i] === currentSeq[currentSeq.length - 1] + 1) {
                    currentSeq.push(sortedDezenas[i]);
                } else {
                    if (currentSeq.length >= 2) currentSeq.forEach(n => sequences.add(n));
                    currentSeq = [sortedDezenas[i]];
                }
            }
            if (currentSeq.length >= 2) currentSeq.forEach(n => sequences.add(n));
        }

        const row = document.createElement('div');
        row.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 4px 8px;
            border-bottom: 1px solid #f0f0f0;
            background: ${idx % 2 === 0 ? '#fff' : '#fafafa'};
        `;

        const info = document.createElement('div');
        info.style.cssText = `width: 140px; font-size: 0.7rem; font-weight: 800; color: #888;`;
        info.innerHTML = `
            <div style="color: var(--primary);">#${res.concurso}</div>
            <div style="font-weight: 400; font-size: 0.6rem;">${res.data}</div>
        `;
        row.appendChild(info);

        const cellsContainer = document.createElement('div');
        cellsContainer.style.cssText = `display: flex; gap: 3px;`;
        for (let i = 1; i <= 25; i++) {
            const cell = document.createElement('div');
            const isSorted = dezenas.includes(i);

            let bgColor = '#fff';
            let color = '#ddd';
            let border = '1px solid #eee';
            let boxShadow = 'none';

            if (isSorted) {
                // Background Priority: Repeat (Yellow) > Default
                let finalBg = (visualConfig ? visualConfig.lotofacil.cor_modalidade : 'var(--primary)');
                let finalColor = 'white';
                let boxShadowParts = [];
                border = 'none';

                if (showRepetidos && prevDezenas.includes(i)) {
                    finalBg = '#f1c40f'; // Yellow highly visible
                    finalColor = '#333';
                }

                // Inner indicator for Par/Impar if the background is taken or for clarity
                if (showPares && i % 2 === 0) {
                    if (finalBg === '#f1c40f') boxShadowParts.push('inset 0 0 0 3px #2ecc71');
                    else finalBg = '#2ecc71';
                } else if (showImpares && i % 2 !== 0) {
                    if (finalBg === '#f1c40f') boxShadowParts.push('inset 0 0 0 3px #3498db');
                    else finalBg = '#3498db';
                }

                // Border: Sequencias
                if (showSequencias && sequences.has(i)) {
                    border = '2px solid #000';
                }

                // Outer Highlight: Finais Iguais (Red glow for high contrast)
                if (showFinais) {
                    const currentEnding = i % 10;
                    const othersWithSameEnding = dezenas.filter(d => d !== i && d % 10 === currentEnding);
                    if (othersWithSameEnding.length > 0) {
                        boxShadowParts.push('0 0 8px rgba(231, 76, 60, 0.9)');
                    }
                }

                bgColor = finalBg;
                color = finalColor;
                boxShadow = boxShadowParts.length > 0 ? boxShadowParts.join(', ') : 'none';
            }

            cell.style.cssText = `
                width: 28px; height: 28px; border-radius: 50%; border: ${border};
                display: flex; align-items: center; justify-content: center;
                font-size: 0.7rem; font-weight: 700; background: ${bgColor}; color: ${color};
                box-shadow: ${boxShadow};
                transition: transform 0.2s;
            `;
            cell.innerText = i.toString().padStart(2, '0');
            cellsContainer.appendChild(cell);
        }

        row.appendChild(cellsContainer);
        container.appendChild(row);
    });
}

function renderStrategySummary() {
    const tabs = document.querySelectorAll('.strat-tab');
    let totalStrategies = 0;

    let summaryHTML = `<p style="margin: 0; font-weight: 600; color: var(--primary);">📊 Resumo do Arsenal (<span style="color: #666;">${tabs.length} Categorias Operacionais</span>):</p>
    <ul style="list-style: none; padding-left: 0; margin-top: 8px; font-size: 0.85rem; display: flex; flex-wrap: wrap; gap: 8px;">`;

    tabs.forEach(tab => {
        const stratId = tab.dataset.id;
        const tabName = tab.innerText.trim();
        let stratCount = 1; // A principal nativa

        const interfaceDiv = document.getElementById(`strategy-${stratId}-interface`);
        if (interfaceDiv) {
            stratCount += interfaceDiv.querySelectorAll('.sub-strategy-btn').length;
        }

        totalStrategies += stratCount;
        summaryHTML += `<li style="background: rgba(255,255,255,0.7); padding: 5px 10px; border-radius: 6px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <b>${tabName}</b>: <span style="color: var(--primary); font-weight: 800;">${stratCount}</span> est.
        </li>`;
    });

    summaryHTML += `</ul>`;

    const summaryContainer = document.getElementById('dynamic-strategy-summary');
    if (summaryContainer) {
        summaryContainer.innerHTML = summaryHTML;
    }

    const countSpan = document.getElementById('dynamic-strategy-count');
    if (countSpan) countSpan.innerText = totalStrategies;
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    selectStrategy(1);

    setTimeout(() => {
        const firstLayer = document.querySelector('.sub-tab-btn');
        if (firstLayer) firstLayer.click();

        renderStrategySummary();
    }, 100);
});
