/**
 * Escolha Visual — aba Visualização (Círculos / Horizontal / Vertical).
 * Isolado desta tela; reutiliza a janela carregada na aba Escolha.
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

  function render() {
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
    mode = next === 'horizontal' || next === 'vertical' ? next : 'circulos';
    content.dataset.evVizMode = mode;
    buttons.forEach((btn) => {
      const active = btn.dataset.evVizMode === mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    render();
  }

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => setMode(btn.dataset.evVizMode));
  });

  window.addEventListener('ev:sorteios-carregados', () => {
    dirty = true;
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
