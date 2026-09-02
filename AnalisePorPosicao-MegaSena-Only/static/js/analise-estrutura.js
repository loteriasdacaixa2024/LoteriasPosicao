/**
 * Renderização estrutural — abas Linhas e Colunas + Geometria do Volante
 */
(function (global) {
    let _dataGeo = null;

    function pctFmt(p) {
        return (typeof p === 'number' ? p : 0).toFixed(1).replace('.', ',') + '%';
    }

    function renderMiniVolante(dezenas, geo) {
        const set = new Set((dezenas || []).map(Number));
        const colH = new Set();
        const linH = new Set();
        if (geo) {
            for (let c = 1; c <= 10; c++) {
                if (parseInt(geo.col_counts?.[String(c)] || 0, 10) >= 2) colH.add(c);
            }
            for (let l = 1; l <= 6; l++) {
                if (parseInt(geo.lin_counts?.[String(l)] || 0, 10) >= 2) linH.add(l);
            }
        }
        let html = '<div class="mini-volante-grid">';
        for (let lin = 1; lin <= 6; lin++) {
            for (let col = 1; col <= 10; col++) {
                const d = (lin - 1) * 10 + col;
                const on = set.has(d);
                let cls = 'mv-cell';
                if (on) cls += ' mv-on';
                if (colH.has(col)) cls += ' mv-col-dup';
                if (linH.has(lin)) cls += ' mv-lin-dup';
                html += `<div class="${cls}" title="${String(d).padStart(2, '0')}">${String(d).padStart(2, '0')}</div>`;
            }
        }
        html += '</div>';
        return html;
    }

    function showGeoModal(exemplo) {
        if (!exemplo || !exemplo.dezenas) return;
        const geo = exemplo.geo || {};
        Swal.fire({
            title: `Concurso #${exemplo.concurso}`,
            html: `
                <p class="small text-muted mb-2">${exemplo.data || ''}</p>
                <p class="fw-bold mb-2">${exemplo.dezenas.join(' • ')}</p>
                ${renderMiniVolante(exemplo.dezenas.map(d => parseInt(d, 10)), geo)}
                <p class="small mt-2 mb-0"><strong>${geo.nome_estrutura || ''}</strong> · ${geo.assinatura || ''}</p>
            `,
            width: 520,
            confirmButtonText: 'Fechar',
        });
    }

    function bindExemploButtons(root) {
        root.querySelectorAll('[data-exemplo]').forEach(btn => {
            btn.addEventListener('click', () => {
                try {
                    showGeoModal(JSON.parse(decodeURIComponent(btn.dataset.exemplo)));
                } catch (_) {}
            });
        });
    }

    function exemploAttr(ex) {
        if (!ex || !ex.concurso) return '';
        return `data-exemplo="${encodeURIComponent(JSON.stringify(ex))}"`;
    }

    function tabelaEstatisticas(id, rows) {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = rows.map(r => `
            <tr>
                <td>${r.estrutura}
                    ${r.exemplo ? `<button type="button" class="btn btn-link btn-sm p-0 ms-1" ${exemploAttr(r.exemplo)} title="Ver no volante"><i class="fas fa-eye"></i></button>` : ''}
                </td>
                <td class="text-end fw-bold">${(r.quantidade || 0).toLocaleString()}</td>
                <td class="text-end font-monospace">${pctFmt(r.porcentagem)}</td>
            </tr>
        `).join('');
        bindExemploButtons(el.closest('table') || el);
    }

    function renderLinCol() {
        if (!_dataGeo) return;
        const d = _dataGeo;

        tabelaEstatisticas('tblEstatColunaRep', d.estatisticas_coluna_repeticao || []);

        const colBody = document.getElementById('tblDistColunas');
        if (colBody) {
            colBody.innerHTML = (d.distribuicao_colunas || []).map(c => `
                <tr>
                    <td>${c.label}</td>
                    <td class="text-end fw-bold">${c.frequencia.toLocaleString()}</td>
                    <td class="text-end font-monospace">${pctFmt(c.porcentagem)}</td>
                </tr>
            `).join('');
        }

        const linBody = document.getElementById('tblDistLinhas');
        if (linBody) {
            linBody.innerHTML = (d.distribuicao_linhas || []).map(l => `
                <tr>
                    <td>Linha ${l.label}</td>
                    <td class="text-end fw-bold">${l.frequencia.toLocaleString()}</td>
                    <td class="text-end font-monospace">${pctFmt(l.porcentagem)}</td>
                </tr>
            `).join('');
        }

        const estBody = document.getElementById('tblEstruturasCompletas');
        if (estBody) {
            estBody.innerHTML = (d.estruturas_completas || []).map(e => `
                <tr>
                    <td>${e.estrutura}
                        <button type="button" class="btn btn-link btn-sm p-0 ms-1" ${exemploAttr(e.exemplo)}><i class="fas fa-eye"></i></button>
                    </td>
                    <td class="text-end fw-bold">${e.frequencia.toLocaleString()}</td>
                    <td class="text-end font-monospace">${pctFmt(e.porcentagem)}</td>
                </tr>
            `).join('');
            bindExemploButtons(estBody.closest('table') || estBody);
        }

        const u = d.ultimo_concurso_analise;
        const ultBox = document.getElementById('ultimoConcursoGeo');
        if (ultBox && u) {
            ultBox.innerHTML = `
                <div class="row g-3 align-items-center">
                    <div class="col-md-5">
                        <table class="table table-sm mb-0">
                            <tr><td>Concurso</td><td class="fw-bold">#${u.concurso}</td></tr>
                            <tr><td>Colunas repetidas</td><td class="fw-bold">${u.cols_duplicadas}</td></tr>
                            <tr><td>Linhas repetidas</td><td class="fw-bold">${u.lins_duplicadas}</td></tr>
                            <tr><td>Dezenas isoladas</td><td class="fw-bold">${u.isoladas}</td></tr>
                            <tr><td>Estrutura</td><td class="fw-bold text-success">${u.nome_estrutura}</td></tr>
                            <tr><td>Assinatura</td><td class="font-monospace">${u.assinatura}</td></tr>
                            <tr><td>Freq. histórica</td><td>${u.freq_historica_nome} concursos (${pctFmt(u.pct_historica_nome)})</td></tr>
                        </table>
                    </div>
                    <div class="col-md-7 text-center">
                        <p class="fw-bold mb-2">${u.dezenas_fmt.join(' • ')}</p>
                        ${renderMiniVolante(u.dezenas, u)}
                    </div>
                </div>
            `;
        }
    }

    function renderGeometria() {
        if (!_dataGeo) return;
        const g = _dataGeo.geometria_avancada || {};
        const sug = _dataGeo.sugestoes_estruturais || {};

        const heat = document.getElementById('geoHeatmap');
        if (heat && _dataGeo.heatmap) {
            let html = '<div class="mini-volante-grid geo-heat">';
            _dataGeo.heatmap.forEach(row => {
                row.forEach(cell => {
                    const intens = Math.min(100, cell.porcentagem * 8);
                    html += `<div class="mv-cell" style="background:rgba(10,107,26,${0.08 + intens / 120})" title="Freq: ${cell.frequencia}">
                        <span class="mv-pct">${pctFmt(cell.porcentagem)}</span>
                    </div>`;
                });
            });
            html += '</div>';
            heat.innerHTML = html;
        }

        const fill = (id, rows, cols) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.innerHTML = rows.map(r => {
                const tds = cols.map(c => {
                    const v = r[c];
                    const txt = c === 'porcentagem' ? pctFmt(v) : (v || 0).toLocaleString();
                    return `<td class="text-end">${txt}</td>`;
                }).join('');
                const label = r.nome || r.label || r.assinatura || r.estrutura || '—';
                return `<tr><td>${label}</td>${tds}</tr>`;
            }).join('');
        };

        fill('tblGeoDominantes', g.estruturas_dominantes || [], ['frequencia', 'porcentagem']);
        fill('tblGeoRaras', g.estruturas_raras || [], ['frequencia', 'porcentagem']);
        fill('tblGeoRegioes', g.regioes_frequentes || [], ['frequencia', 'porcentagem']);

        const ass = document.getElementById('tblGeoAssinaturas');
        if (ass) {
            ass.innerHTML = (_dataGeo.assinaturas_top || []).map(a => `
                <tr>
                    <td class="font-monospace">${a.assinatura}
                        <button type="button" class="btn btn-link btn-sm p-0 ms-1" ${exemploAttr(a.exemplo)}><i class="fas fa-eye"></i></button>
                    </td>
                    <td class="text-end">${a.frequencia}</td>
                    <td class="text-end">${pctFmt(a.porcentagem)}</td>
                </tr>
            `).join('');
            bindExemploButtons(ass.closest('table') || ass);
        }

        const sugEl = document.getElementById('geoSugestoes');
        if (sugEl && sug.itens) {
            sugEl.innerHTML = `
                <ul class="mb-2">${sug.itens.map(i => `<li>${i}</li>`).join('')}</ul>
                <p class="mb-0 fw-bold text-success"><i class="fas fa-compass me-1"></i>Estrutura sugerida: ${sug.estrutura_sugerida}</p>
                <p class="small text-muted mb-0">Assinatura: ${sug.assinatura_sugerida || '—'}</p>
            `;
        }
    }

    async function ensureGeoData() {
        if (_dataGeo) return _dataGeo;
        const resp = await fetch('/analise/api/geometria-estrutural');
        const data = await resp.json();
        if (data.status !== 'success') throw new Error(data.message || 'Erro geometria');
        _dataGeo = data;
        return data;
    }

    global.AnaliseEstrutura = {
        load: ensureGeoData,
        renderLinCol,
        renderGeometria,
        get data() { return _dataGeo; },
    };
})(window);
