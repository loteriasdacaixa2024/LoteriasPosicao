(function () {
    const UI = window.__ESTUDOS_UI__ || {};
    const ABAS = window.__ESTUDOS_ABAS__ || [];
    const API = window.__ESTUDOS_API__ || '/analise/api/analises-gerais';
    const EXTRA_MES = !!window.__ESTUDOS_EXTRA_MES__;
    const CONSTRUTOR_ON = !!window.__ESTUDOS_CONSTRUTOR__;
    const CONSTRUTOR_URL = window.__ESTUDOS_CONSTRUTOR_URL__ || '/geradores-elite/construtor-construcoes/';
    const CC_IMPORT_KEY = 'cc_panorama_import';
    const CC_PENDING_KEY = 'cc_import_pending';

    let baseAtual = 'geral';
    let janelaAtual = UI.janela_default || 10;
    let abaAtual = (ABAS[0] && ABAS[0].id) || 'classificacao-numeros';
    let modoComparativo = false;
    const cacheAba = {};
    const cacheComparativo = {};
    const charts = {};
    let difDataAtual = null;

    const BASE_LABELS = { geral: 'Geral', vencedores: 'Vencedores', acumulados: 'Acumulados' };

    const LINK_LABELS = {
        posicao: 'Análise por Posição',
        gerador_posicao: 'Posição → Apostas',
        comportamento: 'Análise Comportamental',
        comportamento_apostas: 'Comportamento → Apostas',
        soma_digitos: 'Soma dos Dígitos',
        digitos_utilizados: 'Dígitos Utilizados',
        classificacao: 'Classificação dos Números',
        analises_gerais: 'Análises Gerais',
    };

    function pad(n) { return String(n).padStart(2, '0'); }

    function htmlConcursoCol(row) {
        if (window.ComportamentoColConcurso) {
            return window.ComportamentoColConcurso.html(row, { showMes: EXTRA_MES });
        }
        return `#${row.concurso}`;
    }

    function renderInsights(insights) {
        if (!insights || !insights.length) return '';
        return `<div class="mb-3">${insights.map(t =>
            `<div class="insight-item">${t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>`
        ).join('')}</div>`;
    }

    function renderLinks(links) {
        if (!links) return '';
        const items = Object.entries(links)
            .filter(([k, href]) => href && LINK_LABELS[k])
            .map(([k, href]) => `<a href="${href}" class="me-2">${LINK_LABELS[k]}</a>`);
        if (!items.length) return '';
        return `<div class="mb-3 small estudos-links">${items.join(' · ')}</div>`;
    }

    function renderKpis(abaId, kpis) {
        const el = document.getElementById(`kpis-${abaId}`);
        if (!el) return;
        if (!kpis || !kpis.length) { el.innerHTML = ''; return; }
        el.innerHTML = kpis.map(k => `
            <div class="col-6 col-md-3">
                <div class="kpi-card">
                    <div class="kpi-label">${k.label || k.codigo || ''}</div>
                    <div class="kpi-val">${k.valor != null ? k.valor : '—'}</div>
                </div>
            </div>`).join('');
    }

    function destroyChart(id) {
        if (charts[id]) { charts[id].destroy(); delete charts[id]; }
    }

    function scheduleChart(id, buildFn) {
        setTimeout(() => {
            destroyChart(id);
            const canvas = document.getElementById(id);
            if (!canvas || !window.Chart) return;
            charts[id] = buildFn(canvas);
        }, 60);
    }

    function heatmapCoocorrencia(matriz) {
        if (!matriz || !matriz.length) return '';
        let max = 0;
        matriz.forEach(row => row.forEach(v => { if (v > max) max = v; }));
        const hdr = '<th></th>' + [0,1,2,3,4,5,6,7,8,9].map(d => `<th class="text-center">${d}</th>`).join('');
        const body = matriz.map((row, i) => {
            const cells = row.map(v => {
                const pct = max ? v / max : 0;
                const bg = v ? `rgba(46,125,50,${0.12 + pct * 0.75})` : 'transparent';
                return `<td class="text-center heat-cell" style="background:${bg}" title="${v}">${v || ''}</td>`;
            }).join('');
            return `<tr><th class="text-center">${i}</th>${cells}</tr>`;
        }).join('');
        return `<div class="table-responsive"><table class="table table-sm table-bordered heatmap-cooc mb-0">
            <thead><tr>${hdr}</tr></thead><tbody>${body}</tbody></table></div>`;
    }

    function renderComparativo(data) {
        const linhas = data.linhas_comparativo || [];
        if (!linhas.length) return '<p class="text-muted small">Sem dados comparativos.</p>';
        const rows = linhas.map(row => {
            const d = row.delta_num;
            let cls = '';
            if (d != null && d > 0) cls = 'delta-pos';
            else if (d != null && d < 0) cls = 'delta-neg';
            return `<tr>
                <td class="text-start">${row.label || row.codigo || ''}</td>
                <td class="cmp-v">${row.vencedores ?? '—'}</td>
                <td class="cmp-a">${row.acumulados ?? '—'}</td>
                <td class="${cls}">${row.delta ?? '—'}</td>
            </tr>`;
        }).join('');
        return `<div class="card border-primary">
            <div class="card-body py-2">
                <h6 class="small fw-bold mb-2"><i class="fas fa-columns text-primary"></i> Comparativo — Vencedores × Acumulados</h6>
                <p class="small text-muted mb-2">
                    Janela: <strong>${data.janela_label || data.janela}</strong> —
                    Vencedores: <strong>${data.total_vencedores}</strong> concursos —
                    Acumulados: <strong>${data.total_acumulados}</strong> concursos
                </p>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered cmp-table mb-0">
                        <thead><tr>
                            <th>Indicador</th>
                            <th class="cmp-v">Vencedores</th>
                            <th class="cmp-a">Acumulados</th>
                            <th>Δ</th>
                        </tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>
        </div>`;
    }

    async function fetchJson(url) {
        const r = await fetch(url);
        if (!r.ok) {
            if (r.status === 404) {
                throw new Error('Recurso não encontrado (404). Reinicie o servidor Flask na porta 5153.');
            }
            throw new Error(`Erro HTTP ${r.status}`);
        }
        const ct = r.headers.get('content-type') || '';
        if (!ct.includes('json')) {
            throw new Error('Resposta inválida do servidor. Reinicie o Flask e recarregue a página.');
        }
        return r.json();
    }

    async function carregarComparativo(force) {
        const painel = document.getElementById('painelComparativo');
        if (!painel) return;
        if (!modoComparativo) {
            painel.classList.add('d-none');
            painel.innerHTML = '';
            return;
        }
        painel.classList.remove('d-none');
        const key = `${abaAtual}|${janelaAtual}`;
        if (!force && cacheComparativo[key]) {
            painel.innerHTML = renderComparativo(cacheComparativo[key]);
            return;
        }
        painel.innerHTML = '<p class="text-muted small">Carregando comparativo…</p>';
        try {
            const qs = new URLSearchParams({ janela: String(janelaAtual) });
            const data = await fetchJson(`${API}/${encodeURIComponent(abaAtual)}/comparativo?${qs}`);
            if (!data.sucesso) {
                painel.innerHTML = `<div class="alert alert-warning py-2 small">${data.erro || 'Erro.'}</div>`;
                return;
            }
            cacheComparativo[key] = data;
            painel.innerHTML = renderComparativo(data);
        } catch (e) {
            painel.innerHTML = `<div class="alert alert-danger py-2 small">${e.message}</div>`;
        }
    }

    function downloadExport(formato) {
        const qs = new URLSearchParams({
            janela: String(janelaAtual),
            formato,
        });
        if (modoComparativo) {
            qs.set('comparativo', '1');
        } else {
            qs.set('base', baseAtual);
        }
        const url = `${API}/${encodeURIComponent(abaAtual)}/export?${qs}`;
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    function renderClassificacao(data) {
        const inds = data.indicadores || [];
        const linhas = data.linhas || [];
        const head = inds.map(i => `<th class="sigla-hdr" title="${i.label}">${i.codigo}</th>`).join('');
        const body = linhas.map(row => {
            const cells = inds.map(i => `<td>${row[i.codigo] != null ? row[i.codigo] : '—'}</td>`).join('');
            return `<tr><td class="comp-col-concurso">${htmlConcursoCol(row)}</td>${cells}</tr>`;
        }).join('');

        const pan = data.panorama || {};
        const panInds = pan.indicadores || [];
        let panHtml = '';
        if (panInds.length) {
            const mapRank = {};
            panInds.forEach(ind => {
                mapRank[ind.codigo] = {};
                (ind.ranking || []).forEach(r => { mapRank[ind.codigo][r.ranking] = r; });
            });
            const headP = panInds.map(i => `<th class="text-center" title="${i.label}"><span class="fw-bold">${i.codigo}</span></th>`).join('');
            const rowsP = [1, 2, 3].map(rank => {
                const cells = panInds.map(i => {
                    const r = mapRank[i.codigo] && mapRank[i.codigo][rank];
                    if (!r) return '<td class="text-muted">—</td>';
                    const cls = rank === 1 ? 'top1' : '';
                    return `<td class="text-center"><div class="panorama-cel-val ${cls}">${r.valor_label != null ? r.valor_label : r.valor}</div><div class="small text-muted">${r.ocorrencias} · ${r.percentual}%</div></td>`;
                }).join('');
                return `<tr><td class="fw-bold text-center">${rank}º</td>${cells}</tr>`;
            }).join('');
            panHtml = `<div class="mb-3"><h6 class="small fw-bold">Panorama Top-3</h6>
                <div class="table-responsive"><table class="table table-sm table-bordered panorama-matriz mb-0">
                <thead><tr><th>Rank</th>${headP}</tr></thead><tbody>${rowsP}</tbody></table></div></div>`;
        }

        const inter = (data.intersecoes || []).map(x =>
            `<div class="insight-item"><strong>${x.titulo}:</strong> ${(x.numeros || []).map(pad).join(', ')}</div>`
        ).join('');

        return `${renderLinks(data.links)}${panHtml}
            ${inter ? `<div class="mb-3">${inter}</div>` : ''}
            <div class="table-responsive">
                <table class="table table-sm table-bordered estudos-tabela mb-0">
                    <thead><tr><th>Concurso</th>${head}</tr></thead>
                    <tbody>${body || '<tr><td colspan="99" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
    }

    function renderDigitos(data, abaId) {
        const painel = data.painel_digitos || [];
        const linhas = data.linhas || [];
        const chartLineId = `chart-line-${abaId}`;
        const chartBarId = `chart-bar-${abaId}`;

        const bars = painel.map(p => `
            <tr><td class="fw-bold">${p.digito}</td><td>${p.concursos_com_digito}</td><td>${p.pct_concursos}%</td><td>${p.freq_aparicoes}</td></tr>`).join('');

        const topPares = (data.top_pares || []).slice(0, 10).map(p =>
            `<tr><td>${p.par}</td><td>${p.ocorrencias}</td><td>${p.pct}%</td></tr>`
        ).join('');

        const atrasos = (data.atraso_digitos || []).map(a =>
            `<tr><td class="fw-bold">${a.digito}</td><td>${a.atraso}</td></tr>`
        ).join('');

        const hist = linhas.map(r => `<tr>
            <td class="comp-col-concurso">${htmlConcursoCol(r)}</td>
            <td>${r.digitos_distintos_fmt || '—'}</td>
            <td class="fw-bold">${r.qtd_digitos_distintos}</td>
            <td>${r.digitos_repetidos_concurso_anterior != null ? r.digitos_repetidos_concurso_anterior : '—'}</td>
        </tr>`).join('');

        scheduleChart(chartLineId, (canvas) => {
            const evo = data.evolucao_qtd || [];
            return new Chart(canvas, {
                type: 'line',
                data: {
                    labels: evo.map(e => e.concurso),
                    datasets: [{
                        label: 'Qtd dígitos distintos',
                        data: evo.map(e => e.qtd),
                        borderColor: '#2e7d32',
                        tension: 0.2,
                        fill: false,
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
            });
        });

        scheduleChart(chartBarId, (canvas) => {
            const ord = [...painel].sort((a, b) => parseInt(a.digito, 10) - parseInt(b.digito, 10));
            return new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: ord.map(p => p.digito),
                    datasets: [{
                        label: '% concursos',
                        data: ord.map(p => p.pct_concursos),
                        backgroundColor: 'rgba(46,125,50,0.55)',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, max: 100 } },
                },
            });
        });

        const sobre = data.sobreposicao_consecutiva || {};

        return `${renderLinks(data.links)}${renderInsights(data.insights)}
        <div class="row g-3 mb-3">
            <div class="col-md-4">
                <h6 class="small fw-bold">Frequência por dígito</h6>
                <table class="table table-sm estudos-tabela"><thead><tr><th>Díg.</th><th>Conc.</th><th>%</th><th>Apar.</th></tr></thead><tbody>${bars}</tbody></table>
            </div>
            <div class="col-md-4">
                <h6 class="small fw-bold">Barras — % concursos com dígito</h6>
                <div class="chart-box" style="height:200px"><canvas id="${chartBarId}"></canvas></div>
            </div>
            <div class="col-md-4">
                <h6 class="small fw-bold">Evolução — qtd dígitos distintos</h6>
                <div class="chart-box" style="height:200px"><canvas id="${chartLineId}"></canvas></div>
            </div>
        </div>
        <div class="row g-3 mb-3">
            <div class="col-md-6">
                <h6 class="small fw-bold">Co-ocorrência (dígitos no mesmo concurso)</h6>
                ${heatmapCoocorrencia(data.matriz_coocorrencia)}
            </div>
            <div class="col-md-3">
                <h6 class="small fw-bold">Top pares</h6>
                <table class="table table-sm estudos-tabela"><thead><tr><th>Par</th><th>×</th><th>%</th></tr></thead><tbody>${topPares || '<tr><td colspan="3" class="text-muted">—</td></tr>'}</tbody></table>
                <p class="small text-muted mb-0">Sobreposição entre concursos seguidos: média <strong>${sobre.media ?? '—'}</strong>, moda <strong>${sobre.moda ?? '—'}</strong>.</p>
            </div>
            <div class="col-md-3">
                <h6 class="small fw-bold">Atraso por dígito</h6>
                <table class="table table-sm estudos-tabela"><thead><tr><th>Díg.</th><th>Atraso</th></tr></thead><tbody>${atrasos}</tbody></table>
            </div>
        </div>
        <h6 class="small fw-bold">Histórico</h6>
        <div class="table-responsive"><table class="table table-sm estudos-tabela">
            <thead><tr><th>Concurso</th><th>Dígitos</th><th>Qtd</th><th>Rep. ant.</th></tr></thead>
            <tbody>${hist}</tbody></table></div>`;
    }

    function renderSomaDigitos(data, abaId) {
        const linhas = data.linhas || [];
        const chartLineId = `chart-line-${abaId}`;
        const chartHistId = `chart-hist-${abaId}`;
        const dist = data.distribuicao_soma_total || [];

        scheduleChart(chartLineId, (canvas) => {
            const evo = data.evolucao || [];
            return new Chart(canvas, {
                type: 'line',
                data: {
                    labels: evo.map(e => e.concurso),
                    datasets: [{
                        label: 'Soma total dos dígitos',
                        data: evo.map(e => e.soma_total_digitos),
                        borderColor: '#1565c0',
                        tension: 0.2,
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
            });
        });

        scheduleChart(chartHistId, (canvas) => {
            return new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: dist.map(d => String(d.valor)),
                    datasets: [{
                        label: 'Ocorrências',
                        data: dist.map(d => d.ocorrencias),
                        backgroundColor: 'rgba(21,101,192,0.55)',
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { title: { display: true, text: 'Soma total dígitos' } } },
                },
            });
        });

        const distRows = dist.map(d => `<tr><td>${d.valor}</td><td>${d.ocorrencias}</td><td>${d.pct}%</td></tr>`).join('');
        const hist = linhas.slice(0, 40).map(r => `<tr>
            <td class="comp-col-concurso">${htmlConcursoCol(r)}</td>
            <td class="fw-bold">${r.soma_total_digitos}</td>
            <td>${r.media_soma_digitos}</td>
            <td>${r.soma_dezenas}</td>
            <td>${r.soma_par ? 'Par' : 'Ímpar'}</td>
        </tr>`).join('');

        const mapaRows = (data.mapa_dezena_soma || []).map(m =>
            `<tr><td>${m.dezena_fmt}</td><td>${(m.digitos || []).join('+')}</td><td class="fw-bold">${m.soma_digitos}</td></tr>`
        ).join('');

        return `${renderLinks(data.links)}${renderInsights(data.insights)}
        <div class="row g-3 mb-3">
            <div class="col-md-4">
                <h6 class="small fw-bold">Tabela — soma total (concurso)</h6>
                <table class="table table-sm estudos-tabela"><thead><tr><th>Soma</th><th>Ocorr.</th><th>%</th></tr></thead><tbody>${distRows}</tbody></table>
            </div>
            <div class="col-md-4">
                <h6 class="small fw-bold">Histograma — soma total dos dígitos</h6>
                <div class="chart-box" style="height:220px"><canvas id="${chartHistId}"></canvas></div>
            </div>
            <div class="col-md-4">
                <h6 class="small fw-bold">Evolução temporal</h6>
                <div class="chart-box" style="height:220px"><canvas id="${chartLineId}"></canvas></div>
            </div>
        </div>
        <details class="mb-3">
            <summary class="small fw-bold" style="cursor:pointer">Mapa fixo — soma de dígitos por dezena (01–31)</summary>
            <div class="table-responsive mt-2" style="max-height:200px;overflow:auto">
                <table class="table table-sm estudos-tabela"><thead><tr><th>Dez.</th><th>Dígitos</th><th>Soma</th></tr></thead><tbody>${mapaRows}</tbody></table>
            </div>
        </details>
        <h6 class="small fw-bold">Últimos concursos</h6>
        <div class="table-responsive"><table class="table table-sm estudos-tabela">
            <thead><tr><th>Concurso</th><th>Soma dígitos</th><th>Média/dez</th><th>Soma dezenas</th><th>Paridade</th></tr></thead>
            <tbody>${hist}</tbody></table></div>`;
    }

    function renderColapsavel(titulo, innerHtml, aberto) {
        return `<details class="estudos-collapse"${aberto ? ' open' : ''}>
            <summary class="estudos-collapse-summary">${titulo}</summary>
            <div class="estudos-collapse-body">${innerHtml}</div>
        </details>`;
    }

    function fmtDezenas(dz, pad) {
        pad = pad || 2;
        return (dz || []).map(d => String(Number(d)).padStart(pad, '0')).join(' ');
    }

    function extrairApostasDiferencial(data) {
        const bo = data.bloco_ordenado || {};
        const bp = data.bloco_posicional || {};
        const pad = data.pad_width || 2;
        const ordenadas = [...(bo.numeros_apostar_ordenados || [])].map(Number).sort((a, b) => a - b);
        const posicional = [...(bp.numeros_apostar_ordenados || [])].map(Number).sort((a, b) => a - b);
        const iguais = ordenadas.length === posicional.length &&
            ordenadas.every((v, i) => v === posicional[i]);
        return {
            pad,
            ordenadas,
            posicional,
            iguais,
            ultimo: data.ultimo_concurso,
            penultimo: data.penultimo_concurso,
        };
    }

    function textoApostasDiferencial(apostas) {
        const fmt = (dz) => fmtDezenas(dz, apostas.pad);
        const linhas = [
            `# Diferencial Cruzado — últ. #${apostas.ultimo} vs penúlt. #${apostas.penultimo}`,
            `ORDENADAS:   ${fmt(apostas.ordenadas)}`,
        ];
        if (!apostas.iguais) {
            linhas.push(`SORTEIO:     ${fmt(apostas.posicional)}`);
        }
        return linhas.join('\r\n');
    }

    function downloadBlobText(texto, filename) {
        const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function downloadApostasDiferencial() {
        if (!difDataAtual) return;
        const apostas = extrairApostasDiferencial(difDataAtual);
        const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
        downloadBlobText(
            textoApostasDiferencial(apostas),
            `diferencial_apostas_${baseAtual}_j${janelaAtual}_${stamp}.txt`
        );
    }

    function enviarConstrutorDif(dezenas, origem, aviso, abrir = true) {
        const arr = [...new Set(dezenas)].sort((a, b) => a - b);
        if (!arr.length) {
            alert('Nenhuma dezena para enviar.');
            return;
        }
        try {
            sessionStorage.setItem(CC_IMPORT_KEY, JSON.stringify({
                dezenas: arr,
                origem: origem || 'diferencial',
                aviso: aviso || 'Importado do Diferencial Cruzado.',
                ts: Date.now(),
            }));
        } catch (e) {
            alert('Não foi possível salvar para o Construtor.');
            return;
        }
        if (abrir) window.open(CONSTRUTOR_URL, '_blank');
    }

    function enviarConstrutorDifAmbas(apostas) {
        if (apostas.iguais) {
            enviarConstrutorDif(
                apostas.ordenadas,
                'diferencial-ordenada',
                `Diferencial Cruzado #${apostas.ultimo} — Ordenadas (mesmo conjunto do cálculo posicional).`
            );
            return;
        }
        try {
            sessionStorage.setItem(CC_PENDING_KEY, JSON.stringify([{
                dezenas: apostas.posicional,
                origem: 'diferencial-posicional',
                aviso: `Diferencial Cruzado #${apostas.ultimo} — Posicional (cálculo por ordem do sorteio).`,
            }]));
        } catch (e) {
            alert('Não foi possível preparar a fila para o Construtor.');
            return;
        }
        enviarConstrutorDif(
            apostas.ordenadas,
            'diferencial-ordenada',
            `Diferencial Cruzado #${apostas.ultimo} — Ordenadas. Há um 2º conjunto (posicional) aguardando importação.`
        );
    }

    function handleDifAction(action) {
        if (!difDataAtual) return;
        const apostas = extrairApostasDiferencial(difDataAtual);
        if (action === 'download-apostas') {
            downloadApostasDiferencial();
            return;
        }
        if (!CONSTRUTOR_ON) {
            alert('Construtor de Construções indisponível nesta modalidade.');
            return;
        }
        if (action === 'construtor-ordenada') {
            enviarConstrutorDif(
                apostas.ordenadas,
                'diferencial-ordenada',
                `Diferencial Cruzado #${apostas.ultimo} — Ordenadas.`
            );
        } else if (action === 'construtor-posicional') {
            if (apostas.iguais) {
                alert('O cálculo posicional gerou o mesmo conjunto das Ordenadas — enviando uma vez.');
            }
            enviarConstrutorDif(
                apostas.posicional,
                'diferencial-posicional',
                `Diferencial Cruzado #${apostas.ultimo} — Posicional.`
            );
        } else if (action === 'construtor-ambas') {
            enviarConstrutorDifAmbas(apostas);
        }
    }

    function renderDifBarra(apostas) {
        const chip = apostas.iguais ? '1 linha' : '2 linhas';
        const casoUnico = apostas.iguais
            ? ' <span class="text-muted">(seu caso agora)</span>'
            : '';
        const casoDuplo = apostas.iguais
            ? ''
            : ' <span class="text-muted">(seu caso agora)</span>';
        return `<div class="dif-acoes-bar d-flex mb-3 p-2 rounded border bg-light">
            <button type="button" class="btn btn-sm btn-primary" data-dif-action="download-apostas">
                <i class="fas fa-download"></i> Baixar apostas
            </button>
            ${CONSTRUTOR_ON ? `
            <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-success" data-dif-action="construtor-ordenada" title="Enviar aposta ordenada ao Construtor">
                    <i class="fas fa-layer-group"></i> Construtor — Ordenadas
                </button>
                <button type="button" class="btn btn-outline-success" data-dif-action="construtor-posicional" title="Enviar aposta do cálculo posicional">
                    <i class="fas fa-layer-group"></i> Construtor — Posicional
                </button>
                <button type="button" class="btn btn-outline-success" data-dif-action="construtor-ambas" title="Importa ordenadas agora; posicional na fila se for diferente">
                    <i class="fas fa-forward"></i> Construtor — Ambas
                </button>
            </div>` : ''}
            <details class="dif-linha-dica ms-auto">
                <summary title="Clique para ver como funciona o download"><span class="dif-linha-chip">${chip}</span></summary>
                <div class="dif-linha-dica-body">
                    <p class="mb-2 fw-semibold">Barra «Baixar apostas»</p>
                    <p class="small mb-2">Se os dois cálculos derem o <strong>mesmo conjunto</strong> (1 linha):${casoUnico}</p>
                    <div class="dif-exemplo-bloco"># Diferencial Cruzado — últ. #1245 vs penúlt. #1244
ORDENADAS:   01 08 10 11 15 23 24</div>
                    <p class="small mb-2">Se forem <strong>diferentes</strong> (2 linhas):${casoDuplo}</p>
                    <div class="dif-exemplo-bloco"># Diferencial Cruzado — últ. #1245 vs penúlt. #1244
ORDENADAS:   01 08 10 11 15 23 24
SORTEIO:     02 09 11 12 16 24 25</div>
                    <ul class="dif-ajuda-lista small mb-0">
                        <li>Sempre em ordem <strong>crescente</strong>.</li>
                        <li>Nunca duplica a mesma aposta em duas ordens.</li>
                        <li>A 2ª linha (<code>SORTEIO</code>) só aparece se e somente se o conjunto for diferente do cálculo ordenado.</li>
                    </ul>
                </div>
            </details>
        </div>`;
    }

    function renderBlocoDiferencial(blk, pad) {
        if (!blk) return '';
        const cols = (blk.ultimo || []).length;
        const colHdr = Array.from({ length: cols }, (_, i) => `<th>P${i + 1}</th>`).join('');
        const cells = (vals) => (vals || []).map(d => `<td>${String(Number(d)).padStart(pad, '0')}</td>`).join('');
        const cellsSigned = (vals) => (vals || []).map(v => {
            const n = Number(v);
            const cls = n < 0 ? ' text-danger fw-bold' : '';
            return `<td class="${cls}">${String(Math.abs(n)).padStart(pad, '0')}${n < 0 ? ' (−)' : ''}</td>`;
        }).join('');
        const concLabel = (blk.penultimo_concurso && blk.ultimo_concurso)
            ? `<span class="dif-bloco-concursos">· penúlt. #${blk.penultimo_concurso}${blk.penultimo_data ? ' (' + blk.penultimo_data + ')' : ''} → últ. #${blk.ultimo_concurso}${blk.ultimo_data ? ' (' + blk.ultimo_data + ')' : ''}</span>`
            : '';
        return `<div class="card border-0 shadow-sm mb-3">
            <div class="card-header py-2 fw-bold small">${blk.titulo || ''}${concLabel}</div>
            <div class="card-body p-2">
                <div class="table-responsive">
                    <table class="table table-sm estudos-tabela mb-2">
                        <thead><tr><th></th>${colHdr}</tr></thead>
                        <tbody>
                            <tr><th class="text-start">Último</th>${cells(blk.ultimo)}</tr>
                            <tr><th class="text-start">Penúltimo</th>${cells(blk.penultimo)}</tr>
                            <tr class="table-warning"><th class="text-start">Subtração</th>${cells(blk.subtracao_abs)}</tr>
                            <tr class="table-info"><th class="text-start">Resultado</th>${cellsSigned(blk.resultado)}</tr>
                        </tbody>
                    </table>
                </div>
                <div class="d-flex flex-wrap gap-2 align-items-center">
                    <span class="badge bg-primary-subtle text-primary border dif-dezenas-txt">Posicional: ${fmtDezenas(blk.numeros_apostar_posicional, pad)}</span>
                    <span class="badge bg-success-subtle text-success border dif-dezenas-txt">À apostar (ord.): ${fmtDezenas(blk.numeros_apostar_ordenados, pad)}</span>
                </div>
            </div>
        </div>`;
    }

    function renderDiferencialCruzado(data) {
        difDataAtual = data;
        const pad = data.pad_width || 2;
        const avisos = data.avisos || [];
        const alertNeg = (data.bloco_ordenado && data.bloco_ordenado.tem_negativos) ||
            (data.bloco_posicional && data.bloco_posicional.tem_negativos);

        let insightsHtml = '';
        if (data.insights && data.insights.length) {
            const body = data.insights.map(t =>
                `<div class="insight-item mb-1">${t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>')}</div>`
            ).join('');
            insightsHtml = renderColapsavel('Resumo do Diferencial Cruzado', body, true);
        }

        let alertHtml = '';
        if (alertNeg) {
            alertHtml = `<div class="alert alert-warning py-2 small mb-2">
                <i class="fas fa-exclamation-triangle me-1"></i>
                Subtrações negativas detectadas — o sistema usa <strong>valor absoluto</strong> na normalização.
            </div>`;
        }
        if (avisos.length) {
            const lista = `<ul class="mb-0 ps-3">${avisos.map(a => `<li class="dif-dezenas-txt">${a}</li>`).join('')}</ul>`;
            alertHtml += renderColapsavel(`Ajustes automáticos (${avisos.length})`, lista, false);
        }

        const hist = (data.historico || []).map(r => `<tr>
            <td class="text-start">#${r.concurso}</td>
            <td class="text-start">#${r.penultimo_concurso}</td>
            <td class="text-start col-dezenas-left dif-dezenas-txt">${r.ultimo_fmt || ''}</td>
            <td class="text-start col-dezenas-left dif-dezenas-txt fw-bold">${r.aposta_ordenada_fmt || ''}</td>
            <td>${r.teve_ajuste ? '<span class="text-warning">sim</span>' : '—'}</td>
        </tr>`).join('');

        const apostas = extrairApostasDiferencial(data);

        return `${renderLinks(data.links)}
        ${renderDifBarra(apostas)}
        ${insightsHtml}
        ${alertHtml}
        <p class="small text-muted mb-3">
            Regra: <code>sub[i] = último[i] − penúltimo[i]</code> ·
            <code>resultado[i] = último[i] + sub[i]</code> ·
            pool <strong>${String(data.dezena_min).padStart(2, '0')}–${String(data.dezena_max).padStart(2, '0')}</strong>
        </p>
        <div class="row g-3 mb-3">
            <div class="col-lg-6">${renderBlocoDiferencial(data.bloco_ordenado, pad)}</div>
            <div class="col-lg-6">${renderBlocoDiferencial(data.bloco_posicional, pad)}</div>
        </div>
        <h6 class="small fw-bold">Histórico na janela (ordem posicional → aposta ordenada)</h6>
        <div class="table-responsive">
            <table class="table table-sm estudos-tabela estudos-tabela-dif-hist">
                <thead><tr>
                    <th class="text-start">Concurso</th>
                    <th class="text-start">Penúltimo</th>
                    <th class="text-start col-dezenas-left">Último (ordem)</th>
                    <th class="text-start col-dezenas-left">Aposta</th>
                    <th>Ajuste</th>
                </tr></thead>
                <tbody>${hist || '<tr><td colspan="5" class="text-muted text-start">—</td></tr>'}</tbody>
            </table>
        </div>`;
    }

    function renderAbaCorpo(abaId, data) {
        if (abaId === 'classificacao-numeros') return renderClassificacao(data);
        if (abaId === 'digitos-utilizados') return renderDigitos(data, abaId);
        if (abaId === 'soma-digitos') return renderSomaDigitos(data, abaId);
        if (abaId === 'diferencial-cruzado') return renderDiferencialCruzado(data);
        return '<p class="text-muted">Aba em construção.</p>';
    }

    async function carregarAba(abaId, force) {
        const corpo = document.getElementById(`corpo-${abaId}`);
        if (!corpo) return;
        const key = `${abaId}|${baseAtual}|${janelaAtual}`;
        if (!force && cacheAba[key]) {
            renderKpis(abaId, cacheAba[key].kpis);
            corpo.innerHTML = renderAbaCorpo(abaId, cacheAba[key]);
            return;
        }
        corpo.innerHTML = '<p class="text-muted small">Carregando…</p>';
        try {
            const qs = new URLSearchParams({ base: baseAtual, janela: String(janelaAtual) });
            const data = await fetchJson(`${API}/${encodeURIComponent(abaId)}?${qs}`);
            if (!data.sucesso) {
                corpo.innerHTML = `<div class="alert alert-warning py-2 small">${data.erro || 'Erro ao carregar.'}</div>`;
                return;
            }
            cacheAba[key] = data;
            renderKpis(abaId, data.kpis);
            corpo.innerHTML = renderAbaCorpo(abaId, data);
            if (data.ultimo_concurso) {
                const el = document.getElementById('lblUltimoConcurso');
                if (el) el.textContent = `Último #${data.ultimo_concurso}`;
            }
        } catch (e) {
            corpo.innerHTML = `<div class="alert alert-danger py-2 small">${e.message}</div>`;
        }
    }

    function atualizarLabels() {
        const lb = document.getElementById('lblBaseAtiva');
        const lj = document.getElementById('lblJanelaAtiva');
        if (lb) lb.textContent = BASE_LABELS[baseAtual] || baseAtual;
        if (lj) lj.textContent = janelaAtual === 0 ? 'Todos' : `Janela ${janelaAtual}`;
    }

    function initAbas() {
        const params = new URLSearchParams(location.search);
        const abaParam = params.get('aba');
        if (abaParam) {
            abaAtual = abaParam;
            const btn = document.querySelector(`#estudosAbas [data-aba="${abaParam}"]`);
            if (btn && window.bootstrap) {
                bootstrap.Tab.getOrCreateInstance(btn).show();
            }
        }
        document.querySelectorAll('#estudosAbas [data-aba]').forEach(btn => {
            btn.addEventListener('shown.bs.tab', (e) => {
                abaAtual = e.target.getAttribute('data-aba');
                carregarAba(abaAtual, true);
                carregarComparativo(true);
            });
        });
    }

    function initFiltros() {
        document.querySelectorAll('.base-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.base-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                baseAtual = btn.dataset.base;
                atualizarLabels();
                carregarAba(abaAtual, true);
            });
        });
        document.querySelectorAll('.janela-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.janela-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                janelaAtual = parseInt(btn.dataset.janela, 10);
                atualizarLabels();
                carregarAba(abaAtual, true);
                carregarComparativo(true);
            });
        });
        document.getElementById('btnComparativo')?.addEventListener('click', () => {
            modoComparativo = !modoComparativo;
            const btn = document.getElementById('btnComparativo');
            if (btn) btn.classList.toggle('active', modoComparativo);
            carregarComparativo(true);
        });
        document.getElementById('btnExportTxt')?.addEventListener('click', () => downloadExport('txt'));
        document.getElementById('btnExportCsv')?.addEventListener('click', () => downloadExport('csv'));
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-dif-action]');
            if (!btn) return;
            e.preventDefault();
            handleDifAction(btn.getAttribute('data-dif-action'));
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initFiltros();
        initAbas();
        atualizarLabels();
        const first = ABAS.find(a => a.id === abaAtual) || ABAS[0];
        if (first) carregarAba(first.id, true);
    });
})();
