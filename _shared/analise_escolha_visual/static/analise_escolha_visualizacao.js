/**
 * Escolha Visual — aba Visualização (Círculos / Horizontal / Vertical / Pool).
 * Isolado desta tela; reutiliza a janela carregada na aba Escolha.
 * O modo Pool sempre lista do concurso 1 ao atual.
 */
(function () {
  'use strict';

  const root = document.getElementById('ev-root');
  if (!root) return;

  const content = document.getElementById('evVizContent');
  const buttons = root.querySelectorAll('.ev-viz-mode');
  if (!content || !buttons.length) return;

  let mode = 'circulos';
  let dirty = true;
  let selectedDezenas = new Set();
  let poolCache = null;
  let poolReq = 0;

  let mesesCores = {};
  try {
    mesesCores = JSON.parse(root.dataset.mesesCores || '{}') || {};
  } catch (_) {
    mesesCores = {};
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function fmt(n, pad) {
    return String(Number(n)).padStart(pad || 2, '0');
  }

  function mesAbrev(nome) {
    if (!nome) return '';
    const n = String(nome).normalize('NFD').replace(/\p{M}/gu, '');
    return n.slice(0, 3);
  }

  function mesCor(nome) {
    if (!nome) return '#6c757d';
    if (mesesCores[nome]) return mesesCores[nome];
    const key = Object.keys(mesesCores).find((k) =>
      k.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
      === String(nome).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
    );
    return key ? mesesCores[key] : '#6c757d';
  }

  function dataCurta(data) {
    const m = String(data || '').match(/(\d{1,2})\/(\d{1,2})/);
    if (!m) return String(data || '');
    return `${m[1].padStart(2, '0')}/${m[2].padStart(2, '0')}`;
  }

  function meta() {
    return (window.EvEscolha && window.EvEscolha.getMeta)
      ? window.EvEscolha.getMeta()
      : {
        pad: parseInt(root.dataset.padWidth || '2', 10) || 2,
        dezenaMin: parseInt(root.dataset.dezenaMin || '1', 10) || 1,
        dezenaMax: parseInt(root.dataset.dezenaMax || '31', 10) || 31,
        extraMes: String(root.dataset.extraMes || '') === '1',
      };
  }

  function listaSorteios() {
    return (window.EvEscolha && window.EvEscolha.getSorteios)
      ? window.EvEscolha.getSorteios()
      : [];
  }

  /** Laranja = normal; roxo = repetiu do concurso anterior na lista. */
  function tomBola(n, anteriorNums) {
    if (anteriorNums && anteriorNums.has(Number(n))) return 'roxo';
    return 'laranja';
  }

  function badgeMes(s) {
    const m = meta();
    if (!m.extraMes || !s.mes_nome) return '';
    const ab = mesAbrev(s.mes_nome);
    if (!ab) return '';
    const cor = mesCor(s.mes_nome);
    return `<span class="ev-viz-mes" style="background-color:${esc(cor)}">${esc(ab)}</span>`;
  }

  function numsOrdenados(s) {
    if (s.numeros_ordenados && s.numeros_ordenados.length) {
      return s.numeros_ordenados.map(Number);
    }
    return [...(s.numeros || [])].map(Number).sort((a, b) => a - b);
  }

  /** Anterior cronológico: na ordem desc, o próximo item da lista; na asc, o anterior. */
  function anteriorDo(sorteios, index) {
    const filtros = (window.EvEscolha && window.EvEscolha.getFiltros)
      ? window.EvEscolha.getFiltros()
      : { ordem: 'desc' };
    const ordem = (filtros.ordem || 'desc').toLowerCase();
    if (ordem === 'desc') {
      return index < sorteios.length - 1 ? sorteios[index + 1] : null;
    }
    return index > 0 ? sorteios[index - 1] : null;
  }

  function renderCirculos(sorteios) {
    const m = meta();
    const min = m.dezenaMin;
    const max = m.dezenaMax;
    const cards = sorteios.map((s) => {
      const set = new Set(numsOrdenados(s));
      let cells = '';
      for (let n = min; n <= max; n++) {
        const on = set.has(n);
        cells += `<span class="ev-viz-dot${on ? ' is-on' : ''}">${fmt(n, m.pad)}</span>`;
      }
      return `<article class="ev-viz-card-circulo">
        <header class="ev-viz-card-head">
          <span class="ev-viz-card-meta"><strong>#${esc(s.concurso)}</strong> <span class="ev-viz-data">${esc(s.data || '')}</span></span>
          ${badgeMes(s)}
        </header>
        <div class="ev-viz-grid-dots">${cells}</div>
      </article>`;
    }).join('');
    return `<div class="ev-viz-grid-circulos">${cards}</div>`;
  }

  function renderHorizontal(sorteios) {
    const m = meta();
    const rows = sorteios.map((s, index) => {
      const nums = numsOrdenados(s);
      const ant = anteriorDo(sorteios, index);
      const antSet = ant ? new Set(numsOrdenados(ant)) : null;
      const bolas = nums.map((n) =>
        `<span class="ev-viz-bola tom-${tomBola(n, antSet)}">${fmt(n, m.pad)}</span>`
      ).join('');
      return `<div class="ev-viz-row-h">
        <div class="ev-viz-row-meta">
          <strong>#${esc(s.concurso)}</strong>
          <span class="ev-viz-data">${esc(s.data || '')}</span>
          ${badgeMes(s)}
        </div>
        <div class="ev-viz-bolas-h">${bolas}</div>
      </div>`;
    }).join('');
    return `<div class="ev-viz-lista-h">${rows}</div>`;
  }

  function renderVertical(sorteios) {
    const m = meta();
    const cards = sorteios.map((s, index) => {
      const nums = numsOrdenados(s);
      const ant = anteriorDo(sorteios, index);
      const antSet = ant ? new Set(numsOrdenados(ant)) : null;
      const bolas = nums.map((n) =>
        `<span class="ev-viz-bola tom-${tomBola(n, antSet)}">${fmt(n, m.pad)}</span>`
      ).join('');
      return `<article class="ev-viz-card-v">
        <header class="ev-viz-card-v-head">
          <strong>#${esc(s.concurso)}</strong>
          <span class="ev-viz-data">${esc(dataCurta(s.data))}</span>
        </header>
        <div class="ev-viz-bolas-v">${bolas}</div>
        <footer class="ev-viz-card-v-foot">${badgeMes(s)}</footer>
      </article>`;
    }).join('');
    return `<div class="ev-viz-grid-v">${cards}</div>`;
  }

  function applyPoolFilter() {
    const wrap = content.querySelector('.ev-viz-pool');
    if (!wrap) return;
    const filtering = selectedDezenas.size > 0;
    wrap.classList.toggle('is-filtering', filtering);
    wrap.querySelectorAll('[data-pool-toggle]').forEach((btn) => {
      btn.classList.toggle('is-selected', selectedDezenas.has(Number(btn.dataset.poolToggle)));
    });
    let visiveis = 0;
    let primeira = null;
    wrap.querySelectorAll('.ev-viz-pool-row:not(.is-head)').forEach((row) => {
      if (!filtering) {
        row.hidden = false;
        visiveis += 1;
        if (!primeira) primeira = row;
        return;
      }
      const nums = (row.dataset.nums || '').split(/[\s,]+/).map(Number).filter((n) => n > 0);
      const hit = nums.some((n) => selectedDezenas.has(n));
      row.hidden = !hit;
      if (hit) {
        visiveis += 1;
        if (!primeira) primeira = row;
      }
    });
    const info = wrap.querySelector('[data-pool-filtro-info]');
    if (info) {
      if (!filtering) {
        info.textContent = 'Todas as dezenas';
      } else {
        const sel = [...selectedDezenas].sort((a, b) => a - b).map((n) => fmt(n, meta().pad));
        info.textContent = `${sel.join(' · ')} · ${visiveis} concurso${visiveis === 1 ? '' : 's'} · sorteio completo`;
      }
    }
    if (filtering && primeira) {
      const sticky = wrap.querySelector('.ev-viz-pool-sticky');
      const topo = sticky ? sticky.getBoundingClientRect().bottom : 0;
      const y = primeira.getBoundingClientRect().top;
      if (y < topo - 1) {
        primeira.scrollIntoView({ block: 'start', inline: 'nearest' });
      }
    }
  }

  async function sorteiosPool() {
    const filtros = (window.EvEscolha && window.EvEscolha.getFiltros)
      ? window.EvEscolha.getFiltros()
      : { ordem: 'desc', limite: '0' };
    const ordem = (filtros.ordem || 'desc').toLowerCase();
    const atuais = listaSorteios();
    const limite = String(filtros.limite || '0');
    if (limite === '0' && atuais.length) {
      poolCache = { ordem, sorteios: atuais };
      return atuais;
    }
    if (poolCache && poolCache.ordem === ordem && poolCache.sorteios.length) {
      return poolCache.sorteios;
    }
    const API = root.dataset.api || '/analise/api/escolha-visual';
    const qs = new URLSearchParams({ ordem, limite: '0', base: 'geral' });
    const r = await fetch(`${API}/sorteios?${qs}`);
    const data = await r.json();
    if (!data.sucesso) throw new Error(data.erro || 'Falha ao carregar');
    poolCache = { ordem, sorteios: data.sorteios || [] };
    return poolCache.sorteios;
  }

  function renderPoolHtml(sorteios) {
    const m = meta();
    const min = m.dezenaMin;
    const max = m.dezenaMax;
    const cols = max - min + 1;
    let headBtns = '';
    for (let n = min; n <= max; n++) {
      headBtns += `<button type="button" class="ev-viz-pool-head-btn" data-pool-toggle="${n}" title="Ver concursos com ${fmt(n, m.pad)} (sorteio completo)">${fmt(n, m.pad)}</button>`;
    }
    const rows = sorteios.map((s, index) => {
      const nums = numsOrdenados(s);
      const set = new Set(nums);
      const ant = anteriorDo(sorteios, index);
      const antSet = ant ? new Set(numsOrdenados(ant)) : null;
      let cells = '';
      for (let n = min; n <= max; n++) {
        const hit = set.has(n);
        const rep = !!(hit && antSet && antSet.has(n));
        const cls = `ev-viz-pool-cell${rep ? ' is-rep' : hit ? ' is-hit' : ''}`;
        cells += `<span class="${cls}">${fmt(n, m.pad)}</span>`;
      }
      const mes = badgeMes(s);
      return `<div class="ev-viz-pool-row" data-concurso="${esc(s.concurso)}" data-nums="${nums.join(',')}">
        <span class="ev-viz-pool-id">#${esc(s.concurso)}</span>
        <span class="ev-viz-pool-date">${esc(s.data || '')}</span>
        ${cells}
        <div class="ev-viz-pool-mes">${mes || ''}</div>
      </div>`;
    }).join('');

    const total = sorteios.length;
    let concMin = 0;
    let concMax = 0;
    if (total) {
      concMin = Number(sorteios[0].concurso) || 0;
      concMax = concMin;
      for (let i = 1; i < sorteios.length; i++) {
        const c = Number(sorteios[i].concurso) || 0;
        if (c < concMin) concMin = c;
        if (c > concMax) concMax = c;
      }
    }

    return `<div class="ev-viz-pool" style="--ev-pool-cols:${cols}">
      <div class="ev-viz-pool-scroller">
        <div class="ev-viz-pool-sticky">
          <div class="ev-viz-pool-toolbar-top">
            <div class="ev-viz-pool-legend">
              <span class="ev-viz-pool-swatch is-hit">${fmt(min, m.pad)}</span> Sorteada
              <span class="ev-viz-pool-swatch is-rep">${fmt(min, m.pad)}</span> Repetida
            </div>
            <span class="ev-viz-pool-info">${total} concursos · do ${concMin} ao ${concMax}</span>
            <span class="ev-viz-pool-info" data-pool-filtro-info>Todas as dezenas</span>
            <button type="button" class="btn btn-sm btn-outline-secondary" data-pool-todas>Todas</button>
          </div>
          <div class="ev-viz-pool-row is-head" role="toolbar" aria-label="Filtrar dezenas">
            <span class="ev-viz-pool-id">Conc.</span>
            <span class="ev-viz-pool-date">Data</span>
            ${headBtns}
            <div class="ev-viz-pool-mes"></div>
          </div>
        </div>
        <div class="ev-viz-pool-table">${rows}</div>
      </div>
    </div>`;
  }

  async function renderPool() {
    const req = ++poolReq;
    content.innerHTML = `<div class="text-center text-muted py-5">
      <div class="spinner-border spinner-border-sm text-primary"></div>
      <p class="mt-2 small mb-0">Carregando pool do concurso 1 ao atual…</p>
    </div>`;
    try {
      const sorteios = await sorteiosPool();
      if (req !== poolReq || mode !== 'pool') return;
      if (!sorteios.length) {
        content.innerHTML = '<div class="text-center text-muted py-5">Nenhum sorteio disponível.</div>';
        dirty = false;
        return;
      }
      content.innerHTML = renderPoolHtml(sorteios);
      applyPoolFilter();
      dirty = false;
    } catch (err) {
      if (req !== poolReq || mode !== 'pool') return;
      content.innerHTML = `<div class="alert alert-danger mb-0"><i class="fas fa-exclamation-triangle"></i> ${esc(err.message)}</div>`;
    }
  }

  function render() {
    if (mode === 'pool') {
      renderPool();
      return;
    }
    const sorteios = listaSorteios();
    if (!sorteios.length) {
      content.innerHTML = '<div class="text-center text-muted py-5">Nenhum sorteio carregado. Abra a aba <strong>Escolha</strong> e clique em Carregar.</div>';
      dirty = false;
      return;
    }
    if (mode === 'horizontal') content.innerHTML = renderHorizontal(sorteios);
    else if (mode === 'vertical') content.innerHTML = renderVertical(sorteios);
    else content.innerHTML = renderCirculos(sorteios);
    dirty = false;
  }

  function setMode(next) {
    const allowed = { horizontal: 1, vertical: 1, pool: 1, circulos: 1 };
    mode = allowed[next] ? next : 'circulos';
    content.dataset.evVizMode = mode;
    buttons.forEach((btn) => {
      const active = btn.dataset.evVizMode === mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    render();
  }

  content.addEventListener('click', (e) => {
    if (mode !== 'pool') return;
    if (e.target.closest('[data-pool-todas]')) {
      selectedDezenas.clear();
      applyPoolFilter();
      return;
    }
    const btn = e.target.closest('[data-pool-toggle]');
    if (!btn) return;
    const n = Number(btn.dataset.poolToggle);
    if (!Number.isFinite(n)) return;
    if (selectedDezenas.has(n)) selectedDezenas.delete(n);
    else selectedDezenas.add(n);
    applyPoolFilter();
  });

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => setMode(btn.dataset.evVizMode));
  });

  window.addEventListener('ev:sorteios-carregados', () => {
    dirty = true;
    poolCache = null;
    const pane = document.getElementById('ev-pane-visualizacao');
    if (pane && pane.classList.contains('active')) render();
  });

  document.getElementById('ev-tab-visualizacao')?.addEventListener('shown.bs.tab', () => {
    if (dirty) render();
  });

  // Bootstrap 5 fallback se o evento shown.bs.tab não disparar no botão
  document.getElementById('ev-tab-visualizacao')?.addEventListener('click', () => {
    setTimeout(() => { if (dirty) render(); }, 50);
  });

  setMode(mode);
})();
