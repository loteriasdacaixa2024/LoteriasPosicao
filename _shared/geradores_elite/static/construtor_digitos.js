(function () {
    'use strict';

    if (!window.__CC_DIGITOS__) return;

    const PAGE = window.__CC_DIGITOS_PAGE__ || 'construtor'; // 'construtor' | 'intel'
    const root = document.getElementById(PAGE === 'intel' ? 'ge-digitos-intel' : 'ge-construtor');
    if (!root) return;

    const API = window.__CC_API__ || root.dataset.api;
    const UI = window.__CC_UI__ || {};
    const PICK_MIN = UI.pick_min || 7;
    const PICK_MAX = UI.pick_max || 15;
    const PICK_DEFAULT = UI.pick_default || 7;
    const MIN_REC = UI.positional ? 1 : 3;
    const LS_POOL_KEY = 'cc_digitos_pool_v3';
    /** Universo fixo: 10 dígitos únicos (0–9). Em Super Sete = candidatos das colunas. */
    const DIGITOS_TODOS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
    const QTD_DIGITOS_UNIVERSO = DIGITOS_TODOS.length; // 10
    /** Faixa do filtro «Exigir qtd dígitos na aposta» — alinhada aos dígitos únicos 0–9. */
    const EXIGIR_QTD_MIN = 1;
    const EXIGIR_QTD_MAX = 9;
    const PAD_WIDTH = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
    const IS_COLUNAS = !!(UI.positional || UI.export_is_columns || UI.modality_key === 'supersete');
    const HAS_MES = !!UI.has_mes;
    const UNIDADE = IS_COLUNAS
        ? (UI.unidade_label_plural || 'colunas')
        : 'dezenas';
    const UNIDADE_SING = IS_COLUNAS
        ? (UI.unidade_label_singular || 'coluna')
        : 'dezena';

    const $ = (id) => document.getElementById(id);
    let guiaCache = null;
    let poolAba2 = new Set();
    let poolIntel = new Set();
    let sessaoDigitos = null;
    let ultimoLote = [];
    let ultimaAvalIntel = null;
    let ultimoLoteAba2 = [];
    /** Dezenas do último concurso (para Rept). */
    let ultimoSorteioDz = [];
    /** 0 = próximo clique calcula total · 1 = próximo clique mostra apostas */
    let cdComboFase = 0;
    let cdUltimaAval = null;

    const MANUAL_S10_URL = '/geradores-elite/escolha-tubular-apostas/?aba=manual';
    const MANUAL_S10_KEY = 'tb_manual10_import';
    const PADROES_II_URL = '/analise/analises-inteligentes/?aba=padroes-ii';

    window.__CC_POOL_DIGITOS_ABA2__ = () => [...poolAba2].sort((a, b) => a - b);

    /** Formata valor da aposta: Super Sete = dígito "0"…"9"; demais = dezena "01"…"60". */
    function fmtDez(n) {
        const v = Number(n);
        if (!Number.isFinite(v)) return String(n);
        if (PAD_WIDTH <= 1 || IS_COLUNAS) return String(v);
        return String(v).padStart(PAD_WIDTH, '0');
    }

    function escHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        })[c]);
    }

    /** Padrão inicial (1º dígito de cada dezena em ordem crescente). */
    function padraoInicialDe(dezenas) {
        const nums = (dezenas || []).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
        if (IS_COLUNAS) return nums.join(' ');
        return nums.map((n) => Math.floor(n / 10)).join(' ');
    }

    function analisarSeq(dezenas) {
        const nums = (dezenas || []).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
        const sequences = [];
        for (let i = 0; i < nums.length - 1; i++) {
            if (nums[i + 1] === nums[i] + 1) {
                let seqEnd = i + 1;
                while (seqEnd < nums.length - 1 && nums[seqEnd + 1] === nums[seqEnd] + 1) seqEnd++;
                sequences.push({ length: seqEnd - i + 1, numbers: nums.slice(i, seqEnd + 1) });
                i = seqEnd;
            }
        }
        let qtde = 0;
        let quais = '—';
        if (sequences.length === 1) qtde = sequences[0].length;
        else if (sequences.length > 1) qtde = sequences.length;
        if (sequences.length) {
            quais = sequences.map((seq) =>
                seq.length >= 3
                    ? `${fmtDez(seq.numbers[0])}-${fmtDez(seq.numbers[seq.numbers.length - 1])}`
                    : seq.numbers.map(fmtDez).join(',')
            ).join(' ');
        }
        return { qtde, quais, sequences };
    }

    function reptComUltimo(dezenas) {
        const prev = ultimoSorteioDz || [];
        if (!prev.length) return { count: 0, list: [], title: 'Sem último concurso' };
        const setPrev = new Set(prev.map(Number));
        const list = (dezenas || []).map(Number).filter((n) => setPrev.has(n));
        return {
            count: list.length,
            list,
            title: list.length
                ? `Repete do último: ${list.map(fmtDez).join(' ')}`
                : 'Nenhuma dezena do último concurso',
        };
    }

    function metaAposta(dezenas) {
        const nums = (dezenas || []).map(Number).filter(Number.isFinite);
        const sorted = [...nums].sort((a, b) => a - b);
        const seq = analisarSeq(sorted);
        const rept = reptComUltimo(sorted);
        const pares = sorted.filter((n) => n % 2 === 0).length;
        const digSet = new Set();
        sorted.forEach((n) => {
            const s = String(n).padStart(Math.max(2, PAD_WIDTH), '0');
            [...s].forEach((ch) => digSet.add(Number(ch)));
        });
        const digitos = [...digSet].sort((a, b) => a - b);
        const padraoFinal = IS_COLUNAS
            ? sorted.join(' ')
            : sorted.map((n) => n % 10).join(' ');
        return {
            dezenas: sorted,
            padrao: padraoInicialDe(sorted),
            padraoFinal,
            soma: sorted.reduce((a, b) => a + b, 0),
            seq: seq.qtde,
            seqQuais: seq.quais,
            rept: rept.count,
            reptList: rept.list,
            reptTitle: rept.title,
            pares,
            impares: sorted.length - pares,
            qtdDigitos: digitos.length,
            digitos: digitos.join(''),
        };
    }

    function urlPadraoII(padrao) {
        const p = String(padrao || '').trim();
        if (!p) return PADROES_II_URL;
        return `${PADROES_II_URL}&padrao=${encodeURIComponent(p)}`;
    }

    function ordenarLote(lista, modo) {
        const arr = (lista || []).map((ap, i) => {
            const m = metaAposta(ap.dezenas || []);
            return { ...ap, _i: i, _m: m };
        });
        const cmp = {
            soma_asc: (a, b) => a._m.soma - b._m.soma || a._i - b._i,
            soma_desc: (a, b) => b._m.soma - a._m.soma || a._i - b._i,
            seq_desc: (a, b) => b._m.seq - a._m.seq || a._i - b._i,
            rept_desc: (a, b) => b._m.rept - a._m.rept || a._i - b._i,
            geracao: (a, b) => a._i - b._i,
        }[modo] || ((a, b) => a._i - b._i);
        return arr.sort(cmp);
    }

    function htmlTabelaLote(apostas, sortModo) {
        const lista = apostas || [];
        if (!lista.length) {
            return { tableHtml: '', resumoHtml: '' };
        }
        const ordered = ordenarLote(lista, sortModo || 'geracao');
        const metas = ordered.map((ap) => ap._m);
        const somaMed = Math.round(metas.reduce((s, m) => s + m.soma, 0) / metas.length);
        const somaMin = Math.min(...metas.map((m) => m.soma));
        const somaMax = Math.max(...metas.map((m) => m.soma));
        const ultFmt = (guiaCache && guiaCache.ultimo_dezenas_fmt) || '';
        const ultC = (guiaCache && guiaCache.ultimo_concurso) || '—';
        const resumoHtml =
            `<strong>${lista.length}</strong> aposta(s) · soma média <strong>${somaMed}</strong> ` +
            `(${somaMin}–${somaMax})` +
            (ultFmt
                ? ` · Rept vs c.<strong>${ultC}</strong> [${ultFmt}]`
                : '') +
            ` · <a href="${PADROES_II_URL}" target="_blank" rel="noopener">Aba 4 · Padrões II</a>`;
        const cols = Math.max(...ordered.map((ap) => (ap.dezenas || []).length), 1);
        const temOrigem = ordered.some((ap) => ap.origem != null);
        const rows = ordered.map((ap) => {
            const m = ap._m;
            const reptSet = new Set((m.reptList || []).map(Number));
            const dezHtml = (m.dezenas || []).map((n) => {
                const cls = reptSet.has(n) ? 'ci-dez ci-rept' : 'ci-dez';
                return `<span class="${cls}" title="${reptSet.has(n) ? 'Repete do último' : ''}">${fmtDez(n)}</span>`;
            }).join('');
            const padUrl = urlPadraoII(m.padrao);
            const origTd = temOrigem
                ? `<td class="ci-muted" title="Aposta de origem">${ap.origem != null ? '#' + ap.origem : '—'}` +
                  (ap.trocadas != null ? ` · ${ap.trocadas}t` : '') +
                  `</td>`
                : '';
            return (
                `<tr>` +
                origTd +
                `<td class="ci-td-dez"><div class="ci-dez-row" style="--ci-cols:${cols}">${dezHtml}</div></td>` +
                `<td title="Padrão inicial — abrir na aba 4"><a class="ci-pad-link" href="${padUrl}" target="_blank" rel="noopener">${escHtml(m.padrao || '—')}</a></td>` +
                `<td class="ci-num" title="Soma das dezenas">${m.soma}</td>` +
                `<td class="ci-num" title="${escHtml(m.reptTitle)}">${m.rept}</td>` +
                `<td class="ci-num" title="${escHtml(m.seqQuais)}">${m.seq}</td>` +
                `<td class="ci-muted" title="Pares / Ímpares">${m.pares}P/${m.impares}I</td>` +
                `<td class="ci-muted" title="Qtd. dígitos distintos (0–9)">${m.qtdDigitos}</td>` +
                `<td class="ci-muted" title="Padrão final (últimos dígitos)">${escHtml(m.padraoFinal || '—')}</td>` +
                `</tr>`
            );
        }).join('');
        const origTh = temOrigem
            ? `<th title="Variação a partir de qual aposta">Orig</th>`
            : '';
        const tableHtml =
            `<div class="ci-table-wrap">` +
            `<table class="ci-cmp-table">` +
            `<thead><tr>` +
            origTh +
            `<th class="ci-th-dez">Dezenas</th>` +
            `<th title="Padrão inicial (1º dígito de cada dezena)">Padrão</th>` +
            `<th title="Soma das dezenas">Soma</th>` +
            `<th title="Repetições vs último concurso">Rept</th>` +
            `<th title="Sequências consecutivas">Seq</th>` +
            `<th title="Pares / Ímpares">P/I</th>` +
            `<th title="Dígitos distintos na aposta">Dig</th>` +
            `<th title="Padrão final">Final</th>` +
            `</tr></thead>` +
            `<tbody>${rows}</tbody>` +
            `</table></div>`;
        return { tableHtml, resumoHtml };
    }

    function renderLoteIntel(apostas) {
        const out = $('ciResultado');
        const resumo = $('ciLoteResumo');
        const btnManual = $('ciBtnEnviarManual');
        const btnLote = $('ciBtnExportLote');
        const selOrd = $('ciOrdenarLote');
        const lista = apostas || [];
        if (btnLote) btnLote.disabled = !lista.length;
        if (btnManual) btnManual.disabled = !lista.length;
        if (selOrd) selOrd.disabled = !lista.length;
        if (!out) return;
        if (!lista.length) {
            out.className = 'small text-muted';
            out.innerHTML = 'Nenhuma geração ainda.';
            if (resumo) {
                resumo.classList.add('d-none');
                resumo.innerHTML = '';
            }
            return;
        }
        const modo = (selOrd && selOrd.value) || 'geracao';
        const built = htmlTabelaLote(lista, modo);
        if (resumo) {
            resumo.classList.remove('d-none');
            resumo.innerHTML = built.resumoHtml;
        }
        out.className = 'small';
        out.innerHTML = built.tableHtml;
    }

    function enviarLoteParaManual() {
        if (!ultimoLote.length) {
            alert('Gere as apostas antes de enviar ao Manual.');
            return;
        }
        let mesNum = 0;
        let mesNome = '';
        if (HAS_MES && window.MesSorteSelect) {
            const sel = $('ciMesExport');
            const raw = sel ? String(sel.value || '').trim() : '';
            if (raw && /^\d+$/.test(raw)) {
                mesNum = parseInt(raw, 10);
                const hit = (MesSorteSelect.cached && MesSorteSelect.cached.meses || [])
                    .find((m) => Number(m.mes_num || m.num) === mesNum);
                mesNome = (hit && (hit.nome || hit.mes_nome)) || '';
            }
        }
        const jogos = ultimoLote.map((ap) => ({
            dezenas: (ap.dezenas || []).map(Number),
            mes_num: mesNum || 0,
            mes_nome: mesNome || '',
        })).filter((j) => j.dezenas.length > 0);
        if (!jogos.length) {
            alert('Nenhuma aposta válida para enviar.');
            return;
        }
        try {
            sessionStorage.setItem(MANUAL_S10_KEY, JSON.stringify({
                origem: 'gerador_digitos_inteligente',
                replace: false,
                jogos,
                aviso: `Importado do Gerador por Dígitos (${jogos.length} apostas).`,
            }));
        } catch (e) {
            alert('Não foi possível gravar o lote para importação.');
            return;
        }
        const w = window.open(MANUAL_S10_URL, '_blank');
        if (!w) window.location.href = MANUAL_S10_URL;
    }

    function savePoolToStorage(arr) {
        try {
            localStorage.setItem(LS_POOL_KEY, JSON.stringify({
                pool: arr || [],
                dezenas_por_aposta: parseInt(
                    (($(PAGE === 'intel' ? 'ciDezenasAposta' : 'cdDezenasAposta') || {}).value) || PICK_DEFAULT,
                    10
                ),
                ts: Date.now(),
            }));
        } catch (_) { /* ignore */ }
    }

    function loadPoolFromStorage() {
        try {
            const raw = localStorage.getItem(LS_POOL_KEY);
            if (!raw) return null;
            const data = JSON.parse(raw);
            if (!data || !Array.isArray(data.pool)) return null;
            return data;
        } catch (_) {
            return null;
        }
    }

    async function apiGet(path) {
        const r = await fetch(API + path);
        return r.json();
    }
    async function apiPost(path, body) {
        const r = await fetch(API + path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return r.json();
    }

    function downloadTxt(nome, texto) {
        const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nome || 'digitos.txt';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function fmtLinhaAposta(dezenas) {
        return (dezenas || []).map(fmtDez).join(' ');
    }

    function renderListaCombos(apostas, elId, metaId, total, truncado, aviso) {
        const meta = $(metaId);
        const el = $(elId);
        if (meta) {
            if (apostas && apostas.length) {
                meta.className = truncado ? 'small text-warning mb-1' : 'small text-success mb-1';
                meta.textContent = truncado
                    ? (aviso || `Exibindo ${apostas.length.toLocaleString('pt-BR')} de ${total.toLocaleString('pt-BR')} possíveis.`)
                    : `Exibindo ${apostas.length.toLocaleString('pt-BR')} aposta(s) de ${total.toLocaleString('pt-BR')} possíveis.`;
            } else if (truncado) {
                meta.className = 'small text-warning mb-1';
                meta.textContent = aviso || `Há ${total.toLocaleString('pt-BR')} combinações — listagem limitada.`;
            } else {
                meta.className = 'small text-muted mb-1';
                meta.textContent = total
                    ? `${total.toLocaleString('pt-BR')} combinação(ões) possível(is).`
                    : '';
            }
        }
        if (!el) return;
        if (!apostas || !apostas.length) {
            el.innerHTML = truncado
                ? '<span class="text-muted">Nenhuma aposta listada neste recorte.</span>'
                : '';
            return;
        }
        const maxShow = 300;
        const slice = apostas.slice(0, maxShow);
        el.innerHTML = slice.map((ap) =>
            `<div><span class="text-muted">#${ap.linha}</span> ${fmtLinhaAposta(ap.dezenas)}</div>`
        ).join('') + (apostas.length > maxShow
            ? `<div class="text-muted mt-1">… +${apostas.length - maxShow} na lista completa deste lote</div>`
            : '');
    }

    async function listarTodas(poolArr, k, metaId, listaId) {
        const data = await apiPost('/digitos/combinacoes', {
            pool: poolArr,
            dezenas_por_aposta: k,
            incluir_apostas: true,
            exigir_qtd_digitos: exigirQtdAtual(),
        });
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao listar');
            return data;
        }
        renderListaCombos(
            data.apostas,
            listaId,
            metaId,
            data.total_combinacoes || 0,
            data.truncado,
            data.aviso
        );
        return data;
    }

    async function exportar(modo, poolArr, k, apostas) {
        const mesEl = $('ciMesExport');
        const body = {
            modo: modo,
            pool: poolArr,
            dezenas_por_aposta: k,
            apostas: apostas || undefined,
        };
        const exigir = exigirQtdAtual();
        if (exigir) body.exigir_qtd_digitos = exigir;
        if (mesEl && mesEl.value) body.mes_num = mesEl.value;
        const data = await apiPost('/digitos/export-txt', body);
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao exportar');
            return;
        }
        downloadTxt(data.nome_arquivo, data.texto);
    }

    function aplicarPoolCompleto(targetSet) {
        targetSet.clear();
        DIGITOS_TODOS.forEach((d) => targetSet.add(d));
    }

    function aplicarPoolSalvo(targetSet) {
        const stored = loadPoolFromStorage();
        if (!stored || !Array.isArray(stored.pool) || !stored.pool.length) return null;
        const uniq = [];
        const seen = new Set();
        stored.pool.forEach((x) => {
            const d = Number(x);
            if (!Number.isInteger(d) || d < 0 || d > 9 || seen.has(d)) return;
            seen.add(d);
            uniq.push(d);
        });
        // 10 dígitos = universo inteiro: não restaura (é o estado que invertia o clique).
        if (!uniq.length || uniq.length === QTD_DIGITOS_UNIVERSO) return null;
        targetSet.clear();
        uniq.forEach((d) => targetSet.add(d));
        return stored;
    }

    function fillPickSelect(selId, minK, maxK) {
        const sel = $(selId);
        if (!sel) return;
        const lo = Math.max(1, minK != null ? Number(minK) : PICK_MIN);
        const hi = Math.max(lo, maxK != null ? Number(maxK) : PICK_MAX);
        const prev = parseInt(sel.value || '', 10);
        sel.innerHTML = '';
        for (let k = lo; k <= hi; k++) {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k + ' ' + UNIDADE;
            if (k === prev || (!prev && k === PICK_DEFAULT) || (!prev && k === lo && PICK_DEFAULT < lo)) {
                opt.selected = true;
            }
            sel.appendChild(opt);
        }
        if (!sel.value) {
            const prefer = Math.min(Math.max(PICK_DEFAULT, lo), hi);
            sel.value = String(prefer);
        }
    }

    function fillPickSelectDigitosGerar(maxEleg) {
        const hi = Math.max(1, Math.min(PICK_MAX, maxEleg > 0 ? maxEleg : PICK_MAX));
        const sel = $('cdDezenasApostaGerar');
        if (!sel) return;
        const prev = parseInt(sel.value || String(PICK_DEFAULT), 10) || PICK_DEFAULT;
        const next = Math.min(Math.max(1, prev), hi);
        // Só reconstrói se a faixa mudou
        const curMax = sel.options.length ? Number(sel.options[sel.options.length - 1].value) : 0;
        const curMin = sel.options.length ? Number(sel.options[0].value) : 0;
        if (curMin !== 1 || curMax !== hi) {
            sel.innerHTML = '';
            for (let k = 1; k <= hi; k++) {
                const opt = document.createElement('option');
                opt.value = k;
                opt.textContent = k + ' ' + UNIDADE;
                sel.appendChild(opt);
            }
        }
        sel.value = String(next);
        if ($('cdDezenasAposta') && next >= PICK_MIN && next <= PICK_MAX) {
            $('cdDezenasAposta').value = String(next);
        }
    }

    function renderVolante(elId, poolSet, onToggle) {
        const vol = $(elId);
        if (!vol) return;
        vol.innerHTML = '';
        // Sempre desenha os 10 dígitos 0–9 (universo único).
        DIGITOS_TODOS.forEach((d) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'cc-ball' + (poolSet.has(d) ? ' selected' : '');
            btn.textContent = String(d);
            btn.dataset.d = d;
            btn.setAttribute('aria-pressed', poolSet.has(d) ? 'true' : 'false');
            btn.title = poolSet.has(d)
                ? 'Em uso — clique para tirar'
                : 'Clique para USAR este dígito';
            btn.addEventListener('click', () => onToggle(d));
            vol.appendChild(btn);
        });
    }

    function renderTabelaQtd(rows) {
        const tb = $('cdTabelaQtd');
        if (!tb) return;
        tb.innerHTML = (rows || []).map((r) => `
            <tr style="${r.destaque ? 'background:rgba(25,135,84,.12);font-weight:700;' : ''}">
                <td>${r.qtd_digitos}${r.recomendado ? ' ★★' : ''}</td>
                <td>${r.ocorrencias}</td>
                <td>${String(r.pct).replace('.', ',')}%</td>
            </tr>`).join('') || '<tr><td colspan="3">—</td></tr>';
    }

    function renderElegiveis(aval, prefix) {
        const resumo = $(prefix + 'ResumoCombos');
        const elig = $(prefix === 'cd' ? 'cdElegiveis' : null);
        if (resumo) {
            if (!aval || !aval.qtd_pool) {
                resumo.innerHTML =
                    `Selecione dígitos. Para aposta de <strong>${PICK_DEFAULT}</strong> ${UNIDADE}, ` +
                    `o pool precisa liberar ≥ <strong>${PICK_DEFAULT}</strong> elegíveis ` +
                    `(ex.: <strong>0 1 2</strong> ou <strong>1 2 3</strong>).`;
            } else {
                const combos = aval.combinacoes_possiveis != null
                    ? aval.combinacoes_possiveis.toLocaleString('pt-BR')
                    : '0';
                const k = aval.dezenas_por_aposta;
                const n = aval.qtd_elegiveis || 0;
                let extra = '';
                if (!IS_COLUNAS && n > 0 && n < k) {
                    extra =
                        ` <span class="text-danger">· insuficiente: pediu ${k} ${UNIDADE}/aposta, ` +
                        `mas só há ${n} elegível(is) — baixe para ≤ ${n} ou amplie o pool</span>`;
                } else if (aval.pode_gerar || IS_COLUNAS) {
                    extra = ' <span class="text-success">· pode gerar</span>';
                } else {
                    extra = ' <span class="text-danger">· insuficiente para gerar</span>';
                }
                const exigir = aval.exigir_qtd_digitos;
                if (!IS_COLUNAS && exigir && aval.combinacoes_enumeradas) {
                    extra +=
                        ` · <strong>${Number(aval.combinacoes_com_exigir || 0).toLocaleString('pt-BR')}</strong>` +
                        ` com exatamente ${exigir} dígito(s) único(s)`;
                } else if (!IS_COLUNAS && exigir && aval.combinacoes_enumeradas === false) {
                    extra += ` · filtro «exatamente ${exigir} dígitos» será aplicado ao calcular/exportar`;
                }
                resumo.innerHTML =
                    `<strong>${aval.qtd_pool}</strong> dígito(s) · ` +
                    (IS_COLUNAS
                        ? `<strong>${aval.colunas || 7}</strong> ${UNIDADE} · ` +
                          `<strong>${(aval.combinacoes_possiveis || 0).toLocaleString('pt-BR')}</strong> combinações (pool^colunas)`
                        : `<strong>${n}</strong> ${UNIDADE} elegíveis ` +
                          `(só com esses dígitos) · ` +
                          `<strong>${combos}</strong> combinação(ões) C(${n},${k})`) +
                    extra;
            }
        }
        if (elig) {
            elig.innerHTML = (aval && aval.elegiveis || []).map((n) =>
                `<span class="badge bg-success">${fmtDez(n)}</span>`
            ).join(' ') || '<span class="text-muted">Nenhuma dezena do universo usa só esses dígitos.</span>';
        }
        const aviso = $(prefix === 'cd' ? 'cdAvisoRec' : 'ciAviso');
        if (!aviso) return;

        const n = (aval && aval.qtd_elegiveis) || 0;
        const k = (aval && aval.dezenas_por_aposta) || PICK_DEFAULT;
        const pode = !!(aval && aval.pode_gerar);

        if (!aval || !aval.qtd_pool) {
            aviso.className = 'small text-muted';
            aviso.textContent = 'Clique para MARCAR os dígitos que entram (cinza = fora, laranja = usa). Ex.: 0 1 2 3 4 6.';
        } else if (!IS_COLUNAS && !pode) {
            aviso.className = 'small text-danger';
            aviso.innerHTML =
                `<strong>Insuficiente:</strong> ${n} elegível(is) para aposta de ${k}. ` +
                `Ex.: <strong>1 2 3</strong> → 11 12 13 21 22 23 31 (7) · ` +
                `<strong>0 2 3</strong> → só 6 (aí falta dígito ou baixe dezenas/aposta).`;
        } else if (!IS_COLUNAS && pode && n >= k) {
            aviso.className = 'small text-success';
            aviso.innerHTML =
                `<strong>OK para gerar</strong> · ${n} elegíveis · C(${n},${k})=` +
                `${(aval.combinacoes_possiveis || 0).toLocaleString('pt-BR')}` +
                (aval.abaixo_recomendado
                    ? ` <span class="text-muted">(dica: pools com ≥ ${MIN_REC} dígitos costumam ter mais opções)</span>`
                    : '');
        } else if (IS_COLUNAS && pode) {
            aviso.className = 'small text-success';
            aviso.textContent = 'OK para gerar (Super Sete posicional).';
        } else {
            aviso.className = 'small text-muted';
            aviso.textContent = '';
        }

        if (prefix === 'cd' && aval && aval.qtd_elegiveis != null) {
            const cur = kApostaAba2() || PICK_DEFAULT;
            const nEleg = Number(aval.qtd_elegiveis) || 0;
            // Não reduz k enquanto o pool está sendo montado (0 → 3 elegíveis
            // não pode derrubar 7 dezenas para 3). Só amplia a faixa do select.
            fillPickSelectDigitosGerar(Math.max(nEleg, cur, PICK_DEFAULT));
        }
    }

    let avalSeq = 0;

    async function avaliar(poolArr, k, prefix) {
        const seq = ++avalSeq;
        const exigir = exigirQtdAtual();
        const data = await apiPost('/digitos/avaliar', {
            pool: poolArr,
            dezenas_por_aposta: k,
            exigir_qtd_digitos: exigir,
        });
        if (seq !== avalSeq) return data;
        if (data.sucesso) {
            renderElegiveis(data, prefix);
            if (prefix === 'ci') ultimaAvalIntel = data;
        }
        return data;
    }

    function resetCdComboFase() {
        cdComboFase = 0;
        cdUltimaAval = null;
        const btn = $('cdBtnCalcularMostrar');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-calculator"></i> Calcular combinações';
            btn.classList.remove('btn-success');
            btn.classList.add('btn-primary');
        }
        const msg = $('cdComboFaseMsg');
        if (msg) {
            msg.classList.add('d-none');
            msg.innerHTML = '';
        }
        const lista = $('cdCombosLista');
        if (lista) lista.innerHTML = '';
        const meta = $('cdCombosMeta');
        if (meta) {
            meta.className = 'small text-muted mb-1';
            meta.textContent = '';
        }
    }

    function qtdApostasDesejada() {
        const n = parseInt(($('cdQtdApostas') || {}).value || '10', 10);
        if (!Number.isFinite(n) || n < 1) return 10;
        return Math.min(2000, n);
    }

    function kApostaAba2() {
        const a = parseInt(($('cdDezenasApostaGerar') || {}).value || '', 10);
        const b = parseInt(($('cdDezenasAposta') || {}).value || '', 10);
        return a || b || PICK_DEFAULT;
    }

    function syncKSelects(fromId) {
        const k = parseInt(($(fromId) || {}).value || PICK_DEFAULT, 10);
        ['cdDezenasAposta', 'cdDezenasApostaGerar'].forEach((id) => {
            if (id === fromId) return;
            const el = $(id);
            if (el) el.value = String(k);
        });
    }

    async function calcularOuMostrarCombos() {
        const arr = [...poolAba2].sort((a, b) => a - b);
        let k = kApostaAba2();
        const qtd = qtdApostasDesejada();
        const msg = $('cdComboFaseMsg');
        const btn = $('cdBtnCalcularMostrar');
        if (!arr.length) {
            alert('Selecione ao menos 1 dígito no pool.');
            return;
        }

        if (cdComboFase === 0) {
            let aval = await avaliar(arr, k, 'cd');
            if (!aval || !aval.sucesso) {
                alert((aval && aval.erro) || 'Não foi possível calcular as combinações.');
                return;
            }
            const eleg = Number(aval.qtd_elegiveis) || 0;
            const elegFmt = (aval.elegiveis || []).map(fmtDez).join(' ');
            if (eleg < 1) {
                if (msg) {
                    msg.classList.remove('d-none', 'alert-success');
                    msg.classList.add('alert-warning');
                    msg.innerHTML =
                        `Com os dígitos <strong>[${arr.join(', ')}]</strong> não há dezena no universo ` +
                        `usando somente esses dígitos.`;
                }
                return;
            }
            // Ajusta k se maior que elegíveis (ex.: 7 pedidas, só 6 dezenas)
            if (k > eleg) {
                k = eleg;
                if ($('cdDezenasApostaGerar')) $('cdDezenasApostaGerar').value = String(k);
                aval = await avaliar(arr, k, 'cd');
            }
            cdUltimaAval = aval;
            const exigir = exigirQtdAtual();
            const bruto = Number(aval.combinacoes_possiveis) || 0;
            const filtrado = (exigir && aval.combinacoes_enumeradas)
                ? Number(aval.combinacoes_com_exigir || 0)
                : bruto;
            const total = filtrado;
            if (msg) {
                msg.classList.remove('d-none', 'alert-warning', 'alert-success');
                msg.classList.add(total > 0 ? 'alert-success' : 'alert-warning');
                let html =
                    `Dígitos <strong>[${arr.join(', ')}]</strong> → dezenas elegíveis: ` +
                    `<strong>${elegFmt}</strong> (${eleg}). ` +
                    `Com <strong>${k}</strong> ${UNIDADE} por aposta: ` +
                    `<strong>${bruto.toLocaleString('pt-BR')}</strong> combinação(ões) C(${eleg},${k}).`;
                if (exigir && aval.combinacoes_enumeradas) {
                    html +=
                        ` Destas, <strong>${filtrado.toLocaleString('pt-BR')}</strong> usam ` +
                        `exatamente <strong>${exigir}</strong> dígito(s) único(s).`;
                } else if (exigir) {
                    html += ` Filtro «exatamente ${exigir} dígitos» será aplicado ao mostrar/exportar.`;
                }
                html += total > 0
                    ? ` Clique de novo para mostrar até <strong>${qtd}</strong> aposta(s).`
                    : ` Aumente o pool, mude a exigência ou reduza as dezenas por aposta.`;
                msg.innerHTML = html;
            }
            if (btn && total > 0) {
                btn.innerHTML = `<i class="fas fa-th-list"></i> Mostrar ${qtd} aposta(s)`;
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-success');
                cdComboFase = 1;
            } else if (btn) {
                btn.innerHTML = '<i class="fas fa-calculator"></i> Calcular combinações';
                btn.classList.remove('btn-success');
                btn.classList.add('btn-primary');
                cdComboFase = 0;
            }
            return;
        }

        // Fase 2 — mostrar apostas (limite = qtd escolhida)
        k = kApostaAba2();
        const data = await apiPost('/digitos/combinacoes', {
            pool: arr,
            dezenas_por_aposta: k,
            incluir_apostas: true,
            limite: qtd,
            exigir_qtd_digitos: exigirQtdAtual(),
        });
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao listar apostas.');
            return;
        }
        renderListaCombos(
            data.apostas,
            'cdCombosLista',
            'cdCombosMeta',
            data.total_combinacoes || 0,
            data.truncado,
            data.aviso
        );
        const mostradas = (data.apostas || []).length;
        const total = Number(data.total_combinacoes) || 0;
        if (msg) {
            msg.classList.remove('d-none', 'alert-warning');
            msg.classList.add('alert-success');
            msg.innerHTML =
                `Mostrando <strong>${mostradas.toLocaleString('pt-BR')}</strong> de ` +
                `<strong>${total.toLocaleString('pt-BR')}</strong> combinação(ões) ` +
                (exigirQtdAtual()
                    ? `com exatamente ${exigirQtdAtual()} dígito(s) único(s) `
                    : '') +
                `(dezenas só com os dígitos [${arr.join(', ')}]).`;
        }
        if (btn) {
            btn.innerHTML = '<i class="fas fa-calculator"></i> Calcular combinações';
            btn.classList.remove('btn-success');
            btn.classList.add('btn-primary');
        }
        cdComboFase = 0;
    }

    function renderLoteAba2(apostas) {
        const el = $('cdLoteLista');
        const resumo = $('cdLoteResumo');
        const selOrd = $('cdOrdenarLote');
        const has = !!(apostas && apostas.length);
        if ($('cdBtnVariar')) $('cdBtnVariar').disabled = !has;
        if ($('cdBtnExportLote')) $('cdBtnExportLote').disabled = !has;
        if (selOrd) selOrd.disabled = !has;
        if (!el) return;
        if (!has) {
            el.innerHTML = '';
            if (resumo) {
                resumo.classList.add('d-none');
                resumo.innerHTML = '';
            }
            return;
        }
        const modo = (selOrd && selOrd.value) || 'geracao';
        const built = htmlTabelaLote(apostas, modo);
        if (resumo) {
            resumo.classList.remove('d-none');
            resumo.innerHTML = built.resumoHtml;
        }
        el.innerHTML = built.tableHtml;
    }

    async function gerarLoteAba2() {
        const arr = [...poolAba2].sort((a, b) => a - b);
        const st = $('cdLoteStatus');
        if (!arr.length) {
            alert('Selecione o pool de dígitos.');
            return;
        }
        const k = kApostaAba2();
        const qtd = Math.min(20, qtdApostasDesejada());
        if (st) {
            st.className = 'small text-muted mb-1';
            st.textContent = 'Gerando apostas…';
        }
        const data = await apiPost('/digitos/gerar', {
            pool: arr,
            dezenas_por_aposta: k,
            qtd_apostas: qtd,
            modo: 'frequencia',
            exigir_qtd_digitos: exigirQtdAtual(),
            salvar_sessao: false,
        });
        if (!data || !data.sucesso) {
            if (st) {
                st.className = 'small text-danger mb-1';
                st.textContent = formatErroGeracao(data || { erro: 'Falha ao gerar.' });
            }
            ultimoLoteAba2 = [];
            renderLoteAba2([]);
            return;
        }
        ultimoLoteAba2 = data.apostas || [];
        if (st) {
            st.className = 'small text-success mb-1';
            st.textContent =
                `${ultimoLoteAba2.length} aposta(s) só com os dígitos [${arr.join(', ')}]` +
                (exigirQtdAtual() ? ` · exatamente ${exigirQtdAtual()} dígitos únicos` : '') +
                (data.aviso ? ` · ${data.aviso}` : '');
        }
        renderLoteAba2(ultimoLoteAba2);
    }

    async function variarLoteAba2() {
        const arr = [...poolAba2].sort((a, b) => a - b);
        const st = $('cdLoteStatus');
        if (!ultimoLoteAba2.length) {
            alert('Gere as apostas antes das variações.');
            return;
        }
        if (st) {
            st.className = 'small text-muted mb-1';
            st.textContent = 'Gerando variações…';
        }
        const data = await apiPost('/digitos/refinar', {
            pool: arr,
            dezenas_por_aposta: kApostaAba2(),
            apostas: ultimoLoteAba2,
            exigir_qtd_digitos: exigirQtdAtual(),
            modo: 'inteligente',
            intensidade: ($('cdVarIntensidade') || {}).value || 'leve',
            variacoes: parseInt(($('cdVarQtd') || {}).value || '1', 10),
            distancia: 'media',
        });
        if (!data || !data.sucesso) {
            if (st) {
                st.className = 'small text-danger mb-1';
                st.textContent = (data && data.erro) || 'Falha ao variar.';
            }
            return;
        }
        ultimoLoteAba2 = data.apostas || [];
        if (st) {
            st.className = 'small text-success mb-1';
            st.textContent =
                `${ultimoLoteAba2.length} variação(ões) · ainda só com os dígitos [${arr.join(', ')}]`;
        }
        renderLoteAba2(ultimoLoteAba2);
    }

    function syncAba2() {
        const arr = [...poolAba2].sort((a, b) => a - b);
        renderVolante('cdVolante', poolAba2, (d) => {
            if (poolAba2.has(d)) poolAba2.delete(d);
            else poolAba2.add(d);
            syncAba2();
        });
        const cont = $('cdContador');
        if (cont) cont.textContent = `${arr.length}/10`;
        const info = $('cdPoolInfo');
        if (info) {
            info.textContent = arr.length
                ? `Pool: ${arr.join(', ')}`
                : 'Nenhum dígito selecionado';
        }
        savePoolToStorage(arr);
        atualizarOpcoesExigir(arr.length);
        resetCdComboFase();
        ultimoLoteAba2 = [];
        const stLote = $('cdLoteStatus');
        if (stLote) {
            stLote.className = 'small mb-1';
            stLote.textContent = '';
        }
        renderLoteAba2([], 'apostas');
        const k = kApostaAba2();
        avaliar(arr, k, 'cd');
    }

    function syncIntel() {
        const arr = [...poolIntel].sort((a, b) => a - b);
        renderVolante('ciVolante', poolIntel, (d) => {
            if (poolIntel.has(d)) poolIntel.delete(d);
            else poolIntel.add(d);
            syncIntel();
        });
        savePoolToStorage(arr);
        const k = parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10);
        avaliar(arr, k, 'ci').then(() => diagnosticarIntel(true));
    }

    async function carregarGuia() {
        const data = await apiGet('/digitos/guia');
        if (!data.sucesso) {
            if ($('cdGuiaHistorico')) $('cdGuiaHistorico').textContent = data.erro || 'Erro';
            if ($('ciInsights')) $('ciInsights').textContent = data.erro || 'Erro';
            return;
        }
        guiaCache = data;
        ultimoSorteioDz = Array.isArray(data.ultimo_dezenas)
            ? data.ultimo_dezenas.map(Number).filter(Number.isFinite)
            : [];
        if ($('cdGuiaHistorico')) {
            $('cdGuiaHistorico').innerHTML =
                `<strong>★★ Recomendado:</strong> ${data.qtd_recomendada} dígitos distintos ` +
                `(${String(data.qtd_recomendada_pct).replace('.', ',')}%) · ` +
                `dígito +sai: <strong>${data.digito_mais_frequente}</strong> · ` +
                `−sai: <strong>${data.digito_menos_frequente}</strong> · ` +
                `concursos: ${data.total_concursos}`;
        }
        renderTabelaQtd(data.resumo_por_quantidade);
        if ($('ciInsights')) {
            const top = (data.painel_digitos || []).slice(0, 3)
                .map((p) => `${p.digito} (${String(p.pct).replace('.', ',')}%)`).join(', ');
            const ultFmt = data.ultimo_dezenas_fmt || '';
            $('ciInsights').innerHTML =
                `Moda histórica: <strong>${data.qtd_recomendada}</strong> dígitos ` +
                `(${String(data.qtd_recomendada_pct).replace('.', ',')}%) · ` +
                `Top presença: ${top} · ` +
                `Ausentes no último: ${(data.digitos_ausentes_ultimo || []).join(', ') || '—'}` +
                (ultFmt
                    ? ` · Último c.<strong>${data.ultimo_concurso}</strong>: ${ultFmt}`
                    : '') +
                ` · <a href="${PADROES_II_URL}" target="_blank" rel="noopener">Padrões II</a>`;
        }
        if (ultimoLote.length) renderLoteIntel(ultimoLote);
    }

    async function sugerir(target, criterio, qtd) {
        const data = await apiGet(`/digitos/sugerir?criterio=${criterio}&quantidade=${qtd || MIN_REC}`);
        if (!data.sucesso) {
            alert(data.erro || 'Erro');
            return;
        }
        const set = target === 'aba2' ? poolAba2 : poolIntel;
        set.clear();
        (data.pool || []).forEach((d) => set.add(d));
        if (target === 'aba2') syncAba2();
        else syncIntel();
    }

    async function salvarAba2() {
        const arr = [...poolAba2].sort((a, b) => a - b);
        if (!arr.length) {
            alert('Selecione ao menos 1 dígito.');
            return;
        }
        if (arr.length < MIN_REC) {
            if (!confirm(`Pool com ${arr.length} dígito(s) — abaixo do recomendado (${MIN_REC}). Salvar mesmo assim?`)) {
                return;
            }
        }
        const data = await apiPost('/digitos/sessao', {
            nome: ($('cdNomeSessao') || {}).value || '',
            pool: arr,
            dezenas_por_aposta: parseInt(($('cdDezenasAposta') || {}).value || PICK_DEFAULT, 10),
            origem_conjunto: 'manual',
            sessao_id: sessaoDigitos ? sessaoDigitos.id : null,
        });
        const st = $('cdSessaoStatus');
        if (!data.sucesso) {
            if (st) {
                st.className = 'mt-2 small text-danger';
                st.textContent = data.erro || 'Erro';
            }
            return;
        }
        sessaoDigitos = data.sessao;
        savePoolToStorage(arr);
        if (st) {
            st.className = 'mt-2 small text-success';
            st.textContent = `Sessão #${sessaoDigitos.id} salva — pool [${arr.join(', ')}]`;
        }
        carregarSessoesDigitos();
    }

    async function carregarSessoesDigitos() {
        const sel = $('cdSelectSessao');
        if (!sel) return;
        const data = await apiGet('/digitos/sessoes');
        sel.innerHTML = '<option value="">— sessões salvas —</option>';
        (data.sessoes || []).forEach((s) => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `#${s.id} ${s.nome} (${(s.conjunto_base || []).join(',')})`;
            sel.appendChild(opt);
        });
    }

    function formatErroGeracao(data) {
        let msg = data.erro || 'Erro';
        const diag = data.diagnostico || {};
        const hints = diag.sugestoes || [];
        if (hints.length) {
            msg += ' — Sugestões: ' + hints.join(' ');
        }
        return msg;
    }

    function selExigir() {
        return PAGE === 'intel' ? $('ciExigirQtd') : $('cdExigirQtd');
    }

    function exigirQtdAtual() {
        const raw = (selExigir() || {}).value || '';
        if (!raw || raw === '0') return null;
        const n = parseInt(raw, 10);
        return Number.isFinite(n) && n >= EXIGIR_QTD_MIN ? n : null;
    }

    function atualizarOpcoesExigir(poolSize) {
        const sel = selExigir();
        if (!sel) return null;
        const prev = sel.value;
        const keep = prev && parseInt(prev, 10) >= EXIGIR_QTD_MIN && parseInt(prev, 10) <= EXIGIR_QTD_MAX
            ? prev
            : '';

        const precisaRebuild =
            sel.options.length !== (EXIGIR_QTD_MAX - EXIGIR_QTD_MIN + 2) ||
            !sel.querySelector('option[value="' + EXIGIR_QTD_MIN + '"]');

        if (precisaRebuild) {
            sel.innerHTML = '';
            const optNone = document.createElement('option');
            optNone.value = '';
            optNone.textContent = 'Não exigir';
            sel.appendChild(optNone);
            for (let n = EXIGIR_QTD_MIN; n <= EXIGIR_QTD_MAX; n++) {
                const opt = document.createElement('option');
                opt.value = String(n);
                opt.textContent = String(n);
                sel.appendChild(opt);
            }
        }

        // Aviso se a exigência for maior que o subconjunto marcado no pool (0–9)
        const pSize = Number(poolSize) || 0;
        Array.from(sel.options).forEach((opt) => {
            if (!opt.value) {
                opt.title = '';
                opt.style.color = '';
                return;
            }
            const n = parseInt(opt.value, 10);
            const acimaPool = pSize > 0 && n > pSize;
            opt.title = acimaPool
                ? `Impossível com só ${pSize} dígito(s) marcados — marque mais dígitos (universo 0–9)`
                : (n === pSize
                    ? 'Exatamente os dígitos marcados no pool (todos aparecem)'
                    : '');
            opt.style.color = acimaPool ? '#adb5bd' : '';
        });

        sel.value = keep;
        if (prev && prev !== keep) return prev;
        return null;
    }

    async function diagnosticarIntel(silencioso) {
        const arr = [...poolIntel].sort((a, b) => a - b);
        const box = $('ciDiagPrev');
        const st = $('ciStatus');
        const exigInvalidPrev = atualizarOpcoesExigir(arr.length);
        if (!arr.length) {
            if (box) {
                box.className = 'small text-muted mb-2';
                box.classList.remove('d-none');
                box.textContent = 'Selecione o pool para habilitar «Exigir qtd dígitos».';
            }
            return null;
        }
        const exigirRaw = ($('ciExigirQtd') || {}).value;
        if (box && exigInvalidPrev) {
            box.className = 'small text-warning mb-2';
            box.classList.remove('d-none');
            box.textContent =
                `Exigência ${exigInvalidPrev} era impossível com pool de ${arr.length} dígito(s) — ajustada. ` +
                `Máximo disponível: ${arr.length}.`;
        }
        const data = await apiPost('/digitos/diagnosticar', {
            pool: arr,
            dezenas_por_aposta: parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10),
            qtd_apostas: parseInt(($('ciQtdApostas') || {}).value || 10, 10),
            exigir_qtd_digitos: exigirRaw || null,
        });
        if (!data.sucesso) return data;
        if (box) {
            if (data.ok) {
                if (exigInvalidPrev) {
                    // mantém o aviso de ajuste
                } else if (exigirRaw) {
                    box.className = 'small text-success mb-2';
                    box.classList.remove('d-none');
                    box.textContent =
                        `Filtros OK · ${arr.length} dígito(s) únicos marcados (universo 0–9).`;
                } else {
                    box.className = 'small text-muted mb-2';
                    box.classList.remove('d-none');
                    box.textContent =
                        IS_COLUNAS
                            ? `Super Sete: pool 0–9 nas 7 colunas (repetição livre). Marcados: ${arr.length}/10.`
                            : `10 dígitos únicos (0–9) formam as dezenas (ex.: 09, 22, 34). Marcados: ${arr.length}/10.`;
                }
            } else {
                box.className = 'small text-danger mb-2';
                box.classList.remove('d-none');
                const hints = (data.sugestoes || []).slice(0, 2).join(' ');
                box.textContent = (data.mensagem || 'Filtros incompatíveis.') +
                    (hints ? ' ' + hints : '');
            }
        }
        if (!silencioso && !data.ok && st) {
            st.className = 'mt-2 small text-danger';
            st.textContent = formatErroGeracao({ erro: data.mensagem, diagnostico: data });
        }
        return data;
    }

    async function gerarIntel() {
        const arr = [...poolIntel].sort((a, b) => a - b);
        const st = $('ciStatus');
        const btn = $('ciBtnGerar');
        if (!arr.length) {
            alert('Selecione o pool de dígitos.');
            return;
        }
        if (btn) btn.disabled = true;
        try {
            const k = parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            // Avaliação fresca do pool atual (evita confirm/bloqueio com dados antigos)
            const avalFresh = await avaliar(arr, k, 'ci');
            if (avalFresh && avalFresh.sucesso && !avalFresh.pode_gerar && !IS_COLUNAS) {
                const n = Number(avalFresh.qtd_elegiveis) || 0;
                if (st) {
                    st.className = 'mt-2 small text-danger';
                    st.textContent =
                        `Não dá para montar aposta de ${k} com só ${n} dezena(s) elegível(is) ` +
                        `no pool [${arr.join(', ')}]. Amplie o pool ou reduza dezenas/aposta.`;
                }
                return;
            }

            const diag = await diagnosticarIntel(true);
            if (diag && diag.sucesso !== false && diag.ok === false) {
                if (st) {
                    st.className = 'mt-2 small text-danger';
                    st.textContent = formatErroGeracao({ erro: diag.mensagem, diagnostico: diag });
                }
                return;
            }
            if (st) {
                st.className = 'mt-2 small text-muted';
                st.textContent = 'Gerando…';
            }
            const exigirRaw = ($('ciExigirQtd') || {}).value;
            const body = {
                pool: arr,
                dezenas_por_aposta: k,
                qtd_apostas: parseInt(($('ciQtdApostas') || {}).value || 10, 10),
                modo: ($('ciModo') || {}).value || 'frequencia',
                // "" ou "0" = não exigir (0 dígitos é impossível)
                exigir_qtd_digitos: (exigirRaw && exigirRaw !== '0') ? exigirRaw : null,
                salvar_sessao: !!( $('ciSalvarSessao') && $('ciSalvarSessao').checked ),
                nome: ($('ciNomeSessao') || {}).value || '',
            };
            const data = await apiPost('/digitos/gerar', body);
            if (!data || !data.sucesso) {
                if (st) {
                    st.className = 'mt-2 small text-danger';
                    st.textContent = formatErroGeracao(data || { erro: 'Falha na geração.' });
                }
                return;
            }
            if (st) {
                st.className = 'mt-2 small text-success';
                const aval = data.avaliacao || {};
                ultimaAvalIntel = aval;
                st.textContent =
                    `${data.qtd_geradas} aposta(s) · ${aval.qtd_elegiveis} elegíveis · ` +
                    `${(aval.combinacoes_possiveis || 0).toLocaleString('pt-BR')} combinações possíveis` +
                    (data.aviso ? ` · ${data.aviso}` : '');
            }
            ultimoLote = data.apostas || [];
            try {
                renderLoteIntel(ultimoLote);
            } catch (errRender) {
                if (st) {
                    st.className = 'mt-2 small text-warning';
                    st.textContent =
                        `Gerou ${ultimoLote.length} aposta(s), mas a tabela falhou: ` +
                        (errRender && errRender.message ? errRender.message : errRender);
                }
                console.error('renderLoteIntel', errRender);
            }
        } catch (err) {
            if (st) {
                st.className = 'mt-2 small text-danger';
                st.textContent = 'Erro ao gerar: ' + (err && err.message ? err.message : String(err));
            }
            console.error('gerarIntel', err);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function importarPoolDoConstrutor() {
        const data = loadPoolFromStorage();
        if (!data || !data.pool || !data.pool.length) {
            alert('Nenhum pool salvo no Construtor. Abra a aba Pool de Dígitos, selecione os dígitos e volte aqui.');
            return;
        }
        poolIntel.clear();
        data.pool.forEach((d) => poolIntel.add(Number(d)));
        if ($('ciDezenasAposta') && data.dezenas_por_aposta) {
            $('ciDezenasAposta').value = String(data.dezenas_por_aposta);
        }
        syncIntel();
    }

    function bindConstrutor() {
        fillPickSelect('cdDezenasAposta', PICK_MIN, PICK_MAX);
        fillPickSelect('cdDezenasApostaGerar', 1, PICK_MAX);
        $('cdDezenasAposta')?.addEventListener('change', () => {
            syncKSelects('cdDezenasAposta');
            syncAba2();
        });
        $('cdDezenasApostaGerar')?.addEventListener('change', () => {
            syncKSelects('cdDezenasApostaGerar');
            syncAba2();
        });
        $('cdExigirQtd')?.addEventListener('change', () => { syncAba2(); });
        $('cdBtnExatoPool')?.addEventListener('click', () => {
            const n = poolAba2.size;
            if (n < 1) {
                alert('Selecione o pool de dígitos.');
                return;
            }
            if (n > EXIGIR_QTD_MAX) {
                alert('O filtro aceita no máximo 9 dígitos distintos por aposta.');
                return;
            }
            atualizarOpcoesExigir(n);
            if ($('cdExigirQtd')) $('cdExigirQtd').value = String(n);
            syncAba2();
        });
        $('cdQtdApostas')?.addEventListener('change', () => {
            if (cdComboFase === 1) {
                const qtd = qtdApostasDesejada();
                const btn = $('cdBtnCalcularMostrar');
                if (btn) btn.innerHTML = `<i class="fas fa-th-list"></i> Mostrar ${qtd} aposta(s)`;
            }
        });

        $('cdBtnFreq')?.addEventListener('click', () => sugerir('aba2', 'frequencia', MIN_REC));
        $('cdBtnAtraso')?.addEventListener('click', () => sugerir('aba2', 'atraso', MIN_REC));
        $('cdBtnPares')?.addEventListener('click', () => sugerir('aba2', 'pares', 5));
        $('cdBtnImpares')?.addEventListener('click', () => sugerir('aba2', 'impares', 5));
        $('cdBtnTodos')?.addEventListener('click', () => {
            aplicarPoolCompleto(poolAba2);
            syncAba2();
        });
        $('cdBtnLimpar')?.addEventListener('click', () => { poolAba2.clear(); syncAba2(); });
        $('cdBtnSalvar')?.addEventListener('click', salvarAba2);

        $('cdBtnCalcularMostrar')?.addEventListener('click', calcularOuMostrarCombos);
        $('cdBtnGerarLote')?.addEventListener('click', gerarLoteAba2);
        $('cdBtnVariar')?.addEventListener('click', variarLoteAba2);
        $('cdBtnExportLote')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = kApostaAba2();
            if (!ultimoLoteAba2.length) {
                alert('Gere as apostas antes de exportar o lote.');
                return;
            }
            exportar('lote', arr, k, ultimoLoteAba2);
        });
        $('cdOrdenarLote')?.addEventListener('change', () => {
            if (ultimoLoteAba2.length) renderLoteAba2(ultimoLoteAba2);
        });
        $('cdBtnExportTodas')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = kApostaAba2();
            if (!arr.length) { alert('Selecione o pool.'); return; }
            exportar('todas', arr, k);
        });
        $('cdBtnExportElegiveis')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = kApostaAba2();
            if (!arr.length) { alert('Selecione o pool.'); return; }
            exportar('elegiveis', arr, k);
        });

        $('cdSelectSessao')?.addEventListener('change', function () {
            const id = this.value;
            if (!id) return;
            apiGet('/sessao/' + id).then((data) => {
                if (!data.sucesso || !data.sessao) return;
                if ((data.sessao.tipo_universo || 'dezenas') !== 'digitos') {
                    alert('Sessão não é do tipo dígitos.');
                    return;
                }
                sessaoDigitos = data.sessao;
                poolAba2.clear();
                (data.sessao.conjunto_base || []).forEach((d) => poolAba2.add(Number(d)));
                if ($('cdNomeSessao')) $('cdNomeSessao').value = data.sessao.nome || '';
                if (data.sessao.dezenas_por_aposta) {
                    const kv = String(data.sessao.dezenas_por_aposta);
                    if ($('cdDezenasAposta')) $('cdDezenasAposta').value = kv;
                    if ($('cdDezenasApostaGerar')) $('cdDezenasApostaGerar').value = kv;
                }
                syncAba2();
            });
        });

        $('cdBtnIrGerador')?.addEventListener('click', () => {
            savePoolToStorage([...poolAba2].sort((a, b) => a - b));
        });

        $('ccTabDigitos')?.addEventListener('shown.bs.tab', () => {
            if (!guiaCache) carregarGuia();
            syncAba2();
            carregarSessoesDigitos();
        });

        carregarGuia();
        // Começa vazio: clique MARCA o dígito. Não inicia com 0–9 ligados
        // (isso fazia o clique parecer «ao contrário»). Restaura só pool parcial.
        const storedCd = aplicarPoolSalvo(poolAba2);
        if (storedCd && storedCd.dezenas_por_aposta) {
            const kv = String(storedCd.dezenas_por_aposta);
            if ($('cdDezenasAposta')) $('cdDezenasAposta').value = kv;
            if ($('cdDezenasApostaGerar')) $('cdDezenasApostaGerar').value = kv;
        }
        try { localStorage.removeItem('cc_digitos_pool_v2'); } catch (_) { /* ignore */ }
        syncAba2();
        carregarSessoesDigitos();
    }

    function bindIntel() {
        fillPickSelect('ciDezenasAposta');
        $('ciDezenasAposta')?.addEventListener('change', syncIntel);
        $('ciExigirQtd')?.addEventListener('change', () => diagnosticarIntel(true));
        $('ciQtdApostas')?.addEventListener('change', () => diagnosticarIntel(true));

        $('ciBtnFreq')?.addEventListener('click', () => sugerir('intel', 'frequencia', MIN_REC));
        $('ciBtnAtraso')?.addEventListener('click', () => sugerir('intel', 'atraso', MIN_REC));
        $('ciBtnTodos')?.addEventListener('click', () => {
            aplicarPoolCompleto(poolIntel);
            syncIntel();
        });
        $('ciBtnLimpar')?.addEventListener('click', () => { poolIntel.clear(); syncIntel(); });
        $('ciBtnCopiarAba2')?.addEventListener('click', importarPoolDoConstrutor);
        $('ciBtnGerar')?.addEventListener('click', gerarIntel);
        $('ciBtnEnviarManual')?.addEventListener('click', enviarLoteParaManual);
        $('ciOrdenarLote')?.addEventListener('change', () => {
            if (ultimoLote.length) renderLoteIntel(ultimoLote);
        });

        $('ciBtnExportLote')?.addEventListener('click', () => {
            const arr = [...poolIntel].sort((a, b) => a - b);
            const k = parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            if (!ultimoLote.length) { alert('Gere o lote antes de exportar.'); return; }
            exportar('lote', arr, k, ultimoLote);
        });
        $('ciBtnExportTodas')?.addEventListener('click', () => {
            const arr = [...poolIntel].sort((a, b) => a - b);
            const k = parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            if (!arr.length) { alert('Selecione o pool.'); return; }
            exportar('todas', arr, k);
        });
        $('ciBtnListarTodas')?.addEventListener('click', () => {
            const arr = [...poolIntel].sort((a, b) => a - b);
            const k = parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            if (!arr.length) { alert('Selecione o pool.'); return; }
            listarTodas(arr, k, 'ciCombosMeta', 'ciCombosLista');
        });

        // Mesma regra do Construtor: vazio até o usuário marcar (ou restaurar pool parcial).
        const stored = aplicarPoolSalvo(poolIntel);
        if (stored && $('ciDezenasAposta') && stored.dezenas_por_aposta) {
            $('ciDezenasAposta').value = String(stored.dezenas_por_aposta);
        }
        try {
            localStorage.removeItem('cc_digitos_pool_v1');
            localStorage.removeItem('cc_digitos_pool_v2');
        } catch (_) { /* ignore */ }

        carregarGuia();
        syncIntel();
        if (HAS_MES && window.MesSorteSelect && $('ciMesExport')) {
            MesSorteSelect.fillFromApi($('ciMesExport'), API, { defaultPrefer: 'atrasado' }).catch(() => {});
        }
    }

    function bind() {
        if (PAGE === 'intel') bindIntel();
        else bindConstrutor();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bind);
    } else {
        bind();
    }
})();
