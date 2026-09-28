(function () {
  'use strict';

  const root = document.getElementById('gc-root');
  if (!root) return;

  const API = window.__GC_API__ || root.dataset.api;
  const SPEC = window.__GC_SPEC__ || {};
  const padW = Math.max(2, Number(SPEC.pad_width) > 0 ? Number(SPEC.pad_width) : 2);

  let base = 'geral';
  let janela = SPEC.janela_default != null ? Number(SPEC.janela_default) : 0;
  let s1Data = null;
  let reguaData = null;
  let refsEdit = [];
  let sortRank = { key: 'score', dir: 'desc' };
  let sortConf = { key: 'concurso', dir: 'desc' };

  const $ = (id) => document.getElementById(id);

  function pad(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return String(n);
    const sign = v < 0 ? '-' : '';
    return sign + String(Math.abs(v)).padStart(padW, '0');
  }

  function padLista(arr) {
    return (arr || []).map(pad).join(' ');
  }

  function toksDezenas(arr) {
    if (!arr || !arr.length) return '—';
    return `<span class="gc-toks">${arr.map((n) => `<span class="gc-tok">${pad(n)}</span>`).join('')}</span>`;
  }

  function gapsHtml(arr, cls) {
    if (!arr || !arr.length) return '—';
    const extra = cls ? (' ' + cls) : '';
    return `<span class="gc-toks">${arr.map((g) => `<span class="gc-gap${extra}">${pad(g)}</span>`).join('')}</span>`;
  }

  function padraoHtml(raw, gaps) {
    const seq = (gaps && gaps.length) ? gaps : String(raw || '').split(/\s+/).filter(Boolean);
    if (!seq.length) return '—';
    return `<span class="gc-toks">${seq.map((g) => `<span class="gc-tok">${pad(g)}</span>`).join('')}</span>`;
  }

  function fonteLabel(f) {
    if (f === 'ambos') return '<span class="gc-fonte-ambos">Ambos</span>';
    if (f === 'sorteio') return '<span class="gc-fonte-sort">Sorteio</span>';
    return '<span class="gc-fonte-class">Classificado</span>';
  }

  function sortInd(cur, key) {
    if (cur.key !== key) return '<span class="gc-sort-ind">↕</span>';
    return `<span class="gc-sort-ind">${cur.dir === 'asc' ? '▲' : '▼'}</span>`;
  }

  function th(label, key, which) {
    const cur = which === 'rank' ? sortRank : sortConf;
    return `<th class="gc-th-sort" data-sort="${key}" data-which="${which}" title="Ordenar por ${label}">${label}${sortInd(cur, key)}</th>`;
  }

  function toggleSort(which, key) {
    const cur = which === 'rank' ? sortRank : sortConf;
    if (cur.key === key) cur.dir = cur.dir === 'asc' ? 'desc' : 'asc';
    else {
      cur.key = key;
      cur.dir = (key === 'concurso' || key === 'score' || key === 'freq_classificado' || key === 'freq_sorteio' || key === 'rank') ? 'desc' : 'asc';
    }
  }

  function cmp(a, b, key, dir) {
    let va = a[key];
    let vb = b[key];
    if (key === 'padrao') {
      va = String(a.padrao || '');
      vb = String(b.padrao || '');
    } else if (key === 'fonte') {
      va = String(a.fonte || '');
      vb = String(b.fonte || '');
    } else if (key === 'dezenas_sorteio' || key === 'dezenas_classificado') {
      va = (a[key] || []).join(',');
      vb = (b[key] || []).join(',');
    } else if (key === 'gaps_sorteio' || key === 'gaps_classificado') {
      va = (a[key] || a.gaps || []).join(',');
      vb = (b[key] || b.gaps || []).join(',');
    } else if (key === 'padroes_iguais') {
      va = a.padroes_iguais ? 1 : 0;
      vb = b.padroes_iguais ? 1 : 0;
    } else {
      va = va == null ? -Infinity : Number(va);
      vb = vb == null ? -Infinity : Number(vb);
      if (Number.isNaN(va)) va = String(a[key] || '');
      if (Number.isNaN(vb)) vb = String(b[key] || '');
    }
    let r = 0;
    if (va < vb) r = -1;
    else if (va > vb) r = 1;
    return dir === 'asc' ? r : -r;
  }

  function qs() {
    const p = new URLSearchParams();
    p.set('janela', String(janela));
    p.set('base', base);
    return p.toString();
  }

  function bindSort(corpo) {
    corpo.querySelectorAll('th.gc-th-sort').forEach((el) => {
      el.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        toggleSort(el.getAttribute('data-which'), el.getAttribute('data-sort'));
        renderS1(s1Data, true);
      });
    });
  }

  function renderS1(s1, keepKpis) {
    const kpis = $('gcKpisS1');
    const corpo = $('gcCorpoS1');
    if (!s1 || !s1.sucesso) {
      if (corpo) corpo.innerHTML = `<div class="alert alert-warning small mb-0">${(s1 && s1.erro) || 'Sem dados.'}</div>`;
      return;
    }
    s1Data = s1;
    const ult = s1.ultimo || {};
    if (kpis && !keepKpis) {
      kpis.innerHTML = [
        { label: 'Concursos', valor: s1.total_concursos ?? '—' },
        { label: 'Último classificado', valor: padLista(ult.dezenas_classificado || ult.dezenas) || ult.dezenas_fmt || '—' },
        { label: 'Último ordem sorteio', valor: padLista(ult.dezenas_sorteio) || ult.dezenas_sorteio_fmt || '—' },
        { label: 'Leituras iguais', valor: `${s1.coincidem ?? 0} / ${s1.total_concursos ?? 0}` },
      ].map((k) => `
        <div class="col-6 col-md-3">
          <div class="gc-kpi"><div class="lbl">${k.label}</div><div class="val">${k.valor}</div></div>
        </div>`).join('');
    }

    const rankRows = (s1.ranking_comparativo || []).slice().sort((a, b) => cmp(a, b, sortRank.key, sortRank.dir));
    const ranking = rankRows.map((t) => `
      <tr class="${t.recomendado ? 'gc-rec' : ''}">
        <td>${t.rank ?? ''}</td>
        <td>${padraoHtml(t.padrao, t.gaps)}</td>
        <td>${fonteLabel(t.fonte)}</td>
        <td>${t.freq_classificado || 0}</td>
        <td>${t.freq_sorteio || 0}</td>
        <td><strong>${t.score}</strong></td>
      </tr>`).join('');

    const confRows = (s1.confronto || s1.linhas || []).slice().sort((a, b) => cmp(a, b, sortConf.key, sortConf.dir));
    const concursosConf = confRows.map((r) => Number(r.concurso)).filter((n) => Number.isFinite(n));
    const confFaixa = concursosConf.length
      ? ` — do ${Math.max.apply(null, concursosConf)} ao ${Math.min.apply(null, concursosConf)} (${confRows.length})`
      : '';
    const confronto = confRows.map((row) => {
      const eq = !!row.padroes_iguais;
      return `
      <tr>
        <td>${row.concurso ?? '—'}</td>
        <td>${toksDezenas(row.dezenas_sorteio)}</td>
        <td>${gapsHtml(row.gaps_sorteio, 'sorteio')}</td>
        <td>${toksDezenas(row.dezenas_classificado || row.dezenas)}</td>
        <td>${gapsHtml(row.gaps_classificado || row.gaps)}</td>
        <td><span class="badge ${eq ? 'gc-eq' : 'gc-diff'}">${eq ? 'iguais' : 'diferem'}</span></td>
      </tr>`;
    }).join('');

    if (corpo) {
      corpo.innerHTML = `
        <div class="mb-3">
          <div class="gc-col-title">Ranking comparativo — escolha das sequências</div>
          <p class="small text-muted mb-1">Score = vezes no classificado + vezes na ordem de sorteio, com bônus se o mesmo padrão aparece nas duas. Clique no título da coluna para ordenar.</p>
          <div class="table-responsive">
            <table class="table table-sm table-bordered gc-table mb-0">
              <thead><tr>
                ${th('#', 'rank', 'rank')}
                ${th('Padrão de gaps', 'padrao', 'rank')}
                ${th('Origem', 'fonte', 'rank')}
                ${th('Classificado', 'freq_classificado', 'rank')}
                ${th('Sorteio', 'freq_sorteio', 'rank')}
                ${th('Score', 'score', 'rank')}
              </tr></thead>
              <tbody>${ranking || '<tr><td colspan="6">—</td></tr>'}</tbody>
            </table>
          </div>
        </div>
        <div>
          <div class="gc-col-title">Confronto por concurso${confFaixa}</div>
          <p class="small text-muted mb-1">Clique no título da coluna para ordenar. Dezenas unitárias aparecem com zero à esquerda (01, 02…).</p>
          <div class="table-responsive" style="max-height:420px;overflow:auto">
            <table class="table table-sm table-bordered gc-table mb-0">
              <thead>
                <tr>
                  ${th('Concurso', 'concurso', 'conf')}
                  ${th('Ordem de sorteio', 'dezenas_sorteio', 'conf')}
                  ${th('Gaps sorteio', 'gaps_sorteio', 'conf')}
                  ${th('Classificado', 'dezenas_classificado', 'conf')}
                  ${th('Gaps classificado', 'gaps_classificado', 'conf')}
                  ${th('Confronto', 'padroes_iguais', 'conf')}
                </tr>
              </thead>
              <tbody>${confronto || '<tr><td colspan="6">—</td></tr>'}</tbody>
            </table>
          </div>
        </div>`;
      bindSort(corpo);
    }
  }

  function deltaTxt(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return '—';
    return v > 0 ? ('+' + v) : String(v);
  }

  function deltaCls(n) {
    const v = Number(n);
    if (v > 0) return 'gc-acima';
    if (v < 0) return 'gc-abaixo';
    return 'gc-zero';
  }

  function sentidoTxt(n) {
    const v = Number(n);
    if (v > 0) return 'acima';
    if (v < 0) return 'abaixo';
    return 'na referência';
  }

  function resumoConjunto(deltas) {
    if (!deltas || !deltas.length) return '';
    const uniq = Array.from(new Set(deltas.map(Number)));
    if (uniq.length === 1) {
      const d = uniq[0];
      if (d === 0) return 'Todas as posições estão na referência. O conjunto não está deslocado.';
      const lado = d > 0 ? 'acima' : 'abaixo';
      return `Conjunto deslocado ${Math.abs(d)} unidade(s) ${lado} da régua. Os gaps entre vizinhos permanecem os mesmos.`;
    }
    const media = deltas.reduce((a, b) => a + Number(b), 0) / deltas.length;
    return `Deslocamento individual por posição. Média ${media.toFixed(2)}.`;
  }

  function deltasDe(dezenas, refs) {
    return (dezenas || []).map((d, i) => Number(d) - Number(refs[i]));
  }

  function renderRefs() {
    const refs = (reguaData && reguaData.referencias) || [];
    const dmin = Number(SPEC.dezena_min);
    const dmax = Number(SPEC.dezena_max);
    return `
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
        <div class="gc-col-title mb-0">Referência por posição</div>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="gcReguaRestaurar">Restaurar moda da janela</button>
      </div>
      <div class="d-flex flex-wrap gap-2 mb-3" id="gcReguaRefs">
        ${refs.map((r, i) => `
          <div>
            <label class="form-label small mb-0" for="gcRef${i}">P${r.posicao}</label>
            <input id="gcRef${i}" class="form-control form-control-sm gc-ref" type="number"
                   min="${dmin}" max="${dmax}" step="1" value="${refsEdit[i]}" data-idx="${i}">
            <div class="small text-muted">moda ${pad(r.referencia)} · ${r.vezes || 0}×<br>${pad(r.min)}–${pad(r.max)}</div>
          </div>`).join('')}
      </div>`;
  }

  function renderS2(rebuildRefs) {
    const corpo = $('gcCorpoS2');
    if (!corpo) return;
    const s2 = reguaData;
    if (!s2 || !s2.sucesso) {
      corpo.innerHTML = `<div class="alert alert-warning small mb-0">${(s2 && s2.erro) || 'Sem dados da régua.'}</div>`;
      return;
    }
    const ult = s2.ultimo || {};
    const dezenas = ult.dezenas || [];
    const deltas = deltasDe(dezenas, refsEdit);
    const posCards = dezenas.map((d, i) => `
      <div class="col-6 col-md-4 col-xl-3">
        <div class="gc-kpi">
          <div class="lbl">Posição ${i + 1}</div>
          <div class="val">${pad(d)} <span class="badge ${deltaCls(deltas[i])}">${deltaTxt(deltas[i])}</span></div>
          <div class="small text-muted">ref. ${pad(refsEdit[i])} · ${sentidoTxt(deltas[i])}</div>
        </div>
      </div>`).join('');

    const head = (s2.referencias || []).map((r) => `<th>P${r.posicao}</th>`).join('');
    const ordered = (s2.linhas || []).slice().sort((a, b) => Number(b.concurso) - Number(a.concurso));
    const atual = ordered.length ? ordered[0].concurso : null;
    const primeiro = ordered.length ? ordered[ordered.length - 1].concurso : null;
    const faixa = (primeiro != null && atual != null)
      ? `Do concurso ${atual} ao ${primeiro} (${ordered.length})`
      : 'Concursos';
    const rows = ordered.map((row) => {
      const dz = deltasDe(row.dezenas || [], refsEdit);
      const cells = (row.dezenas || []).map((d, i) =>
        `<td>${pad(d)}<span class="gc-delta ${deltaCls(dz[i])}">${deltaTxt(dz[i])}</span></td>`
      ).join('');
      return `<tr><td>${row.concurso ?? '—'}</td>${cells}</tr>`;
    }).join('');

    const refsHtml = rebuildRefs ? renderRefs() : '';
    const corpoId = 'gcReguaDetalhe';
    const detalhe = `
      <div id="${corpoId}">
        <p class="gc-hint mb-3">${resumoConjunto(deltas)} Último concurso ${ult.concurso != null ? ult.concurso : '—'} · leitura classificada (combinação ordenada).</p>
        <div class="row g-2 mb-3">${posCards}</div>
        <div class="gc-col-title">${faixa}</div>
        <div class="table-responsive" style="max-height:420px;overflow:auto">
          <table class="table table-sm table-bordered gc-table mb-0">
            <thead><tr><th>Concurso</th>${head}</tr></thead>
            <tbody>${rows || '<tr><td colspan="99">—</td></tr>'}</tbody>
          </table>
        </div>
      </div>`;

    if (rebuildRefs || !corpo.querySelector('#gcReguaRefs')) {
      corpo.innerHTML = refsHtml + detalhe;
      bindRefs();
    } else {
      const det = corpo.querySelector('#' + corpoId);
      if (det) det.outerHTML = detalhe;
      else corpo.insertAdjacentHTML('beforeend', detalhe);
    }
  }

  function bindRefs() {
    const corpo = $('gcCorpoS2');
    if (!corpo) return;
    corpo.querySelectorAll('.gc-ref').forEach((inp) => {
      inp.addEventListener('change', () => {
        const i = Number(inp.getAttribute('data-idx'));
        let v = Number(inp.value);
        const dmin = Number(SPEC.dezena_min);
        const dmax = Number(SPEC.dezena_max);
        if (!Number.isFinite(v)) v = refsEdit[i];
        v = Math.max(dmin, Math.min(dmax, v));
        inp.value = String(v);
        refsEdit[i] = v;
        renderS2(false);
      });
    });
    const btn = $('gcReguaRestaurar');
    if (btn) {
      btn.addEventListener('click', () => {
        const refs = (reguaData && reguaData.referencias) || [];
        refsEdit = refs.map((r) => r.referencia);
        renderS2(true);
      });
    }
  }

  let geoPayload = null;
  let geoLinhas = [];
  let geoConc = null;
  let sortGeo = { key: 'concurso', dir: 'desc' };

  function coordDezena(n) {
    const v = Number(n);
    if (v === 31) return [3, 0];
    if (v >= 1 && v <= 30) return [Math.floor((v - 1) / 10), (v - 1) % 10];
    return null;
  }

  function round2(n) {
    return Math.round(Number(n) * 100) / 100;
  }

  function sequenciasHoriz(nums, coords) {
    const por = {};
    nums.forEach((n) => {
      if (n === 31) return;
      const c = coords[n];
      if (!c || c[0] > 2) return;
      (por[c[0]] = por[c[0]] || []).push(n);
    });
    const saida = [];
    Object.keys(por).forEach((k) => {
      const ordenados = [...new Set(por[k])].sort((a, b) => a - b);
      let grupo = ordenados.length ? [ordenados[0]] : [];
      ordenados.slice(1).forEach((atual) => {
        if (atual === grupo[grupo.length - 1] + 1) {
          grupo.push(atual);
          return;
        }
        if (grupo.length >= 2) saida.push(grupo.map(pad).join('-'));
        grupo = [atual];
      });
      if (grupo.length >= 2) saida.push(grupo.map(pad).join('-'));
    });
    return saida;
  }

  function diagonaisGeo(nums, coords) {
    const celulas = {};
    nums.forEach((n) => {
      if (n === 31) return;
      const c = coords[n];
      if (!c || c[0] > 2) return;
      celulas[c[0] + ',' + c[1]] = n;
    });
    const vistos = {};
    const saida = [];
    const viz = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
    Object.keys(celulas).forEach((origem) => {
      if (vistos[origem]) return;
      const pilha = [origem];
      const comp = [];
      vistos[origem] = true;
      while (pilha.length) {
        const atual = pilha.pop();
        const partes = atual.split(',').map(Number);
        comp.push(partes);
        viz.forEach(([dr, dc]) => {
          const chave = (partes[0] + dr) + ',' + (partes[1] + dc);
          if (celulas[chave] != null && !vistos[chave]) {
            vistos[chave] = true;
            pilha.push(chave);
          }
        });
      }
      if (comp.length < 2) return;
      comp.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      saida.push(comp.map((p) => pad(celulas[p[0] + ',' + p[1]])).join('-'));
    });
    return saida;
  }

  function indicadoresGeo(dezenas) {
    const nums = [...new Set((dezenas || []).map(Number).filter((n) => coordDezena(n)))].sort((a, b) => a - b);
    const coords = {};
    nums.forEach((n) => { coords[n] = coordDezena(n); });
    const linhas = [0, 1, 2].map((r) => nums.filter((n) => coords[n][0] === r).length);
    linhas.push(nums.indexOf(31) >= 0 ? 1 : 0);
    const noGrid = nums.filter((n) => n !== 31);
    const colunas = noGrid.map((n) => coords[n][1] + 1);
    const cont = {};
    colunas.forEach((c) => { cont[c] = (cont[c] || 0) + 1; });
    const repetidas = Object.keys(cont).map(Number).sort((a, b) => a - b).filter((c) => cont[c] > 1).map((c) => ({
      coluna: c,
      qtd: cont[c],
      dezenas: noGrid.filter((n) => coords[n][1] + 1 === c),
    }));
    const faixas = { esquerda: 0, centro: 0, direita: 0 };
    noGrid.forEach((n) => {
      const col = coords[n][1] + 1;
      if (col <= 3) faixas.esquerda += 1;
      else if (col <= 7) faixas.centro += 1;
      else faixas.direita += 1;
    });
    const faixaMais = ['centro', 'direita', 'esquerda'].reduce((melhor, nome) => {
      if (!melhor) return nome;
      if (faixas[nome] > faixas[melhor]) return nome;
      if (faixas[nome] === faixas[melhor] && nome > melhor) return nome;
      return melhor;
    }, null);
    const linhaMax = Math.max(linhas[0], linhas[1], linhas[2]);
    const linhasMais = [1, 2, 3].filter((i) => linhas[i - 1] === linhaMax && linhaMax);
    const pontos = nums.map((n) => coords[n]);
    let media = 0;
    let maior = 0;
    let parMaior = [];
    if (nums.length >= 2) {
      const pares = [];
      parMaior = [nums[0], nums[1]];
      for (let i = 0; i < nums.length; i += 1) {
        for (let j = i + 1; j < nums.length; j += 1) {
          const d = Math.hypot(coords[nums[i]][0] - coords[nums[j]][0], coords[nums[i]][1] - coords[nums[j]][1]);
          pares.push(d);
          if (d > maior) {
            maior = d;
            parMaior = [nums[i], nums[j]];
          }
        }
      }
      media = pares.reduce((s, d) => s + d, 0) / pares.length;
    }
    const mediaR = pontos.length ? pontos.reduce((s, p) => s + p[0], 0) / pontos.length : 0;
    const mediaC = pontos.length ? pontos.reduce((s, p) => s + p[1], 0) / pontos.length : 0;
    let desvioR = 0;
    let desvioC = 0;
    if (pontos.length >= 2) {
      desvioR = Math.sqrt(pontos.reduce((s, p) => s + (p[0] - mediaR) ** 2, 0) / pontos.length);
      desvioC = Math.sqrt(pontos.reduce((s, p) => s + (p[1] - mediaC) ** 2, 0) / pontos.length);
    }
    const indice = pontos.length ? Math.round(Math.min(100, (media / Math.hypot(3, 9)) * 100)) : 0;
    const outras = nums.filter((n) => n !== 31);
    let media31 = null;
    let outrasLinhas = [];
    if (nums.indexOf(31) >= 0 && outras.length) {
      const dists = outras.map((n) => Math.hypot(coords[31][0] - coords[n][0], coords[31][1] - coords[n][1]));
      media31 = dists.reduce((s, d) => s + d, 0) / dists.length;
      outrasLinhas = [0, 1, 2].map((r) => outras.filter((n) => coords[n][0] === r).length);
    }
    let linhaCentro = 'linha ' + (Math.round(mediaR) + 1);
    if (mediaR >= 2.5) linhaCentro = 'linha do 31';
    return {
      linhas,
      linhas_fmt: linhas.join(' - '),
      tem_31: nums.indexOf(31) >= 0,
      colunas,
      colunas_distintas: Object.keys(cont).length,
      colunas_repetidas: repetidas,
      concentracao: { linhas_mais: linhasMais, faixas, faixa_mais: faixaMais },
      dispersao: { desvio_linha: round2(desvioR), desvio_coluna: round2(desvioC), indice },
      sequencias: sequenciasHoriz(nums, coords),
      diagonais: diagonaisGeo(nums, coords),
      distancias: { media: round2(media), maior: round2(maior), par_maior: parMaior },
      centro: { linha: round2(mediaR), coluna: round2(mediaC), rotulo: linhaCentro + ' · coluna ' + (Math.round(mediaC) + 1) },
      analise_31: {
        presente: nums.indexOf(31) >= 0,
        outras_linhas: outrasLinhas,
        distancia_media: media31 == null ? null : round2(media31),
      },
    };
  }

  function geometriaLocal(linhas) {
    const por = {};
    const padroes = {};
    let com = 0;
    (linhas || []).forEach((row) => {
      const ind = indicadoresGeo(row.dezenas_classificado || row.dezenas || []);
      por[String(row.concurso)] = ind;
      padroes[ind.linhas_fmt] = (padroes[ind.linhas_fmt] || 0) + 1;
      if (ind.tem_31) com += 1;
    });
    const total = Object.keys(por).length;
    const top = Object.keys(padroes)
      .map((padrao) => ({ padrao, frequencia: padroes[padrao] }))
      .sort((a, b) => b.frequencia - a.frequencia)
      .slice(0, 8);
    return {
      sucesso: true,
      por_concurso: por,
      historico: { total, com_31: com, sem_31: Math.max(0, total - com), padroes_linha: top },
    };
  }

  function escGeo(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function volanteHtml(dezenas) {
    const marcadas = new Set((dezenas || []).map((n) => Number(n)));
    const linhas = [rangeGeo(1, 10), rangeGeo(11, 20), rangeGeo(21, 30), [31]];
    return `<div class="gc-volante">${linhas.map((linha, i) => (
      `<div class="gc-vol-row${i === 3 ? ' gc-vol-31' : ''}">${linha.map((n) => (
        `<span class="gc-vol-cell${marcadas.has(n) ? ' on' : ''}">${pad(n)}</span>`
      )).join('')}</div>`
    )).join('')}</div>`;
  }

  function rangeGeo(a, b) {
    const out = [];
    for (let n = a; n <= b; n += 1) out.push(n);
    return out;
  }

  function listaFmt(arr) {
    if (!arr || !arr.length) return '—';
    return arr.map((x) => escGeo(x)).join(' · ');
  }

  function textoRepetidas(ind) {
    const repetidas = (ind.colunas_repetidas || []).map((c) => (
      `coluna ${c.coluna} × ${c.qtd} (${(c.dezenas || []).map(pad).join(' ')})`
    ));
    return repetidas.length ? repetidas.join(' · ') : 'nenhuma';
  }

  function textoConcentracao(ind) {
    const faixas = (ind.concentracao && ind.concentracao.faixas) || {};
    return `linhas ${listaFmt((ind.concentracao || {}).linhas_mais)} · faixa ${(ind.concentracao || {}).faixa_mais || '—'} (esquerda ${faixas.esquerda || 0}, centro ${faixas.centro || 0}, direita ${faixas.direita || 0})`;
  }

  function textoDispersao(ind) {
    const disp = ind.dispersao || {};
    return `índice ${disp.indice ?? '—'} · desvio linha ${disp.desvio_linha ?? '—'} · desvio coluna ${disp.desvio_coluna ?? '—'}`;
  }

  function textoDistancias(ind) {
    const dist = ind.distancias || {};
    const par = (dist.par_maior || []).map(pad).join(' – ');
    return `média ${dist.media ?? '—'} · maior ${dist.maior ?? '—'}${par ? ' (' + par + ')' : ''}`;
  }

  function toksFixos(arr, n) {
    const vals = (arr || []).slice(0, n);
    while (vals.length < n) vals.push(null);
    return `<span class="gc-toks">${vals.map((v) => (
      v == null
        ? '<span class="gc-tok gc-tok-vazio">00</span>'
        : `<span class="gc-tok">${pad(v)}</span>`
    )).join('')}</span>`;
  }

  function htmlColunas(ind) {
    return toksFixos(ind.colunas || [], 7);
  }

  function htmlRepetidas(ind) {
    const reps = ind.colunas_repetidas || [];
    if (!reps.length) return toksFixos([], 1);
    return reps.map((c) => (
      `<span class="gc-toks"><span class="gc-tok">${pad(c.coluna)}</span><span class="gc-tok-x">×${escGeo(c.qtd)}</span>${toksFixos(c.dezenas || [], 4)}</span>`
    )).join('');
  }

  function htmlConcentracao(ind) {
    const faixas = (ind.concentracao && ind.concentracao.faixas) || {};
    const linhas = (ind.concentracao && ind.concentracao.linhas_mais) || [];
    return `<span class="gc-toks"><span class="gc-tok-lbl">L</span>${toksFixos(linhas, 3)}<span class="gc-tok-lbl">E</span><span class="gc-tok">${pad(faixas.esquerda || 0)}</span><span class="gc-tok-lbl">C</span><span class="gc-tok">${pad(faixas.centro || 0)}</span><span class="gc-tok-lbl">D</span><span class="gc-tok">${pad(faixas.direita || 0)}</span></span>`;
  }

  function texto31(ind) {
    const a31 = ind.analise_31 || {};
    if (!a31.presente) return 'ausente';
    return `presente · outras linhas ${listaFmt(a31.outras_linhas)} · distância média ${a31.distancia_media ?? '—'}`;
  }

  function thGeo(label, key) {
    return `<th class="gc-th-sort" data-sort="${key}" title="Ordenar por ${label}">${label}${sortInd(sortGeo, key)}</th>`;
  }

  function cmpGeo(a, b) {
    let va = a[sortGeo.key];
    let vb = b[sortGeo.key];
    const numerico = va != null && vb != null && typeof va === 'number' && typeof vb === 'number';
    if (!numerico) {
      va = String(va == null ? '' : va);
      vb = String(vb == null ? '' : vb);
    }
    let r = 0;
    if (va < vb) r = -1;
    else if (va > vb) r = 1;
    return sortGeo.dir === 'asc' ? r : -r;
  }

  function linhasGeoHistorico() {
    const linhas = geoLinhas || [];
    if (linhas.length < 2) return [];
    const ultimo = String(linhas[0].concurso);
    return linhas.filter((row) => String(row.concurso) !== ultimo);
  }

  function registrosGeo() {
    const por = (geoPayload && geoPayload.por_concurso) || {};
    return linhasGeoHistorico().map((row) => {
      const ind = por[String(row.concurso)] || {};
      const disp = ind.dispersao || {};
      const dist = ind.distancias || {};
      const a31 = ind.analise_31 || {};
      return {
        concurso: Number(row.concurso),
        data: row.data || '',
        linhas: ind.linhas_fmt || '—',
        colunas_distintas: Number(ind.colunas_distintas || 0),
        dispersao: Number(disp.indice || 0),
        colunas: listaFmt(ind.colunas),
        colunas_html: htmlColunas(ind),
        repetidas: textoRepetidas(ind),
        repetidas_html: htmlRepetidas(ind),
        concentracao: textoConcentracao(ind),
        concentracao_html: htmlConcentracao(ind),
        dispersao_txt: textoDispersao(ind),
        sequencias: listaFmt(ind.sequencias),
        diagonais: listaFmt(ind.diagonais),
        dist_media: Number(dist.media || 0),
        distancias: textoDistancias(ind),
        centro: (ind.centro || {}).rotulo || '—',
        tem_31: a31.presente ? 1 : 0,
        situacao_31: texto31(ind),
      };
    }).sort(cmpGeo);
  }

  function bindSortGeo() {
    const corpo = $('gcCorpoS3');
    if (!corpo) return;
    corpo.querySelectorAll('th.gc-th-sort').forEach((el) => {
      el.addEventListener('click', (ev) => {
        ev.preventDefault();
        const key = el.getAttribute('data-sort');
        if (sortGeo.key === key) sortGeo.dir = sortGeo.dir === 'asc' ? 'desc' : 'asc';
        else {
          sortGeo.key = key;
          sortGeo.dir = (key === 'concurso' || key === 'colunas_distintas' || key === 'dispersao' || key === 'dist_media' || key === 'tem_31') ? 'desc' : 'asc';
        }
        renderS3();
      });
    });
  }

  function tabelaGeoHtml() {
    const regs = registrosGeo();
    if (!regs.length) {
      return '<p class="small text-muted mt-3 mb-0">Ainda não há concurso anterior ao último nesta base.</p>';
    }
    const body = regs.map((r) => `
      <tr>
        <td>${escGeo(r.concurso)}</td>
        <td>${escGeo(r.data || '—')}</td>
        <td>${escGeo(r.linhas)}</td>
        <td>${escGeo(r.colunas_distintas)}</td>
        <td>${escGeo(r.dispersao)}</td>
        <td class="gc-alinha">${r.colunas_html}</td>
        <td class="gc-alinha">${r.repetidas_html}</td>
        <td class="gc-alinha">${r.concentracao_html}</td>
        <td>${escGeo(r.dispersao_txt)}</td>
        <td>${r.sequencias}</td>
        <td>${r.diagonais}</td>
        <td>${escGeo(r.distancias)}</td>
        <td>${escGeo(r.centro)}</td>
        <td>${escGeo(r.situacao_31)}</td>
      </tr>`).join('');
    return `
      <div class="mt-3">
        <div class="gc-col-title">Concursos anteriores ao último</div>
        <p class="small text-muted mb-2">Do primeiro ao penúltimo. O penúltimo abre a tabela. O último permanece no panorama acima. Clique no título da coluna para ordenar.</p>
        <div class="gc-geo-scroll">
          <table class="table table-sm table-striped gc-table gc-geo-table">
            <thead><tr>
              ${thGeo('Concurso', 'concurso')}
              ${thGeo('Data', 'data')}
              ${thGeo('Linhas', 'linhas')}
              ${thGeo('Colunas distintas', 'colunas_distintas')}
              ${thGeo('Dispersão', 'dispersao')}
              ${thGeo('Colunas ocupadas', 'colunas')}
              ${thGeo('Colunas repetidas', 'repetidas')}
              ${thGeo('Concentração', 'concentracao')}
              ${thGeo('Dispersão (desvio)', 'dispersao_txt')}
              ${thGeo('Sequências horizontais', 'sequencias')}
              ${thGeo('Diagonais', 'diagonais')}
              ${thGeo('Distâncias', 'dist_media')}
              ${thGeo('Centro', 'centro')}
              ${thGeo('31', 'tem_31')}
            </tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      </div>`;
  }

  function renderS3() {
    const corpo = $('gcCorpoS3');
    if (!corpo) return;
    if (!geoPayload || !geoPayload.sucesso) {
      corpo.innerHTML = '<p class="text-muted small mb-0">Sem dados de geometria.</p>';
      return;
    }
    const sel = $('gcGeoConcurso');
    const linhas = geoLinhas || [];
    if (!linhas.length) {
      corpo.innerHTML = '<p class="text-muted small mb-0">Nenhum concurso nesta base.</p>';
      if (sel) sel.innerHTML = '';
      return;
    }
    if (geoConc == null || !linhas.some((r) => String(r.concurso) === String(geoConc))) {
      geoConc = linhas[0].concurso;
    }
    if (sel && sel.dataset.ready !== '1') {
      sel.addEventListener('change', () => {
        geoConc = sel.value;
        renderS3();
      });
      sel.dataset.ready = '1';
    }
    if (sel) {
      sel.innerHTML = linhas.map((r) => (
        `<option value="${escGeo(r.concurso)}"${String(r.concurso) === String(geoConc) ? ' selected' : ''}>${escGeo(r.concurso)}${r.data ? ' · ' + escGeo(r.data) : ''}</option>`
      )).join('');
    }
    const row = linhas.find((r) => String(r.concurso) === String(geoConc)) || linhas[0];
    const ind = (geoPayload.por_concurso || {})[String(row.concurso)] || {};
    const dezenas = row.dezenas_classificado || row.dezenas || [];
    const hist = geoPayload.historico || {};
    const disp = ind.dispersao || {};
    corpo.innerHTML = `
      <div class="row g-3">
        <div class="col-lg-5">
          <div class="gc-col-title">Volante</div>
          ${volanteHtml(dezenas)}
          <p class="small text-muted mt-2 mb-0">Dezenas: ${escGeo((dezenas || []).map(pad).join(' '))}</p>
        </div>
        <div class="col-lg-7 gc-geo-bloco">
          <div class="row g-2 mb-2">
            <div class="col-6 col-md-4"><div class="gc-kpi"><div class="lbl">Linhas</div><div class="val">${escGeo(ind.linhas_fmt || '—')}</div></div></div>
            <div class="col-6 col-md-4"><div class="gc-kpi"><div class="lbl">Colunas distintas</div><div class="val">${escGeo(ind.colunas_distintas ?? '—')}</div></div></div>
            <div class="col-6 col-md-4"><div class="gc-kpi"><div class="lbl">Dispersão</div><div class="val">${escGeo(disp.indice ?? '—')}</div></div></div>
          </div>
          <p class="mb-1"><strong>Colunas ocupadas:</strong> ${listaFmt(ind.colunas)}</p>
          <p class="mb-1"><strong>Colunas repetidas:</strong> ${escGeo(textoRepetidas(ind))}</p>
          <p class="mb-1"><strong>Concentração:</strong> ${textoConcentracao(ind)}</p>
          <p class="mb-1"><strong>Dispersão:</strong> ${escGeo(textoDispersao(ind))}</p>
          <p class="mb-1"><strong>Sequências horizontais:</strong> ${listaFmt(ind.sequencias)}</p>
          <p class="mb-1"><strong>Diagonais:</strong> ${listaFmt(ind.diagonais)}</p>
          <p class="mb-1"><strong>Distâncias:</strong> ${escGeo(textoDistancias(ind))}</p>
          <p class="mb-1"><strong>Centro:</strong> ${escGeo((ind.centro || {}).rotulo || '—')}</p>
          <p class="mb-1"><strong>31:</strong> ${escGeo(texto31(ind))}</p>
          <p class="small text-muted mb-0">Nesta janela: ${escGeo(hist.total || 0)} concursos · com 31: ${escGeo(hist.com_31 || 0)} · sem 31: ${escGeo(hist.sem_31 || 0)}. Padrão de linhas mais comum: ${escGeo((hist.padroes_linha && hist.padroes_linha[0] && hist.padroes_linha[0].padrao) || '—')} (${escGeo((hist.padroes_linha && hist.padroes_linha[0] && hist.padroes_linha[0].frequencia) || 0)}).</p>
        </div>
      </div>
      ${tabelaGeoHtml()}`;
    bindSortGeo();
  }

  async function load() {
    const bl = $('gcLblBase');
    const jl = $('gcLblJanela');
    if (bl) bl.textContent = base === 'geral' ? 'Geral' : (base === 'vencedores' ? 'Vencedores' : 'Acumulados');
    if (jl) jl.textContent = janela === 0 ? 'Todos' : ('Janela ' + janela);
    try {
      const r = await fetch(API + '/contexto?' + qs());
      const j = await r.json();
      if (!j.sucesso) throw new Error(j.erro || 'Falha ao carregar');
      const ult = (j.sessao1 && j.sessao1.ultimo) || {};
      const ul = $('gcLblUltimo');
      if (ul) ul.textContent = ult.concurso != null ? ('Último c.' + ult.concurso) : '—';
      renderS1(j.sessao1);
      reguaData = j.sessao2 || null;
      const refs = (reguaData && reguaData.referencias) || [];
      refsEdit = refs.map((r) => r.referencia);
      renderS2(true);
      geoLinhas = (j.sessao1 && j.sessao1.linhas) || [];
      geoPayload = j.sessao3 || geometriaLocal(geoLinhas);
      try { renderS3(); } catch (errGeo) {
        const c3 = $('gcCorpoS3');
        if (c3) c3.innerHTML = `<div class="alert alert-danger small mb-0">${escGeo(errGeo.message || errGeo)}</div>`;
      }
    } catch (e) {
      const c1 = $('gcCorpoS1');
      if (c1) c1.innerHTML = `<div class="alert alert-danger small mb-0">${e.message}</div>`;
    }
  }

  root.querySelectorAll('.base-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.base-tab-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      base = btn.getAttribute('data-base') || 'geral';
      load();
    });
  });
  root.querySelectorAll('.janela-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.janela-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      janela = Number(btn.getAttribute('data-janela') || 0);
      load();
    });
  });
  load();
})();
