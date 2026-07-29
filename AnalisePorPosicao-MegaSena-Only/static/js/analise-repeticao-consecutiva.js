/**
 * Aba Repetição Consecutiva — dezenas repetidas entre concursos seguidos
 */
(function (global) {
    let _data = null;

    function pctFmt(p) {
        return (typeof p === 'number' ? p : 0).toFixed(1).replace('.', ',') + '%';
    }

    function showExemploModal(ex) {
        if (!ex) return;
        Swal.fire({
            title: `Concurso #${ex.concurso}`,
            html: `
                <p class="small text-muted mb-1">Anterior: #${ex.concurso_anterior} (${ex.data_anterior || ''})</p>
                <p class="small mb-2"><strong>Anterior:</strong> ${(ex.dezenas_anterior || []).join(' • ')}</p>
                <p class="small text-muted mb-1">Atual: (${ex.data || ''})</p>
                <p class="small mb-2"><strong>Atual:</strong> ${(ex.dezenas || []).join(' • ')}</p>
                <p class="fw-bold text-success mb-0">
                    ${ex.quantidade} repetida(s): ${(ex.repetidas || []).join(', ') || '—'}
                </p>
            `,
            width: 480,
            confirmButtonText: 'Fechar',
        });
    }

    function bindHoverExemplos(root, exemplos) {
        if (!exemplos || !exemplos.length) return;
        const tip = exemplos.slice(0, 3).map(ex =>
            `#${ex.concurso}: ${ex.repetidas?.join(', ') || '0'} rep.`
        ).join(' | ');
        root.querySelectorAll('[data-rep-hover]').forEach(el => {
            el.title = tip;
            el.style.cursor = 'help';
        });
        root.querySelectorAll('[data-rep-exemplo]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const idx = parseInt(btn.dataset.idx || '0', 10);
                showExemploModal(exemplos[idx] || exemplos[0]);
            });
        });
    }

    function renderDistribuicao() {
        const body = document.getElementById('tblRepConsecDist');
        if (!body || !_data) return;
        body.innerHTML = (_data.distribuicao || []).map((r, i) => `
            <tr data-rep-hover>
                <td>${r.repeticoes}
                    ${r.exemplos?.length ? `<button type="button" class="btn btn-link btn-sm p-0 ms-1" data-rep-exemplo data-idx="0" title="Ver exemplos"><i class="fas fa-eye"></i></button>` : ''}
                </td>
                <td class="text-end fw-bold rep-hover-qtd" data-rep-hover>${(r.quantidade || 0).toLocaleString()}</td>
                <td class="text-end font-monospace rep-hover-pct" data-rep-hover>${pctFmt(r.porcentagem)}</td>
            </tr>
        `).join('');
        bindHoverExemplos(body.closest('table') || body, null);
        (_data.distribuicao || []).forEach((r, rowIdx) => {
            const tr = body.children[rowIdx];
            if (tr && r.exemplos?.length) bindHoverExemplos(tr, r.exemplos);
        });
    }

    function renderUltimo() {
        const el = document.getElementById('repConsecUltimo');
        if (!el || !_data) return;
        const u = _data.ultimo_concurso_analise;
        if (!u) {
            el.innerHTML = '<p class="text-muted">Sem dados.</p>';
            return;
        }
        el.innerHTML = `
            <table class="table table-sm mb-0">
                <tr><td>Dezenas repetidas do concurso anterior</td><td class="fw-bold text-end">${u.dezenas_repetidas_qtd}</td></tr>
                <tr><td>Quais dezenas repetiram</td><td class="fw-bold text-end">${u.dezenas_repetidas.join(', ') || '—'}</td></tr>
                <tr><td>Concurso anterior (#${u.concurso_anterior})</td><td class="text-end font-monospace">${u.dezenas_anterior.join(' • ')}</td></tr>
                <tr><td>Último concurso (#${u.concurso})</td><td class="text-end font-monospace">${u.dezenas_atual.join(' • ')}</td></tr>
                <tr><td>Frequência histórica dessa estrutura</td><td class="fw-bold text-end">${u.freq_historica_estrutura.toLocaleString()} concursos</td></tr>
                <tr><td>Similaridade histórica</td><td class="fw-bold text-end">${pctFmt(u.pct_historica_estrutura)}</td></tr>
            </table>
        `;
    }

    function renderAvancado() {
        const seq = _data?.sequencias || {};
        const seqEl = document.getElementById('repConsecSequencias');
        if (seqEl) {
            const s0 = seq.maior_sem_repeticao || {};
            const s1 = seq.maior_com_repeticao || {};
            seqEl.innerHTML = `
                <li>Maior sequência <strong>sem</strong> repetição: <strong>${s0.concursos || 0}</strong> concursos
                    ${s0.de ? `(#${s0.de} a #${s0.ate})` : ''}</li>
                <li>Maior sequência <strong>com</strong> repetição (≥1): <strong>${s1.concursos || 0}</strong> concursos
                    ${s1.de ? `(#${s1.de} a #${s1.ate})` : ''}</li>
                <li>Média histórica de repetição: <strong>${_data.media_historica}</strong> dezenas por transição</li>
            `;
        }

        const tend = document.getElementById('repConsecTendencia');
        if (tend && _data.tendencia_recente_100) {
            const t = _data.tendencia_recente_100;
            tend.innerHTML = `
                <p class="mb-1">Últimos 100 concursos: média <strong>${t.media}</strong> — tendência <strong>${t.tendencia}</strong>
                (histórico: ${t.media_historica})</p>
            `;
        }

        const j10 = document.getElementById('repConsecUlt10');
        const j30 = document.getElementById('repConsecUlt30');
        if (j10 && _data.ultimos_10?.concursos) {
            j10.innerHTML = `Média ${ _data.ultimos_10.media_repeticao }, moda ${ _data.ultimos_10.moda_repeticao } repetições`;
        }
        if (j30 && _data.ultimos_30?.concursos) {
            j30.innerHTML = `Média ${ _data.ultimos_30.media_repeticao }, moda ${ _data.ultimos_30.moda_repeticao } repetições`;
        }

        const decBody = document.getElementById('tblRepConsecDecada');
        if (decBody) {
            decBody.innerHTML = (_data.media_por_decada || []).map(d => `
                <tr><td>${d.decada}</td><td class="text-end fw-bold">${d.media}</td><td class="text-end">${d.concursos}</td></tr>
            `).join('');
        }

        const anoBody = document.getElementById('tblRepConsecAno');
        if (anoBody) {
            const recent = (_data.media_por_ano || []).slice(-12);
            anoBody.innerHTML = recent.map(d => `
                <tr><td>${d.ano}</td><td class="text-end fw-bold">${d.media}</td><td class="text-end">${d.concursos}</td></tr>
            `).join('');
        }
    }

    function renderSugestoes() {
        const el = document.getElementById('repConsecSugestoes');
        if (!el || !_data?.sugestoes_estruturais) return;
        const s = _data.sugestoes_estruturais;
        el.innerHTML = `
            <ul class="mb-2">${(s.itens || []).map(i => `<li>${i}</li>`).join('')}</ul>
            <p class="mb-0 fw-bold text-success"><i class="fas fa-compass me-1"></i>Estrutura sugerida: ${s.estrutura_sugerida}</p>
        `;
    }

    function render() {
        if (!_data) return;
        renderDistribuicao();
        renderUltimo();
        renderAvancado();
        renderSugestoes();
        const meta = document.getElementById('repConsecMeta');
        if (meta) {
            meta.textContent = `${_data.total_pares_analisados.toLocaleString()} transições analisadas (concursos 2 ao ${_data.ultimo_concurso})`;
        }
    }

    async function load() {
        if (_data) return _data;
        const resp = await fetch('/analise/api/repeticao-consecutiva');
        const data = await resp.json();
        if (data.status !== 'success') throw new Error(data.message || 'Erro repetição consecutiva');
        _data = data;
        return data;
    }

    global.AnaliseRepeticaoConsecutiva = {
        load,
        render,
        get data() { return _data; },
    };
})(window);
