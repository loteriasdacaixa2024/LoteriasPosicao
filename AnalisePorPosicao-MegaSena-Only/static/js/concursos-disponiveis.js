/**
 * Aba Concursos Disponíveis — pasta conferencia_apostas + banco Mega-Sena
 */
(function (global) {
    const API = '/central-conferencias/api/conferencia-apostas';
    let concursosDisponiveis = [];
    let concursosSelecionados = [];
    let resultadosProcessamento = {};
    let _inicializado = false;

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
        esconderEstados();
        el('cdLoading').style.display = 'block';
        concursosSelecionados = [];

        try {
            const r = await fetch(`${API}/concursos-disponiveis`);
            const data = await r.json();
            el('cdLoading').style.display = 'none';

            if (!data.sucesso) {
                mostrarErro(data.mensagem || 'Erro ao listar concursos');
                return;
            }

            concursosDisponiveis = data.concursos || [];
            if (concursosDisponiveis.length === 0) {
                el('cdEmpty').style.display = 'block';
                return;
            }

            renderizarGrid();
            el('cdEmpty').style.display = 'none';
            el('cdLista').style.display = 'block';
        } catch (e) {
            el('cdLoading').style.display = 'none';
            mostrarErro('Erro de conexão: ' + e.message);
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
                ? `<i class="fas fa-file-code text-info"></i> JSON · ${c.total_apostas} aposta(s)`
                : `<i class="fas fa-images text-secondary"></i> ${c.total_screenshots} screenshot(s)`;

            const dezenasBanco = c.dezenas_banco?.length
                ? `<div class="small mt-2"><strong>Sorteadas:</strong> <span class="font-monospace">${c.dezenas_banco.join(' ')}</span></div>`
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
                <div class="progress" style="height:12px;background:var(--ms-90,#d4f7e9);">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         id="cdProgBar" role="progressbar" style="width:0%;background:var(--ms-35,#1b9a67);"></div>
                </div>
            </div>`;
        resultadosProcessamento = {};

        for (let i = 0; i < concursosSelecionados.length; i++) {
            const num = concursosSelecionados[i];
            await processarUm(num, i + 1, totalProc);
            const pct = Math.round(((i + 1) / totalProc) * 100);
            const bar = el('cdProgBar');
            const lbl = el('cdProgPct');
            if (bar) bar.style.width = pct + '%';
            if (lbl) lbl.textContent = pct + '%';
        }

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
                statusEl.innerHTML = `<span class="text-success"><i class="fas fa-check-circle"></i> OK — `
                    + `${data.resumo.quadras} quadra(s), ${data.resumo.quinas} quina(s), `
                    + `${data.resumo.senas} sena(s) · ${data.resumo.total_apostas_validas} apostas</span>`;
            } else {
                statusEl.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle"></i> ${data.mensagem || 'Erro'}</span>`;
            }
        } catch (e) {
            statusEl.innerHTML = `<span class="text-danger">Erro: ${e.message}</span>`;
        }
    }

    function bindEvents() {
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
        bindEvents();
        carregarConcursos();
    }

    global.ConcursosDisponiveis = { init, recarregar: carregarConcursos };
})(window);
