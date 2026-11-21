(function () {
  'use strict';

  const root = document.getElementById('gec-root');
  if (!root) return;

  const API = (root.dataset.api || '/geradores-elite/api/estatisticas-ciclo').replace(/\/$/, '');
  const MODALITY = root.dataset.modality || 'diadesorte';
  const ABA_PAN = (MODALITY === 'diadesorte' || MODALITY === 'supersete') ? 7 : 6;
  const EXTRA_MES = root.dataset.extraMes === '1';
  const EXTRA_TIME = root.dataset.extraTime === '1';
  const EXTRA_TREVO = root.dataset.extraTrevo === '1';
  const MANUAL_URL = root.dataset.manual || '/geradores-elite/escolha-tubular-apostas/?aba=manual';
  const VOLANTES_URL = root.dataset.volantes || '/geradores-elite/escolha-tubular-apostas/?aba=volantes';
  const MANUAL_KEY = 'tb_manual10_import';
  let lastApostas = [];
  let lastPayload = null;
  let ultimoOrdem = 'classificado';
  let lastUltimo = null;
  let modoGeracao = 'panorama';
  let JOGOS_POR_PADRAO = {};

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function comPrefixo(path) {
    const raw = String(path || '');
    const baseEl = document.querySelector('base');
    if (!baseEl || !baseEl.href) return raw;
    const baseUrl = new URL(baseEl.href, window.location.origin);
    const basePath = baseUrl.pathname.replace(/\/$/, '');
    if (!basePath) return raw;
    let url;
    try {
      url = new URL(raw, baseUrl);
    } catch (_) {
      return raw;
    }
    const pathPart = url.pathname || '/';
    const tail = url.search + url.hash;
    if (pathPart === basePath || pathPart.startsWith(basePath + '/')) return pathPart + tail;
    return basePath + (pathPart.startsWith('/') ? pathPart : '/' + pathPart) + tail;
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

  function numsUltimo(ult) {
    const draw = ((ult && (ult.numeros || ult.dezenas)) || []).map(Number).filter(Number.isFinite);
    if (ultimoOrdem === 'sorteio') return draw;
    const sorted = (ult && ult.numeros_ordenados) || [];
    if (sorted.length) return sorted.map(Number).filter(Number.isFinite);
    return [...draw].sort((a, b) => a - b);
  }

  function htmlUltimoBalls(ult) {
    const nums = numsUltimo(ult);
    return nums.length ? nums.map((n) => `<span class="gec-ball comp">${pad(n)}</span>`).join('') : '—';
  }

  const PAINEL = {
    stats: ['gecStats', 'g2Stats'],
    ciclo: ['gecCiclo', 'g2CicloPainel'],
    diags: ['gecDiags', 'g2Diags'],
  };

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escrever(ids, html) {
    (ids || []).forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = html;
    });
  }

  function bindUltimoOrdem() {
    if (root.dataset.ordemLigada === '1') return;
    root.dataset.ordemLigada = '1';
    root.addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-gec-ult-ordem]');
      if (!btn) return;
      ultimoOrdem = btn.getAttribute('data-gec-ult-ordem') || 'classificado';
      root.querySelectorAll('[data-gec-ult-ordem]').forEach((b) => {
        b.classList.toggle('active', b.getAttribute('data-gec-ult-ordem') === ultimoOrdem);
      });
      root.querySelectorAll('.gec-ultimo-nums').forEach((box) => {
        box.innerHTML = htmlUltimoBalls(lastUltimo);
      });
    });
  }

  function renderStats(ctx) {
    const est = (ctx && ctx.estatisticas) || {};
    const m = est.medias || {};
    const pct = est.pct_com || {};
    const ult = est.ultimo || {};
    lastUltimo = ult;
    escrever(PAINEL.stats, `
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="gec-chip">Janela: <strong>${est.total_sorteios || '—'}</strong></span>
        <span class="gec-chip">Pares méd. <strong>${m.pares ?? '—'}</strong></span>
        <span class="gec-chip">Ímpares méd. <strong>${m.impares ?? '—'}</strong></span>
        <span class="gec-chip">Repetidos méd. <strong>${m.repetidos ?? '—'}</strong></span>
        <span class="gec-chip">Seq. méd. <strong>${m.sequencias ?? '—'}</strong></span>
        <span class="gec-chip">Finais méd. <strong>${m.finais ?? '—'}</strong></span>
      </div>
      <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
        <p class="small mb-0 text-muted">Último concurso ${ult.concurso || '—'} ${ult.data ? '· ' + ult.data : ''}</p>
        <div class="btn-group btn-group-sm" role="group" aria-label="Ordem do último concurso">
          <button type="button" class="btn btn-outline-secondary${ultimoOrdem === 'classificado' ? ' active' : ''}"
                  data-gec-ult-ordem="classificado">Classificado</button>
          <button type="button" class="btn btn-outline-secondary${ultimoOrdem === 'sorteio' ? ' active' : ''}"
                  data-gec-ult-ordem="sorteio">Ordem de sorteio</button>
        </div>
      </div>
      <div class="gec-ultimo-nums">${htmlUltimoBalls(ult)}</div>
      <p class="small text-muted mb-0 mt-2">% com o grupo na janela — P ${pct.pares ?? '—'} · I ${pct.impares ?? '—'} · R ${pct.repetidos ?? '—'} · S ${pct.sequencias ?? '—'} · F ${pct.finais ?? '—'}</p>
    `);
    bindUltimoOrdem();
  }

  function numsDiagVista(d) {
    const bruto = d.nums_fmt || (d.nums || []).map(pad).join('-');
    const sobe = d.dir_sym === '↗' || d.dir === 'up';
    return sobe ? String(bruto).split('-').reverse().join('-') : bruto;
  }

  function fmtDiag(d) {
    const sym = d.dir_sym || (d.dir === 'up' ? '↗' : '↘');
    return `${sym} ${numsDiagVista(d)}`;
  }

  function renderDiags(ctx, payload, ids) {
    const info = (payload && payload.diagonais) || (ctx && ctx.diagonais) || {};
    const ultimo = info.ultimo || [];
    const pct = info.janela_pct;
    const com = info.janela_com_diagonal;
    const tot = info.janela_total;
    escrever(ids || PAINEL.diags, `
      <p class="small mb-1">Último concurso ${info.ultimo_concurso || '—'}</p>
      <div class="mb-2">${ultimo.length
        ? ultimo.map((d) => `<span class="gec-chip gec-chip-diag">${fmtDiag(d)}</span>`).join(' ')
        : '<span class="text-muted small">Sem diagonal 2+ neste concurso</span>'}</div>
      <p class="small text-muted mb-0">
        Na janela: <strong>${com ?? '—'}</strong> de ${tot ?? '—'} com diagonal
        ${pct != null ? ` (${pct}%)` : ''}.
      </p>
    `);
  }

  function normPad(p) {
    return String(p || '').replace(/,/g, ' ').trim().split(/\s+/).filter(Boolean).join(' ');
  }

  function fmtVol(n) {
    return Number(n || 0).toLocaleString('pt-BR');
  }

  function jogosDoCard(p) {
    const direto = Number(p && p.jogos_possiveis);
    if (Number.isFinite(direto) && direto > 0) return direto;
    const n = Number(JOGOS_POR_PADRAO[normPad(p && p.padrao)]);
    return Number.isFinite(n) && n > 0 ? n : 0;
  }

  function chipsDiagCruz(list, chipClass) {
    const html = (list || []).map((d) => {
      const title = `${d.tipo || ''} · ${d.vezes || 0}×`;
      return `<span class="${chipClass}" title="${escHtml(title)}">${escHtml(d.dir_sym || '')} ${escHtml(numsDiagVista(d))} <span class="text-muted">${escHtml(d.vezes)}×</span></span>`;
    }).join('');
    return html || '<span class="small text-muted">sem diagonal neste recorte</span>';
  }

  function htmlCardsCruz(lista, prefix) {
    return lista.map((p, i) => {
      const num = i + 1;
      const cada = (p && p.cada_concursos != null && p.cada_concursos !== '') ? p.cada_concursos : null;
      const nDiag = Number(p.n_com_diagonal) || 0;
      const pctBruto = p && p.pct_com_diagonal;
      const pct = pctBruto != null && pctBruto !== '' ? `${escHtml(pctBruto)}%` : '';
      const diagTxt = pct ? `${fmtVol(nDiag)} - ${pct} com diagonais` : `${fmtVol(nDiag)} com diagonais`;
      const ultimo = p.eh_padrao_ultimo_concurso ? ' is-ultimo' : '';
      const tituloUlt = p.eh_padrao_ultimo_concurso ? ' title="Padrão do último resultado"' : '';
      const jogos = jogosDoCard(p);
      const jogosTxt = jogos ? fmtVol(jogos) : '—';
      return `<div class="col-md">
        <div class="${prefix}-cruz-card${ultimo}"${tituloUlt}>
          <div class="cruz-linha">
            <span class="cruz-num" title="${num}º card desta fila">${num}º</span>
            <code>${escHtml(p.padrao || '')}</code>
            <span class="cruz-sep">|</span>
            <span class="cruz-cada" title="Média histórica entre saídas seguidas. Não prevê o próximo concurso.">${cada == null ? '—' : escHtml(cada)}</span>
            <span class="cruz-sep">|</span>
            <span class="cruz-jogos" title="${escHtml(jogosTxt)} apostas possíveis neste padrão">${escHtml(jogosTxt)}</span>
          </div>
          <div class="cruz-diag-resumo">${diagTxt}</div>
          <div>${chipsDiagCruz(p.top_diagonais, prefix === 'g2' ? 'g2-diag-chip' : 'gec-diag-chip')}</div>
        </div>
      </div>`;
    }).join('');
  }

  function dadosCruz(ctx) {
    const info = (ctx && ctx.padroes) || {};
    const cruz = info.cruzamento_diagonais || {};
    return {
      info,
      cruz,
      lista: (cruz.mais_saem || []).slice(0, 5),
      fonte: comPrefixo(info.fonte_aba4 || '/analise/analises-inteligentes/?aba=padroes-ii'),
      meta: cruz.n_concursos
        ? `${cruz.n_com_diagonal} / ${cruz.n_concursos} concursos com diagonal (${cruz.pct_com_diagonal}%)`
        : '',
    };
  }

  function renderCruz2a(ctx) {
    const box = document.getElementById('gecCruz');
    if (!box) return;
    const d = dadosCruz(ctx);
    if (!d.lista.length) {
      box.innerHTML = `<p class="small text-muted mb-0">Cruzamento · diagonais × padrões ainda não carregou. <a href="${d.fonte}">Abrir a aba 4</a>.</p>`;
      return;
    }
    box.innerHTML = `
      <div class="gec-cruz">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <strong class="small mb-0">Cruzamento · diagonais × padrões</strong>
          <span class="small text-muted">${escHtml(d.meta)}</span>
          <span class="small text-muted ms-auto">Somente para constar</span>
        </div>
        <p class="small text-muted mb-2">Os cinco que mais saem na aba 4, na mesma ordem. A geração desta aba não usa este bloco.</p>
        <div class="row g-2">${htmlCardsCruz(d.lista, 'gec')}</div>
      </div>`;
  }

  function renderCinco2a1(ctx) {
    const box = document.getElementById('g2Padroes');
    if (!box) return;
    const d = dadosCruz(ctx);
    if (!d.lista.length) {
      box.innerHTML = `<p class="small text-muted mb-0">A análise ainda não devolveu os cinco padrões do cruzamento. <a href="${d.fonte}">Abrir a aba 4</a>.</p>`;
      return;
    }
    box.innerHTML = `
      <div class="g2-cruz">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <strong class="small mb-0">Cruzamento · diagonais × padrões</strong>
          <span class="small text-muted">${escHtml(d.meta)}</span>
          <a class="small ms-auto" href="${d.fonte}">Mesma lista da aba 4</a>
        </div>
        <p class="small text-muted mb-2">Os cinco que mais saem na análise inteligente, na mesma ordem. Padrão sem ocorrência não entra.</p>
        <div class="row g-2">${htmlCardsCruz(d.lista, 'g2')}</div>
      </div>`;
  }

  function bannerCiclo(info) {
    const modo = (info && info.modo) || '';
    const n = (info && info.pendentes) != null ? info.pendentes : '—';
    const limiar = (info && info.limiar) || 10;
    if (modo === 'fim') {
      return `<div class="gec-ciclo-banner fim">Ciclo no fim (${n} pendentes, até ${limiar}) — o ciclo entra e tenta encaixar as que faltam.</div>`;
    }
    if (modo === 'fechado') {
      return `<div class="gec-ciclo-banner fechado">Ciclo fechado (0 pendentes) — o próximo sorteio reabre. Até lá, só aleatório.</div>`;
    }
    if (modo === 'inicio') {
      return `<div class="gec-ciclo-banner inicio">Ciclo no começo (${n} pendentes) — só aleatório. O ciclo entra no fim.</div>`;
    }
    return '';
  }

  function aplicarModo(modo) {
    modoGeracao = modo === 'ciclo' ? 'ciclo' : 'panorama';
    document.querySelectorAll('[data-gec-modo]').forEach((b) => {
      b.classList.toggle('active', b.getAttribute('data-gec-modo') === modoGeracao);
    });
    const pan = document.getElementById('gecRegraPanorama');
    const cla = document.getElementById('gecRegraCiclo');
    if (pan) pan.classList.toggle('d-none', modoGeracao !== 'panorama');
    if (cla) cla.classList.toggle('d-none', modoGeracao !== 'ciclo');
    const hint = document.getElementById('gecModoHint');
    if (hint) {
      hint.textContent = modoGeracao === 'panorama'
        ? 'padrão · sequência · soma · ciclo só no fim'
        : 'estatísticas da janela · pendentes do ciclo';
    }
  }

  function renderCiclo(ctx) {
    const c = (ctx && ctx.ciclo) || {};
    const pend = c.dezenas_pendentes || [];
    const saidas = c.dezenas_saidas || [];
    const info = (ctx && ctx.ciclo_panorama) || {};
    escrever(PAINEL.ciclo, `
      ${bannerCiclo(info)}
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
    `);
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
      if (window.__renderPanoramaConjunto) window.__renderPanoramaConjunto([], { key: MODALITY });
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
      const seed = ap.semente || {};
      const padChip = ap.padrao_inicial
        ? `<span class="gec-chip${ap.padrao_inedito ? ' gec-chip-inedito' : ''}" title="${ap.padrao_inedito ? 'Padrão que ainda não saiu (aba ' + ABA_PAN + ')' : 'Padrão inicial (aba 4)'}">Padrão ${ap.padrao_inicial}${ap.padrao_descricao ? ' · ' + ap.padrao_descricao : ''}${ap.padrao_inedito ? ' · ainda não saiu' : ''}</span>`
        : '';
      const seqChip = seed.sequencia_n
        ? `<span class="gec-chip gec-chip-seq" title="Nº da sequência sorteada (aba ${ABA_PAN})">Nº ${seed.sequencia_n}${seed.concurso ? ' · conc. ' + seed.concurso : ''}</span>`
        : '';
      const stChip = ap.status_media_label
        ? `<span class="gec-chip">${ap.status_media_label}${ap.soma_media != null ? ' · méd. ' + ap.soma_media : ''}</span>`
        : '';
      return `<div class="gec-card${ap.ja_sorteada ? ' gec-ja-saiu' : ''}${ap.padrao_inedito ? ' gec-inedito' : ''}">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <strong>${String(i + 1).padStart(2, '0')}</strong>
          <span class="d-flex align-items-center gap-1">
            ${EXTRA_MES ? `<span class="mes-badge${mesCls}">${ap.mes_abrev || ap.mes_nome || ''}</span>` : ''}
            ${ap.time_nome ? `<span class="gec-chip">${ap.time_nome}</span>` : ''}
            ${ap.trevos_label ? `<span class="gec-chip">${ap.trevos_label}</span>` : ''}
            <button type="button" class="gec-fold-btn" data-fold aria-expanded="false" title="Mostrar detalhes">
              <i class="fas fa-chevron-right"></i>
            </button>
          </span>
        </div>
        <div class="mb-1">${balls(ap.dezenas, ap.obrigatorias)}</div>
        <div class="gec-detalhe d-none">
          <div class="d-flex flex-wrap gap-1">
            ${padChip}
            ${seqChip}
            ${stChip}
            <span class="gec-chip">${ap.pares}P/${ap.impares}I</span>
            <span class="gec-chip">Σ ${ap.soma}</span>
            <span class="gec-chip">Seq ${seq}</span>
            <span class="gec-chip">Fin ${fin}</span>
            ${diags}
            ${ja}
          </div>
        </div>
      </div>`;
    }).join('');

    let msg = '';
    if (payload.modo_geracao === 'panorama') {
      const nPend = (payload.pendentes || []).length;
      if (payload.ciclo_ligado || payload.modo_ciclo === 'fim') {
        msg = `Ciclo no fim (${nPend} pendentes): o ciclo entra e tenta encaixar as que faltam no padrão.`;
      } else if (payload.modo_ciclo === 'fechado') {
        msg = 'Ciclo fechado — o próximo sorteio reabre. Geração aleatória (padrão · sequência · soma).';
      } else {
        msg = `Ciclo no começo (${nPend} pendentes): só aleatório (padrão · sequência · soma). O ciclo entra no fim.`;
      }
    } else {
      msg = payload.modo_ciclo === 'todas_em_cada'
        ? `As ${payload.pendentes.length} dezenas pendentes entram em <strong>cada</strong> aposta.`
        : `As ${payload.pendentes.length} dezenas pendentes entram no <strong>lote</strong> (todas aparecem pelo menos uma vez).`;
    }
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
    renderDiags(null, payload, ['gecDiags']);
    if (window.__renderPanoramaConjunto) {
      const ult = ((payload.estatisticas || {}).ultimo) || {};
      window.__renderPanoramaConjunto(apostas, {
        key: MODALITY,
        ultimo: { concurso: ult.concurso, dezenas: ult.numeros || ult.dezenas || [] },
      });
    }
  }

  function guardarJogosCatalogo(cat) {
    const mapa = {};
    (cat.padroes || []).forEach((row) => {
      const k = normPad(row && row.padrao);
      const n = Number(row && row.jogos_possiveis);
      if (k && Number.isFinite(n) && n > 0) mapa[k] = n;
    });
    if (Object.keys(mapa).length) JOGOS_POR_PADRAO = mapa;
    return mapa;
  }

  function aplicarJogosNoCruz(cruz, mapa) {
    if (!cruz || !Array.isArray(cruz.mais_saem)) return cruz;
    cruz.mais_saem = cruz.mais_saem.map((p) => {
      if (Number(p && p.jogos_possiveis) > 0) return p;
      const n = mapa[normPad(p && p.padrao)];
      return n ? Object.assign({}, p, { jogos_possiveis: n }) : p;
    });
    return cruz;
  }

  async function completarPadroes(ctx) {
    const info = (ctx && ctx.padroes) || {};
    const temCruz = info.cruzamento_diagonais && (info.cruzamento_diagonais.mais_saem || []).length;
    const faltaJogos = ((info.cruzamento_diagonais || {}).mais_saem || []).some((p) => !(Number(p.jogos_possiveis) > 0));
    if (info.total != null && info.ja_sairam != null && info.faltam_sair != null && temCruz && !faltaJogos) return;
    try {
      const r = await fetch(comPrefixo('/analise/api/inteligentes/catalogo-padroes?base=geral'));
      const cat = await r.json();
      if (!cat || !cat.sucesso) return;
      const mapa = guardarJogosCatalogo(cat);
      const cruz = aplicarJogosNoCruz(cat.cruzamento_diagonais || info.cruzamento_diagonais || null, mapa);
      ctx.padroes = Object.assign({}, info, {
        total: cat.total_padroes,
        ja_sairam: cat.total_padroes_com_frequencia,
        faltam_sair: cat.total_padroes_faltantes,
        cruzamento_diagonais: cruz,
      });
    } catch (_) { /* a tela fica com traço se a análise não responder */ }
  }

  async function carregar() {
    try {
      const r = await fetch(`${API}/contexto`);
      const ctx = await r.json();
      if (!ctx.sucesso) throw new Error(ctx.erro || 'Falha no contexto');
      renderStats(ctx);
      renderCiclo(ctx);
      renderDiags(ctx);
      await completarPadroes(ctx);
      renderCruz2a(ctx);
      renderCinco2a1(ctx);
    } catch (err) {
      escrever(PAINEL.stats, `<div class="alert alert-danger py-2 small mb-0">${err.message}</div>`);
      escrever(PAINEL.ciclo, '');
      escrever(PAINEL.diags, '');
      escrever(['g2Padroes'], `<p class="text-danger small mb-0">${escHtml(err.message)}</p>`);
    }
  }

  async function gerar() {
    const btn = document.getElementById('gecBtnGerar');
    btn.disabled = true;
    document.getElementById('gecBadge').textContent = 'Gerando…';
    try {
      const mesEl = EXTRA_MES ? document.getElementById('gecMes') : null;
      const extraEl = document.getElementById('gecTime') || document.getElementById('gecTrevo');
      const mes = (window.MesSorteSelect && mesEl)
        ? MesSorteSelect.payloadFromSelect(mesEl)
        : ((mesEl && mesEl.value) || (extraEl && extraEl.value) || '');
      const r = await fetch(`${API}/gerar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modo: modoGeracao,
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
      const extra = ap.mes_abrev || ap.time_nome || ap.trevos_label || '';
      return `${dez} ${extra}`.trim();
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

  document.querySelectorAll('[data-gec-modo]').forEach((btn) => {
    btn.addEventListener('click', () => aplicarModo(btn.getAttribute('data-gec-modo')));
  });
  aplicarModo(modoGeracao);
  document.getElementById('gecBtnGerar').addEventListener('click', gerar);
  document.getElementById('gecBtnCopiar').addEventListener('click', copiar);
  document.getElementById('gecBtnExport').addEventListener('click', exportar);
  document.getElementById('gecBtnManual').addEventListener('click', () => enviarTubular(MANUAL_URL, false));
  document.getElementById('gecBtnVolantes').addEventListener('click', () => enviarTubular(VOLANTES_URL, true));
  document.getElementById('gecBtnJaSaiu').addEventListener('click', jaSaiu);
  document.getElementById('gecResultados')?.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-fold]');
    if (!btn) return;
    const card = btn.closest('.gec-card');
    const det = card && card.querySelector('.gec-detalhe');
    if (!det) return;
    const aberto = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', aberto ? 'false' : 'true');
    btn.title = aberto ? 'Mostrar detalhes' : 'Ocultar detalhes';
    det.classList.toggle('d-none', aberto);
    const icon = btn.querySelector('i');
    if (icon) icon.className = aberto ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
  });

  if (EXTRA_MES && window.MesSorteSelect) {
    MesSorteSelect.fillFromApi(document.getElementById('gecMes'), '/geradores-elite', { defaultPrefer: 'atrasado' }).catch(() => {});
  }
  if (window.ExtraAnaliseSelect) {
    if (EXTRA_TIME) {
      ExtraAnaliseSelect.fillFromApi(document.getElementById('gecTime'), 'time').catch(() => {});
    }
    if (EXTRA_TREVO) {
      ExtraAnaliseSelect.fillFromApi(document.getElementById('gecTrevo'), 'trevo').catch(() => {});
    }
  }
  carregar();
})();
