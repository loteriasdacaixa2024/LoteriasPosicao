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
  let sortConf = { key: 'concurso', dir: 'asc' };

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
      ? ` — do ${Math.min.apply(null, concursosConf)} ao ${Math.max.apply(null, concursosConf)} (${confRows.length})`
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
    const ordered = (s2.linhas || []).slice().sort((a, b) => Number(a.concurso) - Number(b.concurso));
    const primeiro = ordered.length ? ordered[0].concurso : null;
    const atual = ordered.length ? ordered[ordered.length - 1].concurso : null;
    const faixa = (primeiro != null && atual != null)
      ? `Do concurso ${primeiro} ao ${atual} (${ordered.length})`
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
