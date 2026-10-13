/**
 * Conferência visual por volante e simulação retrospectiva — Dia de Sorte.
 * As combinações usam só as dezenas das apostas registradas, salvo o modo extra.
 * Achar mais acertos no passado não indica chance maior no futuro.
 */
(function (root) {
    const MES = {
        janeiro: 'jan', fevereiro: 'fev', marco: 'mar', abril: 'abr', maio: 'mai', junho: 'jun',
        julho: 'jul', agosto: 'ago', setembro: 'set', outubro: 'out', novembro: 'nov', dezembro: 'dez',
        jan: 'jan', fev: 'fev', mar: 'mar', abr: 'abr', mai: 'mai', jun: 'jun',
        jul: 'jul', ago: 'ago', set: 'set', out: 'out', nov: 'nov', dez: 'dez',
    };

    function spec() {
        const g = typeof window !== 'undefined' ? window : {};
        const m = g.__CC_MODALIDADE__ || {};
        if (!m.key) {
            return { key: 'diasorte', min: 1, max: 31, combo: 7, hasMes: true, positional: false, pad: 2 };
        }
        const max = Number(m.dezenaMax);
        return {
            key: m.key,
            min: Number(m.dezenaMin),
            max,
            combo: Number(m.combo) || 7,
            hasMes: !!m.hasMes,
            positional: m.key === 'supersete',
            pad: max >= 10 ? 2 : 1,
        };
    }

    function pad2(n) {
        return String(parseInt(n, 10)).padStart(spec().pad, '0');
    }

    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    }

    function normalizarMes(mes) {
        const low = String(mes || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        if (!low) return '';
        return MES[low] || MES[low.slice(0, 3)] || low.slice(0, 3);
    }

    function mesesIguais(a, b) {
        const na = normalizarMes(a);
        const nb = normalizarMes(b);
        return !!(na && nb && na === nb);
    }

    function dezenasValidas(nums) {
        const sp = spec();
        const vistos = new Set();
        const duplicadas = [];
        const dezenas = [];
        (nums || []).forEach(raw => {
            const n = parseInt(raw, 10);
            if (!Number.isFinite(n) || n < sp.min || n > sp.max) return;
            if (!sp.positional && vistos.has(n)) duplicadas.push(n);
            else {
                vistos.add(n);
                dezenas.push(n);
            }
        });
        if (!sp.positional) dezenas.sort((a, b) => a - b);
        const seq = sp.positional ? dezenas.slice(0, sp.combo) : dezenas;
        return { dezenas: seq, duplicadas, completa: seq.length === sp.combo && duplicadas.length === 0 };
    }

    function conferirDezenas(apostadas, sorteadas) {
        const sp = spec();
        const a = dezenasValidas(apostadas).dezenas;
        const s = dezenasValidas(sorteadas).dezenas;
        if (sp.positional) {
            const coincidentes = [];
            for (let i = 0; i < sp.combo; i++) {
                if (a[i] != null && a[i] === s[i]) coincidentes.push(a[i]);
            }
            return { apostadas: a, sorteadas: s, coincidentes, soAposta: [], soSorteio: [], acertos: coincidentes.length };
        }
        const setA = new Set(a);
        const setS = new Set(s);
        const coincidentes = a.filter(n => setS.has(n));
        const soAposta = a.filter(n => !setS.has(n));
        const soSorteio = s.filter(n => !setA.has(n));
        return { apostadas: a, sorteadas: s, coincidentes, soAposta, soSorteio, acertos: coincidentes.length };
    }

    /**
     * Prêmios fixos da Caixa. 6 e 7 com mês dependem do rateio e não são estimados.
     * 5+ sem o mês cai na faixa de 4 acertos.
     */
    function premiacaoFixa(acertos, mesOk) {
        const partes = [];
        let total = 0;
        let incompleto = false;
        const n = Number(acertos) || 0;
        if (mesOk) {
            partes.push({ descricao: 'Mês', valor: 2.5 });
            total += 2.5;
        }
        if (n >= 6 && mesOk) {
            incompleto = true;
            partes.push({ descricao: n + ' acertos', valor: null });
        } else if (n >= 5 && mesOk) {
            partes.push({ descricao: '5 acertos', valor: 25 });
            total += 25;
        } else if (n >= 4) {
            partes.push({ descricao: '4 acertos', valor: 5 });
            total += 5;
        }
        return { partes, total: Math.round(total * 100) / 100, incompleto };
    }

    function combinacoes(arr, k, max) {
        const out = [];
        if (k < 0 || k > arr.length) return out;
        const acc = [];
        function rec(start) {
            if (out.length >= max) return;
            if (acc.length === k) {
                out.push(acc.slice());
                return;
            }
            for (let i = start; i < arr.length; i++) {
                acc.push(arr[i]);
                rec(i + 1);
                acc.pop();
                if (out.length >= max) return;
            }
        }
        rec(0);
        return out;
    }

    function chave(nums) {
        return nums.join(',');
    }

    function montarCombos(hitBase, filler, uniao, sorteio, melhorOriginal, limite, exigeFora) {
        const combo = spec().combo;
        const need = combo - hitBase.length;
        if (need < 0) return [];
        const blocos = need === 0 ? [[]] : combinacoes(filler, need, limite);
        const vistos = new Set();
        const out = [];
        blocos.forEach(extra => {
            const nums = hitBase.concat(extra).slice().sort((a, b) => a - b);
            if (nums.length !== combo || new Set(nums).size !== combo) return;
            const key = chave(nums);
            if (vistos.has(key)) return;
            const fora = nums.filter(n => !uniao.has(n));
            if (exigeFora && !fora.length) return;
            if (!exigeFora && fora.length) return;
            vistos.add(key);
            const conf = conferirDezenas(nums, sorteio);
            out.push({
                nums,
                acertos: conf.acertos,
                coincidentes: conf.coincidentes,
                soSorteio: conf.soSorteio,
                delta: conf.acertos - melhorOriginal,
                foraDasApostas: fora,
            });
        });
        return out;
    }

    function ordenarCombos(lista) {
        return lista.slice().sort((a, b) => b.acertos - a.acertos || a.nums[0] - b.nums[0] || chave(a.nums).localeCompare(chave(b.nums)));
    }

    function dedupe(lista) {
        const vistos = new Set();
        return lista.filter(item => {
            const key = chave(item.nums);
            if (vistos.has(key)) return false;
            vistos.add(key);
            return true;
        });
    }

    function simular(listas, sorteadas, opts) {
        const limite = (opts && opts.limite) || 16;
        const incluirFora = !!(opts && opts.incluirFora);
        const freq = {};
        const uniao = new Set();
        (listas || []).forEach(nums => {
            dezenasValidas(nums).dezenas.forEach(n => {
                uniao.add(n);
                freq[n] = (freq[n] || 0) + 1;
            });
        });
        const sorteio = dezenasValidas(sorteadas).dezenas;
        const H = sorteio.filter(n => uniao.has(n));
        const M = [...uniao].filter(n => sorteio.indexOf(n) < 0)
            .sort((a, b) => (freq[b] - freq[a]) || (a - b));
        const furos = sorteio.filter(n => !uniao.has(n));
        const originais = (listas || []).map(nums => conferirDezenas(nums, sorteio).acertos);
        const melhorOriginal = originais.length ? Math.max.apply(null, originais) : 0;
        const frequentes = montarCombos(H, M, uniao, sorteio, melhorOriginal, limite, false);
        const raros = montarCombos(H, M.slice().reverse(), uniao, sorteio, melhorOriginal, limite, false);
        const combinacoes = ordenarCombos(dedupe(frequentes.concat(raros))).slice(0, limite);
        let combinacoesFora = [];
        if (incluirFora && furos.length && uniao.size) {
            const grupos = furos.map(f => [f]);
            const combo = spec().combo;
            if (furos.length > 1 && H.length + furos.length <= combo) grupos.push(furos.slice());
            let extras = [];
            grupos.forEach(g => {
                const hit = H.concat(g);
                if (hit.length > combo) return;
                extras = extras.concat(montarCombos(hit, M, uniao, sorteio, melhorOriginal, 8, true));
            });
            combinacoesFora = ordenarCombos(dedupe(extras)).slice(0, limite);
        }
        return {
            uniao: [...uniao].sort((a, b) => a - b),
            acertaveis: H,
            furos,
            melhorOriginal,
            combinacoes,
            combinacoesFora,
            podeFormar: uniao.size >= spec().combo,
        };
    }

    function resumoConcursos(apostas, sorteios) {
        const listas = (apostas || []).map(ap => dezenasValidas(ap.nums).dezenas);
        return (sorteios || []).map(s => {
            const dezenas = dezenasValidas(s.dezenas).dezenas;
            const conferidas = listas.map((nums, idx) => ({
                idx,
                id: apostas[idx].id,
                acertos: conferirDezenas(nums, dezenas).acertos,
                mesOk: mesesIguais(apostas[idx].mes, s.mes),
            }));
            const dist = distribuicao(conferidas);
            const sim = listas.length ? simular(listas, dezenas, { limite: 1 }) : null;
            const melhor = sim && sim.combinacoes[0];
            return {
                concurso: s.concurso,
                data: s.data || '',
                melhorIds: dist.melhores.map(c => c.id),
                acertos: dist.max,
                mesEntrou: conferidas.some(c => c.mesOk),
                simAcertos: melhor ? melhor.acertos : null,
                delta: melhor ? melhor.delta : null,
                totalApostas: listas.length,
            };
        });
    }

    function distribuicao(conferidas) {
        const lista = conferidas || [];
        const max = lista.length ? Math.max.apply(null, lista.map(c => c.acertos)) : 0;
        const melhores = lista.filter(c => c.acertos === max);
        const comAlgum = lista.filter(c => c.acertos > 0).length;
        return {
            max,
            melhores,
            comAlgum,
            concentrado: melhores.length === 1 && comAlgum <= 1,
        };
    }

    const Sim = {
        pad2, normalizarMes, mesesIguais, dezenasValidas, conferirDezenas,
        premiacaoFixa, simular, distribuicao, combinacoes, resumoConcursos,
    };

    const guardados = {};
    const conferidos = {};
    const pendentes = {};
    const estado = {};
    let pastas = null;
    let pastasPromise = null;

    function guardar(concurso, resultado) {
        guardados[concurso] = resultado;
        if (resultado && resultado.sucesso !== false && resultado.apostas) {
            conferidos[Number(concurso)] = resultado;
        }
    }

    function listaJogaveis() {
        return (pastas || [])
            .filter(p => p.tem_json && p.resultado_disponivel)
            .map(p => ({ numero: Number(p.numero_concurso), data: p.data_sorteio || '' }))
            .sort((a, b) => a.numero - b.numero);
    }

    function carregarPastas() {
        if (pastas) return Promise.resolve(pastas);
        if (!pastasPromise) {
            pastasPromise = fetch('/central-conferencias/api/conferencia-apostas/concursos-disponiveis?escopo=indice')
                .then(r => r.json())
                .then(data => {
                    pastas = data.concursos || [];
                    return pastas;
                })
                .catch(() => {
                    pastasPromise = null;
                    pastas = [];
                    return pastas;
                });
        }
        return pastasPromise;
    }

    function garantirConferido(numero) {
        const n = Number(numero);
        if (conferidos[n]) return Promise.resolve(conferidos[n]);
        if (pendentes[n]) return pendentes[n];
        pendentes[n] = fetch('/central-conferencias/api/conferencia-apostas/processar/' + n, { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data && data.sucesso && data.apostas) conferidos[n] = data;
                return data;
            })
            .catch(() => null)
            .finally(() => { delete pendentes[n]; });
        return pendentes[n];
    }

    function tempoMs(relId) {
        const est = garantirEstado(relId);
        const campo = document.querySelector('[data-cr-vol-tempo="' + relId + '"]');
        let seg = Number(campo ? campo.value : est.passoSeg);
        if (!seg || seg < 1) seg = est.passoSeg || 5;
        seg = Math.max(1, Math.min(60, Math.round(seg)));
        est.passoSeg = seg;
        return seg * 1000;
    }

    function esperar(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function numsAposta(ap) {
        return dezenasValidas(ap.numeros_apostados || ap.numeros || []).dezenas;
    }

    function oficiaisDoRelatorio(rel) {
        const bruto = (rel.resultado_sorteio && rel.resultado_sorteio.numeros && rel.resultado_sorteio.numeros.length)
            ? rel.resultado_sorteio.numeros
            : (rel.dezenas_sorteadas || []);
        return dezenasValidas(bruto).dezenas;
    }

    function sorteioDoRelatorio(rel) {
        if (!rel) return null;
        return {
            concurso: Number(rel.concurso),
            data: rel.data_sorteio || '',
            dezenas: oficiaisDoRelatorio(rel),
            mes: rel.mes_sorteado || '',
            proprio: true,
        };
    }

    function moeda(v) {
        return 'R$ ' + (Number(v) || 0).toFixed(2).replace('.', ',');
    }

    function listaNums(nums) {
        return (nums || []).map(pad2).join(' ');
    }

    function grade(sorteadasSet, apostadasSet, modo) {
        const sp = spec();
        const cols = (sp.max - sp.min + 1) <= 25 ? 5 : 10;
        let html = '';
        for (let n = sp.min; n <= sp.max; n++) {
            const s = sorteadasSet.has(n);
            const a = apostadasSet.has(n);
            let cls = 'cr-vol-cell';
            if (modo === 'oficial') {
                if (s && a) cls += ' is-acerto';
                else if (s) cls += ' is-sorteada';
            } else if ((modo === 'aposta' || modo === 'sim') && a && s) cls += ' is-acerto';
            else if ((modo === 'aposta' || modo === 'sim') && a) cls += ' is-aposta';
            html += `<div class="${cls}">${pad2(n)}</div>`;
        }
        return `<div class="cr-volante" style="grid-template-columns:repeat(${cols},minmax(0,1fr))" aria-hidden="false">${html}</div>`;
    }

    function htmlPremio(acertos, mesOk, ganhoServidor) {
        if (ganhoServidor != null) {
            return ganhoServidor > 0 ? moeda(ganhoServidor) : 'sem prêmio';
        }
        const p = premiacaoFixa(acertos, mesOk);
        if (!p.partes.length) return 'sem prêmio fixo';
        const texto = p.partes.map(parte => parte.valor == null ? parte.descricao + ' (rateio do concurso, não calculado)' : parte.descricao + ' ' + moeda(parte.valor)).join(' + ');
        return p.incompleto ? texto : texto + (p.total ? ' · ' + moeda(p.total) : '');
    }

    function linhaTabela(ap, conf, mesOk, idx, selecionada, melhor) {
        const cls = (selecionada ? ' is-sel' : '') + (melhor ? ' is-melhor' : '');
        return `<tr class="cr-vol-linha${cls}" data-cr-vol-aposta="${idx}">
            <td>Aposta ${esc(ap.numero_aposta)}</td>
            <td class="font-monospace">${esc(listaNums(conf.apostadas))}</td>
            <td class="text-center">${conf.acertos}</td>
            <td class="font-monospace">${esc(listaNums(conf.coincidentes)) || '—'}</td>
            ${spec().hasMes ? `<td>${mesOk ? 'acertou' : 'errou'}</td>` : ''}
        </tr>`;
    }

    function linhaSim(item, i, selecionada, prefixo) {
        const cls = selecionada ? ' is-sel' : '';
        const fora = item.foraDasApostas.length ? ` <span class="badge bg-secondary">fora: ${esc(listaNums(item.foraDasApostas))}</span>` : '';
        const delta = item.delta > 0 ? `+${item.delta}` : String(item.delta);
        return `<tr class="cr-vol-linha${cls}" data-cr-vol-sim="${i}" data-cr-vol-sim-tipo="${prefixo}">
            <td>S${i + 1}${fora}</td>
            <td class="font-monospace">${esc(listaNums(item.nums))}</td>
            <td class="text-center">${item.acertos}</td>
            <td class="font-monospace">${esc(listaNums(item.coincidentes)) || '—'}</td>
            <td class="font-monospace">${esc(listaNums(item.soSorteio)) || '—'}</td>
            <td class="text-center">${delta}</td>
        </tr>`;
    }

    function render(relId) {
        const rel = guardados[relId];
        const box = document.getElementById('container-volante-' + relId);
        if (!box || !rel) return;
        const est = estado[relId];
        const visto = conferidos[Number(est.oficial)] || null;
        let sorteio = sorteioDoRelatorio(visto);
        const apostas = (visto && visto.apostas) || [];
        const semResultado = !sorteio || !sorteio.dezenas.length;
        if (semResultado) {
            sorteio = { concurso: Number(est.oficial), data: '', dezenas: [], mes: '', proprio: false };
        }
        if (est.aposta >= apostas.length) est.aposta = 0;
        const aposta = apostas[est.aposta] || null;
        const numsSel = aposta ? numsAposta(aposta) : [];
        const confSel = conferirDezenas(numsSel, sorteio.dezenas);
        const mesAposta = aposta ? (aposta.mes || '') : '';
        const mesOk = mesesIguais(mesAposta, sorteio.mes);
        const setS = new Set(sorteio.dezenas);
        const setA = new Set(numsSel);
        const listas = apostas.map(numsAposta);
        const sim = listas.length ? simular(listas, sorteio.dezenas, { incluirFora: est.incluirFora, limite: 16 }) : null;
        const conferidas = apostas.map((ap, idx) => {
            const conf = conferirDezenas(numsAposta(ap), sorteio.dezenas);
            return { idx, id: ap.numero_aposta, acertos: conf.acertos, conf, mesOk: mesesIguais(ap.mes, sorteio.mes) };
        });
        const dist = distribuicao(conferidas);
        const melhorSet = new Set(dist.melhores.map(c => c.idx));
        conferidas.sort((a, b) => b.acertos - a.acertos || Number(a.id) - Number(b.id));

        const opConc = htmlOpcoes(rel, est.oficial);

        const opAp = apostas.map((ap, idx) => {
            const sel = idx === est.aposta ? ' selected' : '';
            return `<option value="${idx}"${sel}>Aposta ${esc(ap.numero_aposta)} — ${esc(listaNums(numsAposta(ap)))}${ap.mes ? ' ' + esc(ap.mes) : ''}</option>`;
        }).join('');

        const ganhoSrv = (sorteio.proprio && aposta) ? (Number(aposta.valor_ganho) || 0) : null;
        const premioTxt = aposta ? htmlPremio(confSel.acertos, mesOk, sorteio.proprio ? ganhoSrv : null) : '—';
        const valorAposta = aposta && aposta.valor_aposta ? moeda(aposta.valor_aposta) : '—';

        const comboSel = est.sim == null || !sim ? null : (est.simTipo === 'fora' ? sim.combinacoesFora[est.sim] : sim.combinacoes[est.sim]);
        const melhorSim = sim && sim.combinacoes.length ? sim.combinacoes[0] : null;

        const avisoDist = semResultado
            ? (est.erro || 'Este concurso não tem apostas conferidas.')
            : (!conferidas.length
            ? 'Não há apostas registradas neste concurso.'
            : (dist.concentrado
                ? `Os acertos de dezenas ficaram na aposta ${dist.melhores[0].id}: ${dist.max}.`
                : `Os acertos de dezenas estão distribuídos. ${dist.comAlgum} aposta(s) acertaram ao menos uma dezena. O maior resultado foi ${dist.max}, em ${dist.melhores.length} aposta(s).`));

        const tocando = est.player === 'play';
        const pausado = est.player === 'pause';
        const noArquivo = Number(est.oficial) === Number(rel.concurso);
        const statusPlayer = tocando
            ? ('Aposta ' + (Math.min(est.aposta, Math.max(apostas.length, 1) - 1) + 1) + ' de ' + apostas.length)
            : (pausado ? 'Pausado neste concurso' : (noArquivo ? 'Parado no arquivo' : 'Neste concurso'));
        const blocoResumo = `
            <button type="button" class="cr-vol-abre" data-cr-vol-cmd="toggle-resumo" aria-expanded="${est.resumoAberto ? 'true' : 'false'}">
                <i class="fas ${est.resumoAberto ? 'fa-chevron-down' : 'fa-chevron-right'}"></i>
                Resumo da conferência
            </button>
            ${est.resumoAberto ? `<div class="border rounded p-3 mb-3 small cr-vol-resumo">
                <div>Concurso ${esc(sorteio.concurso)} · ${aposta ? 'aposta ' + esc(aposta.numero_aposta) : 'sem aposta'}</div>
                <div>Apostadas: ${esc(listaNums(confSel.apostadas)) || '—'}</div>
                <div>Sorteadas: ${esc(listaNums(sorteio.dezenas))}</div>
                <div>Coincidentes (${confSel.acertos} de ${spec().combo}): ${esc(listaNums(confSel.coincidentes)) || '—'}</div>
                <div>Apostadas que não saíram: ${esc(listaNums(confSel.soAposta)) || '—'}</div>
                <div>Sorteadas que não foram apostadas: ${esc(listaNums(confSel.soSorteio)) || '—'}</div>
                ${spec().hasMes ? `<div>Mês apostado ${esc(mesAposta || '—')} · mês sorteado ${esc(sorteio.mes || '—')} · ${mesAposta ? (mesOk ? 'acerto do mês' : 'erro do mês') : 'mês não informado'}</div>` : ''}
                <div>Premiação: ${esc(premioTxt)}. Valor da aposta: ${esc(valorAposta)}.${sorteio.proprio && aposta ? ' Financeiro deste concurso: ' + (ganhoSrv > 0 ? 'ganhou ' + moeda(ganhoSrv) : 'não ganhou') + '.' : ''}</div>
            </div>` : ''}`;
        const linhasResumo = (est.resumo || []).map(linha => {
            const delta = linha.delta == null ? '—' : (linha.delta > 0 ? '+' + linha.delta : String(linha.delta));
            const atual = Number(linha.concurso) === Number(est.oficial) ? ' is-sel' : '';
            return `<tr class="cr-vol-linha${atual}" data-cr-vol-ir="${linha.concurso}">
                <td>#${esc(linha.concurso)}</td>
                <td>${esc(linha.data || '')}</td>
                <td>${esc((linha.melhorIds || []).map(id => 'Aposta ' + id).join(', ') || '—')}</td>
                <td class="text-center">${linha.acertos}</td>
                ${spec().hasMes ? `<td>${linha.mesEntrou ? 'sim' : 'não'}</td>` : ''}
                <td class="text-center">${linha.totalApostas == null ? '—' : linha.totalApostas}</td>
                <td class="text-center">${linha.simAcertos == null ? '—' : linha.simAcertos}</td>
                <td class="text-center">${delta}</td>
            </tr>`;
        }).join('');

        box.innerHTML = `
        <div class="cr-vol-view">
            <div class="d-flex flex-wrap gap-3 align-items-end mb-2">
                <label class="small mb-0">Concurso oficial
                    <select class="form-select form-select-sm mt-1" data-cr-vol-conc="${relId}">${opConc}</select>
                </label>
                <label class="small mb-0">Aposta registrada
                    <select class="form-select form-select-sm mt-1" data-cr-vol-aposta-sel="${relId}" ${apostas.length ? '' : 'disabled'}>${opAp || '<option value="">Sem apostas</option>'}</select>
                </label>
            </div>
            <div class="cr-vol-player mb-2">
                <button type="button" data-cr-vol-cmd="prev" title="Concurso anterior"><i class="fas fa-step-backward"></i></button>
                <button type="button" data-cr-vol-cmd="play" class="${tocando ? 'is-on' : ''}" title="Conferir para trás"><i class="fas fa-play"></i></button>
                <button type="button" data-cr-vol-cmd="pause" class="${pausado ? 'is-on' : ''}" title="Pausar"><i class="fas fa-pause"></i></button>
                <button type="button" data-cr-vol-cmd="stop" title="Parar e voltar ao concurso do arquivo"><i class="fas fa-stop"></i></button>
                <button type="button" data-cr-vol-cmd="next" title="Concurso seguinte"><i class="fas fa-step-forward"></i></button>
                <label class="small mb-0 d-inline-flex align-items-center gap-1">Tempo
                    <input type="number" min="1" max="60" step="1" class="form-control form-control-sm cr-vol-tempo" data-cr-vol-tempo="${relId}" value="${esc(est.passoSeg || 5)}">
                    s
                </label>
                <span class="cr-vol-tocando">${esc(est.resumoMsg || (est.carregando ? ('Conferindo as apostas do #' + est.carregando) : (statusPlayer + ' · #' + sorteio.concurso + ' · ' + apostas.length + ' apostas')))}</span>
            </div>
            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
                <label class="small mb-0">Últimos
                    <input type="number" min="1" max="300" class="form-control form-control-sm d-inline-block cr-vol-n" data-cr-vol-n="${relId}" value="${esc(est.resumoN || 30)}">
                    concursos
                </label>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-cr-vol-cmd="resumo">Montar resumo</button>
            </div>
            ${linhasResumo ? `
            <div class="table-responsive mb-3">
                <table class="table table-sm cr-vol-tabela mb-0">
                    <thead><tr><th>Concurso</th><th>Data</th><th>Melhor aposta</th><th>Acertos</th>${spec().hasMes ? '<th>Mês</th>' : ''}<th>Apostas</th><th>Simulação</th><th>Δ</th></tr></thead>
                    <tbody>${linhasResumo}</tbody>
                </table>
            </div>` : ''}
            <p class="small text-muted mb-3">O play confere cada aposta da pasta. Só quando acaba a quantidade daquele concurso ele passa ao anterior e confere a quantidade da pasta de lá.</p>
            <div class="cr-vol-quadros mb-3">
                <div class="cr-vol-quadro">
                    <h6 class="mb-1" style="color:var(--primary-dark,#996e00)">Resultado oficial #${esc(sorteio.concurso)}</h6>
                    <div class="small text-muted mb-2">${esc(sorteio.data || 'sem data')}${spec().hasMes ? ' · Mês ' + esc(sorteio.mes || '—') : ''}</div>
                    ${grade(setS, setA, 'oficial')}
                </div>
                <div class="cr-vol-quadro">
                    <h6 class="mb-1" style="color:var(--primary-dark,#996e00)">${aposta ? 'Aposta ' + esc(aposta.numero_aposta) : 'Nenhuma aposta'}</h6>
                    <div class="small text-muted mb-2">${spec().hasMes ? ('Mês apostado ' + esc(mesAposta || '—') + ' · ' + (mesAposta ? (mesOk ? 'acertou o mês' : 'errou o mês') : 'sem mês')) : (confSel.acertos + ' acerto(s)')}</div>
                    ${aposta ? grade(setS, setA, 'aposta') : '<div class="alert alert-light border mb-0">Este concurso não tem apostas para desenhar o volante.</div>'}
                </div>
            </div>
            <div class="cr-vol-legenda mb-3">
                <span><i class="cr-vol-swatch is-acerto"></i> Coincidente</span>
                <span><i class="cr-vol-swatch is-sorteada"></i> Sorteada e não apostada</span>
                <span><i class="cr-vol-swatch is-aposta"></i> Apostada e não sorteada</span>
                <span><i class="cr-vol-swatch"></i> Fora dos dois</span>
            </div>
            ${blocoResumo}
            <h6 class="mb-2">Apostas deste concurso (${apostas.length})</h6>
            ${apostas.length ? `
            <div class="table-responsive mb-3">
                <table class="table table-sm cr-vol-tabela mb-0">
                    <thead><tr><th>Aposta</th><th>Dezenas</th><th>Acertos</th><th>Coincidentes</th>${spec().hasMes ? '<th>Mês</th>' : ''}</tr></thead>
                    <tbody>${conferidas.map(c => linhaTabela(apostas[c.idx], c.conf, c.mesOk, c.idx, c.idx === est.aposta, melhorSet.has(c.idx))).join('')}</tbody>
                </table>
            </div>
            <p class="small text-muted">${esc(avisoDist)} A soma dos acertos das apostas não é o acerto de um jogo só.</p>` : '<div class="alert alert-light border">Nenhuma aposta registrada.</div>'}
            <h6 class="mb-2">Simulação retrospectiva</h6>
            <p class="small mb-2">Combinações de ${spec().combo} dezenas feitas só com as dezenas que já estão nas apostas deste concurso. Isso olha o resultado depois do sorteio. Não é previsão.</p>
            ${!sim || !sim.podeFormar ? `<div class="alert alert-light border">Não há ${spec().combo} dezenas distintas na união das apostas para montar uma combinação.</div>` : `
            <div class="border rounded p-3 mb-3 small">
                <div>Melhor aposta original: ${dist.melhores.map(c => 'aposta ' + c.id).join(', ')} · ${dist.max} acerto(s).</div>
                <div>Melhor combinação só com dezenas já apostadas: ${melhorSim.acertos} acerto(s) · diferença ${melhorSim.delta > 0 ? '+' : ''}${melhorSim.delta}.</div>
                <div>Dezenas do sorteio que alguma aposta usou: ${esc(listaNums(sim.acertaveis)) || 'nenhuma'}.</div>
                <div>Dezenas sorteadas que ninguém apostou: ${esc(listaNums(sim.furos)) || 'nenhuma'}.</div>
            </div>
            <div class="table-responsive mb-3">
                <table class="table table-sm cr-vol-tabela mb-0">
                    <thead><tr><th>Combinação</th><th>Dezenas</th><th>Acertos</th><th>Acertadas</th><th>Sorteadas de fora</th><th>Δ</th></tr></thead>
                    <tbody>${sim.combinacoes.map((item, i) => linhaSim(item, i, est.simTipo !== 'fora' && est.sim === i, 'base')).join('')}</tbody>
                </table>
            </div>`}
            <label class="small d-flex align-items-center gap-2 mb-2">
                <input type="checkbox" data-cr-vol-fora="${relId}" ${est.incluirFora ? 'checked' : ''}>
                Modo extra: incluir dezenas sorteadas que nenhuma aposta usou. Estas linhas não fazem parte da simulação só com o que foi apostado.
            </label>
            ${est.incluirFora && sim ? (sim.combinacoesFora.length ? `
            <div class="table-responsive mb-3">
                <table class="table table-sm cr-vol-tabela mb-0">
                    <thead><tr><th>Combinação</th><th>Dezenas</th><th>Acertos</th><th>Acertadas</th><th>Sorteadas de fora</th><th>Δ</th></tr></thead>
                    <tbody>${sim.combinacoesFora.map((item, i) => linhaSim(item, i, est.simTipo === 'fora' && est.sim === i, 'fora')).join('')}</tbody>
                </table>
            </div>` : `<div class="alert alert-light border">Nenhuma dezena sorteada ficou de fora das apostas, ou não deu para completar ${spec().combo} números.</div>`) : ''}
            ${comboSel ? `
            <h6 class="mb-2">Volante da combinação ${est.simTipo === 'fora' ? 'extra' : 'simulada'} S${est.sim + 1}</h6>
            <p class="small text-muted">${est.simTipo === 'fora' ? 'Usa dezenas que não estavam nas apostas.' : 'Usa somente dezenas das apostas originais.'} ${comboSel.acertos} acerto(s) neste concurso.</p>
            ${grade(setS, new Set(comboSel.nums), 'sim')}
            ` : ''}
        </div>`;
        const selOficial = box.querySelector('[data-cr-vol-conc]');
        if (selOficial) selOficial.value = String(est.oficial);
    }

    function htmlOpcoes(rel, atual) {
        const base = listaJogaveis();
        const itens = base.length ? base.slice() : [{ numero: Number(rel.concurso), data: rel.data_sorteio || '' }];
        const n = Number(atual);
        if (n && !itens.some(s => s.numero === n)) {
            itens.push({ numero: n, data: '' });
            itens.sort((a, b) => a.numero - b.numero);
        }
        return itens.map(s => `<option value="${s.numero}">#${s.numero}${s.data ? ' — ' + esc(s.data) : ''}</option>`).join('');
    }

    function pastaVizinha(numero, delta) {
        const lista = listaJogaveis();
        const atual = Number(numero);
        if (delta < 0) {
            for (let i = lista.length - 1; i >= 0; i--) {
                if (lista[i].numero < atual) return lista[i].numero;
            }
            return null;
        }
        for (let i = 0; i < lista.length; i++) {
            if (lista[i].numero > atual) return lista[i].numero;
        }
        return null;
    }

    function destinoPasso(est, delta) {
        return pastaVizinha(est.oficial, delta);
    }

    async function passo(relId, delta, token) {
        const est = garantirEstado(relId);
        const numero = destinoPasso(est, delta);
        if (numero == null) return false;
        est.carregando = numero;
        const statusEl = document.querySelector('#container-volante-' + relId + ' .cr-vol-tocando');
        if (statusEl) statusEl.textContent = 'Conferindo as apostas do #' + numero;
        const dados = await garantirConferido(numero);
        if (!estado[relId] || (token != null && estado[relId].token !== token)) return false;
        est.carregando = 0;
        est.oficial = numero;
        est.aposta = 0;
        est.sim = null;
        est.erro = dados && dados.sucesso ? '' : ((dados && dados.mensagem) || 'Não foi possível conferir as apostas deste concurso.');
        render(relId);
        return true;
    }

    async function reproduzir(relId) {
        const est = garantirEstado(relId);
        est.resumoToken = (est.resumoToken || 0) + 1;
        est.resumoMsg = '';
        est.player = 'play';
        est.token = (est.token || 0) + 1;
        const token = est.token;
        est.aposta = 0;
        est.sim = null;
        render(relId);
        while (estado[relId] && estado[relId].player === 'play' && estado[relId].token === token) {
            await esperar(tempoMs(relId));
            if (!estado[relId] || estado[relId].player !== 'play' || estado[relId].token !== token) break;
            const atual = estado[relId];
            const visto = conferidos[Number(atual.oficial)];
            const total = visto && visto.apostas ? visto.apostas.length : 0;
            if (total > 0 && atual.aposta < total - 1) {
                atual.aposta += 1;
                atual.sim = null;
                render(relId);
                continue;
            }
            const ok = await passo(relId, -1, token);
            if (!estado[relId] || estado[relId].token !== token) break;
            if (!ok) {
                estado[relId].player = 'pause';
                render(relId);
                break;
            }
            estado[relId].aposta = 0;
            render(relId);
        }
    }

    function pausar(relId) {
        const est = garantirEstado(relId);
        est.token = (est.token || 0) + 1;
        est.carregando = 0;
        if (est.player === 'play') est.player = 'pause';
        render(relId);
    }

    function parar(relId) {
        const est = garantirEstado(relId);
        const rel = guardados[relId];
        est.token = (est.token || 0) + 1;
        est.player = 'stop';
        est.carregando = 0;
        est.erro = '';
        est.oficial = rel ? Number(rel.concurso) : est.oficial;
        est.aposta = 0;
        est.sim = null;
        render(relId);
    }

    async function gerarResumo(relId) {
        const est = garantirEstado(relId);
        const rel = guardados[relId];
        if (est.player === 'play') {
            est.player = 'pause';
            est.token = (est.token || 0) + 1;
        }
        const campo = document.querySelector('[data-cr-vol-n="' + relId + '"]');
        let n = Number(campo && campo.value);
        if (!n || n < 1) n = est.resumoN || 30;
        n = Math.max(1, Math.min(300, Math.round(n)));
        est.resumoN = n;
        est.resumoToken = (est.resumoToken || 0) + 1;
        const marca = est.resumoToken;
        const lista = listaJogaveis();
        let fim = lista.findIndex(s => s.numero === Number(rel.concurso));
        if (fim < 0) fim = lista.length - 1;
        const fatia = lista.slice(Math.max(0, fim - n + 1), fim + 1).reverse();
        est.resumoMsg = 'Conferindo 0 de ' + fatia.length;
        render(relId);
        const linhas = [];
        for (let i = 0; i < fatia.length; i++) {
            const item = fatia[i];
            const dados = await garantirConferido(item.numero);
            if (!estado[relId] || estado[relId].resumoToken !== marca) return;
            let linha;
            if (dados && dados.sucesso) {
                const apostas = (dados.apostas || []).map(ap => ({
                    id: ap.numero_aposta,
                    nums: numsAposta(ap),
                    mes: ap.mes || '',
                }));
                linha = resumoConcursos(apostas, [{
                    concurso: Number(dados.concurso),
                    data: dados.data_sorteio || item.data || '',
                    dezenas: oficiaisDoRelatorio(dados),
                    mes: dados.mes_sorteado || '',
                }])[0];
            } else {
                linha = {
                    concurso: item.numero,
                    data: item.data || '',
                    melhorIds: [],
                    acertos: '—',
                    mesEntrou: false,
                    simAcertos: null,
                    delta: null,
                    totalApostas: 0,
                };
            }
            linhas.push(linha);
            est.resumoMsg = 'Conferindo ' + (i + 1) + ' de ' + fatia.length;
            const statusEl = document.querySelector('#container-volante-' + relId + ' .cr-vol-tocando');
            if (statusEl) statusEl.textContent = est.resumoMsg;
        }
        if (!estado[relId] || estado[relId].resumoToken !== marca) return;
        est.resumo = linhas;
        est.resumoMsg = '';
        render(relId);
    }

    function garantirEstado(relId) {
        if (!estado[relId]) {
            const rel = guardados[relId];
            estado[relId] = {
                oficial: rel ? Number(rel.concurso) : relId,
                aposta: 0,
                sim: null,
                simTipo: 'base',
                incluirFora: false,
                player: 'stop',
                resumoN: 30,
                resumo: null,
                resumoAberto: false,
                passoSeg: 5,
                token: 0,
                carregando: 0,
                erro: '',
                resumoMsg: '',
            };
        }
        return estado[relId];
    }

    async function montar(relId) {
        const box = document.getElementById('container-volante-' + relId);
        if (!box) return;
        if (!guardados[relId]) {
            box.innerHTML = '<div class="alert alert-warning mb-0">Processe o concurso para abrir a conferência visual.</div>';
            return;
        }
        garantirEstado(relId);
        if (!pastas) {
            box.innerHTML = '<div class="small text-muted"><i class="fas fa-spinner fa-spin me-1"></i> Carregando concursos...</div>';
            await carregarPastas();
        }
        render(relId);
    }

    async function definirConcurso(relId, valor) {
        const est = garantirEstado(relId);
        if (est.player === 'play') est.player = 'pause';
        est.token = (est.token || 0) + 1;
        est.resumoToken = (est.resumoToken || 0) + 1;
        est.resumoMsg = '';
        const token = est.token;
        const numero = Number(valor);
        est.carregando = numero;
        const statusEl = document.querySelector('#container-volante-' + relId + ' .cr-vol-tocando');
        if (statusEl) statusEl.textContent = 'Conferindo as apostas do #' + numero;
        const dados = await garantirConferido(numero);
        if (!estado[relId] || estado[relId].token !== token) return;
        est.carregando = 0;
        est.oficial = numero;
        est.aposta = 0;
        est.sim = null;
        est.erro = dados && dados.sucesso ? '' : ((dados && dados.mensagem) || 'Não foi possível conferir as apostas deste concurso.');
        render(relId);
    }

    function definirAposta(relId, idx) {
        const est = garantirEstado(relId);
        est.aposta = Number(idx) || 0;
        render(relId);
    }

    function definirSim(relId, idx, tipo) {
        const est = garantirEstado(relId);
        est.sim = Number(idx);
        est.simTipo = tipo === 'fora' ? 'fora' : 'base';
        render(relId);
    }

    function definirFora(relId, on) {
        const est = garantirEstado(relId);
        est.incluirFora = !!on;
        est.sim = null;
        render(relId);
    }

    if (typeof document !== 'undefined') {
        document.addEventListener('change', ev => {
            const t = ev.target;
            if (!t || !t.dataset) return;
            if (t.dataset.crVolConc) definirConcurso(t.dataset.crVolConc, t.value);
            else if (t.dataset.crVolApostaSel) definirAposta(t.dataset.crVolApostaSel, t.value);
            else if (t.dataset.crVolFora) definirFora(t.dataset.crVolFora, t.checked);
            else if (t.dataset.crVolTempo) {
                const est = garantirEstado(t.dataset.crVolTempo);
                let seg = Math.round(Number(t.value));
                if (seg >= 1 && seg <= 60) est.passoSeg = seg;
            }
        });
        document.addEventListener('click', ev => {
            const cmd = ev.target.closest ? ev.target.closest('[data-cr-vol-cmd]') : null;
            if (cmd) {
                const box = cmd.closest('.cr-vol-view');
                const sel = box && box.querySelector('[data-cr-vol-conc]');
                if (!sel) return;
                const relId = sel.dataset.crVolConc;
                const acao = cmd.dataset.crVolCmd;
                if (acao === 'play') reproduzir(relId);
                else if (acao === 'pause') pausar(relId);
                else if (acao === 'stop') parar(relId);
                else if (acao === 'prev') {
                    if (estado[relId] && estado[relId].player === 'play') pausar(relId);
                    passo(relId, -1);
                }
                else if (acao === 'next') {
                    if (estado[relId] && estado[relId].player === 'play') pausar(relId);
                    passo(relId, 1);
                }
                else if (acao === 'resumo') gerarResumo(relId);
                else if (acao === 'toggle-resumo') {
                    const est = garantirEstado(relId);
                    est.resumoAberto = !est.resumoAberto;
                    render(relId);
                }
                return;
            }
            const linha = ev.target.closest ? ev.target.closest('tr[data-cr-vol-aposta], tr[data-cr-vol-sim], tr[data-cr-vol-ir]') : null;
            if (!linha) return;
            const box = linha.closest('.cr-vol-view');
            const sel = box && box.querySelector('[data-cr-vol-conc]');
            if (!sel) return;
            const relId = sel.dataset.crVolConc;
            if (linha.dataset.crVolIr) definirConcurso(relId, linha.dataset.crVolIr);
            else if (linha.dataset.crVolAposta != null) definirAposta(relId, linha.dataset.crVolAposta);
            else definirSim(relId, linha.dataset.crVolSim, linha.dataset.crVolSimTipo);
        });
    }

    root.ConferenciaVolanteSim = Sim;
    root.ConferenciaVolanteUi = { guardar, montar, definirConcurso, definirAposta, definirSim, definirFora };
    if (typeof module !== 'undefined' && module.exports) module.exports = Sim;
})(typeof window !== 'undefined' ? window : globalThis);
