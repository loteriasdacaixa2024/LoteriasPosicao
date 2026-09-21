(function () {
  'use strict';

  const root = document.getElementById('gcg-root');
  if (!root) return;

  const API = window.__GCG_API__ || root.dataset.api;
  const SPEC = window.__GCG_SPEC__ || {};
  const HAS_MES = window.__GCG_HAS_MES__ === true || root.dataset.hasMes === '1';
  const padW = Number(SPEC.pad_width) > 0 ? Number(SPEC.pad_width) : 2;
  const MESES_ABREV = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'};
  const MESES_NOME = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'};

  let base = 'geral';
  let janela = SPEC.janela_default != null ? Number(SPEC.janela_default) : 0;
  let apostas = [];
  let lastMes = null;
  let leitura = 'ambos';
  let exibicao = 'hibrido';
  let fontesAtivas = [];
  const LEGENDA = {
    numeros: 'Só a lista de dezenas.',
    volante: 'Só a grade do volante.',
    hibrido: 'Lista em bolinhas e grade do volante juntas.',
  };

  const $ = (id) => document.getElementById(id);

  function pad(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return String(n);
    return padW <= 1 ? String(v) : String(v).padStart(padW, '0');
  }

  function balls(arr) {
    return (arr || []).map((n) => `<span class="gcg-ball">${pad(n)}</span>`).join('') || '—';
  }

  function htmlVolante(dezenas) {
    const marcadas = new Set((dezenas || []).map(Number));
    const dmin = Number(SPEC.dezena_min);
    const dmax = Number(SPEC.dezena_max);
    let cells = '';
    for (let d = dmin; d <= dmax; d += 1) {
      cells += `<div class="volante-cell${marcadas.has(d) ? ' na-aposta' : ''}">${pad(d)}</div>`;
    }
    return `<div class="volante-oficial-wrap"><div class="volante-oficial-grid">${cells}</div></div>`;
  }

  function fillInicial() {
    const sel = $('gcgInicial');
    if (!sel) return;
    const permitidas = SPEC.iniciais_permitidas || [];
    sel.innerHTML = permitidas.map((n) =>
      `<option value="${n}">${pad(n)}</option>`
    ).join('');
    sel.value = String(SPEC.inicial_min);
  }

  function s1on() { return !!($('gcgS1') && $('gcgS1').checked); }
  function s2on() { return !!($('gcgS2') && $('gcgS2').checked); }

  function syncSessoes() {
    const w1 = $('gcgWrapS1');
    const w2 = $('gcgWrapS2');
    if (w1) w1.classList.toggle('off', !s1on());
    if (w2) w2.classList.toggle('off', !s2on());
    const iniCol = $('gcgIniCol');
    if (iniCol) iniCol.style.opacity = s1on() ? '1' : '.45';
    const wrapL = $('gcgLeituraWrap');
    if (wrapL) wrapL.style.opacity = s1on() ? '1' : '.45';
    const btn = $('gcgBtnGerar');
    if (btn) btn.disabled = !s1on() && !s2on();
    const st = $('gcgStatus');
    if (st && !apostas.length) {
      if (!s1on() && !s2on()) st.textContent = 'Ative ao menos uma sessão para gerar.';
      else if (s1on() && s2on()) st.textContent = 'As duas sessões ligadas: padrões de gaps e a régua da janela.';
      else if (s1on()) st.textContent = 'Somente Sessão 1: padrões de gaps. Inicial opcional (trava o ponto de partida).';
      else st.textContent = 'Somente Sessão 2: aposta na referência de cada posição.';
    }
  }

  function mesPayload() {
    const el = $('gcgMes');
    if (!HAS_MES || !el || !el.value) return null;
    return el.value;
  }

  function mesBadge(ap) {
    const nome = ap.mes_nome || MESES_NOME[ap.mes_num] || '';
    const abrev = ap.mes_abrev || MESES_ABREV[ap.mes_num] || '';
    if (!nome && !abrev) return '';
    return `<span class="mes-badge mes-nome-${nome}">${abrev || nome}</span>`;
  }

  function renderApostas(list) {
    const out = $('gcgOut');
    if (!out) return;
    if (!list || !list.length) {
      out.innerHTML = '';
      if (window.__renderPanoramaConjunto) {
        window.__renderPanoramaConjunto([], { key: SPEC.modality_key || SPEC.key });
      }
      return;
    }
    const showNumeros = exibicao === 'numeros' || exibicao === 'hibrido';
    const showVolante = exibicao === 'volante' || exibicao === 'hibrido';
    out.innerHTML = list.map((a) => `
      <div class="gcg-aposta">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
          <span class="num">${String(a.numero || '').padStart(2, '0')}</span>
          <span class="badge bg-light text-dark border font-monospace">${a.origem === 'regua' ? 'Régua' : 'Gaps'} ${a.padrao_gaps || (a.ciclos || []).join(' ')}</span>
          ${mesBadge(a)}
        </div>
        <div class="${exibicao === 'hibrido' ? 'modo-hibrido' : ''}">
          ${showNumeros ? `<div>${balls(a.dezenas)}${window.__htmlDiagLinha ? window.__htmlDiagLinha(a.dezenas, { dezena_min: SPEC.dezena_min, dezena_max: SPEC.dezena_max }) : ''}</div>` : ''}
          ${showVolante ? htmlVolante(a.dezenas) : ''}
        </div>
      </div>`).join('');
    if (window.__renderPanoramaConjunto) {
      window.__renderPanoramaConjunto(list, {
        key: SPEC.modality_key || SPEC.key,
        pad: padW,
        fontes: fontesAtivas,
      });
    }
  }

  async function gerar() {
    const st = $('gcgStatus');
    const btn = $('gcgBtnGerar');
    const exp = $('gcgBtnExport');
    if (st) st.textContent = 'Gerando…';
    if (btn) btn.disabled = true;
    const body = {
      sessao1: s1on(),
      sessao2: s2on(),
      inicial: s1on() && $('gcgInicial') ? Number($('gcgInicial').value) : null,
      janela: janela,
      base: base,
      quantidade: Number(($('gcgQtd') && $('gcgQtd').value) || SPEC.qtd_apostas_default || 10),
      mes_num: mesPayload(),
      leitura: leitura,
    };
    if (!body.sessao2 && !s2on()) {
      /* S1-only: inicial continua opcional; envia o selecionado para travar o ponto de partida */
    }
    lastMes = body.mes_num;
    try {
      const r = await fetch(API + '/gerar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!j.ok && !j.sucesso) {
        apostas = [];
        renderApostas([]);
        if (st) st.textContent = j.erro || 'Não foi possível gerar.';
        if (exp) exp.disabled = true;
        return;
      }
      apostas = j.apostas || [];
      const sessoes = j.sessoes || {};
      fontesAtivas = []
        .concat(sessoes.gaps ? ['gaps'] : [])
        .concat(sessoes.regua ? ['regua'] : []);
      renderApostas(apostas);
      if (st) {
        st.textContent =
          `${apostas.length} aposta(s) · Sessão 1 ${sessoes.gaps ? 'ON' : 'OFF'} · Sessão 2 ${sessoes.regua ? 'ON' : 'OFF'}` +
          (j.leitura ? ` · ${j.leitura}` : '') +
          (j.inicial != null ? ` · inicial ${pad(j.inicial)}` : '');
      }
      if (exp) exp.disabled = !apostas.length;
    } catch (e) {
      if (st) st.textContent = e.message;
    } finally {
      syncSessoes();
    }
  }

  function exportTxt() {
    if (!apostas.length) return;
    if (HAS_MES && (lastMes == null || lastMes === '')) {
      alert('Selecione o Mês da Sorte para exportar o TXT.');
      return;
    }
    const linhas = apostas.map((a) => {
      const dez = (a.dezenas || []).map(pad).join(' ');
      const mn = a.mes_num != null ? Number(a.mes_num) : (lastMes != null ? Number(lastMes) : null);
      const mes = a.mes_abrev || MESES_ABREV[mn] || a.mes_nome || '';
      return mes ? `${dez} ${mes}` : dez;
    });
    const blob = new Blob([linhas.join('\n') + '\n'], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'gaps_ciclo_apostas.txt';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  fillInicial();
  syncSessoes();

  ['gcgS1', 'gcgS2'].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener('change', syncSessoes);
  });
  root.querySelectorAll('.base-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.base-tab-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      base = btn.getAttribute('data-base') || 'geral';
    });
  });
  root.querySelectorAll('.janela-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.janela-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      janela = Number(btn.getAttribute('data-janela') || 0);
    });
  });
  root.querySelectorAll('.gcg-exib').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.gcg-exib').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      exibicao = btn.getAttribute('data-exib') || 'hibrido';
      const leg = $('gcgExibLegenda');
      if (leg) leg.textContent = LEGENDA[exibicao] || '';
      if (apostas.length) renderApostas(apostas);
    });
  });
  root.querySelectorAll('.leitura-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      root.querySelectorAll('.leitura-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      leitura = btn.getAttribute('data-leitura') || 'ambos';
    });
  });
  const btnG = $('gcgBtnGerar');
  if (btnG) btnG.addEventListener('click', gerar);
  const btnE = $('gcgBtnExport');
  if (btnE) btnE.addEventListener('click', exportTxt);

  if (HAS_MES && window.MesSorteSelect) {
    const sel = $('gcgMes');
    const apply = (data) => MesSorteSelect.fill(sel, data, { defaultPrefer: 'atrasado' });
    if (MesSorteSelect.cached) apply(MesSorteSelect.cached);
    else MesSorteSelect.load(API).then(apply).catch(() => {});
  }
})();
