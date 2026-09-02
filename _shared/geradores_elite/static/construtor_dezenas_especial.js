/**
 * Aba "Pool de Dezenas (01–31) Especial"
 * — só seleciona/carrega 16 dezenas no motor já existente (aba Dezenas).
 */
(function () {
    'use strict';

    const sel = document.getElementById('ccEspSelect');
    if (!sel) return;

    const API = window.__CC_API__ || '';
    const TOTAL = 16;
    const UNIVERSO_MIN = 1;
    const UNIVERSO_MAX = 31;

    const DISTRIBUICOES = {
        1: {
            nome: 'Distribuição 1',
            baixas: [1, 2, 4, 6, 8, 9],
            medias: [11, 15, 16, 17, 18],
            altas: [22, 23, 25, 28, 30],
        },
        2: {
            nome: 'Distribuição 2',
            baixas: [3, 5, 7, 9, 10],
            medias: [12, 13, 14, 19, 20],
            altas: [21, 24, 26, 27, 29, 31],
        },
        3: {
            nome: 'Distribuição 3',
            baixas: [1, 2, 3, 4, 5, 7],
            medias: [11, 12, 13, 15, 16],
            altas: [21, 22, 23, 24, 25],
        },
        4: {
            nome: 'Distribuição 4 (mescla D1+D3)',
            baixas: [1, 2, 3, 4, 6, 8],
            medias: [11, 12, 15, 16, 17],
            altas: [21, 22, 23, 25, 28],
        },
    };

    function $(id) { return document.getElementById(id); }

    function fmt(n) {
        return String(n).padStart(2, '0');
    }

    function poolDe(dist) {
        return [...dist.baixas, ...dist.medias, ...dist.altas].sort((a, b) => a - b);
    }

    function validarPool(nums) {
        const unicos = [...new Set(nums)].sort((a, b) => a - b);
        if (unicos.length !== TOTAL) {
            return { ok: false, erro: `Precisa de exatamente ${TOTAL} dezenas (veio ${unicos.length}).` };
        }
        if (unicos.length !== nums.length) {
            return { ok: false, erro: 'Há dezenas duplicadas na distribuição.' };
        }
        for (const n of unicos) {
            if (!Number.isInteger(n) || n < UNIVERSO_MIN || n > UNIVERSO_MAX) {
                return { ok: false, erro: `Dezena inválida: ${n} (universo ${fmt(UNIVERSO_MIN)}–${fmt(UNIVERSO_MAX)}).` };
            }
        }
        return { ok: true, pool: unicos };
    }

    // Valida cadastro estático na carga
    Object.keys(DISTRIBUICOES).forEach((k) => {
        const v = validarPool(poolDe(DISTRIBUICOES[k]));
        if (!v.ok) {
            console.error('[Dezenas Especial] Distribuição', k, v.erro);
        }
    });

    function ballHtml(n, faixa) {
        const cores = { b: '#0d6efd', m: '#fd7e14', a: '#dc3545' };
        const bg = cores[faixa] || '#6c757d';
        return `<span class="dez-ball-mini" style="background:${bg};color:#fff;border:none;">${fmt(n)}</span>`;
    }

    function renderPreview(key) {
        const preview = $('ccEspPreview');
        const balls = $('ccEspBalls');
        const btn = $('ccEspBtnCarregar');
        const status = $('ccEspStatus');
        const confronto = $('ccEspConfronto');

        if (!key || !DISTRIBUICOES[key]) {
            if (preview) preview.innerHTML = 'Selecione uma distribuição para ver o pool.';
            if (balls) balls.innerHTML = '';
            if (btn) btn.disabled = true;
            if (status) status.textContent = '';
            if (confronto) { confronto.style.display = 'none'; confronto.innerHTML = ''; }
            return null;
        }

        const d = DISTRIBUICOES[key];
        const check = validarPool(poolDe(d));
        if (!check.ok) {
            if (preview) preview.innerHTML = `<span class="text-danger">${check.erro}</span>`;
            if (btn) btn.disabled = true;
            return null;
        }

        if (preview) {
            preview.innerHTML =
                `<strong>${d.nome}</strong> · total <strong>${check.pool.length}</strong> dezenas<br>` +
                `<span class="text-primary">Baixas (${d.baixas.length}):</span> ${d.baixas.map(fmt).join(' ')}<br>` +
                `<span style="color:#fd7e14">Médias (${d.medias.length}):</span> ${d.medias.map(fmt).join(' ')}<br>` +
                `<span class="text-danger">Altas (${d.altas.length}):</span> ${d.altas.map(fmt).join(' ')}`;
        }

        if (balls) {
            balls.innerHTML =
                d.baixas.map((n) => ballHtml(n, 'b')).join('') +
                d.medias.map((n) => ballHtml(n, 'm')).join('') +
                d.altas.map((n) => ballHtml(n, 'a')).join('');
        }

        if (btn) btn.disabled = false;
        if (status) status.textContent = '';
        atualizarConfronto(check.pool);
        return check.pool;
    }

    async function apiGet(path) {
        const r = await fetch(API + path);
        return r.json();
    }

    async function atualizarConfronto(pool) {
        const el = $('ccEspConfronto');
        if (!el || !API) return;
        el.style.display = '';
        el.className = 'small text-muted mb-3';
        el.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Confrontando com ciclo/atraso…';

        try {
            const [falt, atr] = await Promise.all([
                apiGet('/ciclo?tipo=faltantes'),
                apiGet('/analise-sugestao?quantidade=16&criterio=atraso'),
            ]);
            const setPool = new Set(pool);
            const faltantes = (falt && falt.sucesso && Array.isArray(falt.dezenas)) ? falt.dezenas : [];
            const atrasadas = (atr && atr.sucesso && Array.isArray(atr.dezenas)) ? atr.dezenas : [];
            const nFalt = faltantes.filter((n) => setPool.has(n)).length;
            const nAtr = atrasadas.filter((n) => setPool.has(n)).length;

            let tom = 'text-muted';
            let dica = 'Informativo — não altera o pool.';
            if (nFalt >= 8 || nAtr >= 8) {
                tom = 'text-success';
                dica = 'Bom alinhamento com o momento atual do ciclo/atraso.';
            } else if (nFalt <= 3 && nAtr <= 3) {
                tom = 'text-warning';
                dica = 'Poucas no faltantes/atraso — ainda assim a distribuição estratégica é válida.';
            }

            el.className = `small ${tom} mb-3`;
            el.innerHTML =
                `<i class="fas fa-chart-line me-1"></i>` +
                `<strong>Confronto (só leitura):</strong> ` +
                `${nFalt}/16 no <em>faltantes do ciclo</em>` +
                ` · ${nAtr}/16 entre as <em>mais atrasadas</em>` +
                `<br><span class="text-muted">${dica}</span>`;
        } catch (_) {
            el.className = 'small text-muted mb-3';
            el.innerHTML = '<i class="fas fa-info-circle me-1"></i> Confronto indisponível no momento.';
        }
    }

    function carregar() {
        const key = sel.value;
        const d = DISTRIBUICOES[key];
        const status = $('ccEspStatus');
        if (!d) return;

        const check = validarPool(poolDe(d));
        if (!check.ok) {
            if (status) {
                status.className = 'small text-danger mt-2 mb-0';
                status.textContent = check.erro;
            }
            return;
        }

        if (typeof window.__CC_aplicarPoolDezenas !== 'function') {
            if (status) {
                status.className = 'small text-danger mt-2 mb-0';
                status.textContent = 'Motor do construtor ainda não carregou. Recarregue a página.';
            }
            return;
        }

        window.__CC_aplicarPoolDezenas(
            check.pool,
            'distribuicao-especial',
            `${d.nome} carregada (${TOTAL} dezenas). Salve o conjunto-base para gerar.`
        );

        if (status) {
            status.className = 'small text-success mt-2 mb-0';
            status.textContent = `OK — ${d.nome} enviada à aba Pool de Dezenas. Salve o conjunto-base e gere.`;
        }
    }

    // Info (i)
    const infoBtn = $('ccEspInfoBtn');
    const infoBox = $('ccEspInfoBox');
    if (infoBtn && infoBox) {
        infoBtn.addEventListener('click', () => {
            const aberto = infoBox.style.display !== 'none';
            infoBox.style.display = aberto ? 'none' : '';
            infoBtn.setAttribute('aria-expanded', aberto ? 'false' : 'true');
        });
    }

    sel.addEventListener('change', () => renderPreview(sel.value));
    $('ccEspBtnCarregar')?.addEventListener('click', carregar);
})();
