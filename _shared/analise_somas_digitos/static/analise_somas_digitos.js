(function () {
    'use strict';

    const root = document.getElementById('asd-root');
    if (!root) return;

    const API = window.__ASD_API__ || root.dataset.api;
    const UI = window.__ASD_UI__ || {};

    let base = 'geral';
    let janela = UI.janela_default != null ? UI.janela_default : 0;
    let loaded = { somas: false, digitos: false };
    let somasCache = null;
    let mediaPage = 1;
    const MEDIA_POR_PAG = 50;
    let faixasData = [];
    let rankingData = [];
    let histData = [];
    const SORT = {
        faixas: { key: '', dir: 'desc' },
        ranking: { key: '', dir: 'desc' },
        hist: { key: '', dir: 'desc' },
        media: { key: '', dir: 'desc' },
    };

    const $ = (id) => document.getElementById(id);

    function escTxt(v) {
        return String(v == null ? '' : v)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function pillMedia(st, label) {
        const s = st === 'dentro' || st === 'proxima' ? st : 'fora';
        const lbl = label || (s === 'dentro' ? 'Dentro da média' : (s === 'proxima' ? 'Próxima da média' : 'Fora da faixa'));
        const icon = s === 'dentro' || s === 'proxima' ? '●' : '○';
        return `<span class="ai-status-pill ${s}" title="${escTxt(lbl)}">${icon} ${escTxt(lbl)}</span>`;
    }

    function fmtPct(v) {
        const n = Number(v);
        if (Number.isNaN(n)) return '—';
        return (Math.round(n * 100) / 100).toLocaleString('pt-BR') + '%';
    }

    function fmtDezenas(arr) {
        if (!arr || !arr.length) return '—';
        const pad = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
        return arr.map((n) => {
            const v = Number(n);
            if (!Number.isFinite(v)) return String(n);
            if (pad <= 1) return String(v);
            return String(v).padStart(pad, '0');
        }).join(pad <= 1 ? ' | ' : ' ');
    }

    function htmlTh(table, key, label) {
        const st = SORT[table] || { key: '', dir: 'desc' };
        const on = st.key === key;
        const cls = on ? (st.dir === 'asc' ? ' ai-sort-asc' : ' ai-sort-desc') : '';
        const ind = on ? (st.dir === 'asc' ? '▲' : '▼') : '⇅';
        return `<th class="ai-sort${cls}" data-sort="${escTxt(key)}" data-table="${table}" title="Clique para ordenar">${escTxt(label)} <span class="ai-sort-ind">${ind}</span></th>`;
    }

    function valorOrdenacao(row, key) {
        if (key === 'data') {
            const m = String(row.data || '').match(/(\d{2})\/(\d{2})\/(\d{4})/);
            return m ? `${m[3]}${m[2]}${m[1]}` : '';
        }
        if (key === 'dezenas') return fmtDezenas(row.dezenas);
        if (key === 'faixa') {
            const n = Number(row.min != null ? row.min : String(row.faixa || '').split(/[–-]/)[0]);
            return Number.isFinite(n) ? n : 0;
        }
        if (key === 'status') return String(row.status_media_label || '');
        if (key === 'par_impar') return String(row.par_impar || '');
        const v = row[key];
        if (typeof v === 'number') return v;
        const n = Number(v);
        if (v != null && String(v).trim() !== '' && Number.isFinite(n)) return n;
        return String(v == null ? '' : v);
    }

    function ordenarLinhas(linhas, key, dir) {
        if (!key) return linhas.slice();
        const mult = dir === 'asc' ? 1 : -1;
        return linhas.slice().sort((a, b) => {
            const va = valorOrdenacao(a, key);
            const vb = valorOrdenacao(b, key);
            if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * mult;
            return String(va).localeCompare(String(vb), 'pt-BR', { numeric: true }) * mult;
        });
    }

    function aplicarOrdem(table, linhas) {
        const st = SORT[table];
        if (!st || !st.key) return linhas.slice();
        return ordenarLinhas(linhas, st.key, st.dir);
    }

    function htmlFaixas(linhas) {
        const rows = aplicarOrdem('faixas', linhas).map((f) => `
            <tr class="${f.destaque ? 'asd-top' : ''}">
                <td>${escTxt(f.faixa)}</td>
                <td>${f.ocorrencias}</td>
                <td>${fmtPct(f.pct)}</td>
            </tr>`).join('');
        return rows || '<tr><td colspan="3" class="text-muted">Sem dados</td></tr>';
    }

    function htmlRanking(linhas) {
        const rows = aplicarOrdem('ranking', linhas).map((s) => `
            <tr class="${s.destaque ? 'asd-top' : ''}">
                <td>${s.soma}</td>
                <td>${s.ocorrencias}</td>
                <td>${fmtPct(s.pct)}</td>
            </tr>`).join('');
        return rows || '<tr><td colspan="3" class="text-muted">Sem dados</td></tr>';
    }

    function htmlHist(linhas) {
        const rows = aplicarOrdem('hist', linhas).map((row) => `
            <tr>
                <td>${row.concurso}</td>
                <td class="text-start font-monospace small">${fmtDezenas(row.dezenas)}</td>
                <td class="fw-bold">${row.soma}</td>
                <td>${escTxt(row.faixa)}</td>
                <td>${escTxt(row.par_impar)}</td>
            </tr>`).join('');
        return rows || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>';
    }

    function setLabels(data) {
        const bl = $('asdLblBase');
        const jl = $('asdLblJanela');
        const ul = $('asdLblUltimo');
        if (bl) bl.textContent = data.base_label || base;
        if (jl) jl.textContent = janela === 0 ? 'Todos' : ('Janela ' + janela);
        if (ul) ul.textContent = data.ultimo_concurso != null ? ('Último c.' + data.ultimo_concurso) : '—';
    }

    function renderKpis(elId, items) {
        const el = $(elId);
        if (!el) return;
        el.innerHTML = items.map((k) => `
            <div class="col-6 col-md-3">
                <div class="asd-kpi">
                    <div class="lbl">${k.label}</div>
                    <div class="val">${k.valor}</div>
                </div>
            </div>`).join('');
    }

    function renderSomas(data) {
        setLabels(data);
        const r = data.resumo || {};
        renderKpis('asdKpisSomas', [
            { label: 'Menor soma', valor: r.soma_minima ?? '—' },
            { label: 'Maior soma', valor: r.soma_maxima ?? '—' },
            { label: 'Média', valor: r.soma_media ?? '—' },
            { label: 'Faixa + frequente', valor: r.faixa_mais_frequente ?? '—' },
        ]);

        faixasData = (data.distribuicao_faixas || []).slice();
        rankingData = (data.ranking_somas || []).slice(0, 15).map((s, i) => Object.assign({ destaque: i === 0 }, s));
        histData = (data.linhas || []).slice(0, 80);

        $('asdCorpoSomas').innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Resumo por faixa de soma</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered asd-table mb-0" id="asdTabelaFaixas">
                            <thead><tr>${htmlTh('faixas', 'faixa', 'Faixa')}${htmlTh('faixas', 'ocorrencias', 'Nº de sorteios')}${htmlTh('faixas', 'pct', 'Porcentagem')}</tr></thead>
                            <tbody id="asdBodyFaixas">${htmlFaixas(faixasData)}</tbody>
                        </table>
                    </div>
                    <p class="small text-muted mt-2 mb-0">
                        Faixa mais frequente: <strong>${r.faixa_mais_frequente || '—'}</strong>
                        · menos frequente: <strong>${r.faixa_menos_frequente || '—'}</strong>
                        · pares: ${r.pares ?? '—'} · ímpares: ${r.impares ?? '—'}
                    </p>
                </div>
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Somas mais recorrentes</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered asd-table mb-0" id="asdTabelaRanking">
                            <thead><tr>${htmlTh('ranking', 'soma', 'Soma')}${htmlTh('ranking', 'ocorrencias', 'Nº de sorteios')}${htmlTh('ranking', 'pct', 'Porcentagem')}</tr></thead>
                            <tbody id="asdBodyRanking">${htmlRanking(rankingData)}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <h6 class="small fw-bold mb-2">Histórico das somas
                <span class="text-muted fw-normal">(exibindo até 80 · total ${data.total_concursos || 0})</span>
            </h6>
            <div class="table-responsive">
                <table class="table table-sm table-bordered asd-table mb-0" id="asdTabelaHist">
                    <thead><tr>
                        ${htmlTh('hist', 'concurso', 'Concurso')}${htmlTh('hist', 'dezenas', 'Dezenas')}${htmlTh('hist', 'soma', 'Soma')}${htmlTh('hist', 'faixa', 'Faixa')}${htmlTh('hist', 'par_impar', 'Par/Ímpar')}
                    </tr></thead>
                    <tbody id="asdBodyHist">${htmlHist(histData)}</tbody>
                </table>
            </div>
            <h6 class="small fw-bold mt-4 mb-1">Classificação de cada concurso</h6>
            <p class="small text-muted mb-2">
                Do concurso mais recente ao 1. A soma de cada sorteio é comparada com a média do próprio padrão:
                Dentro da média, Próxima da média ou Fora da faixa.
            </p>
            <div id="asdMediaBox"></div>`;
        somasCache = null;
        mediaPage = 1;
        if (Number(janela) === 0) {
            somasCache = data;
            pintarClassificacaoMedia();
        } else {
            const box = $('asdMediaBox');
            if (box) box.innerHTML = '<p class="text-muted small mb-0">Carregando todos os concursos…</p>';
            carregarClassificacaoCompleta();
        }
        loaded.somas = true;
    }

    async function carregarClassificacaoCompleta() {
        try {
            const url = `${API}/somas?janela=0&base=${encodeURIComponent(base)}`;
            const r = await fetch(url);
            const data = await r.json();
            if (!data.sucesso) throw new Error(data.erro || 'Erro');
            somasCache = data;
            mediaPage = 1;
            pintarClassificacaoMedia();
        } catch (e) {
            const box = $('asdMediaBox');
            if (box) box.innerHTML = `<p class="text-danger small mb-0">${e.message || e}</p>`;
        }
    }

    function pintarClassificacaoMedia() {
        const box = $('asdMediaBox');
        if (!box || !somasCache) return;
        const linhas = aplicarOrdem('media', somasCache.linhas || []);
        const total = linhas.length;
        const pages = Math.max(1, Math.ceil(total / MEDIA_POR_PAG) || 1);
        if (mediaPage > pages) mediaPage = pages;
        if (mediaPage < 1) mediaPage = 1;
        const ini = (mediaPage - 1) * MEDIA_POR_PAG;
        const fatia = linhas.slice(ini, ini + MEDIA_POR_PAG);
        const rows = fatia.map((row) => `<tr>
                <td>${row.concurso}</td>
                <td>${row.data || '—'}</td>
                <td class="text-start font-monospace small">${fmtDezenas(row.dezenas)}</td>
                <td class="fw-bold">${row.soma}</td>
                <td>${pillMedia(row.status_media, row.status_media_label)}</td>
            </tr>`).join('');
        box.innerHTML = `
            <div class="d-flex flex-wrap gap-2 align-items-center mb-2">
                <button type="button" class="btn btn-sm btn-outline-secondary" id="asdMediaPrev" ${mediaPage <= 1 ? 'disabled' : ''}>‹</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="asdMediaNext" ${mediaPage >= pages ? 'disabled' : ''}>›</button>
                <span class="small text-muted">${total ? `Exibindo ${fatia.length} de ${total} · pág. ${mediaPage}/${pages}` : '—'}</span>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-bordered asd-table mb-0">
                    <thead><tr>
                        ${htmlTh('media', 'concurso', 'Concurso')}${htmlTh('media', 'data', 'Data')}${htmlTh('media', 'dezenas', 'Dezenas')}${htmlTh('media', 'soma', 'Soma')}${htmlTh('media', 'status', 'Classificação')}
                    </tr></thead>
                    <tbody>${rows || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
        $('asdMediaPrev')?.addEventListener('click', () => {
            mediaPage -= 1;
            pintarClassificacaoMedia();
        });
        $('asdMediaNext')?.addEventListener('click', () => {
            mediaPage += 1;
            pintarClassificacaoMedia();
        });
    }

    function renderDigitos(data) {
        setLabels(data);
        const r = data.resumo || {};
        renderKpis('asdKpisDigitos', [
            { label: 'Recomendado', valor: (r.qtd_recomendada != null ? r.qtd_recomendada + ' dígitos' : '—') },
            { label: 'Frequência', valor: fmtPct(r.qtd_recomendada_pct) },
            { label: 'Média qtd', valor: r.media_qtd ?? '—' },
            { label: 'Dígito + sai', valor: r.digito_mais_frequente ?? '—' },
        ]);

        const resumoQtd = (data.resumo_por_quantidade || []).map((row) => `
            <tr class="${row.destaque ? 'asd-top' : ''}">
                <td>${row.qtd_digitos}${row.recomendado ? ' <span class="asd-badge-rec">★★ Recomendado</span>' : ''}</td>
                <td>${row.ocorrencias}</td>
                <td>${fmtPct(row.pct)}</td>
            </tr>`).join('');

        const painel = (data.painel_digitos || []).map((p) => `
            <tr class="${p.destaque ? 'asd-top' : ''}">
                <td class="fw-bold">${p.digito}</td>
                <td>${p.concursos}</td>
                <td>${fmtPct(p.pct)}</td>
                <td>${p.aparicoes}</td>
            </tr>`).join('');

        const hist = (data.linhas || []).slice(0, 80).map((row) => `
            <tr class="${row.qtd_digitos === r.qtd_recomendada ? 'asd-top' : ''}">
                <td>${row.concurso}</td>
                <td class="text-start font-monospace small">${fmtDezenas(row.dezenas)}</td>
                <td>${row.digitos_fmt || '—'}</td>
                <td class="fw-bold">${row.qtd_digitos}</td>
                <td>${row.soma_dezenas ?? '—'}</td>
            </tr>`).join('');

        $('asdCorpoDigitos').innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Resumo por quantidade de dígitos</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered asd-table tabela-ordenavel mb-0">
                            <thead><tr>
                                <th>Qtd. dígitos</th><th>Nº de sorteios</th><th>Porcentagem</th>
                            </tr></thead>
                            <tbody>${resumoQtd || '<tr><td colspan="3" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                    <p class="small text-muted mt-2 mb-0">
                        Bata o olho na linha verde: é o comportamento mais frequente do histórico.
                    </p>
                </div>
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Frequência dos dígitos 0–9</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered asd-table tabela-ordenavel mb-0">
                            <thead><tr>
                                <th>Dígito</th><th>Concursos</th><th>%</th><th>Aparições</th>
                            </tr></thead>
                            <tbody>${painel || '<tr><td colspan="4" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                    <p class="small text-muted mt-2 mb-0">
                        Ausentes no último sorteio:
                        <strong>${(r.digitos_ausentes_ultimo || []).join(', ') || '—'}</strong>
                    </p>
                </div>
            </div>
            <h6 class="small fw-bold mb-2">Resultados detalhados
                <span class="text-muted fw-normal">(exibindo até 80 · total ${data.total_concursos || 0})</span>
            </h6>
            <div class="table-responsive">
                <table class="table table-sm table-bordered asd-table tabela-ordenavel mb-0">
                    <thead><tr>
                        <th>Concurso</th><th>Dezenas</th><th>Dígitos</th><th>Qtd.</th><th>Soma</th>
                    </tr></thead>
                    <tbody>${hist || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
        loaded.digitos = true;
    }

    async function fetchAba(path) {
        const url = `${API}/${path}?janela=${janela}&base=${encodeURIComponent(base)}`;
        const r = await fetch(url);
        return r.json();
    }

    async function carregarSomas(force) {
        if (loaded.somas && !force) return;
        $('asdCorpoSomas').innerHTML = '<p class="text-muted small">Carregando…</p>';
        const data = await fetchAba('somas');
        if (!data.sucesso) {
            $('asdCorpoSomas').innerHTML = `<p class="text-danger small">${data.erro || 'Erro'}</p>`;
            return;
        }
        renderSomas(data);
    }

    async function carregarDigitos(force) {
        if (loaded.digitos && !force) return;
        $('asdCorpoDigitos').innerHTML = '<p class="text-muted small">Carregando…</p>';
        const data = await fetchAba('digitos');
        if (!data.sucesso) {
            $('asdCorpoDigitos').innerHTML = `<p class="text-danger small">${data.erro || 'Erro'}</p>`;
            return;
        }
        renderDigitos(data);
    }

    function resetLoaded() {
        loaded = { somas: false, digitos: false };
    }

    async function recarregarAtiva() {
        resetLoaded();
        const digitosAtivo = $('asdPaneDigitos') && $('asdPaneDigitos').classList.contains('active');
        if (digitosAtivo) await carregarDigitos(true);
        else await carregarSomas(true);
    }

    const corpoSomas = $('asdCorpoSomas');
    if (corpoSomas) {
        corpoSomas.addEventListener('click', (ev) => {
            const th = ev.target.closest('th.ai-sort');
            if (!th) return;
            const table = th.dataset.table;
            const key = th.dataset.sort;
            const st = SORT[table];
            if (!st || !key) return;
            if (st.key === key) st.dir = st.dir === 'asc' ? 'desc' : 'asc';
            else {
                st.key = key;
                const descPrimeiro = new Set(['ocorrencias', 'pct', 'soma', 'concurso', 'data']);
                st.dir = descPrimeiro.has(key) ? 'desc' : 'asc';
            }
            if (table === 'media') {
                mediaPage = 1;
                pintarClassificacaoMedia();
                return;
            }
            const tbody = table === 'faixas' ? $('asdBodyFaixas')
                : table === 'ranking' ? $('asdBodyRanking')
                : $('asdBodyHist');
            if (!tbody) return;
            if (table === 'faixas') tbody.innerHTML = htmlFaixas(faixasData);
            else if (table === 'ranking') tbody.innerHTML = htmlRanking(rankingData);
            else tbody.innerHTML = htmlHist(histData);
            const tabela = th.closest('table');
            if (!tabela) return;
            tabela.querySelectorAll('th.ai-sort').forEach((h) => {
                const on = h.dataset.sort === st.key;
                h.classList.toggle('ai-sort-asc', on && st.dir === 'asc');
                h.classList.toggle('ai-sort-desc', on && st.dir === 'desc');
                const ind = h.querySelector('.ai-sort-ind');
                if (ind) ind.textContent = on ? (st.dir === 'asc' ? '▲' : '▼') : '⇅';
            });
        });
    }

    document.querySelectorAll('#asdTabsBase .base-tab-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#asdTabsBase .base-tab-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            base = btn.dataset.base;
            recarregarAtiva();
        });
    });

    document.querySelectorAll('#asdGrpJanela .janela-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#asdGrpJanela .janela-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            janela = parseInt(btn.dataset.janela, 10);
            recarregarAtiva();
        });
    });

    const tabDigitos = $('asdTabDigitos');
    if (tabDigitos) {
        tabDigitos.addEventListener('shown.bs.tab', () => carregarDigitos(false));
    }
    const tabSomas = $('asdTabSomas');
    if (tabSomas) {
        tabSomas.addEventListener('shown.bs.tab', () => carregarSomas(false));
    }

    carregarSomas(true);
})();
