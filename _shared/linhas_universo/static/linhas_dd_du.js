(function () {
    'use strict';

    const root = document.getElementById('ldd-root');
    if (!root) return;

    const UI = window.__LDD_UI__ || {};
    let base = 'geral';
    // Página abre em "Todos" (1º → atual), independente do default global
    let janela = 0;
    let loaded = { linhas: false, dddu: false };
    let cache = { linhas: null, dddu: null };
    let histState = {
        linhas: { key: 'concurso', dir: 'asc', page: 1, size: 100 },
        dddu: { key: 'concurso', dir: 'asc', page: 1, size: 100 },
    };

    const $ = (id) => document.getElementById(id);

    function fmtPct(v) {
        const n = Number(v);
        if (Number.isNaN(n)) return '—';
        return (Math.round(n * 100) / 100).toLocaleString('pt-BR') + '%';
    }

    function sortedDez(arr) {
        return [...(arr || [])]
            .map((n) => Number(n))
            .filter((n) => Number.isFinite(n))
            .sort((a, b) => a - b);
    }

    function fmtDezenas(arr) {
        const nums = sortedDez(arr);
        if (!nums.length) return '—';
        const pad = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
        return nums.map((v) => {
            if (pad <= 1) return String(v);
            return String(v).padStart(pad, '0');
        }).join(pad <= 1 ? ' | ' : ' ');
    }

    function ddDuOrdenados(arr) {
        const pad = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
        const nums = sortedDez(arr);
        const dd = [];
        const du = [];
        nums.forEach((n) => {
            if (pad <= 1) {
                dd.push(0);
                du.push(Math.abs(n) % 10);
            } else {
                const v = Math.abs(n) % 100;
                dd.push(Math.floor(v / 10));
                du.push(v % 10);
            }
        });
        return { dezenas: nums, dd, du };
    }

    function padDez(n) {
        const pad = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
        const v = Number(n);
        if (!Number.isFinite(v)) return String(n);
        if (pad <= 1) return String(v);
        return String(v).padStart(pad, '0');
    }

    function setLabels(data) {
        const bl = $('lddLblBase');
        const jl = $('lddLblJanela');
        const ul = $('lddLblUltimo');
        if (bl) bl.textContent = data.base_label || base;
        if (jl) jl.textContent = janela === 0 ? 'Todos' : ('Janela ' + janela);
        if (ul) ul.textContent = data.ultimo_concurso != null ? ('Último c.' + data.ultimo_concurso) : '—';
    }

    function renderKpis(elId, items) {
        const el = $(elId);
        if (!el) return;
        el.innerHTML = items.map((k) => `
            <div class="col-6 col-md-3">
                <div class="ldd-kpi" title="${esc(k.tip || k.label)}">
                    <div class="lbl">${k.label}</div>
                    <div class="val">${k.valor}</div>
                </div>
            </div>`).join('');
    }

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function sortInd(state, key) {
        if (state.key !== key) return '⇅';
        return state.dir === 'asc' ? '↑' : '↓';
    }

    function thSort(state, key, label, tip) {
        const active = state.key === key ? ' ldd-sort-active' : '';
        return `<th class="ldd-sort${active}" data-sort="${esc(key)}" title="${esc(tip || 'Clique para ordenar')}">${esc(label)} <span class="ldd-sort-ind">${sortInd(state, key)}</span></th>`;
    }

    function cmpVal(a, b, key) {
        let va = a[key];
        let vb = b[key];
        if (key === 'dezenas') {
            va = fmtDezenas(a.dezenas || []);
            vb = fmtDezenas(b.dezenas || []);
        } else if (key === 'linhas_txt') {
            va = (a.linhas_presentes || []).join(',');
            vb = (b.linhas_presentes || []).join(',');
        } else if (key === 'dd_txt') {
            va = ddDuOrdenados(a.dezenas).dd.join(',');
            vb = ddDuOrdenados(b.dezenas).dd.join(',');
        } else if (key === 'du_txt') {
            va = ddDuOrdenados(a.dezenas).du.join(',');
            vb = ddDuOrdenados(b.dezenas).du.join(',');
        }
        const na = Number(va);
        const nb = Number(vb);
        if (Number.isFinite(na) && Number.isFinite(nb) && String(va).trim() !== '' && String(vb).trim() !== '') {
            return na - nb;
        }
        return String(va ?? '').localeCompare(String(vb ?? ''), 'pt-BR', { numeric: true });
    }

    function sortedRows(rows, state) {
        const dir = state.dir === 'desc' ? -1 : 1;
        return [...rows].sort((a, b) => dir * cmpVal(a, b, state.key));
    }

    function pageSlice(rows, state) {
        const total = rows.length;
        const size = state.size === 0 ? total : state.size;
        const pages = Math.max(1, Math.ceil(total / Math.max(1, size)) || 1);
        if (state.page > pages) state.page = pages;
        if (state.page < 1) state.page = 1;
        const start = (state.page - 1) * size;
        return {
            total,
            pages,
            size,
            page: state.page,
            rows: size === 0 ? rows : rows.slice(start, start + size),
            start: total ? start + 1 : 0,
            end: size === 0 ? total : Math.min(total, start + size),
        };
    }

    function histToolbar(which, meta) {
        const st = histState[which];
        const data = which === 'linhas' ? cache.linhas : cache.dddu;
        const prim = data && data.primeiro_concurso != null ? data.primeiro_concurso : '—';
        const ult = data && data.ultimo_concurso != null ? data.ultimo_concurso : '—';
        return `
            <div class="ldd-hist-toolbar">
                <div class="small text-muted">
                    Concursos <strong>${prim} → ${ult}</strong>
                    · exibindo <strong>${meta.start}–${meta.end}</strong> de <strong>${meta.total}</strong>
                    · ordenado por <strong>${esc(st.key)}</strong> (${st.dir === 'asc' ? 'menor → maior' : 'maior → menor'})
                </div>
                <div class="d-flex flex-wrap gap-2 align-items-center">
                    <label class="small text-muted mb-0">Por página</label>
                    <select class="form-select form-select-sm ldd-page-size" data-which="${which}" style="width:auto">
                        <option value="50"${st.size === 50 ? ' selected' : ''}>50</option>
                        <option value="100"${st.size === 100 ? ' selected' : ''}>100</option>
                        <option value="250"${st.size === 250 ? ' selected' : ''}>250</option>
                        <option value="0"${st.size === 0 ? ' selected' : ''}>Todos</option>
                    </select>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-secondary ldd-page-btn" data-which="${which}" data-delta="-1" ${meta.page <= 1 ? 'disabled' : ''}>‹</button>
                        <button type="button" class="btn btn-outline-secondary" disabled>${meta.page}/${meta.pages}</button>
                        <button type="button" class="btn btn-outline-secondary ldd-page-btn" data-which="${which}" data-delta="1" ${meta.page >= meta.pages ? 'disabled' : ''}>›</button>
                    </div>
                </div>
            </div>`;
    }

    function bindHistControls(container, which, redraw) {
        container.querySelectorAll('th.ldd-sort').forEach((th) => {
            th.addEventListener('click', () => {
                const key = th.getAttribute('data-sort');
                const st = histState[which];
                if (st.key === key) st.dir = st.dir === 'asc' ? 'desc' : 'asc';
                else { st.key = key; st.dir = 'asc'; }
                st.page = 1;
                redraw();
            });
        });
        container.querySelectorAll('.ldd-page-size').forEach((sel) => {
            sel.addEventListener('change', () => {
                histState[which].size = Number(sel.value);
                histState[which].page = 1;
                redraw();
            });
        });
        container.querySelectorAll('.ldd-page-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                histState[which].page += Number(btn.getAttribute('data-delta') || 0);
                redraw();
            });
        });
    }

    function syncJanelaButtons() {
        document.querySelectorAll('#lddGrpJanela .janela-btn').forEach((b) => {
            const j = Number(b.getAttribute('data-janela') || 0);
            b.classList.toggle('active', j === janela);
        });
    }

    function renderLinhasHistOnly() {
        const data = cache.linhas;
        if (!data) return;
        const wrap = $('lddHistLinhasWrap');
        if (!wrap) return;
        const st = histState.linhas;
        const ordered = sortedRows(data.linhas || [], st);
        const meta = pageSlice(ordered, st);
        const body = meta.rows.map((row) => `
            <tr>
                <td>${row.concurso}</td>
                <td class="ldd-col-dezenas font-mono small">${fmtDezenas(row.dezenas)}</td>
                <td>${(row.linhas_presentes || []).map((x) => `<span class="ldd-chip" title="Linha ${esc(x)}">${esc(x)}</span>`).join('')}</td>
                <td class="fw-bold">${row.qtd_linhas}</td>
            </tr>`).join('');

        wrap.innerHTML = `
            <h6 class="small fw-bold mb-2">Histórico completo
                <span class="text-muted fw-normal">(do 1º ao atual na janela · ${data.total_concursos || 0} concursos)</span>
            </h6>
            <p class="small text-muted mb-2">Clique no cabeçalho da coluna para classificar. Ao abrir: <strong>menor → maior</strong> (concurso). Dezenas sempre em ordem crescente.</p>
            ${histToolbar('linhas', meta)}
            <div class="table-responsive">
                <table class="table table-sm table-bordered ldd-table mb-0" id="lddHistLinhasTable">
                    <thead><tr>
                        ${thSort(st, 'concurso', 'Concurso', 'Ordenar por número do concurso')}
                        ${thSort(st, 'dezenas', 'Dezenas', 'Ordenar pelo texto das dezenas')}
                        ${thSort(st, 'linhas_txt', 'Linhas', 'Ordenar pelas linhas presentes')}
                        ${thSort(st, 'qtd_linhas', 'Qtd', 'Ordenar pela quantidade de linhas')}
                    </tr></thead>
                    <tbody>${body || '<tr><td colspan="4" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
        bindHistControls(wrap, 'linhas', renderLinhasHistOnly);
    }

    function renderDdDuHistOnly() {
        const data = cache.dddu;
        if (!data) return;
        const wrap = $('lddHistDdDuWrap');
        if (!wrap) return;
        const st = histState.dddu;
        const ordered = sortedRows(data.linhas || [], st);
        const meta = pageSlice(ordered, st);
        const body = meta.rows.map((row) => {
            const ord = ddDuOrdenados(row.dezenas);
            return `
            <tr>
                <td>${row.concurso}</td>
                <td class="ldd-col-dezenas font-mono small" title="Dezenas em ordem crescente (classificação)">${fmtDezenas(row.dezenas)}</td>
                <td class="font-mono small" title="DD na mesma ordem das dezenas classificadas">${ord.dd.join(', ')}</td>
                <td class="font-mono small" title="DU na mesma ordem das dezenas classificadas">${ord.du.join(', ')}</td>
            </tr>`;
        }).join('');

        wrap.innerHTML = `
            <h6 class="small fw-bold mb-2 mt-3">Histórico completo
                <span class="text-muted fw-normal">(do 1º ao atual na janela · ${data.total_concursos || 0} concursos)</span>
            </h6>
            <p class="small text-muted mb-2">Clique no cabeçalho da coluna para classificar. Ao abrir: <strong>menor → maior</strong> (concurso). Dezenas sempre em ordem crescente.</p>
            ${histToolbar('dddu', meta)}
            <div class="table-responsive">
                <table class="table table-sm table-bordered ldd-table mb-0">
                    <thead><tr>
                        ${thSort(st, 'concurso', 'Concurso', 'Ordenar por número do concurso')}
                        ${thSort(st, 'dezenas', 'Dezenas', 'Ordenar pelo texto das dezenas')}
                        ${thSort(st, 'dd_txt', 'DD', 'Ordenar pela sequência de Dígitos da Dezena')}
                        ${thSort(st, 'du_txt', 'DU', 'Ordenar pela sequência de Dígitos da Unidade')}
                    </tr></thead>
                    <tbody>${body || '<tr><td colspan="4" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
        bindHistControls(wrap, 'dddu', renderDdDuHistOnly);
    }

    function rankingLinhasHtml(freq) {
        const ranked = [...(freq || [])].sort((a, b) => {
            const d = (b.ocorrencias || 0) - (a.ocorrencias || 0);
            if (d !== 0) return d;
            return String(a.linha || '').localeCompare(String(b.linha || ''), 'pt-BR', { numeric: true });
        });
        const medals = ['🥇', '🥈', '🥉'];
        const labels = ['1º Lugar', '2º Lugar', '3º Lugar'];
        const top = ranked.slice(0, 3);

        const cards = [0, 1, 2].map((i) => {
            const f = top[i];
            if (!f) {
                return `<div class="col-md-4"><div class="ldd-rank-card ldd-rank-${i + 1} text-muted small">—</div></div>`;
            }
            return `
              <div class="col-md-4">
                <div class="ldd-rank-card ldd-rank-${i + 1}"
                     title="${esc(f.linha)} (${esc(f.label || '')}): ${f.ocorrencias} presença(s) · ${fmtPct(f.pct)}">
                  <div class="ldd-rank-pos">${medals[i]} ${labels[i]}</div>
                  <div class="ldd-rank-line">${esc(f.linha)}</div>
                  <div class="ldd-rank-faixa">${esc(f.label || '')}</div>
                  <div class="ldd-rank-meta">
                    <strong>${f.ocorrencias}</strong> ocorrências
                    · <strong>${fmtPct(f.pct)}</strong>
                  </div>
                </div>
              </div>`;
        }).join('');

        const rows = ranked.map((f, i) => {
            const pos = i + 1;
            const rowCls = pos <= 3 ? ` ldd-rank-row-${pos}` : '';
            const medal = pos <= 3 ? `${medals[pos - 1]} ` : '';
            return `
              <tr class="${rowCls.trim()}" title="${esc(f.linha)} — ${f.ocorrencias} ocorrências (${fmtPct(f.pct)})">
                <td class="fw-bold">${medal}${pos}º</td>
                <td class="fw-bold">${esc(f.linha)}</td>
                <td>${esc(f.label || '—')}</td>
                <td>${f.ocorrencias}</td>
                <td>${fmtPct(f.pct)}</td>
                <td>${f.atraso ?? '—'}</td>
              </tr>`;
        }).join('');

        return `
          <div class="ldd-rank-wrap">
            <div class="ldd-rank-title">
              <i class="fas fa-trophy me-1 text-warning"></i> Ranking das Linhas
              <span class="text-muted fw-normal small">— mais frequente → menos frequente</span>
            </div>
            <p class="small text-muted mb-2">
              Baseado nas <em>presenças</em> por concurso (mesma regra da frequência).
              Atualiza automaticamente ao mudar Base ou Janela.
            </p>
            <div class="row g-2 mb-3">${cards}</div>
            <h6 class="small fw-bold mb-2">Ranking completo</h6>
            <div class="table-responsive">
              <table class="table table-sm table-bordered ldd-table mb-0">
                <thead><tr>
                  <th title="Posição no ranking">Pos.</th>
                  <th>Linha</th>
                  <th>Faixa</th>
                  <th title="Concursos com pelo menos 1 dezena desta linha">Ocorrências</th>
                  <th title="% sobre o total de concursos da janela">%</th>
                  <th title="Concursos sem a linha desde a última aparição">Atraso</th>
                </tr></thead>
                <tbody>${rows || '<tr><td colspan="6" class="text-muted">Sem dados</td></tr>'}</tbody>
              </table>
            </div>
          </div>`;
    }

    function renderLinhas(data) {
        cache.linhas = data;
        histState.linhas.key = 'concurso';
        histState.linhas.dir = 'asc';
        histState.linhas.page = 1;
        setLabels(data);
        const mapa = data.mapa || {};
        const linhasMapa = mapa.linhas || [];
        const freq = data.frequencia_linhas || [];

        renderKpis('lddKpisLinhas', [
            { label: 'Linhas ativas', valor: mapa.qtd_linhas ?? linhasMapa.length, tip: 'Quantidade de linhas L1–L10 usadas nesta modalidade' },
            { label: 'Universo', valor: `${padDez(mapa.dezena_min)}–${padDez(mapa.dezena_max)}`, tip: 'Intervalo oficial de dezenas' },
            { label: 'Concursos', valor: data.total_concursos ?? '—', tip: 'Total de concursos na janela/base selecionada' },
            { label: 'Último', valor: data.ultimo_concurso ?? '—', tip: 'Último concurso da série carregada' },
        ]);

        const mapaHtml = linhasMapa.map((L) => `
            <tr title="Linha ${esc(L.id)}: dezenas ${esc(L.label)}">
                <td class="fw-bold">${esc(L.id)}</td>
                <td>${esc(L.label)}</td>
                <td>${L.qtd}</td>
                <td class="ldd-col-dezenas font-mono small">${fmtDezenas(L.dezenas)}</td>
            </tr>`).join('');

        $('lddCorpoLinhas').innerHTML = `
            <div class="ldd-help">
                <strong>O que é Linha?</strong>
                Cada linha (L1…L10) é um bloco oficial de 10 dezenas (L1=01–10, L2=11–20…).
                Esta modalidade usa só as linhas do seu universo.
                <em>Ocorrências / Presenças</em> = concursos em que saiu pelo menos uma dezena daquela linha.
                <em>Atraso</em> = quantos concursos seguidos a linha não aparece.
            </div>
            ${rankingLinhasHtml(freq)}
            <div class="row g-3 mb-3">
                <div class="col-12">
                    <h6 class="small fw-bold mb-2">Mapa de linhas desta modalidade</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered ldd-table mb-0">
                            <thead><tr>
                                <th title="Identificador da linha">Linha</th>
                                <th title="Faixa efetiva no universo">Faixa</th>
                                <th title="Quantidade de dezenas na linha">Qtd</th>
                                <th title="Dezenas que pertencem à linha">Dezenas</th>
                            </tr></thead>
                            <tbody>${mapaHtml || '<tr><td colspan="4" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div id="lddHistLinhasWrap"></div>`;
        renderLinhasHistOnly();
        loaded.linhas = true;
    }

    function heatClass(v, max) {
        if (!max || !v) return '';
        const r = v / max;
        if (r >= 0.66) return 'ldd-cell-hot';
        if (r >= 0.33) return 'ldd-cell-mid';
        return '';
    }

    function renderDdDu(data) {
        cache.dddu = data;
        histState.dddu.key = 'concurso';
        histState.dddu.dir = 'asc';
        histState.dddu.page = 1;
        setLabels(data);
        const freqDd = data.frequencia_dd || [];
        const freqDu = data.frequencia_du || [];
        const mat = data.matriz_dd_du || {};
        const grid = mat.grid || [];
        const ddDom = mat.dd || data.dd_dominio || [];
        const duDom = mat.du || data.du_dominio || [];
        let maxCell = 0;
        grid.forEach((row) => row.forEach((v) => { if (v > maxCell) maxCell = v; }));

        const topDd = [...freqDd].sort((a, b) => b.presencas - a.presencas)[0];
        const topDu = [...freqDu].sort((a, b) => b.presencas - a.presencas)[0];

        renderKpis('lddKpisDdDu', [
            { label: 'Concursos', valor: data.total_concursos ?? '—', tip: 'Total na janela/base' },
            { label: 'DD domínio', valor: (ddDom || []).join(',') || '—', tip: 'Dígitos da dezena possíveis neste universo' },
            { label: 'DD + presente', valor: topDd ? String(topDd.dd) : '—', tip: 'DD que mais apareceu em concursos' },
            { label: 'DU + presente', valor: topDu ? String(topDu.du) : '—', tip: 'DU que mais apareceu em concursos' },
        ]);

        const ddHtml = freqDd.map((f) => `
            <tr title="DD ${f.dd}: presente em ${f.presencas} concurso(s); ${f.ocorrencias} dezena(s) no histórico; atraso ${f.atraso}">
                <td class="fw-bold">${f.dd}</td>
                <td>${f.presencas}</td>
                <td>${f.ocorrencias}</td>
                <td>${fmtPct(f.pct_presenca)}</td>
                <td>${f.atraso}</td>
            </tr>`).join('');

        const duHtml = freqDu.map((f) => `
            <tr title="DU ${f.du}: presente em ${f.presencas} concurso(s); ${f.ocorrencias} dezena(s) no histórico; atraso ${f.atraso}">
                <td class="fw-bold">${f.du}</td>
                <td>${f.presencas}</td>
                <td>${f.ocorrencias}</td>
                <td>${fmtPct(f.pct_presenca)}</td>
                <td>${f.atraso}</td>
            </tr>`).join('');

        let matrizHtml = '';
        if (ddDom.length && duDom.length) {
            const head = duDom.map((u) =>
                `<th title="Coluna DU=${u} (unidade). Ex.: DD=2 e DU=${u} forma a dezena ${padDez(2 * 10 + u)}">DU${u}</th>`
            ).join('');
            const body = ddDom.map((d, i) => {
                const cells = (grid[i] || []).map((v, j) => {
                    const u = duDom[j];
                    const dez = padDez(Number(d) * 10 + Number(u));
                    const tip = v
                        ? `Dezena ${dez} (DD=${d}, DU=${u}) saiu ${v} vez(es) no histórico da janela.`
                        : `Dezena ${dez} (DD=${d}, DU=${u}) não saiu nesta janela.`;
                    return `<td class="${heatClass(v, maxCell)}" title="${esc(tip)}">${v || ''}</td>`;
                }).join('');
                return `<tr><th title="Linha DD=${d} (dezena). Ex.: DD=${d} e DU=5 → ${padDez(d * 10 + 5)}">DD${d}</th>${cells}</tr>`;
            }).join('');
            matrizHtml = `
                <div class="table-responsive">
                    <table class="table table-sm table-bordered ldd-table ldd-matriz mb-0">
                        <thead><tr><th title="Cruzamento: linha = DD, coluna = DU">DD \\ DU</th>${head}</tr></thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
                <p class="small text-muted mt-2 mb-0">
                    Cada célula = uma dezena (ex.: DD1 × DU7 = <strong>17</strong>).
                    O número = quantas vezes essa dezena saiu. Passe o mouse na célula para o detalhe.
                </p>`;
        }

        $('lddCorpoDdDu').innerHTML = `
            <div class="ldd-help">
                <strong>O que é DD × DU?</strong>
                Toda dezena se divide em dois dígitos:
                <strong>DD</strong> = Dígito da Dezena e <strong>DU</strong> = Dígito da Unidade.
                Exemplos: <code>08</code> → DD=0, DU=8 · <code>17</code> → DD=1, DU=7 · <code>31</code> → DD=3, DU=1.
                <br>
                <strong>Presenças</strong> = concursos em que o dígito apareceu pelo menos uma vez.
                <strong>Ocorrências</strong> = total de vezes do dígito somando todas as dezenas.
                <strong>Atraso</strong> = concursos seguidos sem aquele dígito.
            </div>
            <div class="row g-3 mb-3">
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Frequência DD (Dígito da Dezena)</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered ldd-table mb-0">
                            <thead><tr>
                                <th title="Dígito da dezena (0 em 01–09, 1 em 10–19…)">DD</th>
                                <th title="Concursos com pelo menos um DD">Presenças</th>
                                <th title="Total de dezenas com este DD">Ocorrências</th>
                                <th>%</th>
                                <th title="Concursos sem este DD">Atraso</th>
                            </tr></thead>
                            <tbody>${ddHtml || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Frequência DU (Dígito da Unidade)</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered ldd-table mb-0">
                            <thead><tr>
                                <th title="Dígito da unidade (o final da dezena)">DU</th>
                                <th title="Concursos com pelo menos um DU">Presenças</th>
                                <th title="Total de dezenas com este DU">Ocorrências</th>
                                <th>%</th>
                                <th title="Concursos sem este DU">Atraso</th>
                            </tr></thead>
                            <tbody>${duHtml || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="mb-3">
                <button class="btn btn-sm btn-outline-secondary" type="button"
                        data-bs-toggle="collapse" data-bs-target="#lddMatrizCollapse"
                        aria-expanded="false" aria-controls="lddMatrizCollapse">
                    <i class="fas fa-table me-1"></i> Mostrar / ocultar Distribuição DD × DU
                </button>
                <span class="small text-muted ms-2">opcional — matriz detalhada dezena a dezena</span>
                <div class="collapse mt-2" id="lddMatrizCollapse">
                    <div class="border rounded p-2 bg-light">
                        <h6 class="small fw-bold mb-2 mb-0">Distribuição DD × DU</h6>
                        ${matrizHtml || '<p class="text-muted small mb-0">Sem matriz</p>'}
                    </div>
                </div>
            </div>
            <div id="lddHistDdDuWrap"></div>`;
        renderDdDuHistOnly();
        loaded.dddu = true;
    }

    async function loadLinhas() {
        $('lddCorpoLinhas').innerHTML = '<p class="text-muted small">Carregando…</p>';
        try {
            const url = `/analise/api/linhas-universo/analise?janela=${janela}&base=${encodeURIComponent(base)}`;
            const r = await fetch(url);
            const j = await r.json();
            if (!j.sucesso) {
                $('lddCorpoLinhas').innerHTML = `<p class="text-danger small">${esc(j.erro || 'Falha')}</p>`;
                return;
            }
            renderLinhas(j);
        } catch (e) {
            $('lddCorpoLinhas').innerHTML = `<p class="text-danger small">${esc(e.message || e)}</p>`;
        }
    }

    async function loadDdDu() {
        $('lddCorpoDdDu').innerHTML = '<p class="text-muted small">Carregando…</p>';
        try {
            const url = `/analise/api/dd-du/analise?janela=${janela}&base=${encodeURIComponent(base)}`;
            const r = await fetch(url);
            const j = await r.json();
            if (!j.sucesso) {
                $('lddCorpoDdDu').innerHTML = `<p class="text-danger small">${esc(j.erro || 'Falha')}</p>`;
                return;
            }
            renderDdDu(j);
        } catch (e) {
            $('lddCorpoDdDu').innerHTML = `<p class="text-danger small">${esc(e.message || e)}</p>`;
        }
    }

    function reloadAll() {
        loaded = { linhas: false, dddu: false };
        loadLinhas();
        const pane = document.getElementById('lddPaneDdDu');
        if (pane && (pane.classList.contains('active') || pane.classList.contains('show'))) {
            loadDdDu();
        }
    }

    document.querySelectorAll('#lddTabsBase .base-tab-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#lddTabsBase .base-tab-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            base = btn.getAttribute('data-base') || 'geral';
            reloadAll();
        });
    });

    document.querySelectorAll('#lddGrpJanela .janela-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#lddGrpJanela .janela-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            janela = Number(btn.getAttribute('data-janela') || 0);
            reloadAll();
        });
    });

    document.querySelector('[data-bs-target="#lddPaneDdDu"]')?.addEventListener('shown.bs.tab', () => {
        if (!loaded.dddu) loadDdDu();
        else {
            // reabre com ordem padrão menor → maior
            histState.dddu.key = 'concurso';
            histState.dddu.dir = 'asc';
            histState.dddu.page = 1;
            renderDdDuHistOnly();
        }
    });

    document.querySelector('[data-bs-target="#lddPaneLinhas"]')?.addEventListener('shown.bs.tab', () => {
        if (loaded.linhas) {
            histState.linhas.key = 'concurso';
            histState.linhas.dir = 'asc';
            histState.linhas.page = 1;
            renderLinhasHistOnly();
        }
    });

    syncJanelaButtons();
    loadLinhas();
})();
