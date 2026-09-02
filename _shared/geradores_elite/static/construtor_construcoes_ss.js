(function () {
    'use strict';

    const root = document.getElementById('ge-construtor');
    if (!root || !(window.__CC_UI__ || {}).positional) return;

    const API = window.__CC_API__ || root.dataset.api;
    const UI = window.__CC_UI__ || {};
    const NUM_COLS = UI.num_colunas || 7;
    const MAX_POR_COL = UI.max_digitos_por_coluna || 5;
    const MAX_TOTAL = UI.max_conjunto_base || 35;
    const QTD_APOSTAS = UI.qtd_apostas_fixa || 10;
    const ACERTOS_TIERS = UI.acertos_tiers || [3, 4, 5, 6, 7];
    const ACERTOS_MAX = UI.acertos_max_possivel || 7;
    const ultimoSorteio = (window.__CC_ULTIMO__ && window.__CC_ULTIMO__.dezenas) || [];

    /** @type {Record<number, Set<number>>} */
    let poolColunas = {};
    for (let c = 1; c <= NUM_COLS; c++) poolColunas[c] = new Set();

    let sessaoAtual = null;
    let origemConjunto = 'manual';
    let editandoConstrucaoId = null;
    let modalEditar = null;
    let modalConfHist = null;

    const $ = (id) => document.getElementById(id);

    function faixaClass(n) {
        if (n <= 3) return 'faixa-baixa';
        if (n <= 6) return 'faixa-media';
        return 'faixa-alta';
    }

    function totalSelecionados() {
        return Object.values(poolColunas).reduce((s, set) => s + set.size, 0);
    }

    function poolToPayload() {
        const out = {};
        for (let c = 1; c <= NUM_COLS; c++) {
            out[c] = [...poolColunas[c]].sort((a, b) => a - b);
        }
        return out;
    }

    function poolHintText(pool) {
        const p = pool || poolToPayload();
        return Object.keys(p).sort((a, b) => a - b).map(c => {
            const arr = p[c] || p[String(c)] || [];
            return `C${c}:${arr.join('') || '—'}`;
        }).join(' · ');
    }

    function setPoolFromPayload(payload, origem, msg) {
        for (let c = 1; c <= NUM_COLS; c++) {
            const arr = payload[c] || payload[String(c)] || [];
            poolColunas[c] = new Set(arr.map(Number));
        }
        origemConjunto = origem || 'import';
        renderVolanteColunas();
        updatePoolInfo(msg);
    }

    function renderVolanteColunas() {
        const wrap = $('ccVolanteColunas');
        if (!wrap) return;
        wrap.innerHTML = '';
        for (let col = 1; col <= NUM_COLS; col++) {
            const row = document.createElement('div');
            row.className = 'cc-coluna-row';
            const lbl = document.createElement('div');
            lbl.className = 'cc-coluna-label';
            lbl.textContent = 'C' + col;
            const balls = document.createElement('div');
            balls.className = 'cc-coluna-balls';
            const colSet = poolColunas[col];
            const colCheia = colSet.size >= MAX_POR_COL;
            const ref = ultimoSorteio[col - 1];
            for (let d = 0; d <= 9; d++) {
                const btn = document.createElement('button');
                btn.type = 'button';
                const sel = colSet.has(d);
                btn.className = 'cc-ball ' + faixaClass(d);
                if (sel) btn.classList.add('cc-selecionada');
                if (!sel && colCheia) btn.classList.add('cc-bloqueado');
                if (!sel && ref === d) btn.classList.add('cc-ultimo-ref');
                btn.textContent = String(d);
                btn.addEventListener('click', () => {
                    if (colSet.has(d)) {
                        colSet.delete(d);
                    } else {
                        if (colSet.size >= MAX_POR_COL) return;
                        if (totalSelecionados() >= MAX_TOTAL) {
                            abrirColinha(true);
                            return;
                        }
                        colSet.add(d);
                    }
                    origemConjunto = 'manual';
                    renderVolanteColunas();
                    updatePoolInfo();
                });
                balls.appendChild(btn);
            }
            row.appendChild(lbl);
            row.appendChild(balls);
            wrap.appendChild(row);
        }
        const cont = $('ccContador');
        if (cont) cont.textContent = `${totalSelecionados()}/${MAX_TOTAL}`;
    }

    function updatePoolInfo(msg) {
        const info = $('ccPoolInfo');
        if (!info) return;
        if (msg) {
            info.textContent = msg;
            return;
        }
        info.textContent = poolHintText() + ` · origem: ${origemConjunto}`;
    }

    function abrirColinha(auto) {
        const pop = $('ccColinhaPop');
        if (!pop) return;
        pop.classList.add('aberto');
        if (auto) pop.classList.add('cc-colinha-auto');
    }

    function fecharColinha() {
        $('ccColinhaPop')?.classList.remove('aberto', 'cc-colinha-auto');
    }

    async function apiGet(path) {
        const r = await fetch(API + path);
        return r.json();
    }

    async function apiPost(path, body) {
        const r = await fetch(API + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        return r.json();
    }

    async function apiPut(path, body) {
        const r = await fetch(API + path, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        });
        return r.json();
    }

    function labelEstrategia(id) {
        const e = (UI.estrategias || []).find(x => x.id === id);
        return e ? e.label : id;
    }

    function htmlApostaColunas(dezenas, sorteadas) {
        const conferindo = Array.isArray(sorteadas) && sorteadas.length > 0;
        return `<div class="cc-aposta-colunas">${(dezenas || []).map((d, i) => {
            const hit = conferindo && sorteadas[i] === d;
            const miss = conferindo && sorteadas[i] !== d;
            let cls = 'cc-col-mini';
            if (hit) cls += ' cc-acerto';
            else if (miss) cls += ' cc-erro';
            return `<div class="${cls}"><small>C${i + 1}</small><span>${d}</span></div>`;
        }).join('')}</div>`;
    }

    function htmlEstrategiaBadge(c) {
        const dist = c.distribuicao || {};
        const extra = c.estrategia === 'personalizada' && (dist.baixas || dist.medias || dist.altas)
            ? ` · B:${dist.baixas || 0} M:${dist.medias || 0} A:${dist.altas || 0}`
            : '';
        return `<span class="cc-estrategia-badge cc-estrategia-${c.estrategia}">${labelEstrategia(c.estrategia)}${extra}</span>`;
    }

    function contadoresAcertos(r) {
        const base = r || {};
        const out = {};
        ACERTOS_TIERS.forEach(t => { out['c' + t] = base['concursos_' + t] ?? 0; });
        return out;
    }

    function textoAcertosResumo(r) {
        return ACERTOS_TIERS.map(t => `${t}:${contadoresAcertos(r)['c' + t]}`).join(' · ');
    }

    function htmlBadgesAcertos(r) {
        const c = contadoresAcertos(r);
        return ACERTOS_TIERS.map(t =>
            `<span class="cc-conf-badge">${t} ac.: ${c['c' + t]}</span>`
        ).join('');
    }

    function htmlResumoConferencia(conf) {
        const r = conf.resumo || {};
        const melhor = r.melhor_concurso;
        const melhorTxt = melhor ? `#${melhor.concurso} (${melhor.max_acertos} ac.)` : '—';
        const k0 = ACERTOS_TIERS[0];
        const k1 = ACERTOS_TIERS[ACERTOS_TIERS.length - 1];
        const total = ACERTOS_TIERS.reduce((s, t) => s + (r['concursos_' + t] ?? 0), 0);
        return `<div class="small">
            <div class="row g-2 mb-2">
                <div class="col-6 col-md-3"><strong>${r.concursos_total || 0}</strong><br><span class="text-muted">concursos</span></div>
                <div class="col-6 col-md-3"><strong>${r.total_pontos || 0}</strong><br><span class="text-muted">soma máx. acertos</span></div>
                <div class="col-6 col-md-3"><strong>${r.media_max_acertos ?? '—'}</strong><br><span class="text-muted">média máx./concurso</span></div>
                <div class="col-6 col-md-3"><strong>${total}</strong><br><span class="text-muted">total ${k0}–${k1} ac.</span></div>
            </div>
            <div class="d-flex flex-wrap gap-2 mb-2">${htmlBadgesAcertos(r)}</div>
            <div class="text-muted mb-2">
                Melhor concurso: ${melhorTxt}
                · Atualizado: ${conf.data_execucao ? conf.data_execucao.slice(0, 16).replace('T', ' ') : '—'}
            </div>
            <p class="text-muted mb-0" style="font-size:.72rem;">
                Super Sete — acertos posicionais por coluna (0 a ${ACERTOS_MAX}).
            </p>
        </div>`;
    }

    function atualizarBotoesSessao() {
        const temConstr = !!(sessaoAtual?.construcoes?.length);
        if ($('ccBtnGerar')) $('ccBtnGerar').disabled = !sessaoAtual?.id;
        if ($('ccBtnConferir')) $('ccBtnConferir').disabled = !sessaoAtual?.id;
        if ($('ccBtnConferirTodas')) $('ccBtnConferirTodas').disabled = !temConstr;
    }

    function renderConstrucoes(sessao) {
        const el = $('ccConstrucoes');
        if (!el) return;
        const list = sessao?.construcoes || [];
        atualizarBotoesSessao();
        if (!list.length) {
            el.innerHTML = '<p class="text-muted small mb-0">Nenhuma construção ainda.</p>';
            return;
        }
        el.innerHTML = list.map(c => {
            const dist = c.distribuicao || {};
            const diff = c.diferenca_pct != null
                ? `<span class="cc-sim-badge">${c.diferenca_pct}% diferente da anterior</span>`
                : '';
            const ch = c.conferencia_historico;
            const confBadge = ch
                ? `<span class="cc-conf-badge ms-1" title="Conferida em ${ch.data_execucao || ''}">
                    Hist: média ${ch.media_max_acertos} · ${textoAcertosResumo(ch)}
                   </span>`
                : '';
            const apostasHtml = (c.apostas || []).map(a =>
                `<div class="cc-aposta-row"><span class="cc-aposta-num">${a.linha}.</span>
                ${htmlApostaColunas(a.dezenas)}</div>`
            ).join('');
            return `<div class="cc-construcao-card cc-estrategia-${c.estrategia}" data-id="${c.id}" data-num="${c.numero}">
                <div class="d-flex flex-wrap justify-content-between align-items-start gap-1 mb-2">
                    <div><strong>Construção ${c.numero}</strong>${confBadge}
                    ${htmlEstrategiaBadge(c)}</div>
                    ${diff}
                </div>
                <div class="cc-acoes mb-2">
                    <button type="button" class="btn btn-sm btn-outline-success cc-btn-conf-hist" data-id="${c.id}" data-num="${c.numero}">
                        <i class="fas fa-history"></i> Conferir histórico
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary cc-btn-editar" data-id="${c.id}">
                        <i class="fas fa-pen"></i> Editar
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary cc-btn-export" data-id="${c.id}" data-num="${c.numero}">TXT</button>
                    <button type="button" class="btn btn-sm btn-outline-danger cc-btn-excluir" data-id="${c.id}" data-num="${c.numero}">Excluir</button>
                </div>
                <div class="small text-muted mb-1">
                    Distribuição: B:${dist.baixas || 0} M:${dist.medias || 0} A:${dist.altas || 0} · ${QTD_APOSTAS} apostas
                </div>
                ${apostasHtml}
            </div>`;
        }).join('');
    }

    async function salvarSessao() {
        for (let c = 1; c <= NUM_COLS; c++) {
            if (poolColunas[c].size === 0) {
                alert(`Selecione ao menos 1 dígito na coluna C${c}.`);
                return;
            }
        }
        const data = await apiPost('/sessao', {
            nome: ($('ccNomeSessao')?.value || '').trim(),
            conjunto_base: poolToPayload(),
            dezenas_por_aposta: 7,
            origem_conjunto: origemConjunto,
            sessao_id: sessaoAtual?.id || null,
        });
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao salvar.');
            return;
        }
        sessaoAtual = data.sessao;
        if (data.sessao.pool_colunas) setPoolFromPayload(data.sessao.pool_colunas, data.sessao.origem_conjunto);
        $('ccSessaoStatus').textContent = `Sessão #${sessaoAtual.id} salva — ${sessaoAtual.total_construcoes} construção(ões).`;
        renderConstrucoes(sessaoAtual);
    }

    async function gerarConstrucao() {
        if (!sessaoAtual?.id) return;
        const estrategia = $('ccEstrategia')?.value || 'automatica';
        const body = {
            sessao_id: sessaoAtual.id,
            estrategia,
            similaridade_min_pct: parseFloat($('ccSimMin')?.value || 80),
            janela_comportamento: parseInt($('ccJanela')?.value || 10, 10),
        };
        if (estrategia === 'personalizada') {
            body.personalizada = {
                baixas: parseInt($('ccPersB')?.value || 0, 10),
                medias: parseInt($('ccPersM')?.value || 0, 10),
                altas: parseInt($('ccPersA')?.value || 0, 10),
            };
        }
        const data = await apiPost('/gerar', body);
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao gerar.');
            return;
        }
        if (data.aviso) alert(data.aviso);
        const refreshed = await apiGet('/sessao/' + sessaoAtual.id);
        if (refreshed.sucesso) {
            sessaoAtual = refreshed.sessao;
            renderConstrucoes(sessaoAtual);
        }
    }

    async function importarAnalise(criterio) {
        const qtd = parseInt($('ccQtdImport')?.value || MAX_POR_COL, 10);
        const data = await apiGet(`/analise-sugestao?quantidade=${qtd}&criterio=${criterio}`);
        if (!data.sucesso) {
            alert(data.erro || 'Erro na importação.');
            return;
        }
        setPoolFromPayload(data.pool_colunas || data.conjunto_base, data.origem, data.aviso || 'Importado da análise por coluna.');
    }

    function importarUltimo() {
        if (!ultimoSorteio.length) {
            alert('Sem último sorteio disponível.');
            return;
        }
        const payload = {};
        for (let c = 1; c <= NUM_COLS; c++) {
            payload[c] = ultimoSorteio[c - 1] != null ? [ultimoSorteio[c - 1]] : [];
        }
        setPoolFromPayload(payload, 'ultimo_sorteio', 'Pools = dígitos do último sorteio (1 por coluna).');
    }

    function fillEstrategias() {
        const sel = $('ccEstrategia');
        if (!sel) return;
        sel.innerHTML = '';
        (UI.estrategias || []).forEach(e => {
            const opt = document.createElement('option');
            opt.value = e.id;
            opt.textContent = e.label;
            sel.appendChild(opt);
        });
        const onChange = () => {
            const v = sel.value;
            const jw = $('ccJanelaWrap');
            const pw = $('ccPersonalizadaWrap');
            if (jw) jw.style.display = v === 'conforme_comportamento' ? '' : 'none';
            if (pw) pw.style.display = v === 'personalizada' ? '' : 'none';
        };
        sel.addEventListener('change', onChange);
        onChange();
    }

    async function carregarSessoes() {
        const data = await apiGet('/sessoes');
        const sel = $('ccSelectSessao');
        if (!sel || !data.sucesso) return;
        sel.innerHTML = '<option value="">— Nova sessão —</option>';
        (data.sessoes || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `#${s.id} ${s.nome} (${s.total_construcoes} constr.)`;
            sel.appendChild(opt);
        });
    }

    async function carregarConcursos() {
        const data = await apiGet('/concursos?limit=120');
        const sel = $('ccConcurso');
        if (!sel || !data.sucesso) return;
        sel.innerHTML = '';
        (data.concursos || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.concurso;
            opt.textContent = `#${c.concurso} ${c.data || ''} · ${(c.dezenas || []).join('-')}`;
            sel.appendChild(opt);
        });
    }

    async function conferir() {
        if (!sessaoAtual?.id) return;
        const concurso = parseInt($('ccConcurso')?.value, 10);
        const data = await apiPost('/conferir', { sessao_id: sessaoAtual.id, concurso });
        const box = $('ccConferencia');
        if (!box) return;
        if (!data.sucesso) {
            box.innerHTML = `<div class="text-danger small">${data.erro}</div>`;
            return;
        }
        const sorteadas = data.sorteadas || [];
        const sortRow = htmlApostaColunas(sorteadas, null);
        let html = `<div class="small mb-2">
            <strong>Concurso ${data.concurso}</strong> (${data.data || ''})
            <div class="cc-sorteadas-row mt-1">${sortRow}</div>
        </div>`;
        if (data.melhor_construcao) {
            html += `<div class="alert alert-success py-2 small mb-2">
                Melhor: <strong>Construção ${data.melhor_construcao}</strong>
            </div>`;
        }
        html += (data.ranking || []).map(r => {
            const cls = r.construcao_numero === data.melhor_construcao ? ' cc-melhor' : '';
            const apRows = (r.apostas || []).map(a => {
                const acCls = a.acertos >= 5 ? 'text-success fw-bold' : a.acertos >= 4 ? 'text-warning' : '';
                return `<div class="cc-aposta-row">
                    <span class="cc-aposta-num">${a.linha}.</span>
                    ${htmlApostaColunas(a.dezenas, sorteadas)}
                    <span class="cc-aposta-acertos ${acCls}">${a.acertos} ac.</span>
                </div>`;
            }).join('');
            return `<div class="cc-construcao-card${cls} mb-2">
                <div class="d-flex justify-content-between mb-1">
                    <strong>Construção ${r.construcao_numero}</strong>
                    ${htmlEstrategiaBadge(r)}
                </div>
                <div class="small mb-1">
                    Máx: <strong>${r.max_acertos}</strong> ac. · Total: ${r.total_acertos} · Média: ${r.media_acertos}
                </div>
                ${apRows}
            </div>`;
        }).join('');
        box.innerHTML = html;
    }

    function renderAnaliseHistorica(analise) {
        const el = $('ccAnaliseHistorica');
        if (!el) return;
        if (!analise || !analise.tem_dados) {
            el.innerHTML = `<p class="text-muted small mb-0">${(analise && analise.mensagem) || 'Nenhuma conferência histórica salva ainda.'}</p>`;
            return;
        }
        const p = analise.perguntas || {};
        const card = (titulo, num, estrategia, detalhe) =>
            `<div class="cc-analise-card">
                <div class="cc-analise-pergunta">${titulo}</div>
                <div class="cc-analise-valor">Constr. ${num}</div>
                <div class="cc-analise-detalhe">${labelEstrategia(estrategia)}<br>${detalhe}</div>
            </div>`;
        const cards = [];
        if (p.mais_pontos) cards.push(card('Mais pontos', p.mais_pontos.construcao_numero, p.mais_pontos.estrategia, `${p.mais_pontos.valor} pts`));
        if (p.melhor_acertos) cards.push(card('Melhor desempenho', p.melhor_acertos.construcao_numero, p.melhor_acertos.estrategia, textoAcertosResumo(p.melhor_acertos)));
        if (p.maior_media) cards.push(card('Maior média', p.maior_media.construcao_numero, p.maior_media.estrategia, `${p.maior_media.valor} ac./concurso`));
        el.innerHTML = `<div class="cc-analise-resumo mb-2"><div class="cc-analise-estrategia-linha">${cards.join('')}</div></div>`;
    }

    async function carregarAnaliseHistorica() {
        if (!sessaoAtual?.id) return;
        const data = await apiGet('/sessao/' + sessaoAtual.id + '/analise-comparativa');
        if (data.sucesso) renderAnaliseHistorica(data.analise);
    }

    async function conferirHistoricoConstrucao(construcaoId, num) {
        const incremental = $('ccHistIncremental')?.checked || false;
        const btn = document.querySelector(`.cc-btn-conf-hist[data-id="${construcaoId}"]`);
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> …';
        }
        try {
            const data = await apiPost('/construcao/' + construcaoId + '/conferir-historico', { incremental });
            if (!data.sucesso) {
                alert(data.erro || 'Erro na conferência.');
                return;
            }
            if (data.conferencia && modalConfHist) {
                $('ccConfHistNum').textContent = '#' + num;
                $('ccConfHistCorpo').innerHTML = (data.mensagem ? `<div class="alert alert-success py-2 small">${data.mensagem}</div>` : '') +
                    htmlResumoConferencia(data.conferencia);
                modalConfHist.show();
            }
            const refreshed = await apiGet('/sessao/' + sessaoAtual.id);
            if (refreshed.sucesso) {
                sessaoAtual = refreshed.sessao;
                renderConstrucoes(sessaoAtual);
            }
            await carregarAnaliseHistorica();
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-history"></i> Conferir histórico';
            }
        }
    }

    async function conferirHistoricoTodas() {
        if (!sessaoAtual?.id) return;
        const incremental = $('ccHistIncremental')?.checked || false;
        const btn = $('ccBtnConferirTodas');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando…';
        }
        try {
            const data = await apiPost('/sessao/' + sessaoAtual.id + '/conferir-historico', { incremental });
            if (!data.sucesso) {
                alert(data.erro || 'Erro na análise.');
                return;
            }
            const tab = document.getElementById('ccTabHistorico');
            if (tab && typeof bootstrap !== 'undefined') bootstrap.Tab.getOrCreateInstance(tab).show();
            if (data.analise) renderAnaliseHistorica(data.analise);
            else await carregarAnaliseHistorica();
            const refreshed = await apiGet('/sessao/' + sessaoAtual.id);
            if (refreshed.sucesso) {
                sessaoAtual = refreshed.sessao;
                renderConstrucoes(sessaoAtual);
            }
            $('ccSessaoStatus').textContent = `Análise histórica: ${data.processadas || 0} construção(ões) processada(s).`;
        } finally {
            if (btn) {
                btn.disabled = !(sessaoAtual?.construcoes?.length);
                btn.innerHTML = '<i class="fas fa-history"></i> Analisar todas no histórico';
            }
        }
    }

    function abrirEditar(construcaoId) {
        if (!sessaoAtual) return;
        const c = (sessaoAtual.construcoes || []).find(x => x.id === construcaoId);
        if (!c) return;
        editandoConstrucaoId = construcaoId;
        $('ccEditNumero').textContent = '#' + c.numero;
        const hint = $('ccEditPoolHint');
        if (hint) hint.textContent = poolHintText(sessaoAtual.pool_colunas || sessaoAtual.conjunto_base);
        const wrap = $('ccEditApostas');
        if (!wrap) return;
        wrap.innerHTML = (c.apostas || []).map(a => {
            const txt = (a.dezenas || []).join(' ');
            return `<div class="cc-edit-aposta row g-1 mb-1 align-items-center" data-linha="${a.linha}">
                <div class="col-auto cc-aposta-num">${a.linha}.</div>
                <div class="col">
                    <input type="text" class="form-control form-control-sm cc-input-dezenas"
                        value="${txt}" data-linha="${a.linha}" placeholder="C1 C2 C3 C4 C5 C6 C7">
                </div>
            </div>`;
        }).join('');
        modalEditar?.show();
    }

    async function salvarEdicao() {
        if (!editandoConstrucaoId) return;
        const inputs = document.querySelectorAll('#ccEditApostas .cc-input-dezenas');
        const apostas = [];
        for (const inp of inputs) {
            const linha = parseInt(inp.dataset.linha, 10);
            const parts = inp.value.trim().split(/\s+/).filter(Boolean);
            if (parts.length !== NUM_COLS) {
                alert(`Aposta ${linha}: informe ${NUM_COLS} dígitos (C1–C7).`);
                return;
            }
            apostas.push({ linha, dezenas: parts.map(x => parseInt(x, 10)) });
        }
        const data = await apiPut('/construcao/' + editandoConstrucaoId, { apostas });
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao salvar.');
            return;
        }
        modalEditar?.hide();
        if (data.sessao) {
            sessaoAtual = data.sessao;
            renderConstrucoes(sessaoAtual);
        }
    }

    function bindConstrucoesAcoes() {
        const el = $('ccConstrucoes');
        if (!el || el.dataset.boundSs) return;
        el.dataset.boundSs = '1';
        el.addEventListener('click', async (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const id = parseInt(btn.dataset.id, 10);
            if (btn.classList.contains('cc-btn-editar')) abrirEditar(id);
            else if (btn.classList.contains('cc-btn-conf-hist')) conferirHistoricoConstrucao(id, parseInt(btn.dataset.num, 10));
            else if (btn.classList.contains('cc-btn-excluir')) {
                if (!confirm('Excluir construção #' + btn.dataset.num + '?')) return;
                const data = await fetch(API + '/construcao/' + id, { method: 'DELETE' }).then(r => r.json());
                if (data.sucesso && data.sessao) {
                    sessaoAtual = data.sessao;
                    renderConstrucoes(sessaoAtual);
                }
            } else if (btn.classList.contains('cc-btn-export')) {
                const data = await apiPost('/construcao/' + id + '/export-txt', {});
                if (data.sucesso) {
                    const blob = new Blob([data.texto], { type: 'text/plain;charset=utf-8' });
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = data.nome_arquivo || 'construcao.txt';
                    a.click();
                }
            }
        });
    }

    function init() {
        renderVolanteColunas();
        fillEstrategias();
        carregarSessoes();
        carregarConcursos();
        bindConstrucoesAcoes();
        atualizarBotoesSessao();

        if (typeof bootstrap !== 'undefined') {
            const elEdit = document.getElementById('ccModalEditar');
            const elHist = document.getElementById('ccModalConfHist');
            if (elEdit) modalEditar = new bootstrap.Modal(elEdit);
            if (elHist) modalConfHist = new bootstrap.Modal(elHist);
        }
        $('ccBtnSalvarEdicao')?.addEventListener('click', salvarEdicao);

        $('ccColinhaBtn')?.addEventListener('click', () => {
            $('ccColinhaPop')?.classList.toggle('aberto');
        });
        $('ccColinhaFechar')?.addEventListener('click', fecharColinha);
        $('ccBtnAnaliseAtraso')?.addEventListener('click', () => importarAnalise('atraso'));
        $('ccBtnAnaliseFreq')?.addEventListener('click', () => importarAnalise('frequencia'));
        $('ccBtnUltimoSorteio')?.addEventListener('click', importarUltimo);
        $('ccBtnLimpar')?.addEventListener('click', () => {
            for (let c = 1; c <= NUM_COLS; c++) poolColunas[c] = new Set();
            origemConjunto = 'manual';
            renderVolanteColunas();
            updatePoolInfo();
        });
        $('ccBtnSalvarSessao')?.addEventListener('click', salvarSessao);
        $('ccBtnGerar')?.addEventListener('click', gerarConstrucao);
        $('ccBtnConferir')?.addEventListener('click', conferir);
        $('ccBtnConferirTodas')?.addEventListener('click', conferirHistoricoTodas);
        $('ccBtnIrPanorama')?.addEventListener('click', () => {
            const tab = document.getElementById('ccTabPanorama');
            if (tab && typeof bootstrap !== 'undefined') bootstrap.Tab.getOrCreateInstance(tab).show();
        });
        $('ccTabHistorico')?.addEventListener('shown.bs.tab', carregarAnaliseHistorica);

        $('ccSelectSessao')?.addEventListener('change', async (e) => {
            const id = parseInt(e.target.value, 10);
            if (!id) {
                sessaoAtual = null;
                renderConstrucoes(null);
                return;
            }
            const data = await apiGet('/sessao/' + id);
            if (data.sucesso) {
                sessaoAtual = data.sessao;
                setPoolFromPayload(sessaoAtual.pool_colunas || sessaoAtual.conjunto_base, sessaoAtual.origem_conjunto);
                $('ccNomeSessao').value = sessaoAtual.nome || '';
                renderConstrucoes(sessaoAtual);
                await carregarAnaliseHistorica();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
