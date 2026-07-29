/**
 * UI "Resultados do Processamento" — Mega-Sena
 * Coberturas, Valor Ganhos, Cards e Análise de Variância (ABS)
 */
(function (global) {
    const DEZENAS_SORTEIO = 6;

    /** Paleta oficial Mega-Sena (#1B9A67) */
    const MS = {
        c0: '#000000', c5: '#04160f', c10: '#082b1d', c15: '#0b412c', c20: '#0f573a',
        c25: '#136c49', c30: '#178257', c35: '#1b9a67', c40: '#1fad74', c45: '#22c383',
        c50: '#26d991', c55: '#3cdd9c', c60: '#52e0a7', c65: '#67e4b2', c70: '#7de8bd',
        c75: '#93ecc8', c80: '#a8f0d3', c85: '#bef4de', c90: '#d4f7e9', c95: '#e9fbf4', c100: '#ffffff',
    };

    function fmtMoeda(v) {
        return 'R$ ' + (v || 0).toFixed(2).replace('.', ',');
    }

    function _categoriaAposta(resultado) {
        return resultado.melhor_categoria ||
            (resultado.acertos >= 6 ? 'sena' : resultado.acertos === 5 ? 'quina' :
                resultado.acertos === 4 ? 'quadra' : 'outro');
    }

    function _proxAte1(n, setNums) {
        if (!setNums) return 99;
        if (setNums.has(n)) return 0;
        if (setNums.has(n - 1) || setNums.has(n + 1)) return 1;
        return 99;
    }

    function _classeDezenaCard(n, acertados, cat, idx, sorteadosSet) {
        const hit = acertados.has(n);
        const extra = idx >= DEZENAS_SORTEIO;
        let cls = extra ? 'cr-dez cr-dez-extra' : 'cr-dez cr-dez-neutro';
        if (hit) {
            cls += (cat === 'quadra') ? ' cr-dez-acerto-quadra' : ' cr-dez-acerto';
        } else if (_proxAte1(n, sorteadosSet) === 1) {
            cls += ' cr-dez-prox1';
        }
        return cls;
    }

    function renderizarAposta(aposta, sorteadosSet) {
        const resultado = aposta.resultado || {};
        const nums = aposta.numeros_apostados || aposta.numeros || [];
        const numsInt = nums.map(n => parseInt(n, 10));
        const temPremio = (aposta.valor_ganho || 0) > 0;
        const acertados = new Set((resultado.numeros_acertados || []).map(n => parseInt(n, 10)));
        const cat = _categoriaAposta(resultado);

        let cardClass = 'cr-aposta-card';
        if (cat === 'sena' || cat === 'quina') cardClass += ' cr-card-premio-alto';
        else if (cat === 'quadra') cardClass += ' cr-card-quadra';

        const badgeClasse =
            cat === 'sena' || cat === 'quina' ? 'cr-badge-ms cr-badge-ms-alto' :
            cat === 'quadra' ? 'cr-badge-ms cr-badge-ms-quadra' :
            'cr-badge-ms';

        const acertosVolante = resultado.acertos_volante ?? acertados.size;

        return `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 ${cardClass}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-0" style="color:${MS.c20}">Aposta ${aposta.numero_aposta}</h6>
                        ${temPremio ? '<i class="fas fa-trophy" style="color:' + MS.c40 + '"></i>' : ''}
                    </div>
                    <span class="badge mb-2" style="background:${MS.c25};color:${MS.c100}"><i class="fas fa-file-code"></i> JSON</span>
                    <div class="d-flex flex-wrap gap-1 mb-2">
                        ${numsInt.map((n, i) =>
                            `<span class="${_classeDezenaCard(n, acertados, cat, i, sorteadosSet)}">${String(n).padStart(2, '0')}</span>`
                        ).join('')}
                    </div>
                    <div class="mb-2">
                        <span class="badge ${badgeClasse}">
                            ${acertosVolante} acerto(s) no volante
                            ${resultado.acertos > 0 && resultado.acertos !== acertosVolante
                                ? ` · melhor comb.: ${resultado.acertos}` : ''}
                        </span>
                    </div>
                    ${resultado.detalhes_premios && resultado.detalhes_premios.length ? `
                        <div class="alert alert-success py-2 px-2 mb-2 small">
                            ${resultado.detalhes_premios.map(p => `
                                <div class="d-flex justify-content-between">
                                    <span><strong>${p.descricao}</strong></span>
                                    <span class="text-success fw-bold">${fmtMoeda(p.valor)}</span>
                                </div>`).join('')}
                        </div>` : ''}
                    <div class="fw-bold ${temPremio ? 'text-success' : 'text-muted'}">
                        ${temPremio ? 'Ganhos: ' : ''}${fmtMoeda(aposta.valor_ganho || 0)}
                    </div>
                    <a href="#" class="small cr-link-historico d-block mt-2"
                       onclick="ConferenciaResultadosUI.abrirHistoricoAposta([${numsInt.join(',')}], this); return false;">
                        <i class="fas fa-search"></i> Ver Histórico Jogo
                    </a>
                </div>
            </div>
        </div>`;
    }

    function renderizarCobertura(resultado) {
        const sorteados = _numerosOficiais(resultado);
        const dezenasJogadas = new Set();
        (resultado.apostas || []).forEach(ap => {
            (ap.numeros_apostados || []).forEach(n => dezenasJogadas.add(parseInt(n, 10)));
        });

        const cobertas = [];
        const perdidas = [];
        sorteados.forEach(n => {
            if (dezenasJogadas.has(parseInt(n, 10))) cobertas.push(n);
            else perdidas.push(n);
        });

        const pct = sorteados.length ? (cobertas.length / sorteados.length) * 100 : 0;
        const barStyle = pct === 100
            ? `background:${MS.c35}`
            : pct >= 60 ? `background:${MS.c55}` : `background:${MS.c25}`;

        return `
        <div class="row mb-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm cr-cobertura-card">
                    <div class="card-header bg-transparent border-0 d-flex justify-content-between align-items-center">
                        <h6 class="mb-0" style="color:${MS.c30}"><i class="fas fa-bullseye"></i> Cobertura de Acertos Inteligente</h6>
                        <span class="badge rounded-pill" style="background:${MS.c35};color:${MS.c100}">${cobertas.length}/${DEZENAS_SORTEIO} Cobertas</span>
                    </div>
                    <div class="card-body py-3">
                        <div class="row align-items-center">
                            <div class="col-md-5 mb-3 mb-md-0">
                                <small class="text-muted d-block mb-2">Eficiência da sua cobertura sobre o resultado oficial:</small>
                                <div class="progress" style="height: 25px;">
                                    <div class="progress-bar progress-bar-striped" style="width:${pct}%;${barStyle}">
                                        <strong>${pct.toFixed(0)}%</strong>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-7">
                                <div class="d-flex flex-wrap justify-content-md-end gap-2">
                                    ${cobertas.map(n => `
                                        <div class="text-center">
                                            <span class="badge shadow-sm p-2 mb-1" style="font-size:1.1em;background:${MS.c35};color:${MS.c100};border:2px solid ${MS.c25};">${String(n).padStart(2, '0')}</span>
                                            <div style="font-size:0.7em;color:${MS.c25};font-weight:bold;">COBERTA</div>
                                        </div>`).join('')}
                                    ${perdidas.map(n => `
                                        <div class="text-center">
                                            <span class="badge bg-light text-danger shadow-sm p-2 mb-1" style="font-size:1.1em;border:2px dashed #dc3545;">${String(n).padStart(2, '0')}</span>
                                            <div style="font-size:0.7em;color:#dc3545;font-weight:bold;">PERDIDA</div>
                                        </div>`).join('')}
                                </div>
                                ${perdidas.length ? `
                                    <div class="text-end mt-2">
                                        <small class="text-danger"><i class="fas fa-exclamation-triangle"></i>
                                        Você não jogou ${perdidas.length === 1 ? 'este número' : 'estes ' + perdidas.length + ' números'} em nenhuma aposta!</small>
                                    </div>` : `
                                    <div class="text-end mt-2">
                                        <small class="text-success"><i class="fas fa-check-double"></i>
                                        Excelência! Todos os números sorteados estavam em seus jogos.</small>
                                    </div>`}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function renderizarDistribuicaoFaixas(resumo) {
        const faixas = resumo.distribuicao_faixas || {};
        const rows = Object.entries(faixas).map(([faixa, dados]) => `
            <tr>
                <td>${faixa}</td>
                <td>${dados.quantidade}x</td>
                <td class="text-success fw-bold">${fmtMoeda(dados.total_ganho)}</td>
            </tr>`).join('');

        return `
        <div class="row mb-4">
            <div class="col-12">
                <h6>Distribuição de Acertos por Faixa:</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead><tr><th>Faixa</th><th>Quantidade</th><th>Total Ganho</th></tr></thead>
                        <tbody>
                            ${rows || `<tr><td colspan="3" class="text-center text-muted">Nenhuma aposta premiada neste concurso</td></tr>`}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;
    }

    /** Destaque por conjunto (Mega-Sena: ordem não importa) — verde = acerto, amarelo = ±1 */
    function _bgClasseVolante(n, setRef) {
        const p = _proxAte1(n, setRef);
        if (p === 0) return 'bg-success text-white fw-bold shadow-sm';
        if (p === 1) return 'bg-warning text-dark fw-bold shadow-sm';
        return 'text-dark';
    }

    /** Tabela de variância — visual Dia de Sorte; destaque Mega-Sena por conjunto */
    function renderizarTabelaDesvio(concurso, resultado) {
        const sorteados = [..._numerosOficiais(resultado)].sort((a, b) => a - b);
        if (!sorteados.length) {
            return '<div class="alert alert-warning">Resultado oficial não disponível.</div>';
        }
        const sorteadosSet = new Set(sorteados.map(n => parseInt(n, 10)));

        let maxDezenas = DEZENAS_SORTEIO;
        (resultado.apostas || []).forEach(ap => {
            const n = (ap.numeros_apostados || []).length;
            if (n > maxDezenas) maxDezenas = n;
        });
        const numColunas = Math.max(DEZENAS_SORTEIO, Math.min(maxDezenas, 20));

        let tableRows = '';
        (resultado.apostas || []).forEach((aposta, rowIdx) => {
            const numeros = aposta.numeros_apostados || [];
            if (numeros.length < DEZENAS_SORTEIO) return;

            const volanteSet = new Set(numeros.map(n => parseInt(n, 10)));
            const numerosOrdenados = [...volanteSet].sort((a, b) => a - b).slice(0, numColunas);
            const dataLabel = `${resultado.resultado_sorteio?.data || resultado.data_sorteio || ''} - ${concurso} - ${aposta.numero_aposta ?? rowIdx + 1}`;

            let rowHtml = `<tr style="height: 32px;">
                <td class="align-middle fw-bold text-muted text-center text-nowrap p-1" style="font-size: 0.85rem;">${dataLabel}</td>`;

            let jogadosHtml = '';
            for (let i = 0; i < numColunas; i++) {
                const num = numerosOrdenados[i];
                if (num !== undefined) {
                    const bgClass = _bgClasseVolante(num, sorteadosSet);
                    jogadosHtml += `<td class="align-middle text-center bg-white" style="width:30px; border: 1px dashed #dee2e6; padding: 0.25rem;">
                        <div style="width: 26px; height: 26px; line-height: 26px; margin: 0 auto; border-radius: 4px;" class="${bgClass}">${String(num).padStart(2, '0')}</div>
                    </td>`;
                } else {
                    jogadosHtml += `<td class="align-middle text-center bg-white" style="width:30px; border: 1px dashed #dee2e6; padding: 0.25rem;">-</td>`;
                }
            }
            rowHtml += jogadosHtml;
            rowHtml += `<td style="width: 8px; background: #fff; border: none;"></td>`;

            let sorteadosHtml = '';
            for (let i = 0; i < numColunas; i++) {
                if (i < DEZENAS_SORTEIO) {
                    const sort = sorteados[i];
                    const bgClass = _bgClasseVolante(sort, volanteSet);
                    sorteadosHtml += `<td class="align-middle text-center bg-white" style="width:30px; border: 1px dashed #dee2e6; padding: 0.25rem;">
                        <div style="width: 26px; height: 26px; line-height: 26px; margin: 0 auto; border-radius: 4px;" class="${bgClass}">${String(sort).padStart(2, '0')}</div>
                    </td>`;
                } else {
                    sorteadosHtml += `<td class="align-middle text-center bg-white" style="width:30px; border: 1px dashed #dee2e6; padding: 0.25rem;"></td>`;
                }
            }
            rowHtml += sorteadosHtml;
            rowHtml += `<td style="width: 8px; background: #fff; border: none;"></td>`;

            let diffHtml = '';
            let somaAbsRow = 0;
            let countDeltasRow = 0;
            for (let i = 0; i < numColunas; i++) {
                if (i < DEZENAS_SORTEIO && numerosOrdenados[i] !== undefined) {
                    const delta = numerosOrdenados[i] - sorteados[i];
                    somaAbsRow += Math.abs(delta);
                    countDeltasRow++;
                    const deltaStr = delta === 0 ? '' : delta;
                    const textClass = delta < 0 ? 'text-danger' : 'text-dark';
                    diffHtml += `<td class="align-middle text-center p-1 ${textClass}" style="width:30px; border: 1px dashed #dee2e6; font-size:0.9rem;">${deltaStr}</td>`;
                } else {
                    diffHtml += `<td class="align-middle text-center p-1 bg-white" style="width:30px; border: 1px dashed #dee2e6;"></td>`;
                }
            }
            rowHtml += diffHtml;
            rowHtml += `<td style="width: 8px; background: #fff; border: none;"></td>`;

            let absCor = 'text-dark';
            if (countDeltasRow > 0) {
                if (somaAbsRow <= 7) absCor = 'text-success fw-bold';
                else if (somaAbsRow <= 14) absCor = 'text-warning fw-bold';
            }
            rowHtml += `<td class="align-middle text-center p-1 ${absCor}" style="width:50px; font-size:0.9rem;">${countDeltasRow > 0 ? somaAbsRow : '-'}</td>`;
            rowHtml += `<td style="width: 8px; background: #fff; border: none;"></td>`;

            const res = aposta.resultado || {};
            const maxAc = res.acertos || 0;
            rowHtml += `<td class="align-middle text-center p-1" style="width:25px; border: 1px dashed #dee2e6; font-size:0.8rem; font-weight:bold;">${maxAc >= 4 && maxAc < 5 ? '★' : ''}</td>`;
            rowHtml += `<td class="align-middle text-center p-1" style="width:25px; border: 1px dashed #dee2e6; font-size:0.8rem; font-weight:bold;">${maxAc === 5 ? '★' : ''}</td>`;
            rowHtml += `<td class="align-middle text-center p-1" style="width:25px; border: 1px dashed #dee2e6; font-size:0.8rem; font-weight:bold; color: #27ae60;">${maxAc >= 6 ? '★' : ''}</td>`;
            rowHtml += '</tr>';
            tableRows += rowHtml;
        });

        let theadNums = '';
        for (let i = 1; i <= numColunas; i++) {
            theadNums += `<th class="text-center p-1" style="width:30px;">${i}</th>`;
        }

        return `
        <div class="card border-0 shadow-sm mb-4 cr-variancia-table" style="border-radius: 8px; border: 1px solid #ccc;">
            <div class="table-responsive" style="overflow-y: hidden;">
                <table class="table table-sm table-borderless mb-0" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                    <thead style="background-color: #f1f3f5; border-bottom: 2px solid #dee2e6;">
                        <tr>
                            <th class="align-middle text-center p-2" style="width: 195px; border-right: 2px solid #dee2e6;">DATA</th>
                            <th colspan="${numColunas}" class="text-center p-2 fw-bold" style="letter-spacing: 1px;">NÚMEROS JOGADOS</th>
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th colspan="${numColunas}" class="text-center p-2 fw-bold" style="letter-spacing: 1px;">SORTEADOS</th>
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th colspan="${numColunas}" class="text-center p-2 text-danger fw-bold" style="letter-spacing: 1px;">DIFERENÇA</th>
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th class="align-middle text-center p-2 fw-bold text-primary" style="width: 50px; border-right: 2px solid #dee2e6;" title="Valor Absoluto: Soma das diferenças sem sinal">ABS</th>
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th colspan="3" class="align-middle text-center p-2" style="width: 75px;">ACERTO</th>
                        </tr>
                        <tr style="border-bottom: 2px solid #dee2e6; font-size: 0.8rem; background-color: #f8f9fa;">
                            <th style="border-right: 2px solid #dee2e6;"></th>
                            ${theadNums}
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            ${theadNums}
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            ${theadNums}
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th style="border-right: 2px solid #dee2e6;"></th>
                            <th style="width: 8px; background: #fff; border: none;"></th>
                            <th class="text-center p-1" style="width:25px; background: #e0e0e0; color: #333; border: 1px dashed #dee2e6;">4</th>
                            <th class="text-center p-1" style="width:25px; background: #c0c0c0; color: #333; border: 1px dashed #dee2e6;">5</th>
                            <th class="text-center p-1" style="width:25px; background: #f1c40f; color: #000; border: 1px dashed #dee2e6;">6</th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        </div>`;
    }

    function _numerosOficiais(resultado) {
        if (resultado.resultado_sorteio?.numeros?.length) {
            return resultado.resultado_sorteio.numeros.map(n => parseInt(n, 10));
        }
        return (resultado.dezenas_sorteadas || []).map(n => parseInt(n, 10));
    }

    function renderizarRelatorioConcurso(concurso, resultado) {
        const resumo = resultado.resumo || {};
        const investido = resumo.total_investido ?? 0;
        const ganho = resumo.total_ganho ?? 0;
        const lucro = ganho - investido;
        const roi = investido > 0 ? ((lucro / investido) * 100).toFixed(2) : '0.00';

        const numsOficiais = _numerosOficiais(resultado);
        const sorteadosSet = new Set(numsOficiais.map(n => parseInt(n, 10)));
        const fonte = resultado.fonte_dados || resultado.origem || 'JSON';
        const fonteBadge = fonte === 'JSON'
            ? '<span class="badge bg-info"><i class="fas fa-file-code"></i> Dados: arquivo JSON</span>'
            : '<span class="badge bg-secondary"><i class="fas fa-images"></i> Dados: Screenshots OCR</span>';

        return `
        <div class="alert alert-info mb-4">
            ${fonteBadge}
            <small class="ms-2 text-muted">Apostas carregadas do arquivo apostas.json</small>
        </div>

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="text-muted mb-0">Resultado Oficial</h6>
                            <button type="button" class="btn btn-sm btn-warning fw-bold"
                                onclick="ConferenciaResultadosUI.toggleOrdemNumeros(${concurso})"
                                id="toggle-ordem-${concurso}">
                                <i class="fas fa-sort-amount-down"></i> Nº Ordem
                            </button>
                        </div>
                        <div class="d-flex flex-wrap gap-2" id="numeros-resultado-${concurso}">
                            ${numsOficiais.map(n => `
                                <span class="cr-bola-oficial">${String(n).padStart(2, '0')}</span>`).join('')}
                        </div>
                        <span class="badge bg-success mt-2">Mega-Sena</span>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card ${lucro >= 0 ? 'bg-success' : 'bg-danger'} text-white">
                    <div class="card-body">
                        <h6 class="mb-2">Resultado Financeiro</h6>
                        <div class="mb-1"><small>Investido:</small><strong class="ms-2">${fmtMoeda(investido)}</strong></div>
                        <div class="mb-1"><small>Ganho:</small><strong class="ms-2">${fmtMoeda(ganho)}</strong></div>
                        <hr class="my-2 bg-white opacity-75">
                        <div>
                            <strong>${lucro >= 0 ? 'LUCRO' : 'PREJUÍZO'}:</strong>
                            <strong class="ms-2 fs-5">${fmtMoeda(Math.abs(lucro))}</strong>
                            <span class="ms-2">(${roi >= 0 ? '+' : ''}${roi}%)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        ${renderizarCobertura(resultado)}
        ${renderizarDistribuicaoFaixas(resumo)}

        <div class="d-flex justify-content-center mb-4 mt-2">
            <div class="btn-group shadow-sm cr-visao-toggle" role="group">
                <button type="button" class="btn btn-outline-primary active px-4 py-2"
                    id="btn-visao-cards-${concurso}"
                    onclick="ConferenciaResultadosUI.alternarVisao(${concurso}, 'cards')">
                    <i class="fas fa-th-large me-1"></i> Visão em Cards
                </button>
                <button type="button" class="btn btn-outline-primary px-4 py-2"
                    id="btn-visao-variancia-${concurso}"
                    onclick="ConferenciaResultadosUI.alternarVisao(${concurso}, 'variancia')">
                    <i class="fas fa-table me-1"></i> Análise de Variância
                </button>
            </div>
        </div>

        <div id="container-cards-${concurso}">
            <h6 class="text-muted"><i class="fas fa-list"></i> Apostas Processadas:</h6>
            <div class="row g-3 mt-1">
                ${(resultado.apostas || []).map(a => renderizarAposta(a, sorteadosSet)).join('')}
            </div>
        </div>

        <div id="container-variancia-${concurso}" style="display:none;">
            <h6 class="text-muted"><i class="fas fa-balance-scale"></i> Análise de Variância Nominal (Desvio Posicional):</h6>
            ${renderizarTabelaDesvio(concurso, resultado)}
        </div>

        <div class="mt-4">
            <button type="button" class="btn btn-success me-2" onclick="ConferenciaResultadosUI.exportarRelatorio(${concurso}, 'csv')">
                <i class="fas fa-file-csv"></i> Exportar CSV
            </button>
            <button type="button" class="btn btn-warning text-dark" onclick="ConferenciaResultadosUI.exportarRelatorio(${concurso}, 'json')">
                <i class="fas fa-file-code"></i> Exportar JSON
            </button>
        </div>`;
    }

    function renderizarConsolidado(resultadosProcessamento) {
        let totalInvestido = 0, totalGanho = 0, totalApostas = 0, totalConcursos = 0;
        const distribuicaoGeral = {};

        Object.values(resultadosProcessamento).forEach(r => {
            if (!r.sucesso) return;
            totalConcursos++;
            totalInvestido += r.resumo?.total_investido || 0;
            totalGanho += r.resumo?.total_ganho || 0;
            totalApostas += r.resumo?.total_apostas_validas || r.resumo?.total_apostas || 0;
            Object.entries(r.resumo?.distribuicao_faixas || {}).forEach(([faixa, dados]) => {
                if (!distribuicaoGeral[faixa]) distribuicaoGeral[faixa] = { quantidade: 0, total_ganho: 0 };
                distribuicaoGeral[faixa].quantidade += dados.quantidade;
                distribuicaoGeral[faixa].total_ganho += dados.total_ganho;
            });
        });

        const lucro = totalGanho - totalInvestido;
        const roi = totalInvestido > 0 ? ((lucro / totalInvestido) * 100).toFixed(2) : '0.00';

        let tabelaFaixas = Object.entries(distribuicaoGeral).map(([f, d]) => `
            <tr><td>${f}</td><td>${d.quantidade}x</td><td class="text-success fw-bold">${fmtMoeda(d.total_ganho)}</td></tr>`).join('');

        return `
        <div class="row mb-4 g-3">
            <div class="col-md-3"><div class="card text-center"><div class="card-body"><h6 class="text-muted">Concursos</h6><h3 class="mb-0">${totalConcursos}</h3></div></div></div>
            <div class="col-md-3"><div class="card text-center"><div class="card-body"><h6 class="text-muted">Apostas</h6><h3 class="mb-0">${totalApostas}</h3></div></div></div>
            <div class="col-md-3"><div class="card text-center bg-danger text-white"><div class="card-body"><h6>Investido</h6><h4 class="mb-0">${fmtMoeda(totalInvestido)}</h4></div></div></div>
            <div class="col-md-3"><div class="card text-center ${lucro >= 0 ? 'bg-success' : 'bg-danger'} text-white"><div class="card-body">
                <h6>${lucro >= 0 ? 'LUCRO' : 'PREJUÍZO'}</h6><h4 class="mb-0">${fmtMoeda(Math.abs(lucro))}</h4>
                <small>(${roi >= 0 ? '+' : ''}${roi}% ROI)</small>
            </div></div></div>
        </div>
        <h6>Distribuição consolidada por faixa:</h6>
        <table class="table table-sm"><thead><tr><th>Faixa</th><th>Qtd</th><th>Total</th></tr></thead>
        <tbody>${tabelaFaixas || '<tr><td colspan="3" class="text-muted text-center">Sem prêmios</td></tr>'}</tbody></table>`;
    }

    function mostrarResultados(resultadosProcessamento) {
        const area = document.getElementById('cdAreaResultados');
        const semRes = document.getElementById('cdSemResultados');
        const conteudo = document.getElementById('cdConteudoResultados');
        if (!area || !conteudo) return;

        const keys = Object.keys(resultadosProcessamento).filter(k => resultadosProcessamento[k].sucesso);
        if (!keys.length) return;

        area.style.display = 'block';
        if (semRes) semRes.style.display = 'none';
        conteudo.style.display = 'block';

        const tabsList = document.getElementById('cdTabsConcursos');
        const tabsContent = document.getElementById('cdTabsContent');
        tabsList.querySelectorAll('li:not(:first-child)').forEach(li => li.remove());
        tabsContent.querySelectorAll('[id^="cd-tab-pane-"]').forEach(el => el.remove());

        keys.sort((a, b) => b - a).forEach(concurso => {
            const resultado = resultadosProcessamento[concurso];
            const resumo = resultado.resumo || {};
            const temPremio = (resumo.total_ganho || 0) > 0;
            let trofeu = '';
            if (temPremio) {
                trofeu = `<span class="cr-valor-ganho-badge">${fmtMoeda(resumo.total_ganho)}</span>`;
            }

            const li = document.createElement('li');
            li.className = 'nav-item';
            li.innerHTML = `<button class="nav-link" data-bs-toggle="tab" data-bs-target="#cd-tab-pane-${concurso}" type="button">
                <i class="fas fa-trophy text-success"></i> Concurso ${concurso} ${trofeu}
            </button>`;
            tabsList.appendChild(li);

            const pane = document.createElement('div');
            pane.className = 'tab-pane fade';
            pane.id = `cd-tab-pane-${concurso}`;
            pane.innerHTML = renderizarRelatorioConcurso(concurso, resultado);
            tabsContent.appendChild(pane);
        });

        const consolidadoEl = document.getElementById('cdRelatorioConsolidado');
        if (consolidadoEl) {
            consolidadoEl.innerHTML = renderizarConsolidado(resultadosProcessamento);
        }

        const firstTab = tabsList.querySelector('li:nth-child(2) button') || tabsList.querySelector('.nav-link');
        if (firstTab && typeof bootstrap !== 'undefined') {
            bootstrap.Tab.getOrCreateInstance(firstTab).show();
        }

        area.scrollIntoView({ behavior: 'smooth' });
    }

    function alternarVisao(concurso, visao) {
        const btnCards = document.getElementById(`btn-visao-cards-${concurso}`);
        const btnVar = document.getElementById(`btn-visao-variancia-${concurso}`);
        const cCards = document.getElementById(`container-cards-${concurso}`);
        const cVar = document.getElementById(`container-variancia-${concurso}`);
        if (!btnCards || !cCards) return;

        const isCards = visao === 'cards';
        btnCards.classList.toggle('active', isCards);
        btnVar.classList.toggle('active', !isCards);
        cCards.style.display = isCards ? 'block' : 'none';
        if (cVar) cVar.style.display = isCards ? 'none' : 'block';
    }

    const _ordemOriginal = {};

    function toggleOrdemNumeros(concurso) {
        const container = document.getElementById(`numeros-resultado-${concurso}`);
        const btn = document.getElementById(`toggle-ordem-${concurso}`);
        if (!container) return;

        const nums = Array.from(container.querySelectorAll('.cr-bola-oficial')).map(el => el.textContent);
        if (!_ordemOriginal[concurso]) {
            _ordemOriginal[concurso] = [...nums];
        }

        const sorted = [...nums].sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
        const isCrescente = btn.dataset.ordem !== 'sorteio';
        const display = isCrescente ? sorted : _ordemOriginal[concurso];
        btn.dataset.ordem = isCrescente ? 'sorteio' : 'crescente';
        btn.innerHTML = isCrescente
            ? '<i class="fas fa-random"></i> Ordem Sorteio'
            : '<i class="fas fa-sort-amount-down"></i> Nº Ordem';

        container.innerHTML = display.map(n => `<span class="cr-bola-oficial">${n}</span>`).join('');
    }

    function exportarRelatorio(concurso, formato) {
        window.open(`/central-conferencias/api/conferencia-apostas/exportar/${concurso}?formato=${formato}`, '_blank');
    }

    async function abrirHistoricoAposta(numeros, btnElement) {
        if (!numeros || !numeros.length) return;
        const btn = btnElement;
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando...';

        try {
            const resp = await fetch('/central-conferencias/api/conferencia-apostas/historico-aposta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ numeros })
            });
            const data = await resp.json();
            btn.disabled = false;
            btn.innerHTML = originalHtml;

            if (!data.sucesso) {
                alert(data.mensagem || 'Erro ao buscar histórico.');
                return;
            }

            const historico = data.historico || [];
            const numerosStr = (data.numeros_apostados || numeros)
                .map(n => String(n).padStart(2, '0'))
                .join(' ');

            let html = `<p class="mb-2">Histórico para a aposta: <strong>${numerosStr}</strong></p>`;
            if (!historico.length) {
                html += '<div class="alert alert-warning mb-0"><i class="fas fa-info-circle"></i> Nenhum concurso com 4 ou mais acertos encontrado no histórico.</div>';
            } else {
                html += '<div class="table-responsive" style="max-height:360px;overflow-y:auto;">';
                html += '<table class="table table-sm align-middle mb-0"><thead><tr><th>Concurso</th><th>Data</th><th>Acertos</th><th>Sorteados</th></tr></thead><tbody>';
                historico.forEach(h => {
                    let badgeClass = 'bg-secondary';
                    if (h.acertos >= 6) badgeClass = 'bg-success';
                    else if (h.acertos === 5) badgeClass = 'bg-success';
                    else if (h.acertos === 4) badgeClass = 'bg-warning text-dark';
                    html += `<tr>
                        <td>${h.concurso}</td>
                        <td>${h.data || ''}</td>
                        <td><span class="badge ${badgeClass}">${h.acertos} acertos</span></td>
                        <td class="font-monospace small">${(h.sorteados || []).sort((a,b)=>a-b).map(n => String(n).padStart(2,'0')).join(' ')}</td>
                    </tr>`;
                });
                html += '</tbody></table></div>';
            }

            let modalWrapper = document.getElementById('cr-modal-historico');
            if (!modalWrapper) {
                modalWrapper = document.createElement('div');
                modalWrapper.id = 'cr-modal-historico';
                modalWrapper.innerHTML = `
                <div class="modal fade" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title"><i class="fas fa-search-plus me-2"></i>Histórico da Aposta</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body"></div>
                        </div>
                    </div>
                </div>`;
                document.body.appendChild(modalWrapper);
            }
            const modalEl = modalWrapper.querySelector('.modal');
            const bodyEl = modalWrapper.querySelector('.modal-body');
            bodyEl.innerHTML = html;
            if (typeof bootstrap !== 'undefined') {
                const instance = bootstrap.Modal.getOrCreateInstance(modalEl);
                instance.show();
            }
        } catch (err) {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            alert('Erro de conexão ao buscar histórico: ' + err.message);
        }
    }

    global.ConferenciaResultadosUI = {
        renderizarRelatorioConcurso,
        renderizarTabelaDesvio,
        renderizarConsolidado,
        mostrarResultados,
        alternarVisao,
        toggleOrdemNumeros,
        exportarRelatorio,
        abrirHistoricoAposta,
    };
})(window);
