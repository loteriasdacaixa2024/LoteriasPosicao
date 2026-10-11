/**
 * Aba Concursos Disponíveis — pasta conferencia_apostas + banco Mega-Sena
 */
(function (global) {
    const API = '/central-conferencias/api/conferencia-apostas';
    const ESCOPO_PESQUISA_KEY = 'cd-escopo-pesquisa';
    let concursosDisponiveis = [];
    let concursosSelecionados = [];
    let resultadosProcessamento = {};
    let _inicializado = false;
    let _cacheListaCompleta = null;

    function aplicarEscopoLocal(data, escopo, concursoEspecifico) {
        const lista = data.concursos || [];
        if (escopo === 'ultimo') {
            const apurados = lista.filter(c => c.resultado_disponivel);
            const alvo = apurados[0] || lista[0];
            const concursos = alvo ? [alvo] : [];
            return {
                ...data,
                escopo: 'ultimo',
                concursos,
                total: concursos.length,
                ultimo_apurado: alvo ? alvo.numero_concurso : null,
                mensagem: alvo ? null : 'Nenhum concurso com resultado oficial foi encontrado nas pastas.'
            };
        }
        if (escopo === 'especifico') {
            const n = parseInt(concursoEspecifico, 10);
            const concursos = lista.filter(c => Number(c.numero_concurso) === n);
            return {
                ...data,
                escopo: 'especifico',
                concurso: n,
                concursos,
                total: concursos.length,
                mensagem: concursos.length ? null : `A pasta do concurso ${n} não foi encontrada.`
            };
        }
        return { ...data, escopo: 'todos', total: data.total || lista.length };
    }

    function obterEscopo() {
        const valor = el('cdEscopo') ? el('cdEscopo').value : 'ultimo';
        return ['todos', 'especifico', 'ultimo'].includes(valor) ? valor : 'ultimo';
    }

    function atualizarUiEscopo() {
        const escopo = obterEscopo();
        const grupo = el('cdGrupoEspecifico');
        const hint = el('cdHintEscopo');
        if (grupo) grupo.style.display = escopo === 'especifico' ? '' : 'none';
        if (!hint) return;
        if (escopo === 'ultimo') {
            hint.textContent = 'Abre só a pasta do concurso mais recente que já tem resultado oficial.';
        } else if (escopo === 'especifico') {
            hint.textContent = 'Abre só a pasta do concurso escolhido.';
        } else {
            hint.textContent = 'Lê o apostas.json de cada pasta. Fica mais lento conforme a quantidade de concursos.';
        }
    }

    function salvarEscopo() {
        try {
            sessionStorage.setItem(ESCOPO_PESQUISA_KEY, JSON.stringify({
                escopo: obterEscopo(),
                concurso: el('cdSelectEspecifico')?.value || ''
            }));
        } catch (e) { /* armazenamento indisponível */ }
    }

    function restaurarEscopo() {
        try {
            const raw = sessionStorage.getItem(ESCOPO_PESQUISA_KEY);
            if (raw) {
                const data = JSON.parse(raw);
                const sel = el('cdEscopo');
                if (sel && ['todos', 'especifico', 'ultimo'].includes(data.escopo)) {
                    sel.value = data.escopo;
                }
                const concurso = el('cdSelectEspecifico');
                if (concurso && data.concurso) concurso.dataset.preferido = String(data.concurso);
            }
        } catch (e) { /* ignora preferência inválida */ }
        atualizarUiEscopo();
    }

    function preencherSelectEspecifico(concursos) {
        const select = el('cdSelectEspecifico');
        if (!select) return;
        const preferido = select.dataset.preferido || select.value;
        select.innerHTML = '<option value="">Selecione o concurso...</option>';
        (concursos || []).forEach(concurso => {
            const opt = document.createElement('option');
            opt.value = concurso.numero_concurso;
            const dataStr = concurso.data_sorteio ? ` (${concurso.data_sorteio})` : '';
            const marca = concurso.resultado_disponivel ? '' : ' — sem resultado';
            opt.textContent = `Concurso ${concurso.numero_concurso}${dataStr}${marca}`;
            select.appendChild(opt);
        });
        if (preferido) select.value = preferido;
    }

    function carregarIndice() {
        return fetch(`${API}/concursos-disponiveis?escopo=indice`)
            .then(r => r.json())
            .then(data => {
                if (!data.sucesso) return;
                preencherSelectEspecifico(data.concursos || []);
                if (data.escopo !== 'indice') _cacheListaCompleta = data;
            })
            .catch(err => console.warn('Índice de concursos:', err));
    }

    function textoResumoEscopo(data) {
        const escopo = data.escopo || obterEscopo();
        if (escopo === 'ultimo') {
            const n = data.ultimo_apurado || (data.concursos && data.concursos[0] && data.concursos[0].numero_concurso);
            return n
                ? `Pesquisa limitada ao último concurso apurado: ${n}.`
                : 'Nenhum concurso apurado encontrado.';
        }
        if (escopo === 'especifico') {
            const n = data.concurso || el('cdSelectEspecifico')?.value;
            return `Pesquisa limitada ao concurso ${n}.`;
        }
        return `Pesquisa em todos os concursos (${data.total || (data.concursos || []).length}). O apostas.json de cada pasta foi lido.`;
    }

    function el(id) { return document.getElementById(id); }

    function mostrarErro(msg) {
        el('cdErrorState').style.display = 'block';
        el('cdErrorMessage').textContent = msg;
    }

    function esconderEstados() {
        el('cdLoading').style.display = 'none';
        el('cdLista').style.display = 'none';
        el('cdEmpty').style.display = 'none';
        el('cdErrorState').style.display = 'none';
    }

    async function carregarConcursos() {
        const escopo = obterEscopo();
        const concursoEspecifico = el('cdSelectEspecifico')?.value || '';
        if (escopo === 'especifico' && !concursoEspecifico) {
            esconderEstados();
            mostrarErro('Escolha o concurso antes de pesquisar.');
            return;
        }

        esconderEstados();
        el('cdLoading').style.display = 'block';
        const loadingTexto = el('cdLoading')?.querySelector('p');
        if (loadingTexto) {
            loadingTexto.textContent = escopo === 'todos'
                ? 'Lendo o apostas.json de todos os concursos...'
                : (escopo === 'especifico'
                    ? `Lendo o concurso ${concursoEspecifico}...`
                    : 'Procurando o último concurso apurado...');
        }
        concursosSelecionados = [];
        salvarEscopo();

        const params = new URLSearchParams({ escopo });
        if (escopo === 'especifico') params.set('concurso', concursoEspecifico);
        const timeoutMs = escopo === 'todos' ? 120000 : 30000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            let data;
            if (_cacheListaCompleta && escopo !== 'todos') {
                data = aplicarEscopoLocal(_cacheListaCompleta, escopo, concursoEspecifico);
                _cacheListaCompleta = null;
            } else {
                const r = await fetch(`${API}/concursos-disponiveis?${params.toString()}`, { signal: controller.signal });
                data = await r.json();
                if (data.sucesso && !data.escopo) {
                    data = aplicarEscopoLocal(data, escopo, concursoEspecifico);
                }
            }
            el('cdLoading').style.display = 'none';

            if (!data.sucesso) {
                mostrarErro(data.mensagem || 'Erro ao listar concursos');
                return;
            }

            concursosDisponiveis = data.concursos || [];
            if (concursosDisponiveis.length === 0) {
                const emptyMsg = el('cdEmpty')?.querySelector('p');
                if (emptyMsg && data.mensagem) emptyMsg.textContent = data.mensagem;
                el('cdEmpty').style.display = 'block';
                return;
            }

            renderizarGrid();
            const resumo = el('cdResumoEscopo');
            if (resumo) {
                resumo.style.display = 'block';
                resumo.textContent = textoResumoEscopo(data);
            }
            el('cdEmpty').style.display = 'none';
            el('cdLista').style.display = 'block';
        } catch (e) {
            el('cdLoading').style.display = 'none';
            const segundos = Math.round(timeoutMs / 1000);
            const msg = e.name === 'AbortError'
                ? `Tempo esgotado ao carregar concursos (${segundos}s). Tente Recarregar.`
                : ('Erro de conexão: ' + e.message);
            mostrarErro(msg);
        } finally {
            clearTimeout(timeoutId);
        }
    }

    function renderizarGrid() {
        const container = el('cdContainer');
        const totalBadge = el('cdTotalBadge');
        if (!container) return;

        totalBadge.textContent = `${concursosDisponiveis.length} concurso(s) encontrado(s)`;
        container.innerHTML = '';

        concursosDisponiveis.forEach(c => {
            const podeProcessar = c.resultado_disponivel && c.tem_json;
            const statusBadge = c.resultado_disponivel
                ? '<span class="badge bg-success"><i class="fas fa-check"></i> Resultado no banco</span>'
                : '<span class="badge bg-warning text-dark"><i class="fas fa-exclamation"></i> Sem resultado no banco</span>';

            const fonte = c.tem_json
                ? `<i class="fas fa-file-code text-info"></i> JSON · ${c.total_apostas || 0} aposta(s)`
                : `<i class="fas fa-images text-secondary"></i> ${c.total_screenshots || 0} screenshot(s)`;

            const dezenasBanco = c.dezenas_banco?.length
                ? `<div class="small mt-2"><strong>Sorteadas:</strong> <span class="font-monospace">${c.dezenas_banco.map(n => String(n).padStart(2, '0')).join(' ')}</span></div>`
                : '';

            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4';
            col.innerHTML = `
                <div class="card h-100 cd-card ${podeProcessar ? '' : 'opacity-75'}">
                    <div class="card-body">
                        <div class="form-check">
                            <input class="form-check-input cd-checkbox" type="checkbox"
                                value="${c.numero_concurso}" id="cd-c-${c.numero_concurso}"
                                ${podeProcessar ? '' : 'disabled'}>
                            <label class="form-check-label w-100" for="cd-c-${c.numero_concurso}">
                                <h6 class="mb-1 fw-bold text-success">Concurso ${c.numero_concurso}</h6>
                                <small class="text-muted d-block">${fonte}</small>
                                ${c.data_sorteio ? `<small class="text-muted d-block">${c.data_sorteio}</small>` : ''}
                                ${dezenasBanco}
                                <div class="mt-2">${statusBadge}</div>
                            </label>
                        </div>
                    </div>
                </div>`;
            container.appendChild(col);
        });

        container.querySelectorAll('.cd-checkbox').forEach(cb => {
            cb.addEventListener('change', atualizarSelecao);
        });
        atualizarSelecao();
    }

    function selecionarTodos(flag) {
        document.querySelectorAll('.cd-checkbox:not(:disabled)').forEach(cb => {
            cb.checked = flag;
        });
        atualizarSelecao();
    }

    function atualizarSelecao() {
        concursosSelecionados = Array.from(document.querySelectorAll('.cd-checkbox:checked'))
            .map(cb => parseInt(cb.value, 10));
        const disabled = concursosSelecionados.length === 0;
        el('cdBtnProcessar').disabled = disabled;
        if (el('cdBtnProcessarTopo')) el('cdBtnProcessarTopo').disabled = disabled;
    }

    async function processarSelecionados() {
        if (!concursosSelecionados.length) return;

        el('cdCardProgresso').style.display = 'block';
        const totalProc = concursosSelecionados.length;
        el('cdProgressoItems').innerHTML = `
            <div class="small mb-2">
                <div class="d-flex justify-content-between mb-1">
                    <span>Processando ${totalProc} concurso(s)...</span>
                    <span id="cdProgPct">0%</span>
                </div>
                <div class="progress" style="height:12px;background:var(--accent-light,#fffaf0);">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         id="cdProgBar" role="progressbar" style="width:0%;background:var(--primary,#c08b00);"></div>
                </div>
            </div>`;
        resultadosProcessamento = {};
        const inicioMs = performance.now();

        for (let i = 0; i < concursosSelecionados.length; i++) {
            const num = concursosSelecionados[i];
            await processarUm(num, i + 1, totalProc);
            const pct = Math.round(((i + 1) / totalProc) * 100);
            const bar = el('cdProgBar');
            const lbl = el('cdProgPct');
            if (bar) bar.style.width = pct + '%';
            if (lbl) lbl.textContent = pct + '%';
        }

        const elapsedMs = performance.now() - inicioMs;
        Object.values(resultadosProcessamento).forEach(r => {
            if (r && r.sucesso) r._elapsedMs = elapsedMs;
        });
        if (window.ConferenciaResultadosUI) {
            ConferenciaResultadosUI.mostrarResultados(resultadosProcessamento);
        }
    }

    async function processarUm(concurso, index, total) {
        const itemId = `cd-prog-${concurso}`;
        el('cdProgressoItems').insertAdjacentHTML('beforeend', `
            <div class="card mb-2" id="${itemId}">
                <div class="card-body py-2 small">
                    <strong>Concurso ${concurso}</strong>
                    <span class="badge bg-primary ms-2">${index}/${total}</span>
                    <div class="text-muted mt-1" id="${itemId}-status">Conferindo apostas...</div>
                </div>
            </div>`);

        const statusEl = el(`${itemId}-status`);
        try {
            const r = await fetch(`${API}/processar/${concurso}`, { method: 'POST' });
            const data = await r.json();
            if (data.sucesso) {
                resultadosProcessamento[concurso] = data;
                const faixas = data.resumo.distribuicao_faixas || {};
                const partes = Object.entries(faixas)
                    .filter(([, d]) => d && d.quantidade)
                    .map(([nome, d]) => `${d.quantidade}× ${nome}`);
                const premio = partes.length ? partes.join(', ') : 'sem faixa premiada';
                statusEl.innerHTML = `<span class="text-success"><i class="fas fa-check-circle"></i> OK — `
                    + `${data.resumo.premiadas || 0} premiada(s) · ${premio} · `
                    + `${data.resumo.total_apostas_validas} apostas · investido `
                    + `R$ ${Number(data.resumo.total_investido || 0).toFixed(2).replace('.', ',')}</span>`;
            } else {
                statusEl.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${data.mensagem || 'Erro'}</span>`;
            }
        } catch (e) {
            statusEl.innerHTML = `<span class="text-danger">Erro: ${e.message}</span>`;
        }
    }

    function bindEvents() {
        el('cdEscopo')?.addEventListener('change', atualizarUiEscopo);
        el('cdBtnPesquisarEscopo')?.addEventListener('click', () => {
            salvarEscopo();
            carregarConcursos();
        });
        el('cdSelecionarTodos')?.addEventListener('change', e => selecionarTodos(e.target.checked));
        el('cdBtnProcessar')?.addEventListener('click', processarSelecionados);
        el('cdBtnProcessarTopo')?.addEventListener('click', processarSelecionados);
        el('cdBtnRecarregar')?.addEventListener('click', carregarConcursos);
        el('cdBtnRecarregarTopo')?.addEventListener('click', carregarConcursos);
    }

    function init() {
        if (_inicializado) {
            carregarConcursos();
            return;
        }
        _inicializado = true;
        restaurarEscopo();
        bindEvents();
        carregarIndice().finally(() => carregarConcursos());
    }

    global.ConcursosDisponiveis = { init, recarregar: carregarConcursos };
})(window);
