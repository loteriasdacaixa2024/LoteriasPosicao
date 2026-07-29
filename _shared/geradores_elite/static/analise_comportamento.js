(function () {
    const UI = window.__COMPORTAMENTO_UI__ || {};
    const API_BASE = window.__ANALISE_COMP_API__ || '/analise/api/comportamento';
    const INDICADORES = UI.indicadores || ['PA', 'IM', 'PR', 'RT', 'MO', 'SQ', 'M3', 'FB', 'MS'];
    const IND_LABELS = UI.indicador_labels || {};
    const MESES_ABREV = { 1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez' };
    const MESES_NOME_NUM = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
    };
    const BASE_LABELS = { geral: 'Geral', vencedores: 'Concursos com Vencedores', acumulados: 'Concursos Acumulados' };

    let janelaAtual = UI.janela_default ?? ((UI.janelas && UI.janelas.length) ? UI.janelas[0] : 10);
    let baseAtual = 'geral';
    let metaBases = UI.meta_bases || null;
    let compData = null;
    let filtrosAtivos = {};

    function fmtModaInline(moda, pct) {
        if (moda == null) return '—';
        if (pct != null && pct !== '') return `${moda}<span class="moda-inline-pct">${pct}%</span>`;
        return String(moda);
    }

    function nomeMes(row) {
        const num = row.mes_num != null ? row.mes_num : row.MS;
        return row.mes_nome || MESES_NOME_NUM[num] || '';
    }

    function badgeMes(row) {
        const nome = nomeMes(row);
        const num = row.mes_num != null ? row.mes_num : row.MS;
        const abrev = row.mes_abrev || MESES_ABREV[num] || '';
        if (!abrev) return '';
        const clsMes = nome ? `mes-nome-${nome}` : '';
        return `<span class="mes-abrev-badge ${clsMes}">${abrev}</span>`;
    }

    function padDez(n) {
        return String(n).padStart(2, '0');
    }

    function htmlDezenas(row) {
        const dz = row.dezenas || [];
        if (!dz.length) return '<span class="text-muted">—</span>';
        const balls = dz.map(n => `<span class="dez-ball">${padDez(n)}</span>`).join('');
        return `<div class="comp-dezenas">${balls}</div>`;
    }

    function htmlConcursoCol(row) {
        return window.ComportamentoColConcurso?.html(row, {
            showMes: UI.show_extra_mes !== false,
            badgeMes: badgeMes,
        }) || `#${row.concurso}`;
    }

    function setEvidenciasVisivel(visivel) {
        const corpo = document.getElementById('evidCorpo');
        const btn = document.getElementById('btnToggleEvidencias');
        const lbl = document.getElementById('lblToggleEvidencias');
        if (!corpo || !btn) return;
        corpo.classList.toggle('d-none', !visivel);
        btn.setAttribute('aria-expanded', visivel ? 'true' : 'false');
        if (lbl) lbl.textContent = visivel ? 'Ocultar' : 'Mostrar';
    }

    function initToggleEvidencias() {
        setEvidenciasVisivel(false);
        document.getElementById('btnToggleEvidencias')?.addEventListener('click', () => {
            const corpo = document.getElementById('evidCorpo');
            setEvidenciasVisivel(corpo?.classList.contains('d-none'));
        });
    }

    function buildQuery() {
        const p = new URLSearchParams({ janela: String(janelaAtual), base: baseAtual });
        Object.entries(filtrosAtivos).forEach(([k, v]) => p.set(k, String(v)));
        return p.toString();
    }

    function setLoader(on) {
        document.getElementById('evidLoader')?.classList.toggle('d-none', !on);
    }

    function renderEvidencias(ev) {
        const el = document.getElementById('evidCorpo');
        if (!el || !ev) return;
        const inds = ev.indicadores || [];
        const chunks = [];
        for (let i = 0; i < inds.length; i += 4) {
            const slice = inds.slice(i, i + 4);
            const html = slice.map(it => {
                const dist = Object.entries(it.distribuicao || {})
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 4)
                    .map(([v, n]) => `${v}(${n})`)
                    .join(' · ');
                return `<div class="col-md-6 col-lg-3">
                    <div class="evid-box">
                        <h6>${it.label} (${it.codigo})</h6>
                        <div class="evid-linha"><span>Moda</span><span class="evid-pct">${fmtModaInline(it.moda, it.moda_pct)}</span></div>
                        <div class="evid-linha"><span>Média</span><span class="evid-pct">${it.media}</span></div>
                        <div class="evid-linha"><span>Último</span><span class="evid-pct">${it.ultimo ?? '—'}</span></div>
                        <div class="small text-muted mt-1">${dist || '—'}</div>
                    </div>
                </div>`;
            }).join('');
            chunks.push(`<div class="row g-2 mb-2">${html}</div>`);
        }
        const baseN = ev.total_concursos_base ?? ev.total_concursos ?? 0;
        const geralN = ev.total_concursos_geral ?? baseN;
        el.innerHTML = chunks.join('') +
            `<p class="small text-muted mb-0 mt-2">${ev.janela_label || ''} · ` +
            `${ev.total_janela || 0} na janela · ${baseN} na base · ${geralN} no banco geral` +
            (Object.keys(filtrosAtivos).length ? ` · ${ev.linhas_filtradas_count || 0} após filtros` : '') +
            `</p>`;
    }

    function renderTabela(linhas) {
        const tb = document.getElementById('tbodyComportamento');
        const cnt = document.getElementById('histContador');
        if (!tb) return;
        const rows = linhas || [];
        if (cnt) cnt.textContent = `${rows.length} linha(s)`;
        tb.innerHTML = rows.map(row => {
            const cells = INDICADORES.map(c => {
                const val = row[c] != null ? row[c] : '—';
                const hl = filtrosAtivos[c] === row[c] ? ' fw-bold text-primary' : '';
                return `<td class="comp-ind${hl}">${val}</td>`;
            }).join('');
            return `<tr>
                <td class="comp-col-concurso">${htmlConcursoCol(row)}</td>
                <td class="text-muted small">${row.data || '—'}</td>
                <td>${htmlDezenas(row)}</td>
                ${cells}
            </tr>`;
        }).join('') || '<tr><td colspan="99" class="text-muted small p-3">Sem dados na base/janela.</td></tr>';
    }

    function atualizarFiltrosBar() {
        const bar = document.getElementById('filtrosAtivosBar');
        const keys = Object.keys(filtrosAtivos);
        document.querySelectorAll('.comp-tabela th[data-ind]').forEach(th => {
            const ind = th.dataset.ind;
            th.classList.toggle('filtro-ativo', filtrosAtivos[ind] != null);
            const old = th.querySelector('.filtro-badge');
            if (old) old.remove();
            if (filtrosAtivos[ind] != null) {
                const b = document.createElement('span');
                b.className = 'filtro-badge';
                b.textContent = filtrosAtivos[ind];
                th.appendChild(b);
            }
        });
        if (!bar) return;
        if (!keys.length) {
            bar.innerHTML = '<span class="text-muted">Clique no cabeçalho de uma coluna para filtrar. ' +
                '<button type="button" class="btn btn-link btn-sm p-0" id="btnLimparFiltros">Limpar</button></span>';
            document.getElementById('btnLimparFiltros')?.addEventListener('click', () => {
                filtrosAtivos = {};
                carregarAnalise();
            });
            return;
        }
        bar.innerHTML = keys.map(k => `<span class="badge bg-primary me-1">${k}=${filtrosAtivos[k]}</span>`).join('') +
            ' <button type="button" class="btn btn-link btn-sm p-0" id="btnLimparFiltros">Limpar</button>';
        document.getElementById('btnLimparFiltros')?.addEventListener('click', () => {
            filtrosAtivos = {};
            carregarAnalise();
        });
    }

    function mostrarAviso(msg) {
        const el = document.getElementById('avisoBase');
        if (!el) return;
        if (msg) {
            el.textContent = msg;
            el.classList.remove('d-none');
        } else {
            el.classList.add('d-none');
        }
    }

    async function carregarAnalise() {
        setLoader(true);
        const lbl = document.getElementById('lblJanelaInfo');
        const lblBase = document.getElementById('lblBaseAtiva');
        if (lblBase) lblBase.textContent = BASE_LABELS[baseAtual] || baseAtual;
        try {
            const r = await fetch(`${API_BASE}?${buildQuery()}`);
            const data = await r.json();
            if (!data.sucesso) {
                document.getElementById('evidCorpo').innerHTML =
                    `<p class="text-danger small mb-0">${data.erro || 'Erro ao carregar.'}</p>`;
                renderTabela([]);
                mostrarAviso(data.aviso_base || null);
                return;
            }
            compData = data;
            if (data.meta_bases) {
                metaBases = data.meta_bases;
                window.ComportamentoBasesResumo?.render(metaBases, baseAtual);
            }
            renderEvidencias(data.evidencias);
            renderTabela((data.analise && data.analise.linhas) || []);
            mostrarAviso(data.aviso_base || data.evidencias?.aviso_base || null);
            if (lbl) {
                lbl.textContent = data.evidencias?.janela_label || `Janela ${janelaAtual}`;
            }
            atualizarFiltrosBar();
        } catch (e) {
            document.getElementById('evidCorpo').innerHTML =
                `<p class="text-danger small mb-0">${e.message}</p>`;
        } finally {
            setLoader(false);
        }
    }

    function renderInsights(payload) {
        const el = document.getElementById('insightsCorpo');
        const tb = document.getElementById('tbodyModasComparativo');
        if (!payload || !payload.sucesso) {
            if (el) el.innerHTML = '<p class="text-danger small">Falha ao carregar comparativo.</p>';
            return;
        }
        const ins = payload.insights || {};
        const conclusoes = ins.conclusoes || [];
        if (el) {
            el.innerHTML = conclusoes.length
                ? conclusoes.map(c => `<div class="insight-item">${c}</div>`).join('')
                : '<p class="text-muted small mb-0">Sem conclusões.</p>';
        }
        const modas = ins.modas_por_base || {};
        if (tb) {
            tb.innerHTML = INDICADORES.map(cod => {
                const g = modas.geral?.[cod] ?? '—';
                const v = modas.vencedores?.[cod] ?? '—';
                const a = modas.acumulados?.[cod] ?? '—';
                const diff = (g !== v || g !== a) ? 'table-warning' : '';
                return `<tr class="${diff}"><th>${cod}</th><td>${g}</td><td>${v}</td><td>${a}</td></tr>`;
            }).join('');
        }
    }

    async function carregarComparativo() {
        try {
            const r = await fetch(`${API_BASE}/comparativo?janela=${janelaAtual}`);
            const data = await r.json();
            renderInsights(data);
        } catch (e) {
            document.getElementById('insightsCorpo').innerHTML =
                `<p class="text-danger small">${e.message}</p>`;
        }
    }

    function rankClass(pos) {
        if (pos === 1) return 'top1';
        if (pos === 2) return 'top2';
        if (pos === 3) return 'top3';
        return '';
    }

    function renderCelulaMatriz(row) {
        if (!row) return '<td class="panorama-cel-vazia">—</td>';
        const rc = rankClass(row.ranking);
        return `<td class="panorama-cel">
            <div class="panorama-cel-val ${rc}">${row.valor_label}</div>
            <div class="panorama-cel-meta">${row.ocorrencias} · ${row.percentual}%</div>
        </td>`;
    }

    function renderMatrizPanorama(inds) {
        const maxRank = 3;
        const mapRank = {};
        inds.forEach(ind => {
            mapRank[ind.codigo] = {};
            (ind.ranking || []).forEach(row => {
                mapRank[ind.codigo][row.ranking] = row;
            });
        });

        const headCols = inds.map(ind =>
            `<th class="text-center panorama-col-hdr" title="${ind.label}">
                <span class="sigla">${ind.codigo}</span>
                <span class="legenda d-block">${ind.label}</span>
            </th>`
        ).join('');

        const bodyRows = [];
        for (let r = 1; r <= maxRank; r++) {
            const linhaTop = r <= 3 ? ' linha-top' : '';
            bodyRows.push(`<tr class="${linhaTop}">
                <td class="panorama-rank-col ${rankClass(r)}">${r}º</td>
                ${inds.map(ind => renderCelulaMatriz(mapRank[ind.codigo]?.[r])).join('')}
            </tr>`);
        }

        return `<div class="table-responsive">
            <table class="table table-sm table-bordered panorama-matriz mb-0">
                <thead>
                    <tr>
                        <th class="panorama-rank-col">Rank</th>
                        ${headCols}
                    </tr>
                </thead>
                <tbody>${bodyRows.join('')}</tbody>
            </table>
        </div>`;
    }

    function renderDetalheVertical(inds) {
        const rowsHtml = inds.map(ind => {
            const ranking = ind.ranking || [];
            if (!ranking.length) {
                return `<tr class="panorama-grupo-ini">
                    <td class="panorama-ind-cell"><span class="sigla">${ind.codigo}</span>
                        <span class="legenda d-block">${ind.label}</span></td>
                    <td colspan="5" class="text-muted small">Sem dados.</td>
                </tr>`;
            }
            return ranking.map((row, i) => {
                const rc = rankClass(row.ranking);
                const primeira = i === 0;
                const indCell = primeira
                    ? `<td class="panorama-ind-cell" rowspan="${ranking.length}">
                            <span class="sigla">${ind.codigo}</span>
                            <span class="legenda d-block">${ind.label}</span>
                            <span class="panorama-total-badge">${ind.total_concursos} conc.</span>
                       </td>`
                    : '';
                return `<tr class="${primeira ? 'panorama-grupo-ini' : ''} ${row.destaque ? 'panorama-destaque' : ''}">
                    ${indCell}
                    <td class="panorama-rank ${rc}">${row.ranking}º</td>
                    <td class="panorama-valor">${row.valor_label}</td>
                    <td class="text-end">${row.ocorrencias}</td>
                    <td class="text-end fw-bold">${row.percentual}%</td>
                    <td class="panorama-bar-td">
                        <div class="panorama-bar-wrap"><div class="panorama-bar" style="width:${Math.min(row.percentual, 100)}%"></div></div>
                    </td>
                </tr>`;
            }).join('');
        }).join('');

        return `<div class="table-responsive">
            <table class="table table-sm panorama-tabela mb-0">
                <thead class="table-light">
                    <tr>
                        <th style="min-width:9rem;">Indicador</th>
                        <th class="text-center" style="width:3.5rem;">Rank</th>
                        <th>Valor</th>
                        <th class="text-end">Ocorr.</th>
                        <th class="text-end">%</th>
                        <th style="min-width:8rem;">Distribuição</th>
                    </tr>
                </thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        </div>`;
    }

    function setPanoramaDetalheVisivel(visivel) {
        const el = document.getElementById('panoramaIndDetalhe');
        const btn = document.getElementById('btnTogglePanoramaDetalhe');
        const lbl = document.getElementById('lblTogglePanoramaDetalhe');
        if (!el) return;
        el.classList.toggle('d-none', !visivel);
        if (btn) btn.setAttribute('aria-expanded', visivel ? 'true' : 'false');
        if (lbl) lbl.textContent = visivel ? 'Ocultar detalhamento vertical' : 'Mostrar detalhamento vertical';
    }

    function renderPanoramaIndicadores(data) {
        const corpo = document.getElementById('panoramaIndCorpo');
        const detalhe = document.getElementById('panoramaIndDetalhe');
        const concl = document.getElementById('panoramaConclusoes');
        const lblBase = document.getElementById('lblPanoramaBase');
        const lblTotal = document.getElementById('lblPanoramaTotal');
        if (!corpo) return;

        if (!data?.sucesso) {
            corpo.innerHTML = `<p class="text-danger small mb-0">${data?.erro || 'Erro ao carregar panorama.'}</p>`;
            if (detalhe) detalhe.innerHTML = '';
            return;
        }

        const pan = data.panorama || {};
        if (lblBase) lblBase.textContent = data.base_label || BASE_LABELS[baseAtual] || baseAtual;
        if (lblTotal) lblTotal.textContent = `${pan.total_concursos || 0} concursos`;

        const inds = pan.indicadores || [];
        if (!inds.length) {
            corpo.innerHTML = '<p class="text-muted small mb-0">Sem dados para panorama.</p>';
            if (detalhe) detalhe.innerHTML = '';
            return;
        }

        const preds = inds
            .filter(i => i.predominante)
            .map(i => `<strong>${i.codigo}</strong> ${i.predominante.valor_label} (${i.predominante.percentual}%)`)
            .join(' · ');
        let conclHtml = preds
            ? `<div class="insight-item small mb-0"><strong>1º rank:</strong> ${preds}</div>`
            : '';
        if (pan.aviso_mes) {
            conclHtml += `<div class="alert alert-warning py-2 small mb-2 mt-2">${pan.aviso_mes}</div>`;
        } else if (pan.concursos_sem_mes > 0) {
            conclHtml += `<div class="alert alert-warning py-2 small mb-2 mt-2">`
                + `${pan.concursos_sem_mes} concurso(s) sem mês no banco (excluídos do MS).</div>`;
        }
        if (concl) concl.innerHTML = conclHtml;

        const avisoMesEl = document.getElementById('panoramaAvisoMes');
        if (avisoMesEl) {
            if (pan.aviso_mes) {
                avisoMesEl.textContent = pan.aviso_mes;
                avisoMesEl.classList.remove('d-none');
            } else {
                avisoMesEl.classList.add('d-none');
            }
        }

        corpo.innerHTML = renderMatrizPanorama(inds);
        if (detalhe) detalhe.innerHTML = renderDetalheVertical(inds);
    }

    async function carregarPanoramaIndicadores() {
        const corpo = document.getElementById('panoramaIndCorpo');
        if (corpo) corpo.innerHTML = '<p class="text-muted small mb-0">Carregando panorama…</p>';
        try {
            const r = await fetch(`${API_BASE}/panorama-indicadores?base=${encodeURIComponent(baseAtual)}`);
            const data = await r.json();
            renderPanoramaIndicadores(data);
        } catch (e) {
            if (corpo) corpo.innerHTML = `<p class="text-danger small">${e.message}</p>`;
        }
    }

    document.querySelectorAll('.janela-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.janela-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            janelaAtual = parseInt(btn.dataset.janela, 10);
            carregarAnalise();
            carregarComparativo();
        });
    });

    document.querySelectorAll('.base-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.base-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            baseAtual = btn.dataset.base || 'geral';
            window.ComportamentoBasesResumo?.render(metaBases, baseAtual);
            carregarAnalise();
            carregarPanoramaIndicadores();
        });
    });

    document.querySelectorAll('.comp-tabela th[data-ind]').forEach(th => {
        th.addEventListener('click', () => {
            const ind = th.dataset.ind;
            if (!compData?.analise?.linhas) return;
            const vals = [...new Set(compData.analise.linhas.map(r => r[ind]).filter(v => v != null))].sort((a, b) => a - b);
            if (!vals.length) return;
            const atual = filtrosAtivos[ind];
            const idx = vals.indexOf(atual);
            if (idx >= 0 && idx < vals.length - 1) {
                filtrosAtivos[ind] = vals[idx + 1];
            } else if (atual != null) {
                delete filtrosAtivos[ind];
            } else {
                filtrosAtivos[ind] = vals[0];
            }
            carregarAnalise();
        });
    });

    document.getElementById('btnAtualizarComparativo')?.addEventListener('click', carregarComparativo);
    document.getElementById('btnAtualizarPanoramaInd')?.addEventListener('click', carregarPanoramaIndicadores);
    document.getElementById('btnTogglePanoramaDetalhe')?.addEventListener('click', () => {
        const el = document.getElementById('panoramaIndDetalhe');
        setPanoramaDetalheVisivel(el?.classList.contains('d-none'));
    });

    initToggleEvidencias();
    carregarAnalise();
    carregarComparativo();
    carregarPanoramaIndicadores();
})();
