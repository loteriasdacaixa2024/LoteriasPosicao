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
        return 'R$ ' + (Number(v) || 0).toFixed(2).replace('.', ',');
    }

    function _mod() {
        return global.__CC_MODALIDADE__ || {};
    }

    function _ehDiaSorte() {
        return _mod().key === 'diasorte';
    }

    function _tempoLabel(ms) {
        if (ms == null || !isFinite(ms)) return '--';
        return (ms / 1000).toFixed(1).replace('.', ',') + 's';
    }

    const _MES_ABREV = {
        janeiro: 'Jan', fevereiro: 'Fev', março: 'Mar', marco: 'Mar', abril: 'Abr',
        maio: 'Mai', junho: 'Jun', julho: 'Jul', agosto: 'Ago', setembro: 'Set',
        outubro: 'Out', novembro: 'Nov', dezembro: 'Dez',
        jan: 'Jan', fev: 'Fev', mar: 'Mar', abr: 'Abr', mai: 'Mai', jun: 'Jun',
        jul: 'Jul', ago: 'Ago', set: 'Set', out: 'Out', nov: 'Nov', dez: 'Dez',
    };
    const _MES_NOME = {
        jan: 'Janeiro', fev: 'Fevereiro', mar: 'Março', abr: 'Abril', mai: 'Maio', jun: 'Junho',
        jul: 'Julho', ago: 'Agosto', set: 'Setembro', out: 'Outubro', nov: 'Novembro', dez: 'Dezembro',
    };

    function _nomeMes(mes) {
        const raw = String(mes || '').trim();
        if (!raw) return '';
        const low = raw.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        const abrev = _MES_ABREV[low];
        if (abrev && _MES_NOME[abrev.toLowerCase()]) return _MES_NOME[abrev.toLowerCase()];
        const hit = Object.values(_MES_NOME).find(n => n.toLowerCase() === raw.toLowerCase());
        return hit || raw;
    }

    function _abrevMes(mes) {
        const nome = _nomeMes(mes);
        const low = nome.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        return _MES_ABREV[low] || nome.slice(0, 3);
    }

    function _corMes(mes) {
        const nome = _nomeMes(mes);
        const cores = global.__MESES_CORES__ || {};
        return cores[nome] || '#6c757d';
    }

    function _textoSobreCor(hex) {
        const h = String(hex || '').replace('#', '');
        if (h.length < 6) return '#fff';
        const r = parseInt(h.slice(0, 2), 16);
        const g = parseInt(h.slice(2, 4), 16);
        const b = parseInt(h.slice(4, 6), 16);
        if ([r, g, b].some(n => Number.isNaN(n))) return '#fff';
        return (r * 299 + g * 587 + b * 114) / 1000 > 160 ? '#1a0a00' : '#fff';
    }

    function _badgeMes(mes) {
        if (!mes) return '';
        const nome = _nomeMes(mes);
        const cor = _corMes(mes);
        return `<span class="badge" title="${nome}" style="background:${cor};color:${_textoSobreCor(cor)};font-weight:700;">${_abrevMes(mes)}</span>`;
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

    function renderizarApostaDiaSorte(aposta) {
        const resultado = aposta.resultado || {};
        const nums = aposta.numeros_apostados || aposta.numeros || [];
        const numsInt = nums.map(n => parseInt(n, 10));
        const ganho = Number(aposta.valor_ganho) || 0;
        const temPremio = ganho > 0 || !!resultado.premiado;
        const acertados = new Set((resultado.numeros_acertados || aposta.dezenas_acertadas || []).map(n => parseInt(n, 10)));
        const acertosVolante = resultado.acertos_volante ?? resultado.acertos ?? acertados.size;
        const acertosN = Number(acertosVolante) || 0;
        const sete = acertosN >= 7 || !!resultado.premio_maximo;
        const faixaVerde = !sete && (acertosN >= 4 || resultado.mes_ok === true || temPremio);
        const cardStyle = faixaVerde ? 'background:#e8f6ee;' : '';
        const cardClass = sete ? 'cr-sete-pulso' : (faixaVerde ? 'cr-card-acerto' : '');
        const mes = aposta.mes ? String(aposta.mes) : '';

        const faixaPaga = acertosN >= 4 || resultado.mes_ok === true || temPremio;
        const rotuloAcertos = acertosN === 1 ? '1 acerto' : `${acertosN} acertos`;
        const valorHtml = ganho > 0
            ? `<span class="fw-bold" style="color:var(--primary-dark,#996e00)">${fmtMoeda(ganho)}</span>`
            : '';

        return `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 ${cardClass}" style="${cardStyle}">
                <div class="card-body">
                    <h6 class="mb-2" style="color:var(--primary-dark,#996e00)">Aposta ${aposta.numero_aposta}</h6>
                    <div class="d-flex flex-wrap align-items-center gap-1 mb-2">
                        ${numsInt.map(n => {
                            const hit = acertados.has(n);
                            const estilo = hit
                                ? 'background:#FFD700;color:#1a0a00;border:2px solid #e6a800;font-weight:800;'
                                : 'background:#6c757d;color:#fff;font-weight:700;';
                            return `<span style="display:inline-flex;align-items:center;justify-content:center;min-width:2rem;height:2rem;border-radius:8px;font-size:.85rem;${estilo}">${String(n).padStart(2, '0')}</span>`;
                        }).join('')}
                        ${mes ? _badgeMes(mes) : ''}
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge" style="background:${faixaPaga ? '#ffd700' : '#e9ecef'};color:${faixaPaga ? '#1a0a00' : '#495057'};">
                            ${rotuloAcertos}
                        </span>
                        ${valorHtml}
                    </div>
                    <a href="#" class="small d-block mt-2" style="color:var(--primary-dark,#996e00)"
                       onclick="ConferenciaResultadosUI.abrirHistoricoAposta([${numsInt.join(',')}], this); return false;">
                        <i class="fas fa-search"></i> Ver Histórico Jogo
                    </a>
                </div>
            </div>
        </div>`;
    }

    function renderizarAposta(aposta, sorteadosSet) {
        if (_ehDiaSorte()) return renderizarApostaDiaSorte(aposta);
        const resultado = aposta.resultado || {};
        const nums = aposta.numeros_apostados || aposta.numeros || [];
        const numsInt = nums.map(n => parseInt(n, 10));
        const temPremio = !!(resultado.premiado || (aposta.valor_ganho || 0) > 0);
        const acertosQtd = Math.max(Number(resultado.acertos) || 0, Number(resultado.acertos_volante) || 0, (resultado.numeros_acertados || []).length);
        const fundoVerde = !!resultado.premiado || resultado.mes_ok === true || acertosQtd >= 4;
        const premioMaximo = !!resultado.premio_maximo;
        const acertados = new Set((resultado.numeros_acertados || aposta.dezenas_acertadas || []).map(n => parseInt(n, 10)));
        const cat = _categoriaAposta(resultado);

        let cardClass = 'cr-aposta-card';
        let cardStyle = '';
        if (premioMaximo) {
            cardClass += ' cr-premio-maximo';
            cardStyle = 'background:linear-gradient(160deg,#fff8e1,#ffe082);border:2px solid #f9a825;';
        } else if (fundoVerde) {
            cardClass += ' cr-card-acerto';
            cardStyle = 'background:#e8f6ee;';
        }

        const badgeClasse =
            cat === 'sena' || cat === 'quina' ? 'cr-badge-ms cr-badge-ms-alto' :
            cat === 'quadra' ? 'cr-badge-ms cr-badge-ms-quadra' :
            'cr-badge-ms';

        const acertosVolante = resultado.acertos_volante ?? acertados.size;

        return `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 ${cardClass}" style="${cardStyle}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-0" style="color:${MS.c20}">Aposta ${aposta.numero_aposta}</h6>
                        ${premioMaximo ? '<span class="cr-trofeu-max" title="Prêmio máximo"><i class="fas fa-trophy"></i></span>' : ''}
                    </div>
                    <span class="badge mb-2" style="background:${MS.c25};color:${MS.c100}"><i class="fas fa-file-code"></i> JSON</span>
                    <div class="d-flex flex-wrap gap-1 mb-2">
                        ${numsInt.map((n, i) => {
                            const hit = acertados.has(n);
                            const estilo = hit
                                ? 'background:#198754;color:#fff;font-weight:700;'
                                : 'background:#f1f3f5;color:#333;';
                            return `<span class="${_classeDezenaCard(n, acertados, cat, i, sorteadosSet)}" style="display:inline-flex;align-items:center;justify-content:center;min-width:1.7rem;height:1.7rem;border-radius:999px;font-size:.8rem;${estilo}">${String(n).padStart(2, '0')}</span>`;
                        }).join('')}
                    </div>
                    ${premioMaximo ? '<div class="badge mb-2 cr-selo-max">Prêmio máximo</div>' : ''}
                    <div class="mb-2">
                        <span class="badge ${badgeClasse}">
                            ${acertosVolante} acerto(s) no volante
                            ${resultado.acertos > 0 && resultado.acertos !== acertosVolante
                                ? ` · melhor comb.: ${resultado.acertos}` : ''}
                        </span>
                    </div>
                    ${resultado.detalhes_premios && resultado.detalhes_premios.length ? `
                        <div class="alert ${fundoVerde ? 'alert-success' : 'alert-light border'} py-2 px-2 mb-2 small">
                            ${resultado.detalhes_premios.map(p => `
                                <div class="d-flex justify-content-between">
                                    <span><strong>${p.descricao}</strong></span>
                                    <span class="text-success fw-bold">${fmtMoeda(p.valor)}</span>
                                </div>`).join('')}
                        </div>` : ''}
                    <div class="small text-muted">Aposta ${fmtMoeda(aposta.valor_aposta || 0)}${aposta.mes ? ' · mês ' + aposta.mes : ''}</div>
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
        const corCheia = _ehDiaSorte() ? 'var(--primary,#c08b00)' : MS.c35;
        const corMedia = _ehDiaSorte() ? 'var(--accent,#e6a800)' : MS.c55;
        const corBaixa = _ehDiaSorte() ? 'var(--primary-dark,#996e00)' : MS.c25;
        const barStyle = pct === 100
            ? `background:${corCheia}`
            : pct >= 60 ? `background:${corMedia}` : `background:${corBaixa}`;

        return `
        <div class="row mb-4">
            <div class="col-12">
                <div class="card border-0 shadow-sm cr-cobertura-card">
                    <div class="card-header bg-transparent border-0 d-flex justify-content-between align-items-center">
                        <h6 class="mb-0" style="color:${_ehDiaSorte() ? 'var(--primary-dark,#996e00)' : MS.c30}"><i class="fas fa-bullseye"></i> Cobertura de Acertos Inteligente</h6>
                        <span class="badge rounded-pill" style="background:${corCheia};color:${_ehDiaSorte() ? '#fff' : MS.c100}">${cobertas.length}/${sorteados.length} Cobertas</span>
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
                                            <span class="badge shadow-sm p-2 mb-1" style="font-size:1.1em;background:${_ehDiaSorte() ? '#FFD700' : MS.c35};color:${_ehDiaSorte() ? '#1a0a00' : MS.c100};border:2px solid ${_ehDiaSorte() ? '#e6a800' : MS.c25};">${String(n).padStart(2, '0')}</span>
                                            <div style="font-size:0.7em;color:${_ehDiaSorte() ? 'var(--primary-dark,#996e00)' : MS.c25};font-weight:bold;">COBERTA</div>
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
                <td class="${_ehDiaSorte() ? 'cr-total-ganho' : 'text-success'} fw-bold">${fmtMoeda(dados.total_ganho)}</td>
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

        const oficiais = sorteados.length || DEZENAS_SORTEIO;
        let maxDezenas = oficiais;
        (resultado.apostas || []).forEach(ap => {
            const n = (ap.numeros_apostados || []).length;
            if (n > maxDezenas) maxDezenas = n;
        });
        const numColunas = Math.max(oficiais, Math.min(maxDezenas, 20));

        let tableRows = '';
        (resultado.apostas || []).forEach((aposta, rowIdx) => {
            const numeros = aposta.numeros_apostados || [];
            if (numeros.length < oficiais) return;

            const volanteSet = new Set(numeros.map(n => parseInt(n, 10)));
            const numerosOrdenados = [...volanteSet].sort((a, b) => a - b).slice(0, numColunas);
            const dataLabel = `${resultado.resultado_sorteio?.data || resultado.data_sorteio || ''} - ${concurso} - ${aposta.numero_aposta ?? rowIdx + 1}`;

            const resLinha = aposta.resultado || {};
            const acertosLinha = Math.max(Number(resLinha.acertos) || 0, Number(resLinha.acertos_volante) || 0, (resLinha.numeros_acertados || []).length);
            const linhaMax = !!resLinha.premio_maximo;
            const linhaAcerto = !linhaMax && (acertosLinha >= 4 || resLinha.mes_ok === true || resLinha.premiado);
            const linhaPremio = linhaMax ? 'background:#fff3cd;' : '';
            let rowHtml = `<tr class="${linhaAcerto ? 'cr-linha-acerto' : ''}" style="height: 32px;${linhaPremio}">
                <td class="align-middle fw-bold text-muted text-center text-nowrap p-1" style="font-size: 0.85rem;">${dataLabel}${linhaMax ? ' ★' : ''}</td>`;

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
                if (i < oficiais) {
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
                if (i < oficiais && numerosOrdenados[i] !== undefined) {
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

    const _ordemCrescente = {};
    const _ordemSorteio = {};
    const _ordemExplicita = {};
    let _mapaOrdemSorteio = null;
    let _mapaOrdemPromise = null;

    function _pad2(n) {
        return String(parseInt(n, 10)).padStart(2, '0');
    }

    function _carregarMapaOrdemSorteio() {
        if (_mapaOrdemSorteio) return Promise.resolve(_mapaOrdemSorteio);
        if (!_mapaOrdemPromise) {
            _mapaOrdemPromise = fetch('/analise/api/ultimos')
                .then(r => r.json())
                .then(data => {
                    const mapa = {};
                    (data.sorteios || []).forEach(s => {
                        if (s.concurso == null || !Array.isArray(s.dezenas_ordem)) return;
                        mapa[String(s.concurso)] = s.dezenas_ordem.map(_pad2);
                    });
                    _mapaOrdemSorteio = mapa;
                    return mapa;
                })
                .catch(() => {
                    _mapaOrdemPromise = null;
                    return {};
                });
        }
        return _mapaOrdemPromise;
    }

    function _aplicarOrdemDoMapa(concurso) {
        const lista = _mapaOrdemSorteio && _mapaOrdemSorteio[String(concurso)];
        if (!lista || !lista.length) return false;
        _ordemSorteio[concurso] = lista;
        _ordemExplicita[concurso] = true;
        return true;
    }

    function _guardarOrdens(concurso, resultado, numsOficiais) {
        const crescente = numsOficiais
            .map(n => parseInt(n, 10))
            .filter(n => !isNaN(n))
            .sort((a, b) => a - b);
        const explicita = resultado.dezenas_ordem_sorteio
            || (resultado.resultado_sorteio && resultado.resultado_sorteio.numeros_ordem_sorteio);
        const bruto = explicita && explicita.length ? explicita : crescente;
        const sorteio = bruto.map(n => parseInt(n, 10)).filter(n => !isNaN(n));
        _ordemCrescente[concurso] = crescente.map(_pad2);
        _ordemSorteio[concurso] = (sorteio.length ? sorteio : crescente).map(_pad2);
        _ordemExplicita[concurso] = !!(explicita && explicita.length);
        if (!_ordemExplicita[concurso] && _ehDiaSorte()) {
            if (_mapaOrdemSorteio) _aplicarOrdemDoMapa(concurso);
            else _carregarMapaOrdemSorteio().then(() => _aplicarOrdemDoMapa(concurso));
        }
    }

    function _numsAposta(aposta) {
        const raw = aposta.numeros_apostados || aposta.numeros || [];
        return raw.map(n => parseInt(n, 10)).filter(n => n >= 1 && n <= 31);
    }

    function renderizarInsightEParecer(concurso, resultado) {
        const apostas = (resultado.apostas || []).filter(a => !a.erro && !a.erro_ocr && !a.dados_incompletos);
        if (!apostas.length) return '';

        const pad = n => String(n).padStart(2, '0');
        const sorteados = _numerosOficiais(resultado).map(n => parseInt(n, 10)).filter(n => !isNaN(n));
        const setSaiu = new Set(sorteados);
        const resumo = resultado.resumo || {};
        const n = apostas.length;
        const freq = {};
        const meses = {};
        const dist = {};
        let melhorAc = -1;
        let melhorAposta = null;
        let melhorNums = [];
        let melhorHits = [];
        let somaAcertos = 0;
        let acertouMes = false;

        apostas.forEach(a => {
            const nums = _numsAposta(a);
            const mes = a.mes || (a.dados_extraidos && a.dados_extraidos.mes_apostado);
            if (mes != null && mes !== '') meses[String(mes)] = (meses[String(mes)] || 0) + 1;
            nums.forEach(num => { freq[num] = (freq[num] || 0) + 1; });
            const hits = nums.filter(num => setSaiu.has(num));
            const ac = (a.resultado && a.resultado.acertos != null) ? Number(a.resultado.acertos) : hits.length;
            somaAcertos += ac;
            dist[ac] = (dist[ac] || 0) + 1;
            if (a.resultado && (a.resultado.mes_ok || a.resultado.acertou_mes)) acertouMes = true;
            if (ac > melhorAc) {
                melhorAc = ac;
                melhorAposta = a.numero_aposta;
                melhorNums = nums.slice().sort((x, y) => x - y);
                melhorHits = hits;
            }
        });

        const setHitsMelhor = new Set(melhorHits);
        const furos = sorteados.filter(d => !freq[d]).sort((a, b) => a - b);
        const cobertas = sorteados.filter(d => freq[d]).sort((a, b) => a - b);
        const maxDist = Math.max(1, ...Object.values(dist));
        const media = somaAcertos / n;
        const mesSorte = resultado.mes_sorteado || (resultado.resultado_sorteio && resultado.resultado_sorteio.mes_sorte);
        const nucleo = Object.entries(freq)
            .filter(e => !setSaiu.has(parseInt(e[0], 10)))
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6)
            .map(e => ({ n: parseInt(e[0], 10), c: e[1] }));

        const estiloBola = (bg, fg, extra) =>
            'display:inline-flex;align-items:center;justify-content:center;min-width:42px;height:42px;border-radius:8px;font-weight:700;font-size:15px;background:' + bg + ';color:' + fg + ';' + (extra || '');
        const bola = (num, tipo, vezes) => {
            const label = pad(num) + (vezes > 0 ? '<small style="font-size:9px;font-weight:600;margin-left:1px;">×' + vezes + '</small>' : '');
            if (tipo === 'furo') {
                return '<span class="me-1 mb-1" title="Saiu e ninguém jogou" style="' + estiloBola('#c0392b', '#fff', 'border:2px solid #922b21;') + '">' + pad(num) + '</span>';
            }
            if (tipo === 'hit') {
                return '<span class="me-1 mb-1" title="Saiu e estava nos jogos" style="' + estiloBola('#FFD700', '#111', 'border:2px solid #e6a800;') + '">' + label + '</span>';
            }
            if (tipo === 'vicio') {
                return '<span class="me-1 mb-1" title="Muito apostada e não saiu" style="' + estiloBola('#1a5276', '#fff', 'border:2px solid #154360;') + '">' + label + '</span>';
            }
            if (tipo === 'aposta') {
                return '<span class="me-1 mb-1" title="Apostada" style="' + estiloBola('#6c757d', '#fff', '') + '">' + label + '</span>';
            }
            return '<span class="me-1 mb-1" title="Fora dos jogos" style="' + estiloBola('#f4f6f7', '#95a5a6', 'border:1px dashed #bdc3c7;') + '">' + pad(num) + '</span>';
        };

        const volante = [];
        for (let d = 1; d <= 31; d++) {
            const vezes = freq[d] || 0;
            let tipo = 'fora';
            if (setSaiu.has(d) && vezes === 0) tipo = 'furo';
            else if (setSaiu.has(d)) tipo = 'hit';
            else if (vezes >= Math.max(5, Math.ceil(n * 0.5))) tipo = 'vicio';
            else if (vezes > 0) tipo = 'aposta';
            volante.push(bola(d, tipo, vezes));
        }

        const barras = [0, 1, 2, 3, 4, 5, 6, 7].map(k => {
            const q = Number(dist[k] || 0);
            const h = Math.max(q ? 8 : 2, Math.round((q / maxDist) * 56));
            const cor = k >= 4 ? '#1e8449' : (k === 3 ? '#d4a017' : '#adb5bd');
            return '<div class="text-center px-1" style="min-width:36px;">' +
                '<div class="d-flex align-items-end justify-content-center" style="height:60px;"><div style="width:18px;height:' + h + 'px;background:' + cor + ';border-radius:4px 4px 0 0;"></div></div>' +
                '<div class="fw-bold" style="font-size:12px;">' + k + '</div>' +
                '<div class="text-muted" style="font-size:11px;">' + q + '</div></div>';
        }).join('');

        const headline = furos.length
            ? furos.length + ' dezena(s) saíram e ninguém jogou — 7 acertos eram impossíveis neste arquivo.'
            : 'Todas as dezenas sorteadas estavam em algum jogo.';
        const mesesHtml = Object.entries(meses).sort((a, b) => b[1] - a[1]).map(e =>
            '<span class="me-2 mb-1 d-inline-flex align-items-center gap-1">' + _badgeMes(e[0]) + '<small class="text-muted">×' + e[1] + '</small></span>'
        ).join('');
        const mesSorteHtml = mesSorte ? _badgeMes(mesSorte) : '—';
        const premiadas = resumo.premiadas || resumo.apostas_premiadas || 0;
        const fato = furos.length
            ? 'No concurso ' + concurso + ', saíram ' + furos.map(pad).join(' e ') + ' e nenhum dos ' + n + ' jogos cobriu.'
            : 'No concurso ' + concurso + ', as 7 dezenas sorteadas apareceram em algum dos ' + n + ' jogos.';

        return `
        <div class="card border-0 shadow-sm mb-3" style="border-top:4px solid #1a5276 !important; background:#f3f6fb;">
            <div class="card-body py-3">
                <h6 class="mb-1" style="color:#1a5276;">
                    <i class="fas fa-lightbulb me-1"></i> Insight — concurso ${concurso}
                </h6>
                <p class="small mb-2"><strong>${fato}</strong> Média ${media.toFixed(1)} acerto(s). Mês sorteado ${acertouMes ? 'entrou em algum jogo' : 'ficou de fora'}.</p>
                <p class="small text-muted mb-2">Parecer geral do ABS, para o próximo palpite. Vale com o orçamento atual: 10 jogos de 7 dezenas.</p>
                <ol class="small mb-0 ps-3" style="line-height:1.45;">
                    <li class="mb-1"><strong>Dez jogos diferentes.</strong> Não gaste vagas variando ±1 a cartela que ficou verde ou amarela no concurso anterior.</li>
                    <li class="mb-1"><strong>Cubra os dois tetos.</strong> Pelo menos 3 jogos com a última dezena entre 20 e 24, e 3 com a última entre 28 e 31.</li>
                    <li class="mb-1"><strong>Descarte salto grande.</strong> P1 acima de 8, ou alguma posição a mais de 5 do envelope 04 · 08 · 12 · 16 · 20 · 24 · 28. Um ±1 não fecha esse buraco.</li>
                    <li class="mb-1"><strong>Leia o ABS assim.</strong> ≤ 20 só diz que o formato não ficou absurdo (em geral 1 ou 2 acertos). Quatro acertos costuma aparecer com ABS ≤ 7.</li>
                    <li><strong>Gap não substitui a régua.</strong> Gap é a distância entre vizinhos. O jogo 10 14 18 22 26 30 31 tem gaps de 4, vizinho perto de vizinho, e a posição 1 está em 10, seis acima do 04. Os buracos estão certos; o bloco inteiro subiu. A régua olha cada posição; o gap olha só o vizinho.</li>
                </ol>
            </div>
        </div>
        <div class="card border-0 shadow-sm mb-4" style="border-top:4px solid #C9A227 !important; background:#fbf8f0;">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2" style="background:#fbf8f0;">
                <h5 class="mb-0" style="color:#6b5710;">Parecer — concurso ${concurso}</h5>
                <span class="small text-muted">Bater o olho: ouro = saiu e você jogou · vermelho = saiu e ninguém jogou · azul = vício (muito jogado, não saiu)</span>
            </div>
            <div class="card-body">
                <div class="alert ${furos.length ? 'alert-danger' : 'alert-success'} py-2 mb-3">
                    <strong>${headline}</strong>
                    <span class="ms-2">${n} jogos · média ${media.toFixed(1)} acerto(s) · premiadas ${premiadas} · mês ${acertouMes ? 'sim' : 'não'}</span>
                </div>
                <div class="row g-3 mb-3">
                    <div class="col-lg-6">
                        <div class="small text-muted fw-bold mb-1">O QUE SAIU</div>
                        <div class="d-flex flex-wrap align-items-center gap-1 mb-2">
                            ${sorteados.map(d => bola(d, freq[d] ? 'hit' : 'furo', freq[d] || 0)).join('')}
                            <span class="ms-2">${mesSorteHtml}</span>
                        </div>
                        <div class="small text-muted">Ouro = você cobriu. Vermelho = furo (saiu fora dos jogos).</div>
                    </div>
                    <div class="col-lg-6">
                        <div class="small text-muted fw-bold mb-1">FUROS DESTE CONCURSO</div>
                        <div class="d-flex flex-wrap align-items-center mb-1">
                            ${furos.length ? furos.map(d => bola(d, 'furo')).join('') : '<span class="text-success fw-bold">Nenhum</span>'}
                        </div>
                        <div class="small text-muted">${cobertas.length ? 'Cobertas: ' + cobertas.map(pad).join(' ') : 'Nenhuma sorteada estava nos jogos.'}</div>
                    </div>
                </div>
                <div class="mb-3">
                    <div class="small text-muted fw-bold mb-1">VOLANTE 01–31 — o que você montou neste arquivo</div>
                    <div class="d-flex flex-wrap">${volante.join('')}</div>
                    <div class="small text-muted mt-1">O número pequeno é quantas vezes a dezena entrou nos ${n} jogos. Contorno tracejado = nem apareceu.</div>
                </div>
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <div class="small text-muted fw-bold mb-1">QUASE — melhor cartela (aposta ${melhorAposta != null ? pad(melhorAposta) : '—'}, ${Math.max(melhorAc, 0)} acerto(s))</div>
                        <div class="d-flex flex-wrap mb-1">
                            ${melhorNums.map(d => bola(d, setHitsMelhor.has(d) ? 'hit' : 'aposta')).join('')}
                        </div>
                        <div class="small text-muted">${furos.length && melhorAc < 4 ? 'Para chegar em 4, troque um cinza por um vermelho (furo).' : ''}</div>
                    </div>
                    <div class="col-md-6">
                        <div class="small text-muted fw-bold mb-1">VÍCIO — mais jogadas e não saíram</div>
                        <div class="d-flex flex-wrap mb-1">
                            ${nucleo.length ? nucleo.map(x => bola(x.n, 'vicio', x.c)).join('') : '<span class="text-muted">—</span>'}
                        </div>
                        <div class="small text-muted">No próximo concurso, não recicle esse bloco em 8 de 10 jogos.</div>
                    </div>
                </div>
                <div class="row g-3 align-items-end">
                    <div class="col-md-6">
                        <div class="small text-muted fw-bold mb-1">QUANTOS JOGOS FIZERAM CADA QUANTIDADE DE ACERTOS</div>
                        <div class="d-flex">${barras}</div>
                    </div>
                    <div class="col-md-6">
                        <div class="small text-muted fw-bold mb-1">MESES NOS JOGOS</div>
                        <div class="mb-1">${mesesHtml || '—'}</div>
                        <div class="small text-muted">Sorteado: ${mesSorteHtml} ${acertouMes ? '(algum jogo acertou)' : '(nenhum jogo neste mês)'}</div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function renderizarRelatorioConcurso(concurso, resultado) {
        const resumo = resultado.resumo || {};
        const investido = resumo.total_investido ?? 0;
        const ganho = resumo.total_ganho ?? 0;
        const lucro = ganho - investido;
        const roi = investido > 0 ? ((lucro / investido) * 100).toFixed(2) : '0.00';

        const numsOficiais = _numerosOficiais(resultado);
        _guardarOrdens(concurso, resultado, numsOficiais);
        const sorteadosSet = new Set(numsOficiais.map(n => parseInt(n, 10)));
        const fonte = resultado.fonte_dados || resultado.origem || 'JSON';
        const fonteBadge = fonte === 'JSON'
            ? '<span class="badge bg-info"><i class="fas fa-file-code"></i> Dados: arquivo JSON</span>'
            : '<span class="badge bg-secondary"><i class="fas fa-images"></i> Dados: Screenshots OCR</span>';

        const resumoProc = _ehDiaSorte() ? renderizarResumoProcessamento(resultado, resultado._elapsedMs) : '';
        const fundoFin = lucro >= 0 ? '#198754' : '#dc3545';
        const cardFinanceiro = `<div class="card text-white h-100" style="background:${fundoFin};border:none;">
                    <div class="card-body">
                        <h6 class="mb-2">Resultado Financeiro</h6>
                        <div class="mb-1"><small>Investido:</small><strong class="ms-2">${fmtMoeda(investido)}</strong></div>
                        <div class="mb-1"><small>Ganho:</small><strong class="ms-2">${fmtMoeda(ganho)}</strong></div>
                        <hr class="my-2" style="border-color:rgba(255,255,255,.75);opacity:1;">
                        <div>
                            <strong>${lucro >= 0 ? 'LUCRO' : 'PREJUÍZO'}:</strong>
                            <strong class="ms-2 fs-5">${fmtMoeda(Math.abs(lucro))}</strong>
                            <span class="ms-2">(${roi >= 0 ? '+' : ''}${roi}%)</span>
                        </div>
                    </div>
                </div>`;

        const blocoVariancia = _ehDiaSorte()
            ? renderizarVarianciaDiaSorte(concurso, resultado)
            : `<h6 class="text-muted"><i class="fas fa-balance-scale"></i> Análise de Variância Nominal (Desvio Posicional):</h6>
               ${renderizarTabelaDesvio(concurso, resultado)}`;

        return `
        ${resumoProc}
        <div class="alert alert-light border mb-4">
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
                                id="toggle-ordem-${concurso}"
                                data-ordem="crescente"
                                title="Alternar entre ordem crescente e ordem de sorteio">
                                <i class="fas fa-sort-amount-down"></i> Nº Ordem
                            </button>
                        </div>
                        <div class="d-flex flex-wrap gap-2" id="numeros-resultado-${concurso}">
                            ${_ordemCrescente[concurso].map(n => `
                                <span class="cr-bola-oficial">${n}</span>`).join('')}
                        </div>
                        ${_ehDiaSorte() && resultado.mes_sorteado ? `<div class="mt-2">${_badgeMes(resultado.mes_sorteado)}</div>` : (resultado.mes_sorteado ? `<span class="badge bg-secondary mt-2">${resultado.mes_sorteado}</span>` : '')}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                ${cardFinanceiro}
            </div>
        </div>

        ${_ehDiaSorte() ? renderizarInsightEParecer(concurso, resultado) : ''}

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
            ${blocoVariancia}
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
            <tr><td>${f}</td><td>${d.quantidade}x</td><td class="${_ehDiaSorte() ? 'cr-total-ganho' : 'text-success'} fw-bold">${fmtMoeda(d.total_ganho)}</td></tr>`).join('');

        const resumoTopo = _ehDiaSorte()
            ? renderizarResumoProcessamentoAgregado(resultadosProcessamento)
            : '';

        return `
        ${resumoTopo}
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

    const _FIXOS_DS = { '4 acertos': 5, '5 acertos': 25, 'Mês': 2.5 };

    function _completarPremiosFixosDiaSorte(resultado) {
        if (!_ehDiaSorte() || !resultado || !resultado.sucesso) return;
        let mudou = false;
        (resultado.apostas || []).forEach(ap => {
            const res = ap.resultado || (ap.resultado = {});
            const detalhes = Array.isArray(res.detalhes_premios) ? res.detalhes_premios : (res.detalhes_premios = []);
            detalhes.forEach(d => {
                const unit = _FIXOS_DS[d.descricao];
                if (unit != null && !(Number(d.valor) > 0)) {
                    d.valor = Math.round(unit * (Number(d.quantidade) || 1) * 100) / 100;
                    mudou = true;
                }
            });
            if (res.mes_ok && !detalhes.some(d => d.descricao === 'Mês')) {
                detalhes.push({ descricao: 'Mês', quantidade: 1, valor: _FIXOS_DS['Mês'] });
                res.faixas_atingidas = (res.faixas_atingidas || []).concat(['Mês']);
                mudou = true;
            }
            const soma = detalhes.reduce((s, d) => s + (Number(d.valor) || 0), 0);
            if (soma > 0 && !(Number(ap.valor_ganho) > 0)) {
                ap.valor_ganho = Math.round(soma * 100) / 100;
                res.valor_premio = ap.valor_ganho;
                res.premiado = true;
                mudou = true;
            }
        });
        if (!mudou) return;
        const dist = {};
        let total = 0;
        let premiadas = 0;
        (resultado.apostas || []).forEach(ap => {
            const g = Number(ap.valor_ganho) || 0;
            total += g;
            if (g > 0) premiadas++;
            (ap.resultado?.detalhes_premios || []).forEach(d => {
                if (!(Number(d.valor) > 0)) return;
                const slot = dist[d.descricao] || { quantidade: 0, total_ganho: 0 };
                slot.quantidade += Number(d.quantidade) || 1;
                slot.total_ganho = Math.round((slot.total_ganho + Number(d.valor)) * 100) / 100;
                dist[d.descricao] = slot;
            });
        });
        const resumo = resultado.resumo || (resultado.resumo = {});
        resumo.total_ganho = Math.round(total * 100) / 100;
        resumo.lucro = Math.round((resumo.total_ganho - (resumo.total_investido || 0)) * 100) / 100;
        resumo.roi = resumo.total_investido ? Math.round((resumo.lucro / resumo.total_investido) * 10000) / 100 : 0;
        resumo.distribuicao_faixas = dist;
        resumo.premiadas = premiadas;
    }

    function mostrarResultados(resultadosProcessamento) {
        Object.values(resultadosProcessamento || {}).forEach(_completarPremiosFixosDiaSorte);
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
        tabsList.querySelectorAll('li').forEach(li => li.remove());
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
        const consolidadoPane = document.getElementById('cd-consolidado');
        const mostrarConsolidado = keys.length > 1;
        if (consolidadoEl) {
            consolidadoEl.innerHTML = mostrarConsolidado
                ? renderizarConsolidado(resultadosProcessamento)
                : '';
        }
        if (consolidadoPane) {
            consolidadoPane.classList.remove('show', 'active');
            consolidadoPane.style.display = '';
        }
        if (mostrarConsolidado && tabsList) {
            const liCons = document.createElement('li');
            liCons.className = 'nav-item';
            liCons.innerHTML = `<button class="nav-link" data-bs-toggle="tab" data-bs-target="#cd-consolidado" type="button">Consolidado</button>`;
            tabsList.insertBefore(liCons, tabsList.firstChild);
        }

        const firstTab = tabsList.querySelector('li:nth-child(2) button') || tabsList.querySelector('.nav-link');
        if (firstTab && typeof bootstrap !== 'undefined') {
            bootstrap.Tab.getOrCreateInstance(firstTab).show();
        } else if (firstTab) {
            firstTab.classList.add('active');
            const alvo = document.querySelector(firstTab.getAttribute('data-bs-target'));
            if (alvo) {
                alvo.classList.add('show', 'active');
                alvo.style.display = 'block';
            }
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
        if (!isCards) {
            const freq = cVar && cVar.querySelector('[id^="cr-freq-abs-pasta-"]');
            if (freq && freq.dataset.carregado !== '1') {
                freq.dataset.carregado = '1';
                carregarFrequenciaAbsPasta(freq.id);
            }
        }
    }

    async function toggleOrdemNumeros(concurso) {
        const container = document.getElementById(`numeros-resultado-${concurso}`);
        const btn = document.getElementById(`toggle-ordem-${concurso}`);
        if (!container || !btn || !_ordemCrescente[concurso]) return;
        if (!_ordemExplicita[concurso] && _ehDiaSorte()) {
            btn.disabled = true;
            await _carregarMapaOrdemSorteio();
            _aplicarOrdemDoMapa(concurso);
            btn.disabled = false;
        }
        const crescente = _ordemCrescente[concurso];
        const sorteio = _ordemSorteio[concurso];
        if (!crescente || !sorteio) return;

        const indoParaSorteio = (btn.dataset.ordem || 'crescente') !== 'sorteio';
        const display = indoParaSorteio ? sorteio : crescente;
        btn.dataset.ordem = indoParaSorteio ? 'sorteio' : 'crescente';
        btn.classList.toggle('btn-warning', !indoParaSorteio);
        btn.classList.toggle('btn-primary', indoParaSorteio);
        btn.innerHTML = indoParaSorteio
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

    function _contagemResumo(resultado) {
        const resumo = resultado.resumo || {};
        const erros = (resultado.erros || []).length;
        const validas = Number(resumo.total_apostas_validas ?? resumo.total_apostas) || 0;
        const total = validas + erros;
        const premiadas = Number(resumo.premiadas) || 0;
        const taxa = total > 0 ? ((validas / total) * 100).toFixed(1) : '0.0';
        return { total, validas, erros, premiadas, taxa, tempo: resultado._elapsedMs };
    }

    function _htmlResumoProcessamento(dados) {
        return `
        <div class="card border-0 shadow-sm mb-4 cr-resumo-proc">
            <div class="card-header text-white fw-bold">
                <i class="fas fa-clipboard-check me-2"></i>Resumo Final do Processamento
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded h-100" style="background:var(--accent-light,#fffaf0);">
                            <i class="fas fa-list-ol fa-2x mb-2" style="color:var(--primary,#c08b00)"></i>
                            <h5 class="mb-0">${dados.total}</h5>
                            <small class="text-muted">Total de Apostas</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded h-100" style="background:var(--accent-light,#fffaf0);">
                            <i class="fas fa-check-circle fa-2x mb-2" style="color:var(--primary-dark,#996e00)"></i>
                            <h5 class="mb-0" style="color:var(--primary-dark,#996e00)">${dados.validas}</h5>
                            <small class="text-muted">Apostas Válidas</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded h-100" style="background:#fff8e8;">
                            <i class="fas fa-exclamation-triangle fa-2x mb-2" style="color:#b28704"></i>
                            <h5 class="mb-0" style="color:#b28704">${dados.erros}</h5>
                            <small class="text-muted">Com Erros/Incompletas</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center p-3 rounded h-100" style="background:var(--accent-light,#fffaf0);">
                            <i class="fas fa-trophy fa-2x mb-2" style="color:#e6a800"></i>
                            <h5 class="mb-0 cr-total-ganho">${dados.premiadas}</h5>
                            <small class="text-muted">Apostas Premiadas</small>
                        </div>
                    </div>
                </div>
                <div class="mt-3 mb-0 py-2 px-3 rounded d-flex flex-wrap justify-content-between align-items-center gap-2" style="background:var(--accent-light,#fffaf0);border:1px solid #f3e0a0;">
                    <div>
                        <i class="fas fa-info-circle me-1" style="color:var(--primary,#c08b00)"></i>
                        <strong>Taxa de Sucesso:</strong>
                        ${dados.taxa}% das apostas foram processadas com sucesso
                    </div>
                    <small class="text-muted">
                        <i class="fas fa-clock"></i>
                        Processado em: <strong>${_tempoLabel(dados.tempo)}</strong>
                    </small>
                </div>
            </div>
        </div>`;
    }

    function renderizarResumoProcessamento(resultado) {
        return _htmlResumoProcessamento(_contagemResumo(resultado || {}));
    }

    function renderizarResumoProcessamentoAgregado(resultadosProcessamento) {
        const acc = { total: 0, validas: 0, erros: 0, premiadas: 0, tempo: null };
        Object.values(resultadosProcessamento || {}).forEach(r => {
            if (!r || !r.sucesso) return;
            const c = _contagemResumo(r);
            acc.total += c.total;
            acc.validas += c.validas;
            acc.erros += c.erros;
            acc.premiadas += c.premiadas;
            if (c.tempo != null) acc.tempo = c.tempo;
        });
        acc.taxa = acc.total > 0 ? ((acc.validas / acc.total) * 100).toFixed(1) : '0.0';
        return _htmlResumoProcessamento(acc);
    }

    function _legendaAbs(stats) {
        const linha = (fundo, rotulo, faixa, s) => `
            <div class="col-md-4">
                <div class="d-flex align-items-start gap-2 p-2 rounded border bg-white h-100">
                    <span class="badge mt-1" style="min-width:64px;${fundo}">${rotulo}</span>
                    <div class="small">
                        <div class="fw-semibold">${faixa}</div>
                        <div class="text-muted">${s.apostas} aposta(s) nesta faixa</div>
                        <div class="mt-1">Acertos: 4→${s.ac4} · 5→${s.ac5} · 6→${s.ac6} · 7→${s.ac7} · M→${s.mes}</div>
                    </div>
                </div>
            </div>`;
        return `
            <div class="border rounded mb-3 py-2 px-3" style="background:var(--accent-light,#fffaf0);font-size:.82rem;">
                <div class="fw-bold mb-2" style="color:var(--primary-dark,#996e00)">
                    <i class="fas fa-info-circle me-1"></i> Legenda ABS — erro do desvio posicional
                </div>
                <div class="row g-2">
                    ${linha('background:#d8f3e4;color:#146c43;', 'Verde', 'ABS ≤ 7', stats.verde)}
                    ${linha('background:#fff3cd;color:#664a00;', 'Amarelo', 'ABS 8–14', stats.amarelo)}
                    ${linha('background:#f1f3f5;color:#495057;', 'Neutro', 'ABS > 14', stats.neutro)}
                </div>
            </div>`;
    }

    function _linhasVarianciaDiaSorte(resultado, maxAbs) {
        const sorteados = [..._numerosOficiais(resultado)].map(n => parseInt(n, 10)).sort((a, b) => a - b);
        const oficiais = sorteados.length || 7;
        const mesSorteado = resultado.mes_sorteado || '';
        const stats = {
            verde: { apostas: 0, ac4: 0, ac5: 0, ac6: 0, ac7: 0, mes: 0 },
            amarelo: { apostas: 0, ac4: 0, ac5: 0, ac6: 0, ac7: 0, mes: 0 },
            neutro: { apostas: 0, ac4: 0, ac5: 0, ac6: 0, ac7: 0, mes: 0 },
        };
        let totalValidas = 0;
        let rows = '';
        let exibidas = 0;
        const valoresAbs = [];

        (resultado.apostas || []).forEach((aposta, rowIdx) => {
            const numeros = (aposta.numeros_apostados || []).map(n => parseInt(n, 10)).filter(n => !isNaN(n));
            if (numeros.length < oficiais) return;
            const ordenados = [...numeros].sort((a, b) => a - b);
            let somaAbs = 0;
            let deltas = 0;
            for (let i = 0; i < oficiais; i++) {
                if (ordenados[i] === undefined || sorteados[i] === undefined) continue;
                somaAbs += Math.abs(ordenados[i] - sorteados[i]);
                deltas++;
            }
            if (!deltas) return;
            totalValidas++;
            valoresAbs.push(somaAbs);
            if (maxAbs != null && somaAbs > maxAbs) return;

            const faixas = aposta.resultado?.faixas_atingidas || [];
            const hit = (txt) => faixas.some(f => String(f).includes(txt));
            const marca = { ac4: hit('4 acertos'), ac5: hit('5 acertos'), ac6: hit('6 acertos'), ac7: hit('7 acertos'), mes: hit('Mês') };
            const bucket = somaAbs <= 7 ? 'verde' : somaAbs <= 14 ? 'amarelo' : 'neutro';
            stats[bucket].apostas++;
            if (marca.ac4) stats[bucket].ac4++;
            if (marca.ac5) stats[bucket].ac5++;
            if (marca.ac6) stats[bucket].ac6++;
            if (marca.ac7) stats[bucket].ac7++;
            if (marca.mes) stats[bucket].mes++;
            exibidas++;

            const dataLabel = `${resultado.data_sorteio || resultado.resultado_sorteio?.data || ''} - ${resultado.concurso || ''} - ${aposta.numero_aposta ?? rowIdx + 1}`;
            const setSorteados = new Set(sorteados);
            const qtdAcertos = ordenados.filter(n => setSorteados.has(n)).length;
            const resAp = aposta.resultado || {};
            const sete = qtdAcertos >= 7 || marca.ac7 || !!resAp.premio_maximo;
            const faixaVerde = !sete && (
                marca.ac4 || marca.ac5 || marca.ac6 || marca.mes
                || (qtdAcertos >= 4 && qtdAcertos < 7) || resAp.mes_ok === true || !!resAp.premiado
            );
            const fundoLinha = faixaVerde ? 'background:#e8f6ee;' : '';
            const cel = (conteudo, extra) => `<td class="align-middle text-center p-1" style="${fundoLinha}border:1px dashed #dee2e6;${extra || ''}">${conteudo}</td>`;
            const bola = (n, classe) => `<div style="width:26px;height:26px;line-height:26px;margin:0 auto;border-radius:4px;" class="${classe}">${String(n).padStart(2, '0')}</div>`;

            let jogados = '';
            let sorteadosHtml = '';
            let diffHtml = '';
            for (let i = 0; i < oficiais; i++) {
                const num = ordenados[i];
                const sort = sorteados[i];
                const perto = num !== undefined && sort !== undefined && Math.abs(num - sort) === 1;
                const igual = num !== undefined && num === sort;
                const clsJ = igual ? 'bg-success text-white fw-bold' : perto ? 'bg-warning text-dark fw-bold' : 'text-secondary';
                const clsS = igual ? 'bg-success text-white fw-bold' : perto ? 'bg-warning text-dark fw-bold' : 'text-secondary';
                jogados += cel(num !== undefined ? bola(num, clsJ) : '-');
                sorteadosHtml += cel(sort !== undefined ? bola(sort, clsS) : '');
                if (num !== undefined && sort !== undefined) {
                    const delta = num - sort;
                    diffHtml += cel(delta === 0 ? '' : delta, `color:${delta < 0 ? '#8b3a3a' : '#333'};`);
                } else {
                    diffHtml += cel('');
                }
            }
            const mesJogado = aposta.mes || '';
            jogados += cel(mesJogado ? _badgeMes(mesJogado) : '-');
            sorteadosHtml += cel(mesSorteado ? _badgeMes(mesSorteado) : '-');
            const absCor = somaAbs <= 7 ? 'color:#996e00;font-weight:700;' : somaAbs <= 14 ? 'color:#b28704;font-weight:700;' : '';
            const x = (v) => v ? 'X' : '';
            rows += `<tr class="${sete ? 'cr-linha-maximo' : (faixaVerde ? 'cr-linha-acerto' : '')}">
                <td class="align-middle text-center text-nowrap p-1 text-muted fw-bold" style="font-size:.8rem;${fundoLinha}">${dataLabel}</td>
                ${jogados}<td style="width:8px;border:none;"></td>
                ${sorteadosHtml}<td style="width:8px;border:none;"></td>
                ${diffHtml}<td style="width:8px;border:none;"></td>
                <td class="align-middle text-center" style="${fundoLinha}${absCor}">${somaAbs}</td>
                <td style="width:8px;border:none;"></td>
                ${cel(x(marca.ac4))}${cel(x(marca.ac5))}${cel(x(marca.ac6))}${cel(x(marca.ac7), 'color:#996e00;font-weight:700;')}${cel(x(marca.mes))}
            </tr>`;
        });

        return { rows, stats, totalValidas, exibidas, oficiais, valoresAbs };
    }

    function _fmtDezenaAbs(n) {
        const hi = Number((window.__CC_MODALIDADE__ || {}).dezenaMax);
        return hi >= 10 ? String(n).padStart(2, '0') : String(n);
    }

    function _limitesAbsPossivel() {
        const mod = window.__CC_MODALIDADE__ || {};
        const k = Number(mod.combo) || 7;
        const lo = mod.dezenaMin != null ? Number(mod.dezenaMin) : 1;
        const hi = mod.dezenaMax != null ? Number(mod.dezenaMax) : 31;
        const baixos = [];
        const altos = [];
        for (let i = 0; i < k; i++) {
            baixos.push(lo + i);
            altos.push(hi - k + 1 + i);
        }
        const partes = baixos.map((n, i) => Math.abs(altos[i] - n));
        const maximo = partes.reduce((s, v) => s + v, 0);
        return {
            minimo: 0,
            maximo,
            apostaIgual: baixos.map(_fmtDezenaAbs).join(' '),
            apostaExtremo: baixos.map(_fmtDezenaAbs).join(' '),
            sorteioExtremo: altos.map(_fmtDezenaAbs).join(' '),
            conta: partes.join(' + ') + ' = ' + maximo,
        };
    }

    function _htmlLimitesAbs() {
        const lim = _limitesAbsPossivel();
        return `
            <div class="cr-abs-limites mb-3">
                <div class="cr-abs-limite">
                    <div class="small text-uppercase text-muted fw-bold" style="letter-spacing:.04em;">Mínimo possível</div>
                    <div class="cr-abs-limite-valor mt-1">${lim.minimo}</div>
                    <div class="small mt-1">A aposta ordenada igual ao sorteio ordenado. Cada posição fecha em zero.</div>
                    <div class="cr-abs-exemplo">
                        aposta ${lim.apostaIgual}<br>
                        sorteio ${lim.apostaIgual}<br>
                        ABS = ${lim.minimo}
                    </div>
                </div>
                <div class="cr-abs-limite cr-abs-limite--max">
                    <div class="small text-uppercase text-muted fw-bold" style="letter-spacing:.04em;">Máximo possível</div>
                    <div class="cr-abs-limite-valor mt-1">${lim.maximo}</div>
                    <div class="small mt-1">Os menores números do volante contra os maiores, posição a posição.</div>
                    <div class="cr-abs-exemplo">
                        aposta ${lim.apostaExtremo}<br>
                        sorteio ${lim.sorteioExtremo}<br>
                        ${lim.conta}
                    </div>
                </div>
            </div>`;
    }

    function _colunaFrequenciaAbs(inicio, fim, contagem, pico) {
        let corpo = '';
        for (let i = inicio; i <= fim; i++) {
            const qtd = Number(contagem[String(i)] ?? contagem[i]) || 0;
            const zero = qtd === 0;
            const topo = pico > 0 && qtd === pico;
            const cls = 'cr-abs-row ' + (zero ? 'cr-abs-zero' : 'cr-abs-ok') + (topo ? ' cr-abs-pico' : '');
            const pct = pico > 0 ? Math.max(6, Math.round((qtd / pico) * 100)) : 0;
            const vezes = zero
                ? '<span class="cr-abs-vezes-zero" title="Nenhuma aposta neste ABS">0</span>'
                : `<span class="cr-abs-vezes-wrap"><span class="cr-abs-vezes-num">${qtd}</span>${topo ? '<span class="cr-abs-selo">maior</span>' : ''}<span class="cr-abs-track" aria-hidden="true"><span class="cr-abs-bar" style="width:${pct}%"></span></span></span>`;
            corpo += `<tr class="${cls}"><td class="cr-abs-col-abs">${i}</td><td class="cr-abs-col-vezes">${vezes}</td></tr>`;
        }
        return `
            <div class="cr-abs-card">
                <table class="cr-abs-tabela mb-0">
                    <thead>
                        <tr><th>ABS</th><th>Vezes</th></tr>
                    </thead>
                    <tbody>${corpo}</tbody>
                </table>
            </div>`;
    }

    function _textoPicoAbs(picos, pico) {
        if (!pico) return '';
        const lista = picos.length === 1
            ? String(picos[0])
            : picos.length === 2
                ? `${picos[0]} e ${picos[1]}`
                : `${picos.slice(0, -1).join(', ')} e ${picos[picos.length - 1]}`;
        const verbo = picos.length > 1
            ? `Os ABS ${lista} empataram no topo: cada um saiu <strong>${pico}</strong> vezes.`
            : `O ABS <strong>${lista}</strong> é o que mais saiu: <strong>${pico}</strong> vezes.`;
        return `
            <div class="cr-abs-pico-banner mb-3">
                <i class="fas fa-crown me-1" style="color:#c08b00"></i>
                ${verbo}
                <span class="text-muted"> É a quantidade de apostas da pasta que fecharam nesse ABS.</span>
            </div>`;
    }

    function _htmlFrequenciaAbsPasta(data) {
        const max = Number(data.max_abs) || 0;
        const contagem = data.contagem || {};
        let pico = 0;
        const picos = [];
        for (let i = 0; i <= max; i++) {
            const qtd = Number(contagem[String(i)] ?? contagem[i]) || 0;
            if (qtd > pico) {
                pico = qtd;
                picos.length = 0;
                picos.push(i);
            } else if (qtd === pico && pico > 0) {
                picos.push(i);
            }
        }
        const bloco = 40;
        const colunas = [];
        for (let inicio = 0; inicio <= max; inicio += bloco) {
            colunas.push(_colunaFrequenciaAbs(inicio, Math.min(inicio + bloco - 1, max), contagem, pico));
        }
        return `
            <div class="cr-abs-freq mt-2 mb-4">
                <h6 class="fw-bold mb-1 cr-abs-titulo">
                    <i class="fas fa-list-ol me-1"></i> Frequência do ABS — pasta inteira
                </h6>
                <p class="small text-muted mb-2">
                    Da primeira aposta até a última que está na pasta.
                    ${data.total_apostas || 0} apostas em ${data.total_concursos || 0} concursos.
                    A tabela vai do ABS 0 até o maior que apareceu na pasta (${max}).
                    Entra aposta nova, a contagem soma de novo.
                </p>
                ${_htmlLimitesAbs()}
                <div class="cr-abs-legenda mb-2">
                    <span class="cr-abs-chip"><span class="cr-abs-swatch cr-abs-swatch--zero"></span> 0 — nenhuma aposta neste ABS</span>
                    <span class="cr-abs-chip"><span class="cr-abs-swatch cr-abs-swatch--ok"></span> número — apostas que fecharam nesse ABS</span>
                    <span class="cr-abs-chip"><span class="cr-abs-swatch cr-abs-swatch--pico"></span> destaque — ABS que mais saiu</span>
                </div>
                ${_textoPicoAbs(picos, pico)}
                <div class="row g-2">
                    ${colunas.map(html => `<div class="col-md-6 col-xl-4">${html}</div>`).join('')}
                </div>
            </div>`;
    }

    function _ligarMovimentoAbs(box) {
        if (!box || box.dataset.absHover === '1') return;
        box.dataset.absHover = '1';
        box.addEventListener('mousemove', (ev) => {
            const tr = ev.target.closest('.cr-abs-row');
            if (!tr || !box.contains(tr)) return;
            const r = tr.getBoundingClientRect();
            tr.style.setProperty('--mx', (ev.clientX - r.left) + 'px');
            tr.style.setProperty('--my', (ev.clientY - r.top) + 'px');
        });
    }

    function _absDaAposta(aposta, sorteados) {
        const nums = (aposta.numeros_apostados || []).map(n => parseInt(n, 10)).filter(n => !isNaN(n)).sort((a, b) => a - b);
        if (nums.length < sorteados.length) return null;
        let soma = 0;
        for (let i = 0; i < sorteados.length; i++) soma += Math.abs(nums[i] - sorteados[i]);
        return soma;
    }

    function _montarContagem(valores) {
        let max = 0;
        const contagem = {};
        valores.forEach(v => { if (v > max) max = v; });
        for (let i = 0; i <= max; i++) contagem[String(i)] = 0;
        valores.forEach(v => { contagem[String(v)] += 1; });
        return { sucesso: true, max_abs: max, contagem };
    }

    async function _frequenciaAbsPeloProcessamento(alvoId, lista) {
        const chave = lista.map(c => c.numero_concurso).join(',');
        const cacheKey = 'cr-freq-abs-pasta';
        try {
            const salvo = JSON.parse(sessionStorage.getItem(cacheKey) || 'null');
            if (salvo && salvo.chave === chave && salvo.data) return salvo.data;
        } catch (e) { /* cache inválido */ }
        const valores = [];
        let concursos = 0;
        for (let i = 0; i < lista.length; i++) {
            const box = document.getElementById(alvoId);
            if (box && i % 4 === 0) {
                box.innerHTML = `<div class="small text-muted"><i class="fas fa-spinner fa-spin me-1"></i> Somando o ABS da pasta: ${i} de ${lista.length} concursos...</div>`;
            }
            const resp = await fetch(`/central-conferencias/api/conferencia-apostas/processar/${lista[i].numero_concurso}`, { method: 'POST' });
            const data = await resp.json();
            if (!data || !data.sucesso) continue;
            const sorteados = _numerosOficiais(data).map(n => parseInt(n, 10)).filter(n => !isNaN(n)).sort((a, b) => a - b);
            if (!sorteados.length) continue;
            let usou = false;
            (data.apostas || []).forEach(ap => {
                const abs = _absDaAposta(ap, sorteados);
                if (abs == null) return;
                valores.push(abs);
                usou = true;
            });
            if (usou) concursos += 1;
        }
        const data = _montarContagem(valores);
        data.total_apostas = valores.length;
        data.total_concursos = concursos;
        try { sessionStorage.setItem(cacheKey, JSON.stringify({ chave, data })); } catch (e) { /* armazenamento cheio */ }
        return data;
    }

    function carregarFrequenciaAbsPasta(alvoId) {
        const alvo = document.getElementById(alvoId);
        if (!alvo) return;
        const pintar = (data) => {
            const box = document.getElementById(alvoId);
            if (!box) return;
            if (!data || !data.sucesso) {
                box.innerHTML = `<div class="alert alert-warning mb-0">${(data && data.mensagem) || 'Não foi possível somar o ABS da pasta.'}</div>`;
                return;
            }
            box.innerHTML = _htmlFrequenciaAbsPasta(data);
            _ligarMovimentoAbs(box);
        };
        fetch('/central-conferencias/api/conferencia-apostas/frequencia-abs')
            .then(async r => {
                if (r.status === 404) {
                    const indice = await fetch('/central-conferencias/api/conferencia-apostas/concursos-disponiveis?escopo=indice').then(x => x.json());
                    const lista = (indice.concursos || []).filter(c => c.tem_json && c.resultado_disponivel);
                    return _frequenciaAbsPeloProcessamento(alvoId, lista);
                }
                return r.json();
            })
            .then(pintar)
            .catch(() => pintar(null));
    }

    function _tabelaVarianciaDiaSorte(resultado, bloco, titulo) {
        const n = bloco.oficiais;
        let nums = '';
        for (let i = 1; i <= n; i++) nums += `<th class="text-center p-1">${i}</th>`;
        const mesTh = `<th class="text-center p-1" style="background:#fff8e1;">MÊS</th>`;
        const tituloHtml = titulo ? `
            <div class="d-flex justify-content-between align-items-center mb-2 mt-2">
                <h6 class="fw-bold mb-0" style="color:var(--primary-dark,#996e00)">
                    <i class="fas fa-filter me-1"></i> Resumo ABS ≤ 20 — todas as apostas do concurso
                </h6>
                <span class="badge" style="background:var(--primary,#c08b00)">${bloco.exibidas} de ${bloco.totalValidas} apostas</span>
            </div>` : '';
        if (!bloco.rows) {
            return `${_legendaAbs(bloco.stats)}${tituloHtml}<div class="alert alert-light border text-muted">Nenhuma aposta neste recorte.</div>`;
        }
        return `${_legendaAbs(bloco.stats)}${tituloHtml}
            <div class="card border-0 shadow-sm mb-4" style="border:1px solid #e6d7a2 !important;">
                <div class="table-responsive">
                    <table class="table table-sm table-borderless mb-0" style="font-size:.8rem;">
                        <thead style="background:#fff8e1;border-bottom:2px solid #f3e0a0;">
                            <tr>
                                <th class="text-center p-2">DATA</th>
                                <th colspan="${n + 1}" class="text-center p-2">NÚMEROS JOGADOS</th>
                                <th style="width:8px;border:none;"></th>
                                <th colspan="${n + 1}" class="text-center p-2">SORTEADOS</th>
                                <th style="width:8px;border:none;"></th>
                                <th colspan="${n}" class="text-center p-2" style="color:#8b3a3a;">DIFERENÇA</th>
                                <th style="width:8px;border:none;"></th>
                                <th class="text-center p-2" title="Soma das diferenças sem sinal">ABS</th>
                                <th style="width:8px;border:none;"></th>
                                <th colspan="5" class="text-center p-2">ACERTO</th>
                            </tr>
                            <tr style="font-size:.75rem;">
                                <th></th>
                                ${nums}${mesTh}
                                <th style="width:8px;border:none;"></th>
                                ${nums}${mesTh}
                                <th style="width:8px;border:none;"></th>
                                ${nums}
                                <th style="width:8px;border:none;"></th>
                                <th></th>
                                <th style="width:8px;border:none;"></th>
                                <th class="text-center" style="background:#eee;">4</th>
                                <th class="text-center" style="background:#e0e0e0;">5</th>
                                <th class="text-center" style="background:#f1c40f;">6</th>
                                <th class="text-center" style="background:#ffd700;">7</th>
                                <th class="text-center" style="background:#fff;">M</th>
                            </tr>
                        </thead>
                        <tbody>${bloco.rows}</tbody>
                    </table>
                </div>
            </div>`;
    }

    function renderizarVarianciaDiaSorte(concurso, resultado) {
        const completo = _linhasVarianciaDiaSorte(resultado, null);
        const resumo = _linhasVarianciaDiaSorte(resultado, 20);
        const freqId = `cr-freq-abs-pasta-${concurso}`;
        return `
            <h6 class="text-muted"><i class="fas fa-balance-scale"></i> Análise de Variância Nominal (Desvio Posicional):</h6>
            ${_tabelaVarianciaDiaSorte(resultado, completo, false)}
            ${_tabelaVarianciaDiaSorte(resultado, resumo, true)}
            <div id="${freqId}" class="mb-4">
                <div class="small text-muted"><i class="fas fa-spinner fa-spin me-1"></i> Somando o ABS de todas as apostas da pasta...</div>
            </div>`;
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
