(function () {
  'use strict';

  const root = document.getElementById('gc-root');
  if (!root) return;

  const API = window.__GC_API__ || root.dataset.api;
  const SPEC = window.__GC_SPEC__ || {};
  const padW = Math.max(2, Number(SPEC.pad_width) > 0 ? Number(SPEC.pad_width) : 2);

  let base = 'geral';
  let janela = SPEC.janela_default != null ? Number(SPEC.janela_default) : 0;
  let padraoSel = '';
  let s1Data = null;
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

  function balls(arr) {
    return (arr || []).map((n) => `<span class="gc-ball">${pad(n)}</span>`).join('') || '—';
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

  function fillInicial() {
    const sel = $('gcInicial');
    if (!sel) return;
    const permitidas = SPEC.iniciais_permitidas || [];
    const cur = sel.value;
    sel.innerHTML = permitidas.map((n) =>
      `<option value="${n}">${pad(n)}</option>`
    ).join('');
    const min = SPEC.inicial_min;
    sel.value = (cur && permitidas.map(String).includes(cur)) ? cur : String(min);
    const hint = $('gcInicialHint');
    if (hint) {
      hint.textContent =
        `Permitidos: ${pad(SPEC.inicial_min)}–${pad(SPEC.inicial_max)} (configurável). ` +
        `Dezenas acima de ${pad(SPEC.inicial_max)} não entram como inicial.`;
    }
  }

  function qs() {
    const p = new URLSearchParams();
    p.set('janela', String(janela));
    p.set('base', base);
    const ini = $('gcInicial') && $('gcInicial').value;
    if (ini) p.set('inicial', ini);
    const perfil = $('gcPerfil') && $('gcPerfil').value;
    if (perfil) p.set('perfil', perfil);
    if (padraoSel) p.set('padrao', padraoSel);
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
      <tr class="${t.recomendado ? 'gc-rec' : ''} gc-padrao${t.padrao === padraoSel ? ' sel' : ''}" data-padrao="${String(t.padrao).replace(/"/g, '&quot;')}">
        <td>${t.rank ?? ''}</td>
        <td>${padraoHtml(t.padrao, t.gaps)}</td>
        <td>${fonteLabel(t.fonte)}</td>
        <td>${t.freq_classificado || 0}</td>
        <td>${t.freq_sorteio || 0}</td>
        <td><strong>${t.score}</strong></td>
      </tr>`).join('');

    const confRows = (s1.confronto || s1.linhas || []).slice(0, 80).sort((a, b) => cmp(a, b, sortConf.key, sortConf.dir));
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
          <p class="small text-muted mb-1">Score = vezes no classificado + vezes na ordem de sorteio, com bônus se o mesmo padrão aparece nas duas. Clique no título da coluna para ordenar; clique na linha para usar na Sessão 2.</p>
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
          <div class="gc-col-title">Confronto por concurso</div>
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
      corpo.querySelectorAll('.gc-padrao').forEach((tr) => {
        tr.addEventListener('click', () => {
          padraoSel = tr.getAttribute('data-padrao') || '';
          load();
        });
      });
    }
  }

  function renderBlocoCiclo(bloco, titulo) {
    if (!bloco) return `<div class="text-muted small">—</div>`;
    if (!bloco.sucesso) {
      return `<div class="alert alert-warning small mb-0">${bloco.erro || 'Sem ciclo viável nesta leitura.'}</div>`;
    }
    const passos = (bloco.passos || []).map((p) => `
      <div class="gc-passo">
        <strong>Posição ${p.posicao}</strong>
        → ${pad(p.dezena)}
        ${p.ciclo == null ? ' · número inicial' : ` · ciclo ${pad(p.ciclo)} (${p.origem || ''})`}
      </div>`).join('');
    return `
      <div class="gc-col-title">${titulo}</div>
      <div class="mb-2">${balls(bloco.aposta)}
        <span class="badge ${bloco.viavel ? 'bg-success' : 'bg-danger'} ms-2">${bloco.viavel ? 'Viável' : 'Não cabe'}</span>
        <span class="badge bg-light text-dark border">Ciclos ${padLista(bloco.ciclos) || bloco.padrao || '—'}</span>
      </div>
      <div class="border rounded">${passos || '<div class="p-2 text-muted small">Sem passos.</div>'}</div>`;
  }

  function renderS2(s2) {
    const corpo = $('gcCorpoS2');
    if (!corpo) return;
    if (!s2) {
      corpo.innerHTML = `<div class="alert alert-warning small mb-0">Informe um inicial válido.</div>`;
      return;
    }
    const clas = s2.classificado || (s2.leitura !== 'sorteio' ? s2 : null);
    const sort = s2.sorteio || null;
    corpo.innerHTML = `
      <div class="row g-3">
        <div class="col-lg-6">${renderBlocoCiclo(clas, 'Ciclo · classificado (divulgação Caixa)')}</div>
        <div class="col-lg-6">${renderBlocoCiclo(sort, 'Ciclo · ordem de sorteio (posições do sorteio)')}</div>
      </div>`;
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
      renderS2(j.sessao2);
    } catch (e) {
      const c1 = $('gcCorpoS1');
      if (c1) c1.innerHTML = `<div class="alert alert-danger small mb-0">${e.message}</div>`;
    }
  }

  fillInicial();

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
  ['gcInicial', 'gcPerfil'].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener('change', load);
  });

  load();
})();
