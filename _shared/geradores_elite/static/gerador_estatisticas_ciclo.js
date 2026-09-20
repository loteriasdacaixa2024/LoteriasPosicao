(function () {
  'use strict';

  const root = document.getElementById('gec-root');
  if (!root) return;

  const API = (root.dataset.api || '/geradores-elite/api/estatisticas-ciclo').replace(/\/$/, '');
  const MANUAL_URL = root.dataset.manual || '/geradores-elite/escolha-tubular-apostas/?aba=manual';
  const VOLANTES_URL = root.dataset.volantes || '/geradores-elite/escolha-tubular-apostas/?aba=volantes';
  const MANUAL_KEY = 'tb_manual10_import';
  let lastApostas = [];
  let lastPayload = null;

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function balls(nums, obr) {
    const set = new Set(obr || []);
    return (nums || []).map((n) => {
      const cls = set.has(n) ? 'pend' : 'comp';
      return `<span class="gec-ball ${cls}" title="${set.has(n) ? 'Pendente do ciclo' : 'Complemento'}">${pad(n)}</span>`;
    }).join('');
  }

  function alertBox(tipo, html) {
    const el = document.getElementById('gecAlert');
    el.innerHTML = `<div class="alert alert-${tipo} py-2 small mb-0">${html}</div>`;
  }

  function renderStats(ctx) {
    const est = (ctx && ctx.estatisticas) || {};
    const m = est.medias || {};
    const pct = est.pct_com || {};
    const ult = est.ultimo || {};
    const nums = ult.numeros || [];
    document.getElementById('gecStats').innerHTML = `
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="gec-chip">Janela: <strong>${est.total_sorteios || '—'}</strong></span>
        <span class="gec-chip">Pares méd. <strong>${m.pares ?? '—'}</strong></span>
        <span class="gec-chip">Ímpares méd. <strong>${m.impares ?? '—'}</strong></span>
        <span class="gec-chip">Repetidos méd. <strong>${m.repetidos ?? '—'}</strong></span>
        <span class="gec-chip">Seq. méd. <strong>${m.sequencias ?? '—'}</strong></span>
        <span class="gec-chip">Finais méd. <strong>${m.finais ?? '—'}</strong></span>
      </div>
      <p class="small mb-1 text-muted">Último concurso ${ult.concurso || '—'} ${ult.data ? '· ' + ult.data : ''}</p>
      <div>${nums.length ? nums.map((n) => `<span class="gec-ball comp">${pad(n)}</span>`).join('') : '—'}</div>
      <p class="small text-muted mb-0 mt-2">% com o grupo na janela — P ${pct.pares ?? '—'} · I ${pct.impares ?? '—'} · R ${pct.repetidos ?? '—'} · S ${pct.sequencias ?? '—'} · F ${pct.finais ?? '—'}</p>
    `;
  }

  function fmtDiag(d) {
    const sym = d.dir_sym || (d.dir === 'up' ? '↗' : '↘');
    return `${sym} ${d.nums_fmt || (d.nums || []).map(pad).join('-')}`;
  }

  function renderDiags(ctx, payload) {
    const el = document.getElementById('gecDiags');
    if (!el) return;
    const info = (payload && payload.diagonais) || (ctx && ctx.diagonais) || {};
    const ultimo = info.ultimo || [];
    const pct = info.janela_pct;
    const com = info.janela_com_diagonal;
    const tot = info.janela_total;
    el.innerHTML = `
      <p class="small mb-1">Último concurso ${info.ultimo_concurso || '—'}</p>
      <div class="mb-2">${ultimo.length
        ? ultimo.map((d) => `<span class="gec-chip gec-chip-diag">${fmtDiag(d)}</span>`).join(' ')
        : '<span class="text-muted small">Sem diagonal 2+ neste concurso</span>'}</div>
      <p class="small text-muted mb-0">
        Na janela: <strong>${com ?? '—'}</strong> de ${tot ?? '—'} com diagonal
        ${pct != null ? ` (${pct}%)` : ''}.
      </p>
    `;
  }

  function renderPadroes(ctx, payload) {
    const el = document.getElementById('gecPadroes');
    if (!el) return;
    const info = (payload && payload.padroes) || (ctx && ctx.padroes) || {};
    const aba4 = info.fonte_aba4 || '/analise/analises-inteligentes/?aba=padroes-ii';
    const aba7 = info.fonte_aba7 || '/analise/analises-inteligentes/?aba=panorama';
    const falt = info.faltantes || [];
    const inedito = info.inedito || (payload && payload.padrao_inedito);
    const distintos = info.distintos;
    el.innerHTML = `
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="gec-chip">85 padrões: <strong>${info.total ?? '—'}</strong></span>
        <span class="gec-chip">Já saíram <strong>${info.ja_sairam ?? '—'}</strong></span>
        <span class="gec-chip gec-chip-inedito">Faltam sair <strong>${info.faltam_sair ?? '—'}</strong></span>
        ${distintos != null ? `<span class="gec-chip">Nesta geração: <strong>${distintos}</strong> distintos</span>` : ''}
      </div>
      <p class="small mb-1">
        <a href="${aba4}">Aba 4 · Padrões II</a>
        ·
        <a href="${aba7}">Aba 7 · Panorama Histórico</a>
      </p>
      ${inedito ? `<p class="small mb-1"><span class="gec-chip gec-chip-inedito">Padrão inédito nesta geração: <strong>${inedito}</strong></span></p>` : ''}
      ${falt.length ? `<p class="small text-muted mb-0">Ainda não saíram (aba 7): ${falt.slice(0, 8).map((p) => p.padrao || p).join(' · ')}${falt.length > 8 ? ' …' : ''}</p>` : ''}
    `;
  }

  function renderCiclo(ctx) {
    const c = (ctx && ctx.ciclo) || {};
    const pend = c.dezenas_pendentes || [];
    const saidas = c.dezenas_saidas || [];
    document.getElementById('gecCiclo').innerHTML = `
      <p class="small mb-2">
        Ciclo <strong>${c.numero_ciclo ?? '—'}</strong>
        · concursos ${c.quantidade_concursos ?? '—'}
        · ${c.percentual_completo ?? 0}% coberto
      </p>
      <div class="progress mb-2" style="height:.45rem">
        <div class="progress-bar" style="width:${c.percentual_completo || 0}%;background:var(--primary)"></div>
      </div>
      <p class="small mb-1"><strong>${pend.length}</strong> pendentes</p>
      <div class="mb-2">${pend.length ? pend.map((n) => `<span class="gec-ball pend">${pad(n)}</span>`).join('') : '<span class="text-muted">Nenhuma</span>'}</div>
      <p class="small mb-1 text-muted">${saidas.length} já saíram no ciclo</p>
      <div>${saidas.slice(0, 16).map((n) => `<span class="gec-ball saida">${pad(n)}</span>`).join('')}${saidas.length > 16 ? ' <span class="small text-muted">…</span>' : ''}</div>
    `;
  }

  function renderApostas(payload) {
    const box = document.getElementById('gecResultados');
    const apostas = payload.apostas || [];
    lastApostas = apostas;
    lastPayload = payload;
    const btnC = document.getElementById('gecBtnCopiar');
    const btnE = document.getElementById('gecBtnExport');
    const btnM = document.getElementById('gecBtnManual');
    const btnV = document.getElementById('gecBtnVolantes');
    const btnJ = document.getElementById('gecBtnJaSaiu');
    const badge = document.getElementById('gecBadge');
    const setBtns = (on) => {
      [btnC, btnE, btnM, btnV, btnJ].forEach((b) => { if (b) b.disabled = !on; });
    };
    if (!apostas.length) {
      box.innerHTML = '<p class="text-muted small mb-0" style="grid-column:1/-1;">Nenhuma aposta gerada.</p>';
      setBtns(false);
      badge.textContent = 'Sem jogos';
      return;
    }
    setBtns(true);
    badge.textContent = `${apostas.length} apostas`;
    box.innerHTML = apostas.map((ap, i) => {
      const mesCls = ap.mes_nome ? ` mes-nome-${ap.mes_nome}` : '';
      const seq = (ap.sequencias || []).map((g) => (g || []).map(pad).join('-')).join(' · ') || '—';
      const fin = (ap.finais || []).map((g) => (g || []).map(pad).join(',')).join(' · ') || '—';
      const diags = (ap.diagonais || []).map((d) => `<span class="gec-chip gec-chip-diag">${fmtDiag(d)}</span>`).join('')
        || '<span class="gec-chip">Sem diagonal</span>';
      const ja = ap.ja_sorteada
        ? `<span class="gec-chip gec-chip-warn">Já saiu · conc. ${ap.concurso_historico || '?'}${ap.data_historico ? ' · ' + ap.data_historico : ''}</span>`
        : '';
      const padChip = ap.padrao_inicial
        ? `<span class="gec-chip${ap.padrao_inedito ? ' gec-chip-inedito' : ''}" title="${ap.padrao_inedito ? 'Padrão que ainda não saiu (aba 7)' : 'Padrão inicial (aba 4)'}">Padrão ${ap.padrao_inicial}${ap.padrao_descricao ? ' · ' + ap.padrao_descricao : ''}${ap.padrao_inedito ? ' · ainda não saiu' : ''}</span>`
        : '';
      return `<div class="gec-card${ap.ja_sorteada ? ' gec-ja-saiu' : ''}${ap.padrao_inedito ? ' gec-inedito' : ''}">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <strong>${String(i + 1).padStart(2, '0')}</strong>
          <span class="mes-badge${mesCls}">${ap.mes_abrev || ap.mes_nome || ''}</span>
        </div>
        <div class="mb-1">${balls(ap.dezenas, ap.obrigatorias)}</div>
        <div class="d-flex flex-wrap gap-1">
          ${padChip}
          <span class="gec-chip">${ap.pares}P/${ap.impares}I</span>
          <span class="gec-chip">Σ ${ap.soma}</span>
          <span class="gec-chip">Seq ${seq}</span>
          <span class="gec-chip">Fin ${fin}</span>
          ${diags}
          ${ja}
        </div>
      </div>`;
    }).join('');

    let msg = payload.modo_ciclo === 'todas_em_cada'
      ? `As ${payload.pendentes.length} dezenas pendentes entram em <strong>cada</strong> aposta.`
      : `As ${payload.pendentes.length} dezenas pendentes entram no <strong>lote</strong> (todas aparecem pelo menos uma vez).`;
    if (payload.quantidade_ajustada) {
      msg += ` Quantidade ajustada de ${payload.quantidade_solicitada} para ${payload.quantidade} para caber todas as pendentes.`;
    }
    if (payload.padroes_distintos) {
      msg += ` ${payload.padroes_distintos} padrões iniciais distintos.`;
    }
    if (payload.padrao_inedito) {
      msg += ` Padrão que ainda não saiu (aba 7): <strong>${payload.padrao_inedito}</strong>.`;
    }
    const nDup = apostas.length - new Set(apostas.map((a) => (a.dezenas || []).join(','))).size;
    if (nDup > 0) {
      msg += ' Há volantes repetidos — gere novamente.';
    }
    const nJa = apostas.filter((a) => a.ja_sorteada).length
      || (payload.historico && payload.historico.ja_sorteadas_count)
      || 0;
    if (payload.pendentes_faltando && payload.pendentes_faltando.length) {
      alertBox('warning', 'Alguma pendente não coube no lote. Gere novamente.');
    } else if (nJa) {
      alertBox('warning', `${msg} <strong>${nJa} aposta(s) já saiu no histórico oficial</strong> — conferida concurso a concurso.`);
    } else {
      alertBox('success', `${msg} Nenhuma destas apostas saiu no histórico oficial.`);
    }
    renderDiags(null, payload);
    renderPadroes(null, payload);
  }

  async function carregar() {
    try {
      const r = await fetch(`${API}/contexto`);
      const ctx = await r.json();
      if (!ctx.sucesso) throw new Error(ctx.erro || 'Falha no contexto');
      renderStats(ctx);
      renderCiclo(ctx);
      renderDiags(ctx);
      renderPadroes(ctx);
    } catch (err) {
      document.getElementById('gecStats').innerHTML = `<div class="alert alert-danger py-2 small mb-0">${err.message}</div>`;
      document.getElementById('gecCiclo').innerHTML = '';
      const d = document.getElementById('gecDiags');
      if (d) d.innerHTML = '';
    }
  }

  async function gerar() {
    const btn = document.getElementById('gecBtnGerar');
    btn.disabled = true;
    document.getElementById('gecBadge').textContent = 'Gerando…';
    try {
      const mesEl = document.getElementById('gecMes');
      const mes = (window.MesSorteSelect && mesEl)
        ? MesSorteSelect.payloadFromSelect(mesEl)
        : (mesEl && mesEl.value);
      const r = await fetch(`${API}/gerar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quantidade: parseInt(document.getElementById('gecQtd').value, 10) || 10,
          mes_num: mes,
        }),
      });
      const data = await r.json();
      if (!data.sucesso) throw new Error(data.erro || 'Falha ao gerar');
      renderApostas(data);
    } catch (err) {
      alertBox('danger', err.message);
      document.getElementById('gecBadge').textContent = 'Erro';
    } finally {
      btn.disabled = false;
    }
  }

  function textoApostas() {
    return lastApostas.map((ap) => {
      const dez = (ap.dezenas || []).map(pad).join(' ');
      return `${dez} ${ap.mes_abrev || ''}`.trim();
    }).join('\n');
  }

  async function copiar() {
    const txt = textoApostas();
    if (!txt) return;
    try {
      await navigator.clipboard.writeText(txt);
      alertBox('success', 'Apostas copiadas.');
    } catch (_) {
      alertBox('warning', 'Não foi possível copiar automaticamente. Use Exportar TXT.');
    }
  }

  async function exportar() {
    if (!lastApostas.length) return;
    try {
      const r = await fetch(`${API}/export-txt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apostas: lastApostas }),
      });
      const data = await r.json();
      const txt = data.txt || textoApostas();
      const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = data.filename || 'apostas_estatisticas_ciclo.txt';
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      alertBox('danger', err.message);
    }
  }

  function jogosParaEnvio() {
    return lastApostas.map((ap) => ({
      dezenas: ap.dezenas || [],
      mes_num: ap.mes_num || 0,
      mes_nome: ap.mes_nome || '',
    })).filter((j) => (j.dezenas || []).length);
  }

  function enviarTubular(url, abrirVolantes) {
    const jogos = jogosParaEnvio();
    if (!jogos.length) {
      alertBox('warning', 'Gere as apostas antes de enviar.');
      return;
    }
    try {
      sessionStorage.setItem(MANUAL_KEY, JSON.stringify({
        origem: 'estatisticas_ciclo',
        replace: false,
        jogos,
        abrir_volantes: !!abrirVolantes,
        aviso: `Importado de Estatísticas e Ciclo (${jogos.length} apostas).`,
      }));
    } catch (err) {
      alertBox('danger', 'Não foi possível preparar o envio: ' + (err.message || err));
      return;
    }
    const w = window.open(url, '_blank');
    if (!w) window.location.href = url;
  }

  function jaSaiu() {
    if (!lastApostas.length) {
      alertBox('warning', 'Gere as apostas antes de verificar.');
      return;
    }
    const hits = lastApostas.filter((a) => a.ja_sorteada);
    if (!hits.length) {
      alertBox('success', 'Nenhuma destas apostas saiu no histórico oficial (concurso 1 até o atual).');
      return;
    }
    const lista = hits.map((a) => {
      const dez = (a.dezenas || []).map(pad).join(' ');
      return `${dez} · conc. ${a.concurso_historico || '?'}${a.data_historico ? ' · ' + a.data_historico : ''}`;
    }).join('<br>');
    alertBox('warning', `<strong>${hits.length} aposta(s) já saiu no histórico oficial</strong><br>${lista}`);
  }

  document.getElementById('gecBtnGerar').addEventListener('click', gerar);
  document.getElementById('gecBtnCopiar').addEventListener('click', copiar);
  document.getElementById('gecBtnExport').addEventListener('click', exportar);
  document.getElementById('gecBtnManual').addEventListener('click', () => enviarTubular(MANUAL_URL, false));
  document.getElementById('gecBtnVolantes').addEventListener('click', () => enviarTubular(VOLANTES_URL, true));
  document.getElementById('gecBtnJaSaiu').addEventListener('click', jaSaiu);

  if (window.MesSorteSelect) {
    MesSorteSelect.fillFromApi(document.getElementById('gecMes'), '/geradores-elite', { defaultPrefer: 'atrasado' }).catch(() => {});
  }
  carregar();
})();
