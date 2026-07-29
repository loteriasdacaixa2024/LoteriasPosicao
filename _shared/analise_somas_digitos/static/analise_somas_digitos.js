(function () {
    'use strict';

    const root = document.getElementById('asd-root');
    if (!root) return;

    const API = window.__ASD_API__ || root.dataset.api;
    const UI = window.__ASD_UI__ || {};

    let base = 'geral';
    let janela = UI.janela_default != null ? UI.janela_default : 0;
    let loaded = { somas: false, digitos: false };

    const $ = (id) => document.getElementById(id);

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

        const faixas = (data.distribuicao_faixas || []).map((f) => `
            <tr class="${f.destaque ? 'asd-top' : ''}">
                <td>${f.faixa}</td>
                <td>${f.ocorrencias}</td>
                <td>${fmtPct(f.pct)}</td>
            </tr>`).join('');

        const ranking = (data.ranking_somas || []).slice(0, 15).map((s, i) => `
            <tr class="${i === 0 ? 'asd-top' : ''}">
                <td>${s.soma}</td>
                <td>${s.ocorrencias}</td>
                <td>${fmtPct(s.pct)}</td>
            </tr>`).join('');

        const hist = (data.linhas || []).slice(0, 80).map((row) => `
            <tr>
                <td>${row.concurso}</td>
                <td class="text-start font-monospace small">${fmtDezenas(row.dezenas)}</td>
                <td class="fw-bold">${row.soma}</td>
                <td>${row.faixa}</td>
                <td>${row.par_impar}</td>
            </tr>`).join('');

        $('asdCorpoSomas').innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-lg-6">
                    <h6 class="small fw-bold mb-2">Resumo por faixa de soma</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered asd-table mb-0">
                            <thead><tr><th>Faixa</th><th>Nº de sorteios</th><th>Porcentagem</th></tr></thead>
                            <tbody>${faixas || '<tr><td colspan="3" class="text-muted">Sem dados</td></tr>'}</tbody>
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
                        <table class="table table-sm table-bordered asd-table mb-0">
                            <thead><tr><th>Soma</th><th>Nº de sorteios</th><th>Porcentagem</th></tr></thead>
                            <tbody>${ranking || '<tr><td colspan="3" class="text-muted">Sem dados</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <h6 class="small fw-bold mb-2">Histórico das somas
                <span class="text-muted fw-normal">(exibindo até 80 · total ${data.total_concursos || 0})</span>
            </h6>
            <div class="table-responsive">
                <table class="table table-sm table-bordered asd-table mb-0">
                    <thead><tr>
                        <th>Concurso</th><th>Dezenas</th><th>Soma</th><th>Faixa</th><th>Par/Ímpar</th>
                    </tr></thead>
                    <tbody>${hist || '<tr><td colspan="5" class="text-muted">Sem dados</td></tr>'}</tbody>
                </table>
            </div>`;
        loaded.somas = true;
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
                        <table class="table table-sm table-bordered asd-table mb-0">
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
                        <table class="table table-sm table-bordered asd-table mb-0">
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
                <table class="table table-sm table-bordered asd-table mb-0">
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
