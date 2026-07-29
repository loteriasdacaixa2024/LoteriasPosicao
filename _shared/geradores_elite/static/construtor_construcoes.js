(function () {
    'use strict';

    const root = document.getElementById('ge-construtor');
    if (!root) return;

    const API = window.__CC_API__ || root.dataset.api;
    const UI = window.__CC_UI__ || {};
    const PICK_MIN = parseInt(root.dataset.pickMin, 10) || UI.pick_min || 7;
    const PICK_MAX = parseInt(root.dataset.pickMax, 10) || UI.pick_max || 15;
    const PICK_DEFAULT = UI.pick_default || PICK_MIN;
    const QTD_APOSTAS = parseInt(root.dataset.qtdApostas, 10) || 10;
    const CONJUNTO_MAX = parseInt(root.dataset.conjuntoMax, 10) || UI.max_conjunto_base || 16;
    const ORIGEM_APOSTAS_10X7 = 'apostas_10x7';
    const APOSTAS_LINHAS = 10;
    const APOSTAS_POR_LINHA = 7;
    const DEZENA_MIN = UI.dezena_min != null ? UI.dezena_min : 1;
    const DEZENA_MAX = UI.total_dezenas || 31;
    const DEZENA_WIDTH = (UI.dezena_fmt_width != null ? UI.dezena_fmt_width : 2);
    const ACERTOS_MIN = UI.acertos_min_relevante || 4;
    const ACERTOS_MAX = UI.acertos_max_possivel || 7;
    const ACERTOS_TIERS = (UI.acertos_tiers && UI.acertos_tiers.length)
        ? UI.acertos_tiers
        : Array.from({ length: ACERTOS_MAX - ACERTOS_MIN + 1 }, (_, i) => ACERTOS_MIN + i);
    const FAIXA_LIMITES = UI.faixa_limites || {
        baixas: [1, 10], medias: [11, 20], altas: [21, 31]
    };
    const HAS_MES = !!UI.has_mes;
    const HAS_TIME = !!UI.has_time;
    const HAS_TREVOS = !!UI.has_trevos;
    const VOLANTE_COLS = UI.volante_cols || 10;

    let selecionadas = new Set();
    let sessaoAtual = null;
    let origemConjunto = 'manual';
    let modoEntrada = 'volante'; // 'volante' | 'apostas10x7'
    let editandoConstrucaoId = null;
    let exportandoConstrucaoId = null;
    let exportandoSessaoTodas = false;
    let modalEditar = null;
    let modalExport = null;
    let modalConfHist = null;

    const MESES = UI.meses || [];
    const ultimoSorteioSet = new Set((window.__CC_ULTIMO__ && window.__CC_ULTIMO__.dezenas) || []);

    const $ = (id) => document.getElementById(id);

    function abrirColinha(auto) {
        const pop = $('ccColinhaPop');
        const btn = $('ccColinhaBtn');
        if (!pop) return;
        pop.classList.add('aberto');
        if (btn) btn.setAttribute('aria-expanded', 'true');
        if (auto) pop.classList.add('cc-colinha-auto');
    }

    function fecharColinha() {
        const pop = $('ccColinhaPop');
        const btn = $('ccColinhaBtn');
        if (!pop) return;
        pop.classList.remove('aberto', 'cc-colinha-auto');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        try { localStorage.setItem(COLINHA_KEY, '1'); } catch (_) {}
    }

    function toggleColinha() {
        const pop = $('ccColinhaPop');
        if (pop && pop.classList.contains('aberto')) fecharColinha();
        else abrirColinha(false);
    }

    function avisoLimite() {
        abrirColinha(true);
        const info = $('ccPoolInfo');
        if (info) {
            info.className = 'small text-danger';
            info.textContent = `Limite de ${CONJUNTO_MAX} dezenas no conjunto-base. Desmarque uma para trocar.`;
        }
    }

    function maxConjuntoParaOrigem(origem) {
        const o = origem != null ? origem : origemConjunto;
        return o === ORIGEM_APOSTAS_10X7 ? DEZENA_MAX : CONJUNTO_MAX;
    }

    function labelMaxConjunto() {
        return maxConjuntoParaOrigem();
    }

    function setModoEntrada(modo, limparAoTrocar) {
        if (!$('ccModoApostasWrap')) return;
        const novo = modo === 'apostas10x7' ? 'apostas10x7' : 'volante';
        const anterior = modoEntrada;
        modoEntrada = novo;

        const wrapV = $('ccModoVolanteWrap');
        const wrapA = $('ccModoApostasWrap');
        const btnV = $('ccModoVolanteBtn');
        const btnA = $('ccModoApostasBtn');
        const hint = $('ccStep1Hint');

        if (wrapV) wrapV.style.display = novo === 'volante' ? '' : 'none';
        if (wrapA) wrapA.style.display = novo === 'apostas10x7' ? '' : 'none';
        if (btnV) btnV.classList.toggle('active', novo === 'volante');
        if (btnA) btnA.classList.toggle('active', novo === 'apostas10x7');

        if (hint) {
            if (novo === 'apostas10x7') {
                hint.textContent =
                    'Cole exatamente 10 apostas com 7 dezenas. O conjunto-base será a união dessas dezenas (pode passar de ' +
                    CONJUNTO_MAX + ').';
            } else {
                hint.textContent =
                    'Marque as dezenas da matéria-prima ou importe do ciclo/análise. Máximo ' +
                    CONJUNTO_MAX + ' números.';
            }
        }

        if (limparAoTrocar && anterior !== novo) {
            if (novo === 'volante') {
                if (origemConjunto === ORIGEM_APOSTAS_10X7 && selecionadas.size > CONJUNTO_MAX) {
                    setSelecionadas([...selecionadas].slice(0, CONJUNTO_MAX), 'manual',
                        `Modo volante limita a ${CONJUNTO_MAX}; mantidas as primeiras.`);
                } else if (origemConjunto === ORIGEM_APOSTAS_10X7) {
                    origemConjunto = 'manual';
                    updatePoolInfo();
                }
            }
        }
        updatePoolInfo();
    }

    function extrairNumsLinha(linha) {
        const parts = String(linha || '').match(/\d+/g) || [];
        return parts.map((x) => parseInt(x, 10));
    }

    function parseApostas10x7(texto) {
        const raw = String(texto || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
        if (!raw) {
            return { ok: false, erro: 'Cole as 10 apostas no campo de texto.' };
        }
        let linhas = raw.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
        let apostas = [];

        if (linhas.length === APOSTAS_LINHAS) {
            for (let i = 0; i < linhas.length; i++) {
                const nums = extrairNumsLinha(linhas[i]);
                if (nums.length !== APOSTAS_POR_LINHA) {
                    return {
                        ok: false,
                        erro: `Linha ${i + 1}: esperado ${APOSTAS_POR_LINHA} dezenas, veio ${nums.length}.`
                    };
                }
                apostas.push(nums);
            }
        } else {
            const todos = extrairNumsLinha(raw);
            if (todos.length === APOSTAS_LINHAS * APOSTAS_POR_LINHA) {
                for (let i = 0; i < APOSTAS_LINHAS; i++) {
                    const ini = i * APOSTAS_POR_LINHA;
                    apostas.push(todos.slice(ini, ini + APOSTAS_POR_LINHA));
                }
            } else {
                return {
                    ok: false,
                    erro: `Precisa de exatamente ${APOSTAS_LINHAS} linhas com ${APOSTAS_POR_LINHA} dezenas ` +
                        `(ou ${APOSTAS_LINHAS * APOSTAS_POR_LINHA} números no total). ` +
                        `Encontrado: ${linhas.length} linha(s), ${todos.length} número(s).`
                };
            }
        }

        const uniao = new Set();
        for (let i = 0; i < apostas.length; i++) {
            const ap = apostas[i];
            const vistos = new Set();
            for (const n of ap) {
                if (!Number.isFinite(n) || n < DEZENA_MIN || n > DEZENA_MAX) {
                    return {
                        ok: false,
                        erro: `Aposta ${i + 1}: dezena ${fmt(n)} fora de ${fmt(DEZENA_MIN)}–${fmt(DEZENA_MAX)}.`
                    };
                }
                if (vistos.has(n)) {
                    return {
                        ok: false,
                        erro: `Aposta ${i + 1}: dezena ${fmt(n)} repetida na mesma linha.`
                    };
                }
                vistos.add(n);
                uniao.add(n);
            }
        }

        const pool = [...uniao].sort((a, b) => a - b);
        if (pool.length < PICK_MIN) {
            return {
                ok: false,
                erro: `União das dezenas tem só ${pool.length}; mínimo ${PICK_MIN}.`
            };
        }
        return { ok: true, apostas, pool };
    }

    function atualizarInfoParseApostas() {
        const el = $('ccApostasParseInfo');
        const ta = $('ccApostasTexto');
        if (!el || !ta) return;
        const texto = ta.value;
        if (!String(texto || '').trim()) {
            el.className = 'small text-muted mb-1';
            el.textContent = '';
            return;
        }
        const r = parseApostas10x7(texto);
        if (!r.ok) {
            el.className = 'small text-danger mb-1';
            el.textContent = r.erro;
            return;
        }
        el.className = 'small text-success mb-1';
        el.textContent =
            `OK: ${APOSTAS_LINHAS}×${APOSTAS_POR_LINHA} — união: ${r.pool.length} dezenas distintas ` +
            `(${r.pool.map(fmt).join(' ')}).`;
    }

    function aplicarApostas10x7(silencioso) {
        const ta = $('ccApostasTexto');
        if (!ta) return false;
        const r = parseApostas10x7(ta.value);
        if (!r.ok) {
            if (!silencioso) alert(r.erro);
            atualizarInfoParseApostas();
            return false;
        }
        setSelecionadas(r.pool, ORIGEM_APOSTAS_10X7);
        atualizarInfoParseApostas();
        if (!silencioso) {
            const info = $('ccPoolInfo');
            if (info) {
                info.className = 'small text-success';
                info.textContent +=
                    ` · 10×7 aplicadas (${r.pool.length} únicas). Salve o conjunto-base para gerar.`;
            }
        }
        return true;
    }

    function faixaClass(n) {
        const iso = FAIXA_LIMITES.isolada;
        if (iso && n >= iso[0] && n <= iso[1]) return 'faixa-isolada';
        const b = FAIXA_LIMITES.baixas || [1, 10];
        const m = FAIXA_LIMITES.medias || [11, 20];
        if (n >= b[0] && n <= b[1]) return 'faixa-baixa';
        if (n >= m[0] && n <= m[1]) return 'faixa-media';
        return 'faixa-alta';
    }

    function faixaContagem(n) {
        const iso = FAIXA_LIMITES.isolada;
        if (iso && n >= iso[0] && n <= iso[1]) return 'i';
        const b = FAIXA_LIMITES.baixas || [1, 10];
        const m = FAIXA_LIMITES.medias || [11, 20];
        if (n >= b[0] && n <= b[1]) return 'b';
        if (n >= m[0] && n <= m[1]) return 'm';
        return 'a';
    }

    function fmt(n) {
        return String(n).padStart(DEZENA_WIDTH, '0');
    }

    function renderVolante() {
        const vol = $('ccVolante');
        if (vol) vol.style.gridTemplateColumns = `repeat(${VOLANTE_COLS}, 1fr)`;
        const noLimite = selecionadas.size >= CONJUNTO_MAX;
        vol.innerHTML = '';
        for (let n = DEZENA_MIN; n <= DEZENA_MAX; n++) {
            const btn = document.createElement('button');
            btn.type = 'button';
            const sel = selecionadas.has(n);
            btn.className = 'cc-ball ' + faixaClass(n);
            if (!sel && noLimite) btn.classList.add('cc-bloqueado');
            btn.textContent = fmt(n);
            btn.dataset.n = n;
            if (sel) btn.classList.add('selected');
            else if (ultimoSorteioSet.has(n)) btn.classList.add('cc-ultimo-ref');
            btn.title = ultimoSorteioSet.has(n) && !sel ? 'Saiu no último sorteio' : '';
            btn.addEventListener('click', () => {
                if (selecionadas.has(n)) {
                    selecionadas.delete(n);
                } else {
                    if (selecionadas.size >= CONJUNTO_MAX) {
                        avisoLimite();
                        return;
                    }
                    selecionadas.add(n);
                }
                origemConjunto = 'manual';
                renderVolante();
                updatePoolInfo();
            });
            vol.appendChild(btn);
        }
    }

    function updatePoolInfo() {
        const arr = [...selecionadas].sort((a, b) => a - b);
        let b = 0, m = 0, a = 0, iso = 0;
        arr.forEach(n => {
            const f = faixaContagem(n);
            if (f === 'b') b++;
            else if (f === 'm') m++;
            else if (f === 'i') iso++;
            else a++;
        });
        const cont = $('ccContador');
        const maxLabel = labelMaxConjunto();
        if (cont) {
            cont.textContent = `${arr.length}/${maxLabel}`;
            cont.classList.toggle('cc-limite', arr.length >= maxLabel);
        }
        const info = $('ccPoolInfo');
        if (info) {
            info.className = 'small text-muted';
            const isoTxt = (FAIXA_LIMITES.isolada && iso) ? ` · 31:${iso}` : (FAIXA_LIMITES.isolada ? ` · 31:${iso}` : '');
            info.textContent =
                `${arr.length}/${maxLabel} dezenas — B:${b} M:${m} A:${a}${isoTxt} · origem: ${origemConjunto}`;
        }
        atualizarSomasDigitosLive(arr);
    }

    function digitosDoPool(arr) {
        const digs = new Set();
        arr.forEach((n) => {
            String(n).padStart(DEZENA_WIDTH, '0').split('').forEach((ch) => {
                if (/\d/.test(ch)) digs.add(ch);
            });
        });
        const ordenados = [...digs].sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
        return { digitos: ordenados, qtd: ordenados.length, soma: arr.reduce((s, n) => s + n, 0) };
    }

    let sdHistoricoCache = null;

    function regrasSomasDigitos() {
        const panel = $('ccSomasDigitosPanel');
        if (!panel) return null;
        const somaMinEl = $('ccSomaMin');
        const somaMaxEl = $('ccSomaMax');
        const exigir = $('ccExigirDigitos') && $('ccExigirDigitos').checked;
        const digitos = $('ccDigitosExigidos') ? parseInt($('ccDigitosExigidos').value, 10) : null;
        const somaMin = somaMinEl && somaMinEl.value !== '' ? parseInt(somaMinEl.value, 10) : null;
        const somaMax = somaMaxEl && somaMaxEl.value !== '' ? parseInt(somaMaxEl.value, 10) : null;
        if (somaMin == null && somaMax == null && !exigir) return null;
        return {
            soma_min: Number.isFinite(somaMin) ? somaMin : null,
            soma_max: Number.isFinite(somaMax) ? somaMax : null,
            exigir_digitos: !!exigir,
            digitos_exigidos: exigir && Number.isFinite(digitos) ? digitos : null,
        };
    }

    function atualizarSomasDigitosLive(arr) {
        const resumo = $('ccSdResumoAtual');
        const valid = $('ccSdValidacao');
        if (!resumo) return;
        if (!arr.length) {
            resumo.innerHTML = 'Selecione dezenas para ver soma atual e dígitos distintos.';
            if (valid) valid.textContent = '';
            return;
        }
        const m = digitosDoPool(arr);
        resumo.innerHTML =
            `<strong>Soma atual:</strong> ${m.soma}` +
            ` · <strong>Dígitos:</strong> ${m.digitos.join(', ') || '—'} (${m.qtd})`;

        const regras = regrasSomasDigitos();
        if (!valid) return;
        if (!regras) {
            valid.className = 'small mt-1 text-muted';
            valid.textContent = 'Sem regra ativa — o save não bloqueia por soma/dígitos.';
            return;
        }
        const erros = [];
        if (regras.soma_min != null && m.soma < regras.soma_min) {
            erros.push(`❌ Soma ${m.soma} abaixo do mínimo ${regras.soma_min}.`);
        }
        if (regras.soma_max != null && m.soma > regras.soma_max) {
            erros.push(`❌ Soma ${m.soma} acima do máximo ${regras.soma_max}.`);
        }
        if (regras.exigir_digitos && regras.digitos_exigidos != null && m.qtd !== regras.digitos_exigidos) {
            erros.push(`❌ Precisa de ${regras.digitos_exigidos} dígitos distintos (atual: ${m.qtd}).`);
        }
        if (erros.length) {
            valid.className = 'small mt-1 text-danger';
            valid.innerHTML = erros.join('<br>');
        } else {
            valid.className = 'small mt-1 text-success';
            valid.textContent = '✅ Dentro da faixa / regra definida.';
        }
    }

    async function carregarGuiaSomasDigitos() {
        const el = $('ccSdGuiaHistorico');
        if (!el) return;
        try {
            const data = await apiGet('/estatisticas-somas-digitos?janela=0&base=geral');
            if (!data.sucesso) {
                el.textContent = data.erro || 'Guia histórico indisponível.';
                return;
            }
            sdHistoricoCache = data;
            const hs = data.historico_somas || {};
            const hd = data.historico_digitos || {};
            const topFaixa = (data.distribuicao_faixas || []).find((f) => f.destaque);
            el.innerHTML =
                `<strong>Guia histórico (7 dezenas):</strong> ` +
                `min ${hs.soma_minima ?? '—'} · max ${hs.soma_maxima ?? '—'} · média ${hs.soma_media ?? '—'}` +
                ` · faixa +freq: <strong>${hs.faixa_mais_frequente || (topFaixa && topFaixa.faixa) || '—'}</strong>` +
                `<br><strong>★★ Recomendado:</strong> ${hd.qtd_recomendada ?? 7} dígitos distintos ` +
                `(${(hd.qtd_recomendada_pct != null ? String(hd.qtd_recomendada_pct).replace('.', ',') : '—')}%)` +
                ` · dígito +sai: <strong>${hd.digito_mais_frequente ?? '—'}</strong>`;
            const sel = $('ccDigitosExigidos');
            if (sel && hd.qtd_recomendada != null) {
                sel.value = String(hd.qtd_recomendada);
            }
        } catch (e) {
            el.textContent = 'Guia histórico indisponível.';
        }
    }

    function fillSelectDezenas() {
        const sel = $('ccDezenasAposta');
        sel.innerHTML = '';
        for (let k = PICK_MIN; k <= PICK_MAX; k++) {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k + ' dezenas';
            if (k === PICK_DEFAULT) opt.selected = true;
            sel.appendChild(opt);
        }
    }

    function fillEstrategias() {
        const sel = $('ccEstrategia');
        sel.innerHTML = '';
        (UI.estrategias || []).forEach(e => {
            const opt = document.createElement('option');
            opt.value = e.id;
            opt.textContent = e.label;
            opt.title = e.desc || '';
            sel.appendChild(opt);
        });
        sel.addEventListener('change', onEstrategiaChange);
        onEstrategiaChange();
    }

    function onEstrategiaChange() {
        const v = $('ccEstrategia').value;
        $('ccPersonalizadaWrap').style.display = v === 'personalizada' ? '' : 'none';
        const showJanela = v === 'conforme_comportamento';
        $('ccJanelaWrap').style.display = showJanela ? '' : 'none';
        const hint = $('ccJanelaHint');
        if (hint) hint.classList.toggle('d-none', !showJanela);
    }

    function atualizarBotoesSessaoConstrucoes() {
        const has = !!(sessaoAtual && sessaoAtual.construcoes && sessaoAtual.construcoes.length);
        if ($('ccBtnConferirTodas')) $('ccBtnConferirTodas').disabled = !has;
        if ($('ccBtnExportTodas')) $('ccBtnExportTodas').disabled = !has;
    }

    function atualizarEstadoGerar() {
        const btn = $('ccBtnGerar');
        const hint = $('ccGerarHint');
        if (!btn) return;
        const liberado = !!sessaoAtual;
        btn.disabled = !liberado;
        if (hint) {
            if (liberado) {
                hint.className = 'mt-2 small text-success';
                hint.innerHTML = `<i class="fas fa-check-circle"></i> Sessão #${sessaoAtual.id} ativa — pode gerar construções.`;
            } else {
                hint.className = 'mt-2 small text-muted';
                hint.innerHTML = '<i class="fas fa-info-circle"></i> Para liberar: selecione o conjunto-base e clique em <strong>Salvar conjunto-base (sessão)</strong>.';
            }
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

    async function apiPut(path, body) {
        const r = await fetch(API + path, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return r.json();
    }

    async function apiDelete(path) {
        const r = await fetch(API + path, { method: 'DELETE' });
        return r.json();
    }

    function fillMesSelect(sel, selected) {
        if (!sel) return;
        sel.innerHTML = '';
        MESES.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.num;
            opt.textContent = `${m.nome} (${m.abrev})`;
            if (selected && parseInt(selected, 10) === m.num) opt.selected = true;
            sel.appendChild(opt);
        });
    }

    function parseDezenasInput(txt) {
        return txt.trim().split(/[\s,;]+/).filter(Boolean).map(x => parseInt(x, 10)).filter(n => !isNaN(n));
    }

    function downloadTxt(nome, texto) {
        const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nome;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function setSelecionadas(nums, origem, aviso) {
        const unicos = [...new Set(nums)].sort((a, b) => a - b);
        const origemNova = origem || 'manual';
        const maxOk = maxConjuntoParaOrigem(origemNova);
        if (unicos.length > maxOk) {
            selecionadas = new Set(unicos.slice(0, maxOk));
            origemConjunto = origemNova;
            renderVolante();
            updatePoolInfo();
            abrirColinha(true);
            const info = $('ccPoolInfo');
            if (info) {
                info.className = 'small text-warning';
                info.textContent = (aviso || `Importação tinha ${unicos.length} dezenas; mantidas ${maxOk}.`) +
                    ` — B/M/A atualizados.`;
            }
            return;
        }
        selecionadas = new Set(unicos);
        origemConjunto = origemNova;
        renderVolante();
        updatePoolInfo();
        if (aviso) {
            const info = $('ccPoolInfo');
            if (info) {
                info.className = 'small text-warning';
                info.textContent += ' · ' + aviso;
            }
        }
    }

    async function importarCiclo(tipo) {
        const data = await apiGet('/ciclo?tipo=' + tipo);
        if (!data.sucesso) { alert(data.erro || 'Erro'); return; }
        setSelecionadas(data.dezenas, data.origem, data.aviso);
    }

    async function importarAnalise(criterio) {
        const qtd = Math.min(parseInt($('ccQtdImport').value, 10) || CONJUNTO_MAX, CONJUNTO_MAX);
        const data = await apiGet(`/analise-sugestao?quantidade=${qtd}&criterio=${criterio}`);
        if (!data.sucesso) { alert(data.erro || 'Erro'); return; }
        setSelecionadas(data.dezenas, data.origem, data.aviso);
    }

    async function salvarSessao() {
        if (modoEntrada === 'apostas10x7') {
            const ta = $('ccApostasTexto');
            const temTexto = ta && String(ta.value || '').trim();
            if (temTexto) {
                if (!aplicarApostas10x7(true)) return;
            } else if (origemConjunto !== ORIGEM_APOSTAS_10X7 || selecionadas.size < PICK_MIN) {
                alert('Cole as 10 apostas × 7 dezenas e clique em “Usar estas 10 apostas”, ou carregue uma sessão.');
                return;
            }
        }
        const arr = [...selecionadas].sort((a, b) => a - b);
        if (arr.length < PICK_MIN) {
            alert(`Selecione ao menos ${PICK_MIN} dezenas no conjunto-base.`);
            return;
        }
        const maxOk = maxConjuntoParaOrigem(origemConjunto);
        if (arr.length > maxOk) {
            abrirColinha(true);
            alert(`Conjunto-base limitado a ${maxOk} dezenas.`);
            return;
        }
        const regras = regrasSomasDigitos();
        if (regras) {
            const m = digitosDoPool(arr);
            if (regras.soma_min != null && m.soma < regras.soma_min) {
                alert(`❌ Soma ${m.soma} fora da faixa (mín. ${regras.soma_min}).`);
                return;
            }
            if (regras.soma_max != null && m.soma > regras.soma_max) {
                alert(`❌ Soma ${m.soma} fora da faixa (máx. ${regras.soma_max}).`);
                return;
            }
            if (regras.exigir_digitos && regras.digitos_exigidos != null && m.qtd !== regras.digitos_exigidos) {
                alert(`❌ Exigidos ${regras.digitos_exigidos} dígitos distintos (atual: ${m.qtd}).`);
                return;
            }
        }
        const body = {
            nome: $('ccNomeSessao').value.trim(),
            conjunto_base: arr,
            dezenas_por_aposta: parseInt($('ccDezenasAposta').value, 10),
            origem_conjunto: origemConjunto,
            sessao_id: sessaoAtual ? sessaoAtual.id : null,
        };
        if (regras) body.regras_somas_digitos = regras;
        const data = await apiPost('/sessao', body);
        if (!data.sucesso) {
            $('ccSessaoStatus').className = 'mt-2 small text-danger';
            $('ccSessaoStatus').textContent = data.erro || 'Erro ao salvar.';
            return;
        }
        sessaoAtual = data.sessao;
        $('ccSessaoStatus').className = 'mt-2 small text-success';
        $('ccSessaoStatus').textContent = `Sessão #${sessaoAtual.id} salva — ${sessaoAtual.conjunto_base.length} dezenas.`;
        atualizarEstadoGerar();
        $('ccBtnConferir').disabled = false;
        atualizarBotoesSessaoConstrucoes();
        await carregarSessoes();
        renderConstrucoes(sessaoAtual);
        carregarAnaliseHistorica();
    }

    async function gerarConstrucao() {
        if (!sessaoAtual) {
            alert('Salve a sessão antes de gerar.');
            return;
        }
        $('ccGerarStatus').textContent = 'Gerando…';
        $('ccGerarStatus').className = 'mt-2 small text-muted';
        const body = {
            sessao_id: sessaoAtual.id,
            estrategia: $('ccEstrategia').value,
            similaridade_min_pct: parseFloat($('ccSimMin').value),
            janela_comportamento: parseInt($('ccJanela').value, 10),
        };
        if (body.estrategia === 'personalizada') {
            body.personalizada = {
                baixas: parseInt($('ccPersB').value, 10) || 0,
                medias: parseInt($('ccPersM').value, 10) || 0,
                altas: parseInt($('ccPersA').value, 10) || 0,
            };
        }
        const data = await apiPost('/gerar', body);
        if (!data.sucesso) {
            $('ccGerarStatus').className = 'mt-2 small text-danger';
            $('ccGerarStatus').textContent = data.erro || 'Erro na geração.';
            return;
        }
        $('ccGerarStatus').className = 'mt-2 small text-success';
        let msg = `Construção #${data.construcao.numero} gerada`;
        if (data.construcao.diferenca_pct != null) {
            msg += ` — ${data.construcao.diferenca_pct}% diferente da anterior`;
        }
        if (data.qtd_padroes_distintos != null) {
            msg += ` · ${data.qtd_padroes_distintos} padrões iniciais distintos`;
        }
        if (data.aviso) msg += '. ' + data.aviso;
        $('ccGerarStatus').textContent = msg;
        const refreshed = await apiGet('/sessao/' + sessaoAtual.id);
        if (refreshed.sucesso) {
            sessaoAtual = refreshed.sessao;
            atualizarBotoesSessaoConstrucoes();
            renderConstrucoes(sessaoAtual);
        }
    }

    function renderMatrizSim(matriz) {
        const el = $('ccMatrizSim');
        if (!matriz || !matriz.length) {
            el.innerHTML = '';
            return;
        }
        el.innerHTML = '<div class="small fw-semibold mb-1">Similaridade entre construções</div>' +
            matriz.map(m =>
                `<span class="cc-sim-badge me-1 mb-1">C${m.de}↔C${m.para}: ${m.diferenca_pct}% diferente</span>`
            ).join('');
    }

    function labelEstrategia(id) {
        const e = (UI.estrategias || []).find(x => x.id === id || x.key === id);
        return e ? (e.label || e.nome || id) : id;
    }

    function descEstrategia(id) {
        const e = (UI.estrategias || []).find(x => x.id === id);
        return e ? (e.desc || '') : '';
    }

    function detalheEstrategia(c) {
        const dist = c.distribuicao || {};
        const params = c.estrategia_params || {};
        if (c.estrategia === 'personalizada' && (dist.baixas || dist.medias || dist.altas)) {
            return `${dist.baixas || 0}B · ${dist.medias || 0}M · ${dist.altas || 0}A`;
        }
        if (c.estrategia === 'conforme_comportamento') {
            const moda = params.comportamento_moda;
            if (moda) {
                return `Moda ${moda.baixas || 0}B · ${moda.medias || 0}M · ${moda.altas || 0}A`;
            }
            const j = params.janela_comportamento;
            return j != null ? `Janela de comportamento: ${j === 0 ? 'todos os concursos' : j + ' concursos'}` : '';
        }
        if (dist.baixas != null && !['somente_baixas', 'somente_medias', 'somente_altas'].includes(c.estrategia)) {
            return `${dist.baixas || 0}B · ${dist.medias || 0}M · ${dist.altas || 0}A`;
        }
        return '';
    }

    function htmlEstrategiaBadge(c) {
        const id = c.estrategia || 'automatica';
        const label = labelEstrategia(id);
        const desc = descEstrategia(id);
        const det = detalheEstrategia(c);
        const detHtml = det ? `<span class="cc-estrategia-detalhe">· ${det}</span>` : '';
        return `<div class="cc-estrategia-badge cc-estrategia-${id}" title="${desc.replace(/"/g, '&quot;')}">
            <i class="fas fa-sliders"></i>
            <span>Estratégia: ${label}${detHtml}</span>
        </div>`;
    }

    function renderBalls(dezenas, sorteadasSet) {
        const conferindo = sorteadasSet && sorteadasSet.size > 0;
        return dezenas.map(d => {
            const hit = conferindo && sorteadasSet.has(d);
            let cls = 'dez-ball-mini';
            if (conferindo) cls += hit ? ' cc-acerto' : ' cc-erro';
            return `<span class="${cls}">${fmt(d)}</span>`;
        }).join('');
    }

    function renderApostas(apostas, editavel, sorteadasSet) {
        if (editavel) {
            return apostas.map(a => {
                const txt = a.dezenas.map(d => fmt(d)).join(' ');
                return `<div class="cc-edit-aposta row g-1 mb-1 align-items-center" data-linha="${a.linha}">
                    <div class="col-auto cc-aposta-num">${a.linha}.</div>
                    <div class="col">
                        <input type="text" class="form-control form-control-sm cc-input-dezenas"
                            value="${txt}" data-linha="${a.linha}">
                    </div>
                </div>`;
            }).join('');
        }
        return apostas.map(a => {
            const ac = a.acertos;
            const clsAc = ac != null ? (ac >= 5 ? 'text-success fw-bold' : ac >= 4 ? 'text-warning' : '') : '';
            const acHtml = ac != null
                ? `<span class="cc-aposta-acertos ${clsAc}">${ac} ac.</span>`
                : '';
            return `<div class="cc-aposta-row">
                <span class="cc-aposta-num">${a.linha}.</span>
                <div class="cc-aposta-balls">${renderBalls(a.dezenas, sorteadasSet)}</div>
                ${acHtml}
            </div>`;
        }).join('');
    }

    function renderConstrucoes(sessao) {
        renderMatrizSim(sessao.matriz_similaridade);
        const el = $('ccConstrucoes');
        if (!sessao.construcoes || !sessao.construcoes.length) {
            el.innerHTML = '<p class="text-muted small mb-0">Nenhuma construção ainda.</p>';
            return;
        }
        el.innerHTML = sessao.construcoes.map(c => {
            const dist = c.distribuicao || {};
            const diff = c.diferenca_pct != null
                ? `<span class="cc-sim-badge">${c.diferenca_pct}% diferente da anterior</span>`
                : '';
            const mesBadge = c.mes_abrev
                ? `<span class="cc-mes-badge ms-1" title="Mês da Sorte">${c.mes_abrev}</span>`
                : '';
            const ch = c.conferencia_historico;
            const confBadge = ch
                ? `<span class="cc-conf-badge ms-1" title="Conferida em ${ch.data_execucao || ''}">
                    Hist: média ${ch.media_max_acertos} · ${textoAcertosResumo(ch)}
                   </span>`
                : '';
            return `<div class="cc-construcao-card" data-id="${c.id}" data-num="${c.numero}">
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-1 mb-1">
                    <div>
                        <strong>Construção ${c.numero}</strong>${mesBadge}${confBadge}
                    </div>
                    ${diff}
                </div>
                ${htmlEstrategiaBadge(c)}
                <div class="cc-acoes">
                    <button type="button" class="btn btn-outline-success cc-btn-conf-hist" data-id="${c.id}" data-num="${c.numero}"
                        title="Conferir contra todo o histórico e salvar">
                        <i class="fas fa-history"></i> Conferir histórico
                    </button>
                    <button type="button" class="btn btn-outline-primary cc-btn-editar" data-id="${c.id}">
                        <i class="fas fa-pen"></i> Editar
                    </button>
                    <button type="button" class="btn btn-outline-danger cc-btn-excluir" data-id="${c.id}" data-num="${c.numero}">
                        <i class="fas fa-trash"></i> Excluir
                    </button>
                    <button type="button" class="btn btn-outline-secondary cc-btn-export" data-id="${c.id}" data-num="${c.numero}">
                        <i class="fas fa-file-export"></i> Exportar .TXT
                    </button>
                </div>
                <div class="small text-muted mb-1">
                    Distribuição aplicada: B:${dist.baixas || 0} M:${dist.medias || 0} A:${dist.altas || 0}
                    · ${QTD_APOSTAS} apostas
                </div>
                ${renderApostas(c.apostas, false, null)}
            </div>`;
        }).join('');
    }

    function abrirEditar(construcaoId) {
        if (!sessaoAtual) return;
        const c = (sessaoAtual.construcoes || []).find(x => x.id === construcaoId);
        if (!c) return;
        editandoConstrucaoId = construcaoId;
        $('ccEditNumero').textContent = '#' + c.numero;
        $('ccEditPoolHint').textContent = (sessaoAtual.conjunto_base || []).map(fmt).join(' ');
        fillMesSelect($('ccEditMes'), c.mes_num || 1);
        $('ccEditApostas').innerHTML = renderApostas(c.apostas, true);
        modalEditar?.show();
    }

    async function salvarEdicao() {
        if (!editandoConstrucaoId) return;
        const inputs = document.querySelectorAll('#ccEditApostas .cc-input-dezenas');
        const apostas = [];
        for (const inp of inputs) {
            const linha = parseInt(inp.dataset.linha, 10);
            apostas.push({ linha, dezenas: parseDezenasInput(inp.value) });
        }
        const data = await apiPut(`/construcao/${editandoConstrucaoId}`, {
            apostas,
            mes_num: parseInt($('ccEditMes').value, 10),
        });
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao salvar.');
            return;
        }
        modalEditar?.hide();
        editandoConstrucaoId = null;
        if (data.sessao) {
            sessaoAtual = data.sessao;
            renderConstrucoes(sessaoAtual);
        }
    }

    async function excluirConstrucao(construcaoId, numero) {
        if (!confirm(`Excluir a Construção ${numero}? Esta ação não pode ser desfeita.`)) return;
        const data = await apiDelete(`/construcao/${construcaoId}`);
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao excluir.');
            return;
        }
        if (data.sessao) {
            sessaoAtual = data.sessao;
            renderConstrucoes(sessaoAtual);
        }
    }

    function abrirExport(construcaoId, numero) {
        if (!sessaoAtual) return;
        const c = (sessaoAtual.construcoes || []).find(x => x.id === construcaoId);
        exportandoConstrucaoId = construcaoId;
        exportandoSessaoTodas = false;
        $('ccExportNumero').textContent = '#' + numero;
        if (HAS_MES) fillMesSelect($('ccExportMes'), c?.mes_num || 1);
        modalExport?.show();
    }

    function abrirExportTodas() {
        if (!sessaoAtual || !(sessaoAtual.construcoes || []).length) {
            alert('Não há construções para exportar.');
            return;
        }
        exportandoConstrucaoId = null;
        exportandoSessaoTodas = true;
        const n = sessaoAtual.construcoes.length;
        $('ccExportNumero').textContent = `1–${n} (todas)`;
        if (HAS_MES) fillMesSelect($('ccExportMes'), sessaoAtual.construcoes[0]?.mes_num || 1);
        modalExport?.show();
    }

    async function confirmarExport() {
        const payload = {};
        if (HAS_MES) {
            payload.mes_num = parseInt($('ccExportMes').value, 10);
        }
        let data;
        if (exportandoSessaoTodas) {
            if (!sessaoAtual) return;
            data = await apiPost(`/sessao/${sessaoAtual.id}/export-txt`, payload);
        } else {
            if (!exportandoConstrucaoId) return;
            data = await apiPost(`/construcao/${exportandoConstrucaoId}/export-txt`, payload);
        }
        if (!data.sucesso) {
            alert(data.erro || 'Erro ao exportar.');
            return;
        }
        downloadTxt(data.nome_arquivo || 'construcao.txt', data.texto);
        modalExport?.hide();
        const sid = sessaoAtual?.id;
        exportandoConstrucaoId = null;
        exportandoSessaoTodas = false;
        if (sid) {
            const refreshed = await apiGet('/sessao/' + sid);
            if (refreshed.sucesso) {
                sessaoAtual = refreshed.sessao;
                renderConstrucoes(sessaoAtual);
            }
        }
    }

    function bindConstrucoesAcoes() {
        const el = $('ccConstrucoes');
        if (!el || el.dataset.bound) return;
        el.dataset.bound = '1';
        el.addEventListener('click', (e) => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const id = parseInt(btn.dataset.id, 10);
            if (btn.classList.contains('cc-btn-editar')) abrirEditar(id);
            else if (btn.classList.contains('cc-btn-excluir')) {
                excluirConstrucao(id, parseInt(btn.dataset.num, 10));
            }             else if (btn.classList.contains('cc-btn-export')) {
                abrirExport(id, parseInt(btn.dataset.num, 10));
            } else if (btn.classList.contains('cc-btn-conf-hist')) {
                conferirHistoricoConstrucao(id, parseInt(btn.dataset.num, 10));
            }
        });
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

    function chaveTotalAcertos(r) {
        const k0 = ACERTOS_TIERS[0];
        const k1 = ACERTOS_TIERS[ACERTOS_TIERS.length - 1];
        return r['concursos_' + k0 + '_a_' + k1]
            ?? ACERTOS_TIERS.reduce((s, t) => s + (r['concursos_' + t] ?? 0), 0);
    }

    function htmlBadgesAcertos(r) {
        const c = contadoresAcertos(r);
        return ACERTOS_TIERS.map(t =>
            `<span class="cc-conf-badge">${t} ac.: ${c['c' + t]}</span>`
        ).join('');
    }

    function theadAcertosCols() {
        return ACERTOS_TIERS.map(t => `<th>${t} ac.</th>`).join('');
    }

    function tbodyAcertosCols(r) {
        const c = contadoresAcertos(r);
        return ACERTOS_TIERS.map(t => `<td>${c['c' + t]}</td>`).join('');
    }

    function htmlResumoConferencia(conf) {
        const r = conf.resumo || {};
        const melhor = r.melhor_concurso;
        const melhorTxt = melhor
            ? `#${melhor.concurso} (${melhor.max_acertos} ac.)`
            : '—';
        const k0 = ACERTOS_TIERS[0];
        const k1 = ACERTOS_TIERS[ACERTOS_TIERS.length - 1];
        return `<div class="small">
            <div class="row g-2 mb-2">
                <div class="col-6 col-md-3"><strong>${r.concursos_total || 0}</strong><br><span class="text-muted">concursos</span></div>
                <div class="col-6 col-md-3"><strong>${r.total_pontos || 0}</strong><br><span class="text-muted">soma máx. acertos</span></div>
                <div class="col-6 col-md-3"><strong>${r.media_max_acertos ?? '—'}</strong><br><span class="text-muted">média máx./concurso</span></div>
                <div class="col-6 col-md-3"><strong>${chaveTotalAcertos(r)}</strong><br><span class="text-muted">total ${k0}–${k1} ac.</span></div>
            </div>
            <div class="d-flex flex-wrap gap-2 mb-2">${htmlBadgesAcertos(r)}</div>
            <div class="text-muted mb-2">
                Melhor concurso: ${melhorTxt}
                · Atualizado: ${conf.data_execucao ? conf.data_execucao.slice(0, 16).replace('T', ' ') : '—'}
            </div>
            <p class="text-muted mb-0" style="font-size:.72rem;">
                Sorteio com ${ACERTOS_MAX} dezenas — acertos por aposta vão de 0 a ${ACERTOS_MAX}.
                Contamos concursos com melhor aposta em ${ACERTOS_MIN} a ${ACERTOS_MAX} acertos.
            </p>
        </div>`;
    }

    function renderAnaliseHistorica(analise) {
        const el = $('ccAnaliseHistorica');
        if (!el) return;
        if (!analise || !analise.tem_dados) {
            el.innerHTML = `<p class="text-muted small mb-0">${(analise && analise.mensagem) || 'Nenhuma conferência histórica salva ainda.'}</p>`;
            return;
        }
        const p = analise.perguntas || {};
        const cardHtml = (titulo, constrNum, estrategia, detalhe) =>
            `<div class="cc-analise-card">
                <div class="cc-analise-pergunta">${titulo}</div>
                <div class="cc-analise-valor">Constr. ${constrNum}</div>
                <div class="cc-analise-detalhe">${labelEstrategia(estrategia)}<br>${detalhe}</div>
            </div>`;

        const mp = p.mais_pontos;
        const cardPontos = mp
            ? cardHtml('Mais pontos no histórico', mp.construcao_numero, mp.estrategia, `${mp.valor} pts`)
            : '';

        const ba = p.melhor_acertos;
        const k0 = ACERTOS_TIERS[0];
        const k1 = ACERTOS_TIERS[ACERTOS_TIERS.length - 1];
        const cardAcertos = ba
            ? cardHtml(
                `Melhor desempenho (${k0}–${k1} ac.)`,
                ba.construcao_numero,
                ba.estrategia,
                textoAcertosResumo(ba)
            )
            : '';

        const mm = p.maior_media;
        const cardMedia = mm
            ? cardHtml('Maior média de acertos', mm.construcao_numero, mm.estrategia, `${mm.valor} ac./concurso`)
            : '';

        const est = p.melhor_estrategia;
        const cardEstrategia = est
            ? `<div class="cc-analise-estrategia-linha">
                <div class="cc-analise-card cc-analise-card-estrategia">
                    <div class="cc-analise-pergunta">Melhor estratégia (mesmo conjunto-base)</div>
                    <div class="cc-analise-valor">${labelEstrategia(est.estrategia)}</div>
                    <div class="cc-analise-detalhe">
                        <span class="cc-analise-soma-label">Soma de ${est.qtd_construcoes ?? 1} construção(ões)</span><br>
                        ${ACERTOS_TIERS.map(t => `${t} ac.: ${est['concursos_' + t] ?? 0}`).join(' · ')}<br>
                        Média: ${est.media_max_acertos} ac./concurso
                    </div>
                </div>
               </div>`
            : '';
        const ranking = (analise.ranking_acertos || analise.ranking_media || []).map((r, i) =>
            `<tr class="${i === 0 ? 'cc-top' : ''}">
                <td>${r.construcao_numero}</td>
                <td>${labelEstrategia(r.estrategia)}</td>
                ${tbodyAcertosCols(r)}
                <td>${r.media_max_acertos}</td>
                <td>${r.total_pontos}</td>
            </tr>`
        ).join('');
        const faltam = (analise.sem_conferencia || []).length
            ? `<p class="small text-warning mb-2 cc-analise-alerta">Sem conferência: construção(ões) ${analise.sem_conferencia.join(', ')}.</p>`
            : '';
        el.innerHTML = `${faltam}
            <div class="cc-analise-resumo">
                <div class="cc-analise-resumo-titulo">Resumo comparativo</div>
                <div class="cc-analise-painel">
                    ${cardPontos}${cardAcertos}${cardMedia}
                </div>
                ${cardEstrategia}
            </div>
            <p class="small text-muted cc-analise-hint mb-2">Cada coluna: concursos em que a <strong>melhor aposta</strong> teve exatamente N acertos (máx. ${ACERTOS_MAX}). Ordenação: ${[...ACERTOS_TIERS].reverse().join(' → ')} ac.</p>
            <div class="table-responsive">
                <table class="table table-sm cc-ranking-hist mb-0">
                    <thead><tr>
                        <th>#</th><th>Estratégia</th>${theadAcertosCols()}<th>Média máx.</th><th>Pontos</th>
                    </tr></thead>
                    <tbody>${ranking}</tbody>
                </table>
            </div>`;
    }

    async function carregarAnaliseHistorica() {
        if (!sessaoAtual) return;
        const data = await apiGet('/sessao/' + sessaoAtual.id + '/analise-comparativa');
        if (data.sucesso && data.analise) renderAnaliseHistorica(data.analise);
    }

    function renderPanoramaGeral(data) {
        const el = $('ccPanoramaGeral');
        if (!el) return;
        const k0 = ACERTOS_TIERS[0];
        const k1 = ACERTOS_TIERS[ACERTOS_TIERS.length - 1];
        const totalEstKey = `total_${k0}_a_${k1}`;
        if (!data || !data.sucesso) {
            el.innerHTML = `<p class="text-danger small mb-0">${(data && data.erro) || 'Erro ao carregar panorama.'}</p>`;
            return;
        }
        if (!data.ranking || !data.ranking.length) {
            el.innerHTML = '<p class="text-muted small mb-0">Nenhuma conferência histórica salva no banco ainda.</p>';
            return;
        }
        const rows = data.ranking.map((r, i) => {
            const dataConf = r.data_execucao
                ? r.data_execucao.slice(0, 16).replace('T', ' ')
                : '—';
            return `<tr class="${i === 0 ? 'cc-top' : ''}">
                <td>S#${r.sessao_id}</td>
                <td class="text-start">${r.sessao_nome || '—'}</td>
                <td>C${r.construcao_numero}</td>
                <td class="text-start">${labelEstrategia(r.estrategia)}</td>
                ${tbodyAcertosCols(r)}
                <td>${r.media_max_acertos}</td>
                <td>${r.total_pontos}</td>
                <td class="small text-muted">${dataConf}</td>
            </tr>`;
        }).join('');

        const est = data.melhor_estrategia;
        const cardEstrategia = est
            ? `<div class="cc-analise-resumo mb-3">
                <div class="cc-analise-resumo-titulo">Soma geral — melhor estratégia no banco</div>
                <div class="cc-analise-estrategia-linha">
                    <div class="cc-analise-card cc-analise-card-estrategia">
                        <div class="cc-analise-pergunta">Estratégia campeã (todas as sessões)</div>
                        <div class="cc-analise-valor">${labelEstrategia(est.estrategia)}</div>
                        <div class="cc-analise-detalhe">
                            <span class="cc-analise-soma-label">Soma de ${est.qtd_construcoes} construção(ões) · ${est.qtd_sessoes} sessão(ões)</span><br>
                            ${ACERTOS_TIERS.map(t => `${t} ac.: ${est['concursos_' + t] ?? 0}`).join(' · ')}<br>
                            Total ${k0}–${k1} ac.: ${est[totalEstKey] ?? chaveTotalAcertos(est)} · Pontos: ${est.total_pontos} · Média: ${est.media_max_acertos} ac./concurso
                        </div>
                    </div>
                </div>
               </div>`
            : '';

        const estrategiasRows = (data.estrategias || []).map((e, i) =>
            `<tr class="${i === 0 ? 'cc-top' : ''}">
                <td class="text-start">${labelEstrategia(e.estrategia)}</td>
                <td>${e.qtd_construcoes}</td>
                <td>${e.qtd_sessoes}</td>
                ${tbodyAcertosCols(e)}
                <td>${e[totalEstKey] ?? chaveTotalAcertos(e)}</td>
                <td>${e.total_pontos}</td>
                <td>${e.media_max_acertos}</td>
            </tr>`
        ).join('');

        const tabelaEstrategias = (data.estrategias || []).length
            ? `<div class="cc-analise-resumo mb-3">
                <div class="cc-analise-resumo-titulo">Soma por estratégia (todas as sessões)</div>
                <div class="table-responsive">
                    <table class="table table-sm cc-ranking-hist mb-0">
                        <thead><tr>
                            <th>Estratégia</th><th>Constr.</th><th>Sessões</th>
                            ${theadAcertosCols()}
                            <th>Σ ${k0}–${k1}</th><th>Pontos</th><th>Média</th>
                        </tr></thead>
                        <tbody>${estrategiasRows}</tbody>
                    </table>
                </div>
               </div>`
            : '';

        el.innerHTML = `
            ${cardEstrategia}
            ${tabelaEstrategias}
            <p class="small text-muted mb-2 cc-analise-hint">
                <strong>${data.total}</strong> conferência(s) salva(s) — detalhe por construção.
                Cada coluna = concursos em que a melhor aposta teve exatamente N acertos (${k0} a ${k1}).
            </p>
            <div class="table-responsive">
                <table class="table table-sm cc-ranking-hist mb-0">
                    <thead><tr>
                        <th>Sessão</th><th>Nome</th><th>Constr.</th><th>Estratégia</th>
                        ${theadAcertosCols()}
                        <th>Média máx.</th><th>Pontos</th><th>Conferida em</th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    }

    async function carregarPanoramaGeral() {
        const el = $('ccPanoramaGeral');
        if (el) el.innerHTML = '<p class="text-muted small mb-0">Carregando panorama…</p>';
        const data = await apiGet('/panorama-conferencias');
        renderPanoramaGeral(data);
    }

    async function conferirHistoricoConstrucao(construcaoId, num) {
        const incremental = $('ccHistIncremental')?.checked || false;
        const btn = document.querySelector(`.cc-btn-conf-hist[data-id="${construcaoId}"]`);
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Conferindo…';
        }
        try {
            const data = await apiPost('/construcao/' + construcaoId + '/conferir-historico', { incremental });
            if (!data.sucesso) {
                alert(data.erro || 'Erro na conferência.');
                return;
            }
            if (data.conferencia) {
                abrirModalConfHist(num, data.conferencia, data.mensagem);
            }
            if (sessaoAtual) {
                const refreshed = await apiGet('/sessao/' + sessaoAtual.id);
                if (refreshed.sucesso) {
                    sessaoAtual = refreshed.sessao;
                    renderConstrucoes(sessaoAtual);
                }
                await carregarAnaliseHistorica();
                await carregarPanoramaGeral();
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-history"></i> Conferir histórico';
            }
        }
    }

    async function conferirHistoricoTodas() {
        if (!sessaoAtual) return;
        const incremental = $('ccHistIncremental')?.checked || false;
        const btn = $('ccBtnConferirTodas');
        const pane = $('ccTabHistoricoPane');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando…';
        }
        if (pane) pane.classList.add('cc-hist-loading');
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
            const n = data.processadas || 0;
            $('ccSessaoStatus').textContent = `Análise histórica: ${n} construção(ões) processada(s).`;
            await carregarPanoramaGeral();
        } finally {
            if (btn) {
                btn.disabled = !(sessaoAtual && sessaoAtual.construcoes && sessaoAtual.construcoes.length);
                btn.innerHTML = '<i class="fas fa-history"></i> Analisar todas no histórico';
            }
            if (pane) pane.classList.remove('cc-hist-loading');
        }
    }

    function abrirModalConfHist(num, conf, mensagem) {
        $('ccConfHistNum').textContent = '#' + num;
        const corpo = $('ccConfHistCorpo');
        const msg = mensagem ? `<div class="alert alert-success py-2 small">${mensagem}</div>` : '';
        corpo.innerHTML = msg + htmlResumoConferencia(conf);
        modalConfHist?.show();
    }

    async function carregarSessoes() {
        const data = await apiGet('/sessoes');
        const sel = $('ccSelectSessao');
        const cur = sel.value;
        sel.innerHTML = '<option value="">— Carregar sessão —</option>';
        if (data.sucesso && data.sessoes) {
            data.sessoes.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `#${s.id} ${s.nome} (${s.conjunto_base.length} dz)`;
                sel.appendChild(opt);
            });
        }
        if (cur) sel.value = cur;
    }

    async function carregarSessao(id) {
        const data = await apiGet('/sessao/' + id);
        if (!data.sucesso) return;
        sessaoAtual = data.sessao;
        const base = sessaoAtual.conjunto_base || [];
        const origem = sessaoAtual.origem_conjunto || 'manual';
        if (origem === ORIGEM_APOSTAS_10X7) {
            setModoEntrada('apostas10x7', false);
            setSelecionadas(base, ORIGEM_APOSTAS_10X7);
            const el = $('ccApostasParseInfo');
            if (el) {
                el.className = 'small text-muted mb-1';
                el.textContent =
                    `Sessão carregada com origem 10×7 — pool união: ${base.length} dezenas ` +
                    `(${base.map(fmt).join(' ')}). Cole as 10 apostas de novo só se quiser alterar.`;
            }
        } else if (base.length > CONJUNTO_MAX) {
            setModoEntrada('volante', false);
            setSelecionadas(base, origem,
                `Sessão antiga tinha ${base.length} dezenas; exibindo ${CONJUNTO_MAX}. Salve novamente para atualizar.`);
        } else {
            setModoEntrada('volante', false);
            setSelecionadas(base, origem);
        }
        $('ccNomeSessao').value = sessaoAtual.nome;
        $('ccDezenasAposta').value = sessaoAtual.dezenas_por_aposta;
        atualizarEstadoGerar();
        $('ccBtnConferir').disabled = false;
        atualizarBotoesSessaoConstrucoes();
        $('ccSessaoStatus').textContent = `Sessão #${sessaoAtual.id} carregada.`;
        renderConstrucoes(sessaoAtual);
        carregarAnaliseHistorica();
    }

    async function carregarConcursos() {
        const data = await apiGet('/concursos?limit=150');
        const sel = $('ccConcurso');
        sel.innerHTML = '';
        if (data.sucesso && data.concursos) {
            data.concursos.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.concurso;
                opt.textContent = `#${c.concurso} — ${c.data}`;
                sel.appendChild(opt);
            });
        }
    }

    async function conferir() {
        if (!sessaoAtual) return;
        const concurso = parseInt($('ccConcurso').value, 10);
        const data = await apiPost('/conferir', { sessao_id: sessaoAtual.id, concurso });
        const el = $('ccConferencia');
        if (!data.sucesso) {
            el.innerHTML = `<div class="text-danger small">${data.erro}</div>`;
            return;
        }
        const sorteadasSet = new Set(data.sorteadas || []);
        const sortBalls = (data.sorteadas || []).map(d =>
            `<span class="dez-ball-mini cc-acerto">${fmt(d)}</span>`
        ).join('');
        const mesInfo = data.mes_nome
            ? ` · Mês: <strong>${data.mes_nome}</strong>`
            : '';
        let html = `<div class="small mb-2">
            <strong>Concurso ${data.concurso}</strong> (${data.data})${mesInfo}
            <div class="cc-sorteadas-row">${sortBalls}</div>
        </div>`;
        if (data.melhor_construcao) {
            html += `<div class="alert alert-success py-2 small mb-2">
                Melhor: <strong>Construção ${data.melhor_construcao}</strong>
            </div>`;
        }
        html += data.ranking.map(r => {
            const cls = r.construcao_numero === data.melhor_construcao ? ' cc-melhor' : '';
            const cRef = {
                estrategia: r.estrategia,
                distribuicao: r.distribuicao || {},
                estrategia_params: r.estrategia_params || {},
            };
            const apRows = renderApostas(
                r.apostas.map(a => ({ linha: a.linha, dezenas: a.dezenas, acertos: a.acertos })),
                false,
                sorteadasSet,
            );
            return `<div class="cc-construcao-card${cls}">
                <div class="d-flex justify-content-between mb-1">
                    <strong>Construção ${r.construcao_numero}</strong>
                </div>
                ${htmlEstrategiaBadge(cRef)}
                <div class="small mb-1">
                    Máx: <strong>${r.max_acertos}</strong> ac.
                    · Total: ${r.total_acertos}
                    · Média: ${r.media_acertos}
                </div>
                ${apRows}
            </div>`;
        }).join('');
        el.innerHTML = html;
    }

    async function carregarMesesIndicadosBanner() {
        const banner = $('ccMesesIndicadosBanner');
        const txt = $('ccMesesIndicadosTxt');
        if (!banner || !txt) return;
        try {
            const r = await fetch('/geradores-elite/api/meses-indicados');
            const d = await r.json();
            if (!d.sucesso) {
                txt.textContent = d.erro || 'Indisponível';
                banner.classList.remove('alert-success');
                banner.classList.add('alert-warning');
                banner.style.display = '';
                return;
            }
            if (d.sem_indicados) {
                txt.textContent = 'Nenhum (todos os 12 meses saíram na janela)';
                banner.classList.remove('alert-success');
                banner.classList.add('alert-warning');
            } else {
                txt.textContent = (d.meses_indicados || []).map(m => m.mes_abrev).join(' · ') || '—';
            }
            banner.style.display = '';
            window.__CC_MESES_INDICADOS__ = d;
        } catch (e) {
            txt.textContent = 'Erro ao carregar';
            banner.style.display = '';
        }
    }

    function processarImportPendente() {
        try {
            const raw = sessionStorage.getItem('cc_import_pending');
            if (!raw) return;
            const pending = JSON.parse(raw);
            if (!Array.isArray(pending) || !pending.length) {
                sessionStorage.removeItem('cc_import_pending');
                return;
            }
            mostrarBannerPending(pending);
        } catch (_) {
            sessionStorage.removeItem('cc_import_pending');
        }
    }

    function mostrarBannerPending(pending) {
        if (!pending || !pending.length) return;
        let banner = document.getElementById('ccImportPendingBanner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'ccImportPendingBanner';
            banner.className = 'alert alert-info py-2 small mb-2 d-flex flex-wrap align-items-center gap-2';
            const anchor = document.querySelector('#ge-construtor .cc-panel');
            if (anchor) anchor.insertAdjacentElement('afterend', banner);
        }
        const next = pending[0];
        const label = (next.origem || '').includes('posicional') ? 'Posicional' : 'Ordenadas';
        banner.innerHTML = `
            <span><i class="fas fa-clock me-1"></i> Conjunto <strong>${label}</strong> do Diferencial Cruzado aguardando importação.</span>
            <button type="button" class="btn btn-sm btn-primary" id="ccBtnImportPending">Importar agora</button>
            <button type="button" class="btn btn-sm btn-outline-secondary" id="ccBtnDismissPending">Descartar</button>
        `;
        $('ccBtnImportPending')?.addEventListener('click', () => {
            const item = pending.shift();
            if (item && item.dezenas && item.dezenas.length) {
                setSelecionadas(
                    item.dezenas,
                    item.origem || 'diferencial',
                    item.aviso || 'Importado do Diferencial Cruzado.'
                );
            }
            if (pending.length) {
                sessionStorage.setItem('cc_import_pending', JSON.stringify(pending));
                mostrarBannerPending(pending);
            } else {
                sessionStorage.removeItem('cc_import_pending');
                banner.remove();
            }
        }, { once: true });
        $('ccBtnDismissPending')?.addEventListener('click', () => {
            sessionStorage.removeItem('cc_import_pending');
            banner.remove();
        }, { once: true });
    }

    function init() {
        if (HAS_MES) carregarMesesIndicadosBanner();
        renderVolante();
        fillSelectDezenas();
        fillEstrategias();
        updatePoolInfo();
        atualizarEstadoGerar();
        try {
            const raw = sessionStorage.getItem('cc_panorama_import');
            if (raw) {
                const imp = JSON.parse(raw);
                if (imp.dezenas && imp.dezenas.length) {
                    setSelecionadas(
                        imp.dezenas,
                        imp.origem || 'panorama',
                        imp.aviso || 'Importado da aba Panorama Top-3.'
                    );
                    sessionStorage.removeItem('cc_panorama_import');
                }
            }
        } catch (_) { /* ignore */ }
        processarImportPendente();
        carregarSessoes();
        carregarConcursos();
        bindConstrucoesAcoes();

        if (typeof bootstrap !== 'undefined') {
            const elEdit = document.getElementById('ccModalEditar');
            const elExp = document.getElementById('ccModalExport');
            const elHist = document.getElementById('ccModalConfHist');
            if (elEdit) modalEditar = new bootstrap.Modal(elEdit);
            if (elExp) modalExport = new bootstrap.Modal(elExp);
            if (elHist) modalConfHist = new bootstrap.Modal(elHist);
        }
        fillMesSelect($('ccEditMes'), 1);
        if (HAS_MES) fillMesSelect($('ccExportMes'), 1);

        $('ccBtnSalvarEdicao')?.addEventListener('click', salvarEdicao);
        $('ccBtnConfirmarExport')?.addEventListener('click', confirmarExport);

        $('ccBtnCicloSorteadas').addEventListener('click', () => importarCiclo('sorteadas'));
        $('ccBtnCicloFaltantes').addEventListener('click', () => importarCiclo('faltantes'));
        $('ccBtnAnaliseAtraso').addEventListener('click', () => importarAnalise('atraso'));
        $('ccBtnAnaliseFreq').addEventListener('click', () => importarAnalise('frequencia'));
        $('ccBtnLimpar').addEventListener('click', () => setSelecionadas([], 'manual'));
        $('ccModoVolanteBtn')?.addEventListener('click', () => setModoEntrada('volante', true));
        $('ccModoApostasBtn')?.addEventListener('click', () => setModoEntrada('apostas10x7', true));
        $('ccBtnAplicarApostas')?.addEventListener('click', () => aplicarApostas10x7(false));
        $('ccBtnLimparApostas')?.addEventListener('click', () => {
            const ta = $('ccApostasTexto');
            if (ta) ta.value = '';
            selecionadas = new Set();
            origemConjunto = ORIGEM_APOSTAS_10X7;
            updatePoolInfo();
            atualizarInfoParseApostas();
        });
        $('ccApostasTexto')?.addEventListener('input', atualizarInfoParseApostas);
        const drop = $('ccApostasDrop');
        if (drop) {
            ['dragenter', 'dragover'].forEach((ev) => {
                drop.addEventListener(ev, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    drop.classList.add('cc-dragover');
                });
            });
            ['dragleave', 'drop'].forEach((ev) => {
                drop.addEventListener(ev, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    drop.classList.remove('cc-dragover');
                });
            });
            drop.addEventListener('drop', (e) => {
                const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => {
                    const ta = $('ccApostasTexto');
                    if (ta) ta.value = String(reader.result || '');
                    atualizarInfoParseApostas();
                    aplicarApostas10x7(false);
                };
                reader.readAsText(file);
            });
        }
        $('ccBtnSalvarSessao').addEventListener('click', salvarSessao);
        $('ccExigirDigitos')?.addEventListener('change', () => {
            const on = !!($('ccExigirDigitos') && $('ccExigirDigitos').checked);
            if ($('ccDigitosExigidos')) $('ccDigitosExigidos').disabled = !on;
            atualizarSomasDigitosLive([...selecionadas].sort((a, b) => a - b));
        });
        $('ccDigitosExigidos')?.addEventListener('change', () => {
            atualizarSomasDigitosLive([...selecionadas].sort((a, b) => a - b));
        });
        $('ccSomaMin')?.addEventListener('input', () => {
            atualizarSomasDigitosLive([...selecionadas].sort((a, b) => a - b));
        });
        $('ccSomaMax')?.addEventListener('input', () => {
            atualizarSomasDigitosLive([...selecionadas].sort((a, b) => a - b));
        });
        carregarGuiaSomasDigitos();
        $('ccBtnGerar').addEventListener('click', gerarConstrucao);
        $('ccBtnConferir').addEventListener('click', conferir);
        $('ccBtnExportTodas')?.addEventListener('click', abrirExportTodas);
        $('ccBtnConferirTodas')?.addEventListener('click', conferirHistoricoTodas);
        $('ccBtnAtualizarPanorama')?.addEventListener('click', carregarPanoramaGeral);
        $('ccBtnIrPanorama')?.addEventListener('click', () => {
            const tab = document.getElementById('ccTabPanorama');
            if (tab && typeof bootstrap !== 'undefined') {
                bootstrap.Tab.getOrCreateInstance(tab).show();
            }
            carregarPanoramaGeral();
        });
        $('ccTabPanorama')?.addEventListener('shown.bs.tab', carregarPanoramaGeral);
        $('ccColinhaBtn')?.addEventListener('click', toggleColinha);
        $('ccColinhaFechar')?.addEventListener('click', fecharColinha);
        $('ccToggleComoUsar')?.addEventListener('click', () => {
            const corpo = $('ccComoUsarCorpo');
            const btn = $('ccToggleComoUsar');
            if (!corpo || !btn) return;
            const oculto = corpo.classList.toggle('d-none');
            btn.textContent = oculto ? 'Mostrar' : 'Ocultar';
            btn.setAttribute('aria-expanded', oculto ? 'false' : 'true');
        });
        $('ccSelectSessao').addEventListener('change', function () {
            if (this.value) carregarSessao(this.value);
        });

        try {
            if (!localStorage.getItem(COLINHA_KEY)) {
                setTimeout(() => abrirColinha(true), 600);
            }
        } catch (_) {}
    }

    init();
})();
