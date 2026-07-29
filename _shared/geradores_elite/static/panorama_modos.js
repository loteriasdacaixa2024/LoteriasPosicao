/**
 * Panorama Top-3 — modos Volante pool e Seleção guiada.
 */
(function (global) {
    'use strict';

    const CC_IMPORT_KEY = 'cc_panorama_import';
    const CC_IMPORT_URL = '/geradores-elite/construtor-construcoes/';

    let apiPathFn = (p) => p;
    let modoPanorama = 'automatico';
    let modoValidacao = 'estrito';
    let ctxSelecao = null;
    let ultimoSet = new Set();
    let poolVolante = new Set();
    let guiadoSel = new Set();
    let catFiltro = null;
    let kJogo = 15;
    let kMinConstrutor = 7;
    let poolMax = 16;
    let universoMax = 60;
    let dezenaMin = 1;
    let ultimaValidacao = null;

    const CAT_LABELS = {
        par: 'Pares',
        impar: 'Ímpares',
        primo: 'Primos',
        fibonacci: 'Fibonacci',
        multiplos_3: 'Múlt. de 3',
        moldura: 'Moldura',
        ultimo_concurso: 'Último concurso',
    };

    function fmt(n) {
        return String(n).padStart(2, '0');
    }

    function faixaClass(n) {
        if (n <= 10) return 'faixa-baixa';
        if (n <= 20) return 'faixa-media';
        return 'faixa-alta';
    }

    function $(id) {
        return document.getElementById(id);
    }

    function setModo(m) {
        modoPanorama = m || 'automatico';
        document.querySelectorAll('.pan-modo-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.pmodo === modoPanorama);
        });
        $('painelPanVolante16')?.classList.toggle('d-none', modoPanorama !== 'volante_pool');
        $('painelPanGuiado')?.classList.toggle('d-none', modoPanorama !== 'guiado');
        $('grpModoValidacaoPan')?.classList.toggle('d-none', modoPanorama === 'automatico');
    }

    function setModoValidacao(m) {
        modoValidacao = m || 'estrito';
        document.querySelectorAll('.pan-val-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.pval === modoValidacao);
        });
        if (modoPanorama === 'guiado' && guiadoSel.size) validarGuiado(false);
    }

    function renderBall(container, n, opts) {
        opts = opts || {};
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pan-ball ' + faixaClass(n);
        btn.textContent = fmt(n);
        btn.dataset.n = n;
        const sel = opts.selected && opts.selected.has(n);
        if (sel) btn.classList.add('selected');
        if (opts.ultimo && opts.ultimo.has(n) && !sel) btn.classList.add('pan-ultimo-ref');
        if (opts.bloqueado && !sel) btn.classList.add('pan-bloqueado');
        if (opts.highlight && opts.highlight.has(n)) btn.classList.add('pan-cat-highlight');
        btn.title = (opts.ultimo && opts.ultimo.has(n)) ? 'Saiu no último concurso' : '';
        btn.addEventListener('click', opts.onClick);
        container.appendChild(btn);
    }

    function renderVolantePool() {
        const vol = $('panVolante16');
        if (!vol) return;
        vol.innerHTML = '';
        const noLimite = poolVolante.size >= poolMax;
        for (let n = dezenaMin; n <= universoMax; n++) {
            renderBall(vol, n, {
                selected: poolVolante,
                ultimo: ultimoSet,
                bloqueado: noLimite,
                onClick: () => {
                    if (poolVolante.has(n)) poolVolante.delete(n);
                    else {
                        if (poolVolante.size >= poolMax) return;
                        poolVolante.add(n);
                    }
                    renderVolantePool();
                    updateVolantePoolInfo();
                },
            });
        }
        updateVolantePoolInfo();
    }

    function updateVolantePoolInfo() {
        const cnt = $('panVolanteContador');
        const info = $('panVolanteInfo');
        const btnC = $('btnPanEnviarConstrutor16');
        const arr = [...poolVolante].sort((a, b) => a - b);
        if (cnt) cnt.textContent = `${arr.length}/${poolMax}`;
        const ult = arr.filter(n => ultimoSet.has(n)).length;
        if (info) {
            info.textContent = arr.length
                ? `${arr.map(fmt).join(' ')} · ${ult} do último concurso`
                : 'Nenhuma dezena selecionada';
        }
        if (btnC) btnC.disabled = arr.length < kMinConstrutor;
    }

    function renderCotas() {
        const el = $('panCotasCorpo');
        if (!el || !ctxSelecao) return;
        const cotas = ctxSelecao.cotas || [];
        el.innerHTML = cotas.map(c =>
            `<div class="pan-cota-item">
                <span class="sigla">${c.codigo}</span>
                <span class="text-muted">${c.label}</span>
                <div class="val">${c.valor_label ?? c.alvo}</div>
            </div>`
        ).join('') || '<span class="text-muted small">Carregue o contexto do rank.</span>';
    }

    function renderCatChips() {
        const el = $('panCatChips');
        if (!el) return;
        el.innerHTML = Object.keys(CAT_LABELS).map(k =>
            `<button type="button" class="pan-cat-chip${catFiltro === k ? ' active' : ''}" data-cat="${k}">${CAT_LABELS[k]}</button>`
        ).join('');
        el.querySelectorAll('.pan-cat-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const c = btn.dataset.cat;
                catFiltro = catFiltro === c ? null : c;
                renderCatChips();
                renderVolanteGuiado();
            });
        });
    }

    function catHighlightSet() {
        if (!catFiltro || !ctxSelecao?.categorias) return null;
        return new Set(ctxSelecao.categorias[catFiltro] || []);
    }

    function renderVolanteGuiado() {
        const vol = $('panVolanteGuiado');
        if (!vol) return;
        vol.innerHTML = '';
        const hl = catHighlightSet();
        const noLimite = guiadoSel.size >= kJogo;
        for (let n = dezenaMin; n <= universoMax; n++) {
            renderBall(vol, n, {
                selected: guiadoSel,
                ultimo: ultimoSet,
                bloqueado: noLimite,
                highlight: hl,
                onClick: () => {
                    if (guiadoSel.has(n)) guiadoSel.delete(n);
                    else {
                        if (guiadoSel.size >= kJogo) return;
                        guiadoSel.add(n);
                    }
                    ultimaValidacao = null;
                    $('panValidacaoCorpo')?.classList.add('d-none');
                    renderVolanteGuiado();
                    updateGuiadoInfo();
                },
            });
        }
        updateGuiadoInfo();
    }

    function updateGuiadoInfo() {
        const cnt = $('panGuiadoContador');
        const info = $('panGuiadoInfo');
        const btnC = $('btnPanEnviarConstrutorGuiado');
        const arr = [...guiadoSel].sort((a, b) => a - b);
        if (cnt) cnt.textContent = `${arr.length}/${kJogo}`;
        if (info) {
            info.textContent = arr.length ? arr.map(fmt).join(' ') : 'Clique nas dezenas';
        }
        if (btnC) btnC.disabled = !(ultimaValidacao && ultimaValidacao.valido);
    }

    function renderValidacao(val) {
        const el = $('panValidacaoCorpo');
        if (!el) return;
        if (!val) {
            el.classList.add('d-none');
            return;
        }
        el.classList.remove('d-none');
        const det = (val.detalhes || []).map(d => {
            const ok = modoValidacao === 'relaxar' ? d.ok_relaxar : d.ok_estrito;
            const cls = ok ? 'pan-val-ok' : 'pan-val-fail';
            const mark = ok ? '✓' : '✗';
            return `<div class="${cls}">${mark} ${d.codigo}: alvo ${d.alvo} → atual ${d.atual}</div>`;
        }).join('');
        const status = val.valido
            ? `<div class="pan-val-ok fw-bold mb-1">Aposta VÁLIDA (${modoValidacao})</div>`
            : `<div class="pan-val-fail fw-bold mb-1">Inválida — ${val.motivo || ''}</div>`;
        const mes = val.mes_alvo ? `<div class="text-muted">Mês alvo: ${val.mes_alvo.abrev || val.mes_alvo.nome}</div>` : '';
        el.innerHTML = status + det + mes;
    }

    async function carregarContexto(base, rank) {
        try {
            const r = await fetch(`${apiPathFn('/panorama-selecao-contexto')}?base=${encodeURIComponent(base)}&rank=${rank}`);
            const data = await r.json();
            if (!data.sucesso) return null;
            ctxSelecao = data;
            kJogo = data.dezenas_por_jogo || kJogo;
            universoMax = data.universo_max || universoMax;
            dezenaMin = data.dezena_min != null ? data.dezena_min : dezenaMin;
            const ult = data.ultimo_sorteio?.dezenas || [];
            ultimoSet = new Set(ult);
            renderCotas();
            renderCatChips();
            if (modoPanorama === 'volante_pool') renderVolantePool();
            if (modoPanorama === 'guiado') renderVolanteGuiado();
            return data;
        } catch (e) {
            console.warn('panorama contexto', e);
            return null;
        }
    }

    async function validarGuiado(showAlert) {
        if (guiadoSel.size !== kJogo) {
            if (showAlert) alert(`Selecione exatamente ${kJogo} dezenas.`);
            return null;
        }
        const base = global.__panBasePanorama ? global.__panBasePanorama() : 'geral';
        const rank = global.__panRankPanorama ? global.__panRankPanorama() : 1;
        try {
            const r = await fetch(apiPathFn('/panorama-validar-selecao'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dezenas: [...guiadoSel],
                    base,
                    rank_escolhido: rank,
                    modo_validacao: modoValidacao,
                    dezenas_por_jogo: kJogo,
                }),
            });
            const data = await r.json();
            ultimaValidacao = data;
            renderValidacao(data);
            updateGuiadoInfo();
            if (showAlert && !data.valido) alert(data.motivo || 'Seleção inválida.');
            return data;
        } catch (e) {
            if (showAlert) alert(e.message);
            return null;
        }
    }

    function enviarConstrutor(dezenas, origem) {
        const arr = [...new Set(dezenas)].sort((a, b) => a - b);
        if (arr.length < kMinConstrutor) {
            alert(`Selecione ao menos ${kMinConstrutor} dezenas.`);
            return;
        }
        try {
            sessionStorage.setItem(CC_IMPORT_KEY, JSON.stringify({
                dezenas: arr,
                origem: origem || 'panorama',
                ts: Date.now(),
            }));
        } catch (e) {
            alert('Não foi possível salvar para o Construtor.');
            return;
        }
        window.open(CC_IMPORT_URL, '_blank');
    }

    function getGerarExtras() {
        const base = {
            modo_panorama: modoPanorama,
            modo_validacao: modoValidacao,
        };
        if (modoPanorama === 'volante_pool') {
            const pool = [...poolVolante].sort((a, b) => a - b);
            if (pool.length !== poolMax) {
                return { erro: `Marque exatamente ${poolMax} dezenas no volante (atual: ${pool.length}).` };
            }
            base.pool_dezenas = pool;
        }
        if (modoPanorama === 'guiado') {
            if (guiadoSel.size !== kJogo) {
                return { erro: `Selecione ${kJogo} dezenas na seleção guiada.` };
            }
            base.dezenas_manuais = [...guiadoSel].sort((a, b) => a - b);
        }
        return base;
    }

    function bindEvents() {
        document.querySelectorAll('.pan-modo-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                setModo(btn.dataset.pmodo);
                const base = global.__panBasePanorama ? global.__panBasePanorama() : 'geral';
                const rank = global.__panRankPanorama ? global.__panRankPanorama() : 1;
                carregarContexto(base, rank);
            });
        });
        document.querySelectorAll('.pan-val-btn').forEach(btn => {
            btn.addEventListener('click', () => setModoValidacao(btn.dataset.pval));
        });
        $('btnPanVolanteLimpar')?.addEventListener('click', () => {
            poolVolante.clear();
            renderVolantePool();
        });
        $('btnPanGuiadoLimpar')?.addEventListener('click', () => {
            guiadoSel.clear();
            ultimaValidacao = null;
            $('panValidacaoCorpo')?.classList.add('d-none');
            renderVolanteGuiado();
        });
        $('btnPanCatLimpar')?.addEventListener('click', () => {
            catFiltro = null;
            renderCatChips();
            renderVolanteGuiado();
        });
        $('btnPanValidarGuiado')?.addEventListener('click', () => validarGuiado(true));
        $('btnPanEnviarConstrutor16')?.addEventListener('click', () => {
            enviarConstrutor([...poolVolante], 'panorama_volante_pool');
        });
        $('btnPanEnviarConstrutorGuiado')?.addEventListener('click', () => {
            if (!ultimaValidacao?.valido) {
                alert('Valide a seleção antes de enviar ao Construtor.');
                return;
            }
            enviarConstrutor(ultimaValidacao.dezenas, 'panorama_guiado');
        });
    }

    function init(opts) {
        opts = opts || {};
        if (opts.apiPath) apiPathFn = opts.apiPath;
        kJogo = opts.dezenasPorJogo || 15;
        kMinConstrutor = opts.dezenasMin || opts.dezenasPorJogo || 7;
        poolMax = opts.poolPanorama || 16;
        universoMax = opts.universoMax || 60;
        dezenaMin = opts.dezenaMin != null ? opts.dezenaMin : 1;
        if (opts.volanteCols) {
            document.querySelectorAll('.pan-volante').forEach(el => {
                el.style.gridTemplateColumns = `repeat(${opts.volanteCols}, 1fr)`;
            });
        }
        bindEvents();
        setModo('automatico');
    }

    function onPanoramaRefresh(base, rank) {
        carregarContexto(base, rank);
    }

    function syncDezenasPorJogo(k) {
        kJogo = k || kJogo;
        if ($('panGuiadoContador')) $('panGuiadoContador').textContent = `${guiadoSel.size}/${kJogo}`;
    }

    global.PanoramaModos = {
        init,
        onPanoramaRefresh,
        syncDezenasPorJogo,
        getGerarExtras,
        getModo: () => modoPanorama,
    };
})(typeof window !== 'undefined' ? window : this);
