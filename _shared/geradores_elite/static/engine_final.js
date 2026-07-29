(function () {
    'use strict';

    const root = document.getElementById('ge-engine-final');
    if (!root) return;

    const modality = root.dataset.modality;
    const dezenaClass = root.dataset.dezenaClass || 'dez-ball';
    const extraType = root.dataset.extraType || '';
    const extraClass = root.dataset.extraClass || '';
    const trevoClass = root.dataset.trevoClass || 'trevo-ball';

    const pickMin = parseInt(root.dataset.pickMin, 10) || 6;
    const pickMax = parseInt(root.dataset.pickMax, 10) || 15;
    const pickDefault = parseInt(root.dataset.pickDefault, 10) || pickMin;
    const otimizadorOn = root.dataset.otimizador === '1';
    const construtorOn = root.dataset.construtor === '1';

    let ultimoPayload = null;
    let otimizadorPayload = null;
    let conferenciaAtual = null;
    let backtestAtual = null;
    let concursosLista = [];
    let sessoesConstrutor = [];

    function fmtDezena(n) {
        if (pickMin === 0 && pickMax >= 99) return String(n).padStart(2, '0');
        if (modality === 'supersete') return String(n);
        return String(n).padStart(2, '0');
    }

    function mesClassName(nome) {
        return nome ? `mes-nome-${nome}` : '';
    }

    function extrasAposta(ap, data) {
        if (ap.extras && ap.extras.tipo) return ap.extras;
        if (data.extra && data.extra.tipo) return data.extra;
        return ap.extras || {};
    }

    function acBadgeClass(ac) {
        if (ac >= 7) return 'ge-ac-7';
        if (ac >= 6) return 'ge-ac-6';
        if (ac >= 5) return 'ge-ac-5';
        return '';
    }

    function renderExtra(ex, conf) {
        if (!ex || !ex.tipo) return '';
        const conferindo = conf && conf.sorteadasSet && conf.sorteadasSet.size > 0;

        if (ex.tipo === 'mes') {
            const abrev = ex.label || ex.mes_abrev || '';
            const num = ex.num != null ? parseInt(ex.num, 10) : 0;
            const nomeCor = ex.mes_nome || '';
            let hitCls = '';
            if (conferindo && conf.acertoExtra != null) {
                hitCls = conf.acertoExtra ? 'ge-mes-hit' : 'ge-mes-miss';
            }
            const cls = `${extraClass} ge-mes-slot m-0 ${mesClassName(nomeCor)} ${hitCls}`.trim();
            const txt = abrev || (num ? String(num) : '');
            if (!txt) return '';
            return `<span class="${cls}" title="${nomeCor || txt}">${txt}</span>`;
        }
        if (ex.tipo === 'time' && ex.label) {
            let hitCls = '';
            if (conferindo && conf.acertoExtra != null) {
                hitCls = conf.acertoExtra ? 'ge-mes-hit' : 'ge-mes-miss';
            }
            return `<span class="${extraClass} m-0 ${hitCls}"><span class="tb-icon">⚽</span>${ex.label}</span>`;
        }
        if (ex.tipo === 'trevo' && ex.numeros) {
            const sortTr = conf && conf.sortTrevos ? new Set(conf.sortTrevos) : null;
            const tr = ex.numeros
                .map((t) => {
                    let cls = trevoClass;
                    if (sortTr && sortTr.size) {
                        cls += sortTr.has(parseInt(t, 10)) ? ' ge-dez-hit' : ' ge-dez-miss';
                    }
                    return `<span class="${cls}">${t}</span>`;
                })
                .join('');
            return `<div class="draw-trevos">${tr}</div>`;
        }
        return '';
    }

    function renderDezenas(nums, sorteadasSet, movedSet) {
        const conferindo = sorteadasSet && sorteadasSet.size > 0;
        const moved = movedSet || null;
        return nums
            .map((n) => {
                let cls = dezenaClass;
                const nn = parseInt(n, 10);
                if (conferindo) {
                    cls += sorteadasSet.has(nn) ? ' ge-dez-hit' : ' ge-dez-miss';
                }
                if (moved && moved.has(nn)) {
                    cls += ' ge-dez-moved';
                }
                return `<span class="${cls}">${fmtDezena(n)}</span>`;
            })
            .join('');
    }

    function renderApostaRow(ap, data, confRow, movedSet) {
        const nums = ap.dezenas || [];
        const ex = extrasAposta(ap, data);
        const sorteadasSet = confRow ? confRow.sorteadasSet : null;
        const dezHtml = renderDezenas(nums, sorteadasSet, movedSet);
        const extraHtml = renderExtra(ex, confRow ? {
            sorteadasSet,
            acertoExtra: confRow.acerto_extra,
            sortTrevos: confRow.sort_trevos,
        } : null);

        let acHtml = '';
        if (confRow && confRow.acertos != null) {
            acHtml = `<span class="ge-ac-badge ${acBadgeClass(confRow.acertos)}">${confRow.acertos} ac.</span>`;
            if (confRow.acerto_extra === true && extraType) {
                const lbl = extraType === 'mes' ? '+ mês' : extraType === 'time' ? '+ time' : '+ extra';
                acHtml += `<span class="ge-ac-badge ge-ac-5 ms-1">${lbl}</span>`;
            }
        }

        return `<div class="ge-row-aposta">
            <div class="draw-balls m-0">${dezHtml}</div>
            ${extraHtml}
            ${acHtml}
        </div>`;
    }

    function statPill(val, lbl, color) {
        const style = color ? ` style="border-color:${color};"` : '';
        const valStyle = color ? ` style="color:${color};"` : '';
        return `<span class="ge-stat-pill"${style}>
            <span class="ge-sp-val"${valStyle}>${val}</span>
            <span class="ge-sp-lbl">${lbl}</span>
        </span>`;
    }

    function renderConfBar() {
        if (!backtestAtual && !conferenciaAtual) return '';

        let btHtml = '';
        if (backtestAtual && backtestAtual.sucesso) {
            const bt = backtestAtual;
            const extraLbl = bt.extra_label || '';
            const extraVal = bt.extras_acertados != null ? bt.extras_acertados : '—';
            btHtml = `
                <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                    <span class="text-muted small">
                        <i class="fas fa-history me-1"></i>Backtest
                        <strong>${bt.concursos_analisados}</strong> conc.
                        (#${bt.concurso_de}…#${bt.concurso_ate})
                    </span>
                    ${statPill(bt.media_max_acertos, 'média máx.', '')}
                    ${statPill(bt.dist_7 || 0, '7 ac.', '#dc3545')}
                    ${statPill(bt.dist_6 || 0, '6 ac.', '#b28704')}
                    ${statPill(bt.dist_5 || 0, '5 ac.', '#198754')}
                    ${statPill(bt.dist_4 || 0, '4 ac.', '#6c757d')}
                    ${extraLbl ? statPill(extraVal, extraLbl, 'var(--accent-mes, #6f42c1)') : ''}
                </div>`;

            const dest = (bt.destaques || []).slice(0, 6);
            if (dest.length) {
                const cur = conferenciaAtual ? conferenciaAtual.concurso : null;
                btHtml += `<div class="d-flex flex-wrap gap-1 justify-content-center mb-2">
                    ${dest.map((d) => {
                        const active = cur === d.concurso ? ' active' : '';
                        const mesTag = d.acerto_extra ? ' · mês' : '';
                        return `<span class="ge-destaque-item${active}" data-concurso="${d.concurso}" title="Ver concurso #${d.concurso}">
                            #${d.concurso} · ${d.max_acertos} ac.${mesTag}
                        </span>`;
                    }).join('')}
                </div>`;
            }
        }

        let selHtml = '';
        if (concursosLista.length) {
            const opts = concursosLista.map((c) => {
                const sel = conferenciaAtual && conferenciaAtual.concurso === c.concurso ? ' selected' : '';
                return `<option value="${c.concurso}"${sel}>#${c.concurso} — ${c.data || ''}</option>`;
            }).join('');
            selHtml = `
                <div class="d-flex flex-wrap align-items-center gap-2 justify-content-center">
                    <label class="small text-muted mb-0"><i class="fas fa-check-double me-1"></i>Conferir</label>
                    <select class="form-select form-select-sm" id="geSelConcurso" style="max-width:11rem;">${opts}</select>
                </div>`;
        }

        return `<div class="ge-conf-bar">${selHtml}${btHtml}</div>`;
    }

    function renderSorteioHeader() {
        if (!conferenciaAtual || !conferenciaAtual.sucesso) return '';
        const c = conferenciaAtual;
        const sorteadasSet = new Set(c.sorteadas || []);
        const balls = (c.sorteadas || []).map((n) =>
            `<span class="${dezenaClass} ge-dez-hit">${fmtDezena(n)}</span>`
        ).join('');

        let extraInfo = '';
        if (c.mes_nome) {
            extraInfo = ` · Mês: <strong>${c.mes_abrev || c.mes_nome}</strong>`;
        } else if (c.mes_num) {
            extraInfo = ` · Mês: <strong>${c.mes_num}</strong>`;
        }

        const resumo = `<span class="text-muted small ms-2">
            Máx <strong>${c.max_acertos}</strong> ac.
            · Média <strong>${c.media_acertos}</strong>
        </span>`;

        return `<div class="text-center small mb-2 pb-2 border-bottom">
            <span class="text-muted">Sorteio #${c.concurso}</span>${extraInfo}${resumo}
            <div class="ge-sorteadas-row">${balls}</div>
        </div>`;
    }

    function renderAvisosBanner(data) {
        if (!data.conjunto_base || !data.conjunto_base.dezenas) return '';
        const dz = data.conjunto_base.dezenas;
        const chips = dz.map((n) => `<span class="ge-conjunto-chip">${fmtDezena(n)}</span>`).join('');
        return `<div class="text-center small mb-2 w-100">
            <span class="text-muted">Conjunto-base</span>
            <div class="ge-conjunto-chips justify-content-center">${chips}</div>
        </div>`;
    }

    function renderApostas(data) {
        const box = document.getElementById('geResultados');
        if (!box) return;
        const apostas = data.apostas || [];
        if (!apostas.length) {
            box.innerHTML = '<p class="text-muted mb-0">Nenhuma aposta gerada.</p>';
            return;
        }

        const confMap = {};
        if (conferenciaAtual && conferenciaAtual.apostas) {
            const sorteadasSet = new Set(conferenciaAtual.sorteadas || []);
            conferenciaAtual.apostas.forEach((a, idx) => {
                confMap[idx] = {
                    sorteadasSet,
                    acertos: a.acertos,
                    acerto_extra: a.acerto_extra,
                    sort_trevos: conferenciaAtual.trevos || null,
                };
            });
        }

        const rows = apostas
            .map((ap, idx) => renderApostaRow(ap, data, confMap[idx] || null))
            .join('');

        box.innerHTML = `${renderAvisosBanner(data)}${renderConfBar()}${renderSorteioHeader()}${rows}`;

        const sel = document.getElementById('geSelConcurso');
        if (sel) {
            sel.addEventListener('change', () => {
                conferirConcurso(parseInt(sel.value, 10));
            });
        }
        box.querySelectorAll('.ge-destaque-item').forEach((el) => {
            el.addEventListener('click', () => {
                const n = parseInt(el.dataset.concurso, 10);
                if (sel) sel.value = String(n);
                conferirConcurso(n);
            });
        });
    }

    async function carregarConcursos() {
        try {
            const r = await fetch('/geradores-elite/api/inteligente/concursos?limit=80');
            const d = await r.json();
            concursosLista = (d.sucesso && d.concursos) ? d.concursos : [];
        } catch (e) {
            concursosLista = [];
        }
    }

    async function conferirConcurso(concurso) {
        if (!ultimoPayload || !ultimoPayload.apostas || !ultimoPayload.apostas.length) return;
        if (!concurso) return;
        try {
            const r = await fetch('/geradores-elite/api/engine-final/conferir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    apostas: ultimoPayload.apostas,
                    concurso,
                }),
            });
            conferenciaAtual = await r.json();
        } catch (e) {
            conferenciaAtual = { sucesso: false, erro: e.message };
        }
        renderApostas(ultimoPayload);
    }

    async function rodarBacktest() {
        if (!ultimoPayload || !ultimoPayload.apostas || !ultimoPayload.apostas.length) return;
        try {
            const r = await fetch('/geradores-elite/api/engine-final/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    apostas: ultimoPayload.apostas,
                    limite: 30,
                }),
            });
            backtestAtual = await r.json();
        } catch (e) {
            backtestAtual = { sucesso: false, erro: e.message };
        }
    }

    async function atualizarConferencia() {
        await carregarConcursos();
        await rodarBacktest();
        const primeiro = concursosLista.length ? concursosLista[0].concurso : null;
        if (primeiro) {
            await conferirConcurso(primeiro);
        } else {
            renderApostas(ultimoPayload);
        }
    }

    async function gerar() {
        const modo = document.getElementById('geModo').value;
        const body = {
            quantidade: parseInt(document.getElementById('geQtdApostas').value, 10) || 5,
            dezenas: parseInt(document.getElementById('geQtdDezenas').value, 10) || pickDefault,
            modo,
            extra_criterio: 'atrasado',
        };
        if (modo === 'conjunto_base') {
            const selSess = document.getElementById('geSessaoConjunto');
            const sid = selSess ? parseInt(selSess.value, 10) : 0;
            if (!sid) {
                alert('Selecione uma sessão com conjunto-base salvo no Construtor.');
                return;
            }
            body.sessao_id = sid;
        }
        const mesCrit = document.getElementById('geMesCriterio');
        if (mesCrit) {
            if (mesCrit.value === 'manual') {
                body.mes_manual = parseInt(document.getElementById('geMesManual').value, 10);
            } else {
                body.extra_criterio = mesCrit.value;
            }
        }
        const timeCrit = document.getElementById('geExtraCriterio');
        if (timeCrit) body.extra_criterio = timeCrit.value;

        const box = document.getElementById('geResultados');
        box.innerHTML =
            '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div></div>';

        conferenciaAtual = null;
        backtestAtual = null;
        otimizadorPayload = null;

        const r = await fetch('/geradores-elite/api/engine-final/gerar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await r.json();
        if (!data.sucesso) {
            box.innerHTML = `<div class="alert alert-danger py-2 mb-0">${data.erro || 'Erro ao gerar'}</div>`;
            return;
        }
        ultimoPayload = data;
        await atualizarConferencia();
        if (otimizadorOn) {
            await rodarOtimizador();
        }
    }

    function dezenasMudaram(orig, opt) {
        const moved = new Set();
        const oSet = new Set((orig || []).map((n) => parseInt(n, 10)));
        (opt || []).forEach((n) => {
            const nn = parseInt(n, 10);
            if (!oSet.has(nn)) moved.add(nn);
        });
        return moved;
    }

    function renderOptMetrics(antes, depois, meta) {
        if (!antes || !depois) return '';
        const delta = meta && meta.delta_media_max != null ? meta.delta_media_max : 0;
        const deltaCls = delta > 0 ? 'text-success' : delta < 0 ? 'text-danger' : 'text-muted';
        const deltaTxt = delta > 0 ? `+${delta}` : String(delta);
        return `<div class="ge-opt-metrics">
            <span class="text-muted small me-2">Backtest ${antes.concursos_analisados || 30} conc.</span>
            ${statPill(antes.media_max_acertos, 'média máx. (antes)', '#6c757d')}
            ${statPill(depois.media_max_acertos, 'média máx. (depois)', '#198754')}
            <span class="ge-stat-pill"><span class="ge-sp-val ${deltaCls}">${deltaTxt}</span><span class="ge-sp-lbl">Δ média</span></span>
            ${statPill(depois.dist_5 || 0, '5 ac.', '#198754')}
            ${statPill(depois.dist_6 || 0, '6 ac.', '#b28704')}
            ${statPill(depois.dist_7 || 0, '7 ac.', '#dc3545')}
            ${meta ? `<span class="text-muted small align-self-center">${meta.swaps_aceitos || 0} redistribuições</span>` : ''}
        </div>`;
    }

    function renderColunaApostas(apostas, data, titulo, colCls, movedPorLinha) {
        const rows = (apostas || [])
            .map((ap, idx) => {
                const moved = movedPorLinha ? movedPorLinha[idx] : null;
                return renderApostaRow(ap, data, null, moved);
            })
            .join('');
        return `<div class="ge-compare-col ${colCls || ''}">
            <div class="ge-compare-title">${titulo}</div>
            ${rows}
        </div>`;
    }

    function renderOtimizador() {
        const box = document.getElementById('geOtimizadorResultados');
        const status = document.getElementById('geOptStatus');
        if (!box) return;

        if (!ultimoPayload || !ultimoPayload.apostas || !ultimoPayload.apostas.length) {
            box.innerHTML = `<p class="text-muted mb-0 text-center py-4">
                Gere apostas na aba <strong>Gerador Elite</strong> para ativar o otimizador.
            </p>`;
            if (status) status.textContent = '';
            return;
        }

        if (!otimizadorPayload) {
            box.innerHTML = `<div class="text-center py-4">
                <div class="spinner-border spinner-border-sm"></div>
                <p class="text-muted small mt-2 mb-0">Otimizando concentração…</p>
            </div>`;
            return;
        }

        if (!otimizadorPayload.sucesso) {
            box.innerHTML = `<div class="alert alert-warning py-2 mb-0">${otimizadorPayload.erro || 'Falha na otimização'}</div>`;
            if (status) status.textContent = '';
            return;
        }

        const orig = otimizadorPayload.apostas_originais || ultimoPayload.apostas;
        const opt = otimizadorPayload.apostas || [];
        const dataOrig = { ...ultimoPayload, apostas: orig };
        const dataOpt = { ...ultimoPayload, apostas: opt };

        const movedPorLinha = opt.map((ap, idx) =>
            dezenasMudaram((orig[idx] || {}).dezenas, ap.dezenas)
        );

        const btAntes = otimizadorPayload.backtest_antes || {};
        const btDepois = otimizadorPayload.backtest_depois || {};
        const metricsHtml = renderOptMetrics(btAntes, btDepois, otimizadorPayload);

        const coberturaOk = otimizadorPayload.cobertura_preservada !== false;
        const coberturaNote = coberturaOk
            ? `<span class="text-success small"><i class="fas fa-check-circle me-1"></i>Cobertura preservada (${otimizadorPayload.cobertura_otimizada || '—'} dezenas)</span>`
            : `<span class="text-warning small">Cobertura alterada</span>`;

        const swaps = otimizadorPayload.swaps_aceitos || 0;
        let alertHtml = '';
        if (otimizadorPayload.sem_alteracao || swaps === 0) {
            alertHtml = `<div class="alert alert-info py-2 small mb-2 text-center">
                <i class="fas fa-info-circle me-1"></i>
                <strong>Original = Otimizado</strong> — nenhuma troca entre apostas melhorou a concentração
                no backtest dos últimos 30 concursos, mantendo B/M/A e paridade de cada aposta.
                Pode clicar em <strong>Reotimizar</strong> (resultado pode variar) ou gerar um novo conjunto.
            </div>`;
        }

        box.innerHTML = `${metricsHtml}
            ${alertHtml}
            <div class="text-center mb-2">${coberturaNote}</div>
            <div class="ge-compare-wrap">
                ${renderColunaApostas(orig, dataOrig, 'Original', '', null)}
                ${renderColunaApostas(opt, dataOpt, 'Otimizada', 'ge-col-opt', movedPorLinha)}
            </div>
            <p class="text-muted small text-center mt-2 mb-0">
                Dezenas com contorno azul foram redistribuídas. Meses mantidos da geração original.
            </p>`;

        if (status) {
            const m = otimizadorPayload.metricas_depois || {};
            status.textContent = `Score ${otimizadorPayload.melhoria_score >= 0 ? '+' : ''}${otimizadorPayload.melhoria_score || 0} · índice ${m.indice_concentracao || '—'}`;
        }
    }

    async function rodarOtimizador() {
        if (!otimizadorOn || !ultimoPayload || !ultimoPayload.apostas) return;
        renderOtimizador();
        try {
            const r = await fetch('/geradores-elite/api/engine-final/otimizar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    apostas: ultimoPayload.apostas,
                    modo: 'restrito',
                    iteracoes: 5000,
                    janela_historico: 30,
                }),
            });
            otimizadorPayload = await r.json();
        } catch (e) {
            otimizadorPayload = { sucesso: false, erro: e.message };
        }
        renderOtimizador();
    }

    function exportarTxt() {
        if (!ultimoPayload || !ultimoPayload.apostas || !ultimoPayload.apostas.length) {
            alert('Gere apostas antes de exportar.');
            return;
        }
        fetch('/geradores-elite/api/engine-final/export-txt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                apostas: ultimoPayload.apostas,
                extra: ultimoPayload.extra,
            }),
        })
            .then((r) => r.json())
            .then((j) => {
                if (!j.sucesso) {
                    alert(j.erro || 'Falha na exportação');
                    return;
                }
                const blob = new Blob([j.texto], { type: 'text/plain;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const stamp = new Date();
                const p = (x) => String(x).padStart(2, '0');
                a.href = url;
                a.download = `engine-final-${modality}-${stamp.getFullYear()}${p(stamp.getMonth() + 1)}${p(stamp.getDate())}.txt`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            })
            .catch(() => alert('Erro ao exportar.'));
    }

    function fillDezenasSelect() {
        const sel = document.getElementById('geQtdDezenas');
        if (!sel) return;
        sel.innerHTML = '';
        for (let k = pickMin; k <= pickMax; k++) {
            const opt = document.createElement('option');
            opt.value = String(k);
            opt.textContent = String(k);
            if (k === pickDefault) opt.selected = true;
            sel.appendChild(opt);
        }
    }

    async function atualizarHintMesComportamento() {
        const mesCrit = document.getElementById('geMesCriterio');
        const hint = document.getElementById('geMesComportamentoHint');
        const wrap = document.getElementById('geMesManualWrap');
        if (!mesCrit || !hint) return;
        if (wrap) wrap.style.display = mesCrit.value === 'manual' ? 'block' : 'none';
        if (mesCrit.value !== 'comportamento') {
            hint.classList.add('d-none');
            hint.textContent = '';
            return;
        }
        hint.classList.remove('d-none');
        hint.innerHTML = '<span class="text-muted"><i class="fas fa-spinner fa-spin me-1"></i>Carregando meses indicados…</span>';
        try {
            const r = await fetch('/geradores-elite/api/meses-indicados');
            const d = await r.json();
            if (!d.sucesso) {
                hint.innerHTML = `<span class="text-danger">${d.erro || 'Indisponível'}</span>`;
                return;
            }
            const ind = (d.meses_indicados || []).map(m => m.mes_abrev).join(' · ') || '—';
            const conc = (d.concursos_janela || []).length
                ? `#${d.concursos_janela[0]}…#${d.concursos_janela[d.concursos_janela.length - 1]}`
                : '—';
            hint.innerHTML = d.sem_indicados
                ? '<span class="text-warning">Nenhum mês indicado nos últimos 10 concursos.</span>'
                : `<span class="text-success fw-semibold">Indicados: ${ind}</span>`
                    + `<span class="text-muted"> · janela ${conc} · ciclo por aposta</span>`;
        } catch (e) {
            hint.innerHTML = `<span class="text-danger">${e.message || 'Erro'}</span>`;
        }
    }

    function atualizarUiConjunto() {
        const modoEl = document.getElementById('geModo');
        const wrap = document.getElementById('geConjuntoWrap');
        const hint = document.getElementById('geConjuntoHint');
        const sel = document.getElementById('geSessaoConjunto');
        if (!modoEl || !wrap) return;

        const ativo = modoEl.value === 'conjunto_base';
        wrap.style.display = ativo ? 'block' : 'none';
        if (!ativo || !hint || !sel) return;

        const sid = parseInt(sel.value, 10);
        const sess = sessoesConstrutor.find((s) => s.id === sid);
        if (!sess) {
            hint.innerHTML = sessoesConstrutor.length
                ? '<span class="text-warning">Selecione uma sessão.</span>'
                : '<span class="text-danger">Nenhuma sessão salva. '
                    + '<a href="/geradores-elite/construtor-construcoes/">Abrir Construtor</a></span>';
            return;
        }

        const dz = sess.conjunto_base || [];
        const chips = dz.map((n) => `<span class="ge-conjunto-chip">${fmtDezena(n)}</span>`).join('');
        hint.innerHTML = `<div class="ge-conjunto-chips">${chips}</div>`;
    }

    async function carregarSessoesConstrutor() {
        if (!construtorOn) return;
        const sel = document.getElementById('geSessaoConjunto');
        if (!sel) return;
        try {
            const r = await fetch('/geradores-elite/api/construtor-construcoes/sessoes');
            const d = await r.json();
            sessoesConstrutor = (d.sucesso && d.sessoes) ? d.sessoes : [];
            sel.innerHTML = '';
            if (!sessoesConstrutor.length) {
                sel.innerHTML = '<option value="">— Nenhuma sessão —</option>';
            } else {
                sessoesConstrutor.forEach((s, i) => {
                    const opt = document.createElement('option');
                    opt.value = String(s.id);
                    const qtd = (s.conjunto_base || []).length;
                    opt.textContent = `${s.nome || 'Sessão ' + s.id} (${qtd} dez.)`;
                    if (i === 0) opt.selected = true;
                    sel.appendChild(opt);
                });
            }
        } catch (e) {
            sel.innerHTML = '<option value="">Erro ao carregar</option>';
        }
        atualizarUiConjunto();
    }

    fillDezenasSelect();
    document.getElementById('geBtnGerar').addEventListener('click', gerar);
    document.getElementById('geBtnExportar').addEventListener('click', exportarTxt);

    if (otimizadorOn) {
        document.getElementById('geBtnReotimizar')?.addEventListener('click', rodarOtimizador);
    }

    if (construtorOn) {
        carregarSessoesConstrutor();
        document.getElementById('geModo')?.addEventListener('change', atualizarUiConjunto);
        document.getElementById('geSessaoConjunto')?.addEventListener('change', atualizarUiConjunto);
    }

    const mesCrit = document.getElementById('geMesCriterio');
    if (mesCrit) {
        mesCrit.addEventListener('change', () => {
            atualizarHintMesComportamento();
        });
    }
})();
