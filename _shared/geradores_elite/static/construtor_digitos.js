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
    const MIN_REC = UI.positional ? 1 : 4;
    const LS_POOL_KEY = 'cc_digitos_pool_v2';
    /** Universo fixo: 10 dígitos únicos (0–9). Em Super Sete = candidatos das colunas. */
    const DIGITOS_TODOS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
    const QTD_DIGITOS_UNIVERSO = DIGITOS_TODOS.length; // 10
    /** Faixa do filtro «Exigir qtd dígitos na aposta» — alinhada aos dígitos únicos 0–9. */
    const EXIGIR_QTD_MIN = 0;
    const EXIGIR_QTD_MAX = 9;
    const PAD_WIDTH = Number(UI.pad_width) > 0 ? Number(UI.pad_width) : 2;
    const IS_COLUNAS = !!(UI.positional || UI.export_is_columns || UI.modality_key === 'supersete');
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

    window.__CC_POOL_DIGITOS_ABA2__ = () => [...poolAba2].sort((a, b) => a - b);

    /** Formata valor da aposta: Super Sete = dígito "0"…"9"; demais = dezena "01"…"60". */
    function fmtDez(n) {
        const v = Number(n);
        if (!Number.isFinite(v)) return String(n);
        if (PAD_WIDTH <= 1 || IS_COLUNAS) return String(v);
        return String(v).padStart(PAD_WIDTH, '0');
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
            if (truncado) {
                meta.className = 'small text-warning mb-1';
                meta.textContent = aviso || `Há ${total} combinações — listagem limitada. Use Exportar todas se couber no limite.`;
            } else if (apostas && apostas.length) {
                meta.className = 'small text-success mb-1';
                meta.textContent = `Exibindo ${apostas.length.toLocaleString('pt-BR')} aposta(s) de ${total.toLocaleString('pt-BR')} possíveis.`;
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
                ? '<span class="text-muted">Lista omitida (volume alto). Use <strong>Exportar todas .TXT</strong>.</span>'
                : '';
            return;
        }
        const maxShow = 300;
        const slice = apostas.slice(0, maxShow);
        el.innerHTML = slice.map((ap) =>
            `<div><span class="text-muted">#${ap.linha}</span> ${fmtLinhaAposta(ap.dezenas)}</div>`
        ).join('') + (apostas.length > maxShow
            ? `<div class="text-muted mt-1">… +${apostas.length - maxShow} na exportação completa</div>`
            : '');
    }

    async function listarTodas(poolArr, k, metaId, listaId) {
        const data = await apiPost('/digitos/combinacoes', {
            pool: poolArr,
            dezenas_por_aposta: k,
            incluir_apostas: true,
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
        if (mesEl && mesEl.value) body.mes_num = parseInt(mesEl.value, 10);
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

    function fillPickSelect(selId) {
        const sel = $(selId);
        if (!sel) return;
        sel.innerHTML = '';
        for (let k = PICK_MIN; k <= PICK_MAX; k++) {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k + ' ' + UNIDADE;
            if (k === PICK_DEFAULT) opt.selected = true;
            sel.appendChild(opt);
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
                resumo.textContent = 'Selecione o pool para ver elegíveis e combinações.';
            } else {
                const combos = aval.combinacoes_possiveis != null
                    ? aval.combinacoes_possiveis.toLocaleString('pt-BR')
                    : '0';
                resumo.innerHTML =
                    `<strong>${aval.qtd_pool}</strong> dígito(s) · ` +
                    (IS_COLUNAS
                        ? `<strong>${aval.colunas || 7}</strong> ${UNIDADE} · ` +
                          `<strong>${(aval.combinacoes_possiveis || 0).toLocaleString('pt-BR')}</strong> combinações (pool^colunas)`
                        : `<strong>${aval.qtd_elegiveis}</strong> ${UNIDADE} elegíveis · ` +
                          `<strong>${combos}</strong> combinações possíveis ` +
                          `(C(${aval.qtd_elegiveis},${aval.dezenas_por_aposta}))`) +
                    (aval.pode_gerar || IS_COLUNAS
                        ? ' <span class="text-success">· pode gerar</span>'
                        : ' <span class="text-danger">· insuficiente para gerar</span>');
            }
        }
        if (elig) {
            elig.innerHTML = (aval && aval.elegiveis || []).map((n) =>
                `<span class="badge bg-success">${fmtDez(n)}</span>`
            ).join(' ') || '<span class="text-muted">—</span>';
        }
        const aviso = $(prefix === 'cd' ? 'cdAvisoRec' : 'ciAviso');
        if (aviso) {
            if (aval && aval.abaixo_recomendado) {
                aviso.className = 'small text-warning';
                aviso.textContent = aval.aviso || `Abaixo do mínimo recomendado (${MIN_REC}).`;
            } else {
                aviso.textContent = '';
            }
        }
    }

    async function avaliar(poolArr, k, prefix) {
        const data = await apiPost('/digitos/avaliar', {
            pool: poolArr,
            dezenas_por_aposta: k,
        });
        if (data.sucesso) renderElegiveis(data, prefix);
        return data;
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
        const k = parseInt(($('cdDezenasAposta') || {}).value || PICK_DEFAULT, 10);
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
            $('ciInsights').innerHTML =
                `Moda histórica: <strong>${data.qtd_recomendada}</strong> dígitos ` +
                `(${String(data.qtd_recomendada_pct).replace('.', ',')}%) · ` +
                `Top presença: ${top} · ` +
                `Ausentes no último: ${(data.digitos_ausentes_ultimo || []).join(', ') || '—'}`;
        }
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

    function atualizarOpcoesExigir(poolSize) {
        const sel = $('ciExigirQtd');
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
                : '';
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
        const out = $('ciResultado');
        if (!arr.length) {
            alert('Selecione o pool de dígitos.');
            return;
        }
        if (arr.length < MIN_REC) {
            if (!confirm(`Pool abaixo do recomendado (${MIN_REC}). Gerar mesmo assim?`)) return;
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
        const body = {
            pool: arr,
            dezenas_por_aposta: parseInt(($('ciDezenasAposta') || {}).value || PICK_DEFAULT, 10),
            qtd_apostas: parseInt(($('ciQtdApostas') || {}).value || 10, 10),
            modo: ($('ciModo') || {}).value || 'frequencia',
            exigir_qtd_digitos: ($('ciExigirQtd') || {}).value || null,
            salvar_sessao: !!( $('ciSalvarSessao') && $('ciSalvarSessao').checked ),
            nome: ($('ciNomeSessao') || {}).value || '',
        };
        const data = await apiPost('/digitos/gerar', body);
        if (!data.sucesso) {
            if (st) {
                st.className = 'mt-2 small text-danger';
                st.textContent = formatErroGeracao(data);
            }
            return;
        }
        if (st) {
            st.className = 'mt-2 small text-success';
            const aval = data.avaliacao || {};
            ultimaAvalIntel = aval;
            st.textContent =
                `${data.qtd_geradas} aposta(s) · ${aval.qtd_elegiveis} elegíveis · ` +
                `${(aval.combinacoes_possiveis || 0).toLocaleString('pt-BR')} combinações possíveis`;
        }
        ultimoLote = data.apostas || [];
        const btnLote = $('ciBtnExportLote');
        if (btnLote) btnLote.disabled = !ultimoLote.length;
        if (out) {
            if (!ultimoLote.length) {
                out.className = 'small text-muted';
                out.innerHTML = '—';
            } else {
                const cols = Math.max(
                    ...(ultimoLote.map((ap) => (ap.dezenas || []).length)),
                    1
                );
                out.className = 'small';
                out.innerHTML =
                    '<div class="ci-apostas-lista" style="--ci-cols:' + cols + '">' +
                    ultimoLote.map((ap) => {
                        const dez = (ap.dezenas || []).map(fmtDez);
                        return (
                            '<div class="ci-aposta-row">' +
                            '<span class="ci-aposta-num">#' + ap.linha + '</span>' +
                            dez.map((x) => '<span class="ci-dez">' + x + '</span>').join('') +
                            '</div>'
                        );
                    }).join('') +
                    '</div>';
            }
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
        fillPickSelect('cdDezenasAposta');
        $('cdDezenasAposta')?.addEventListener('change', syncAba2);

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

        $('cdBtnListarCombos')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = parseInt(($('cdDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            if (!arr.length) { alert('Selecione o pool.'); return; }
            listarTodas(arr, k, 'cdCombosMeta', 'cdCombosLista');
        });
        $('cdBtnExportTodas')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = parseInt(($('cdDezenasAposta') || {}).value || PICK_DEFAULT, 10);
            if (!arr.length) { alert('Selecione o pool.'); return; }
            exportar('todas', arr, k);
        });
        $('cdBtnExportElegiveis')?.addEventListener('click', () => {
            const arr = [...poolAba2].sort((a, b) => a - b);
            const k = parseInt(($('cdDezenasAposta') || {}).value || PICK_DEFAULT, 10);
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
                if ($('cdDezenasAposta') && data.sessao.dezenas_por_aposta) {
                    $('cdDezenasAposta').value = String(data.sessao.dezenas_por_aposta);
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
        // Padrão em todas as modalidades: pool completo 0–9 (10 dígitos).
        // Ignora cache antigo parcial (v1) — nova chave LS v2.
        const storedCd = loadPoolFromStorage();
        if (storedCd && Array.isArray(storedCd.pool) && storedCd.pool.length === QTD_DIGITOS_UNIVERSO) {
            storedCd.pool.forEach((d) => poolAba2.add(Number(d)));
        } else {
            aplicarPoolCompleto(poolAba2);
        }
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

        // Padrão: sempre inicia com os 10 dígitos (0–9).
        // Só restaura storage se for pool completo; cache antigo com 6 dígitos é descartado.
        const stored = loadPoolFromStorage();
        if (stored && Array.isArray(stored.pool) && stored.pool.length === QTD_DIGITOS_UNIVERSO) {
            stored.pool.forEach((d) => poolIntel.add(Number(d)));
            if ($('ciDezenasAposta') && stored.dezenas_por_aposta) {
                $('ciDezenasAposta').value = String(stored.dezenas_por_aposta);
            }
        } else {
            aplicarPoolCompleto(poolIntel);
            try { localStorage.removeItem('cc_digitos_pool_v1'); } catch (_) { /* ignore */ }
        }

        carregarGuia();
        syncIntel();
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
