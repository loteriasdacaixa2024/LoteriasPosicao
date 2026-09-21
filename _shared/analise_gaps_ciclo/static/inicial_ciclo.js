(function () {
  'use strict';

  const root = document.getElementById('ic-root');
  if (!root) return;

  const API = window.__IC_API__ || root.dataset.api;
  const SPEC = window.__IC_SPEC__ || {};
  const padW = Math.max(2, Number(SPEC.pad_width) > 0 ? Number(SPEC.pad_width) : 2);

  let base = 'geral';
  let janela = SPEC.janela_default != null ? Number(SPEC.janela_default) : 0;
  let padraoSel = '';

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
    return (arr || []).map((n) => `<span class="ic-ball">${pad(n)}</span>`).join('') || '—';
  }

  function fillInicial() {
    const sel = $('icInicial');
    if (!sel) return;
    const permitidas = SPEC.iniciais_permitidas || [];
    const cur = sel.value;
    sel.innerHTML = permitidas.map((n) => `<option value="${n}">${pad(n)}</option>`).join('');
    const min = SPEC.inicial_min;
    sel.value = (cur && permitidas.map(String).includes(cur)) ? cur : String(min);
    const hint = $('icInicialHint');
    if (hint) {
      hint.textContent =
        `Permitidos: ${pad(SPEC.inicial_min)}–${pad(SPEC.inicial_max)}. ` +
        `Dezenas acima de ${pad(SPEC.inicial_max)} não entram como inicial.`;
    }
  }

  function qs() {
    const p = new URLSearchParams();
    p.set('janela', String(janela));
    p.set('base', base);
    const ini = $('icInicial') && $('icInicial').value;
    if (ini) p.set('inicial', ini);
    const perfil = $('icPerfil') && $('icPerfil').value;
    if (perfil) p.set('perfil', perfil);
    if (padraoSel) p.set('padrao', padraoSel);
    return p.toString();
  }

  function fonteLabel(f) {
    if (f === 'ambos') return 'Ambos';
    if (f === 'sorteio') return 'Sorteio';
    return 'Classificado';
  }

  function renderPadroes(lista) {
    const tb = $('icPadroes');
    if (!tb) return;
    const rows = lista || [];
    if (padraoSel && !rows.some((t) => t.padrao === padraoSel)) padraoSel = '';
    tb.innerHTML = `
      <tr class="ic-padrao${!padraoSel ? ' sel' : ''}" data-padrao="">
        <td colspan="5">Usar o perfil selecionado</td>
      </tr>` + rows.map((t) => `
      <tr class="ic-padrao${t.padrao === padraoSel ? ' sel' : ''}" data-padrao="${String(t.padrao).replace(/"/g, '&quot;')}">
        <td class="font-monospace">${padLista(String(t.padrao).split(/\s+/))}</td>
        <td>${fonteLabel(t.fonte)}</td>
        <td>${t.freq_classificado || 0}</td>
        <td>${t.freq_sorteio || 0}</td>
        <td>${t.score ?? '—'}</td>
      </tr>`).join('');
    tb.querySelectorAll('.ic-padrao').forEach((tr) => {
      tr.addEventListener('click', () => {
        padraoSel = tr.getAttribute('data-padrao') || '';
        load();
      });
    });
  }

  function renderBloco(bloco, titulo) {
    if (!bloco) return '<div class="text-muted small">—</div>';
    if (!bloco.sucesso) {
      return `<div class="alert alert-warning small mb-0">${bloco.erro || 'Sem ciclo viável nesta leitura.'}</div>`;
    }
    const passos = (bloco.passos || []).map((p) => `
      <div class="ic-passo">
        <strong>Posição ${p.posicao}</strong>
        → ${pad(p.dezena)}
        ${p.ciclo == null ? ' · número inicial' : ` · ciclo ${pad(p.ciclo)} (${p.origem || ''})`}
      </div>`).join('');
    return `
      <div class="ic-col-title">${titulo}</div>
      <div class="mb-2">${balls(bloco.aposta)}
        <span class="badge ${bloco.viavel ? 'bg-success' : 'bg-danger'} ms-2">${bloco.viavel ? 'Viável' : 'Não cabe'}</span>
        <span class="badge bg-light text-dark border">Ciclos ${padLista(bloco.ciclos) || bloco.padrao || '—'}</span>
      </div>
      <div class="border rounded">${passos || '<div class="p-2 text-muted small">Sem passos.</div>'}</div>`;
  }

  function render(s2) {
    const corpo = $('icCorpo');
    if (!corpo) return;
    const temBlocos = s2 && (s2.classificado || s2.sorteio);
    if (!temBlocos) {
      corpo.innerHTML = `<div class="alert alert-warning small mb-0">${(s2 && s2.erro) || 'Informe um inicial válido.'}</div>`;
      renderPadroes((s2 && s2.padroes_disponiveis) || []);
      return;
    }
    const lbl = $('icLblUltimo');
    if (lbl) lbl.textContent = s2.ultimo_concurso != null ? ('Ciclos medidos até o concurso ' + s2.ultimo_concurso) : '';
    renderPadroes(s2.padroes_disponiveis || []);
    corpo.innerHTML = `
      <div class="row g-3">
        <div class="col-lg-6">${renderBloco(s2.classificado, 'Ciclo · classificado (divulgação Caixa)')}</div>
        <div class="col-lg-6">${renderBloco(s2.sorteio, 'Ciclo · ordem de sorteio (posições do sorteio)')}</div>
      </div>`;
  }

  async function load() {
    try {
      const r = await fetch(API + '?' + qs());
      const j = await r.json();
      render(j);
    } catch (e) {
      const corpo = $('icCorpo');
      if (corpo) corpo.innerHTML = `<div class="alert alert-danger small mb-0">${e.message}</div>`;
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
  ['icInicial', 'icPerfil'].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener('change', () => {
      if (id === 'icPerfil') padraoSel = '';
      load();
    });
  });
  load();
})();
