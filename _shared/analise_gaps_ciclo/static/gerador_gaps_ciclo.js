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

  const $ = (id) => document.getElementById(id);

  function pad(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return String(n);
    return padW <= 1 ? String(v) : String(v).padStart(padW, '0');
  }

  function balls(arr) {
    return (arr || []).map((n) => `<span class="gcg-ball">${pad(n)}</span>`).join('') || '—';
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
    const perfilCol = $('gcgPerfilCol');
    if (iniCol) iniCol.style.opacity = s2on() || s1on() ? '1' : '.45';
    if (perfilCol) perfilCol.style.opacity = (s2on() && !s1on()) ? '1' : '.45';
    const wrapL = $('gcgLeituraWrap');
    if (wrapL) wrapL.style.opacity = s1on() ? '1' : '.45';
    const btn = $('gcgBtnGerar');
    if (btn) btn.disabled = !s1on() && !s2on();
    const st = $('gcgStatus');
    if (st && !apostas.length) {
      if (!s1on() && !s2on()) st.textContent = 'Ative ao menos uma sessão para gerar.';
      else if (s1on() && s2on()) st.textContent = 'As duas sessões ligadas: inicial do usuário + padrões de gaps.';
      else if (s1on()) st.textContent = 'Somente Sessão 1: padrões de gaps. Inicial opcional (trava o ponto de partida).';
      else st.textContent = 'Somente Sessão 2: inicial + ciclo do perfil escolhido.';
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
      return;
    }
    out.innerHTML = list.map((a) => `
      <div class="gcg-aposta d-flex flex-wrap align-items-center gap-2">
        <span class="num">${String(a.numero || '').padStart(2, '0')}</span>
        <div>${balls(a.dezenas)}</div>
        <span class="badge bg-light text-dark border font-monospace">${a.padrao_gaps || (a.ciclos || []).join(' ')}</span>
        ${mesBadge(a)}
        <span class="small text-muted">${a.origem || ''}</span>
      </div>`).join('');
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
      inicial: $('gcgInicial') ? Number($('gcgInicial').value) : null,
      perfil: $('gcgPerfil') ? $('gcgPerfil').value : 'ultimo',
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
      renderApostas(apostas);
      const sessoes = j.sessoes || {};
      if (st) {
        st.textContent =
          `${apostas.length} aposta(s) · Sessão 1 ${sessoes.gaps ? 'ON' : 'OFF'} · Sessão 2 ${sessoes.ciclo ? 'ON' : 'OFF'}` +
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
      const mes = a.mes_abrev || a.mes_nome || '';
      return mes ? `${dez} | ${mes}` : dez;
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
