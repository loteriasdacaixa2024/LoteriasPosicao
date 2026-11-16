(function () {
  'use strict';

  const root = document.getElementById('g2a1');
  if (!root) return;
  const API = (root.dataset.api || '/geradores-elite/api/estatisticas-2a1').replace(/\/$/, '');
  const MANUAL_URL = '/geradores-elite/escolha-tubular-apostas/?aba=manual';
  const VOLANTES_URL = '/geradores-elite/escolha-tubular-apostas/?aba=volantes';
  const MANUAL_KEY = 'tb_manual10_import';
  let ultima = null;

  function acoes(ligadas) {
    ['g2Copiar', 'g2Export', 'g2Manual', 'g2Volantes', 'g2JaSaiu'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.disabled = !ligadas;
    });
  }

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function alerta(tipo, html) {
    document.getElementById('g2Alert').innerHTML = html
      ? `<div class="alert alert-${tipo} py-2 small mb-0">${html}</div>` : '';
  }

  function linhaTxt(ap) {
    const nums = (ap.dezenas || []).map(pad).join(' ');
    const extra = ap.mes_abrev || ap.time_nome || ap.trevos_label || '';
    return extra ? `${nums} ${extra}` : nums;
  }

  function renderLista(payload) {
    const el = document.getElementById('g2Lista');
    const apostas = (payload && payload.apostas) || [];
    if (!apostas.length) {
      el.innerHTML = '<p class="text-muted small mb-0">Nenhuma aposta.</p>';
      return;
    }
    el.innerHTML = apostas.map((ap, i) => `
      <article class="g2-card mb-2">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <strong>#${i + 1}</strong>
          <button type="button" class="g2-fold-btn" data-fold aria-expanded="false" title="Mostrar detalhes">
            <i class="fas fa-chevron-right"></i>
          </button>
        </div>
        <div class="mb-1">${(ap.dezenas || []).map((n) => {
          const pend = (ap.pendentes || []).indexOf(n) >= 0;
          const rep = !pend && (ap.repetidos || []).indexOf(n) >= 0;
          const cls = pend ? 'pend' : (rep ? 'rep' : '');
          const titulo = pend ? ' title="Pendente do ciclo"' : '';
          return `<span class="g2-ball ${cls}"${titulo}>${pad(n)}</span>`;
        }).join('')}
          ${ap.mes_abrev ? `<span class="g2-chip">${ap.mes_abrev}</span>` : ''}
          ${ap.time_nome ? `<span class="g2-chip">${ap.time_nome}</span>` : ''}
          ${ap.trevos_label ? `<span class="g2-chip">${ap.trevos_label}</span>` : ''}
        </div>
        ${ap.ja_sorteada ? `<p class="small mb-1" style="color:#9f1239;">Já saiu · conc. ${ap.concurso_historico || '?'}${ap.data_historico ? ' · ' + ap.data_historico : ''}</p>` : ''}
        <div class="g2-detalhe d-none">
          <p class="small text-muted mb-1">padrão ${ap.padrao || '—'} · sequência ${ap.sequencia_n || '—'} · faixa ${ap.faixa_sequencia || '—'}</p>
          <p class="small text-muted mb-0">${ap.justificativa || ''}</p>
        </div>
      </article>
    `).join('');
  }

  async function gerar() {
    const btn = document.getElementById('g2Gerar');
    const badge = document.getElementById('g2Badge');
    btn.disabled = true;
    badge.textContent = 'Analisando…';
    alerta('', '');
    try {
      const r = await fetch(`${API}/gerar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quantidade: parseInt(document.getElementById('g2Qtd').value, 10) || 10,
          repetidos: document.getElementById('g2Rep').value,
          mes_num: (function () {
            const mesEl = document.getElementById('g2Mes');
            const extraEl = document.getElementById('g2Time') || document.getElementById('g2Trevo');
            if (mesEl) {
              return (window.MesSorteSelect && MesSorteSelect.payloadFromSelect(mesEl)) || mesEl.value || '';
            }
            return (extraEl && extraEl.value) || '';
          })(),
        }),
      });
      const data = await r.json();
      if (!data.sucesso) {
        alerta('warning', data.erro || 'A geração não fechou.');
        badge.textContent = 'Sem aposta';
        ultima = null;
        acoes(false);
        renderPanorama(null);
        return;
      }
      ultima = data;
      renderLista(data);
      renderPanorama(data);
      const avisos = (data.avisos || []).slice(0, 3).join(' ');
      alerta(avisos ? 'info' : '', avisos);
      badge.textContent = `${data.quantidade} aposta(s)`;
      acoes(true);
    } catch (err) {
      alerta('danger', 'Falha ao gerar.');
      badge.textContent = 'Erro';
      acoes(false);
      renderPanorama(null);
    } finally {
      btn.disabled = false;
    }
  }

  document.getElementById('g2Gerar')?.addEventListener('click', gerar);
  document.getElementById('g2Lista')?.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-fold]');
    if (!btn) return;
    const card = btn.closest('.g2-card');
    const det = card && card.querySelector('.g2-detalhe');
    if (!det) return;
    const aberto = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', aberto ? 'false' : 'true');
    btn.title = aberto ? 'Mostrar detalhes' : 'Ocultar detalhes';
    det.classList.toggle('d-none', aberto);
    const icon = btn.querySelector('i');
    if (icon) icon.className = aberto ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
  });
  document.getElementById('g2Copiar')?.addEventListener('click', async () => {
    if (!ultima) return;
    const txt = (ultima.apostas || []).map(linhaTxt).join('\n');
    try {
      await navigator.clipboard.writeText(txt);
      document.getElementById('g2Badge').textContent = 'Copiado';
    } catch (_) {
      alerta('warning', 'Não foi possível copiar.');
    }
  });
  document.getElementById('g2Export')?.addEventListener('click', async () => {
    if (!ultima) return;
    const r = await fetch(`${API}/export-txt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apostas: ultima.apostas || [] }),
    });
    const data = await r.json();
    if (!data.sucesso) return;
    const blob = new Blob([data.txt || ''], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = data.filename || 'apostas_2a1.txt';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  function renderPanorama(data) {
    const box = document.getElementById('painelPanorama2a1');
    if (!box || !window.__renderPanoramaConjunto) return;
    const apostas = (data && data.apostas) || [];
    if (!apostas.length) {
      box.classList.add('d-none');
      return;
    }
    const restr = data.restricoes || {};
    const pagina = document.getElementById('gec-root');
    window.__renderPanoramaConjunto(apostas, {
      key: (pagina && pagina.dataset.modality) || 'diadesorte',
      box: box,
      ultimo: {
        concurso: restr.concurso,
        dezenas: restr.ultimo || [],
      },
    });
  }

  function jogosParaEnvio() {
    return ((ultima && ultima.apostas) || []).map((ap) => ({
      dezenas: ap.dezenas || [],
      mes_num: ap.mes_num || 0,
      mes_nome: ap.mes_nome || '',
    })).filter((j) => (j.dezenas || []).length);
  }

  function enviarTubular(url, abrirVolantes) {
    const jogos = jogosParaEnvio();
    if (!jogos.length) {
      alerta('warning', 'Gere as apostas antes de enviar.');
      return;
    }
    try {
      sessionStorage.setItem(MANUAL_KEY, JSON.stringify({
        origem: 'estatisticas_2a1',
        replace: false,
        jogos,
        abrir_volantes: !!abrirVolantes,
        aviso: `Importado de 2a1 — Estatísticas Básicas (${jogos.length} apostas).`,
      }));
    } catch (err) {
      alerta('danger', 'Não foi possível preparar o envio.');
      return;
    }
    const w = window.open(url, '_blank');
    if (!w) window.location.href = url;
  }

  function jaSaiu() {
    const apostas = (ultima && ultima.apostas) || [];
    if (!apostas.length) {
      alerta('warning', 'Gere as apostas antes de verificar.');
      return;
    }
    const hits = apostas.filter((a) => a.ja_sorteada);
    if (!hits.length) {
      alerta('success', 'Nenhuma destas apostas saiu no histórico oficial (concurso 1 até o atual).');
      return;
    }
    const lista = hits.map((a) => {
      const dez = (a.dezenas || []).map(pad).join(' ');
      return `${dez} · conc. ${a.concurso_historico || '?'}${a.data_historico ? ' · ' + a.data_historico : ''}`;
    }).join('<br>');
    alerta('warning', `<strong>${hits.length} aposta(s) já saiu no histórico oficial</strong><br>${lista}`);
  }

  document.getElementById('g2Manual')?.addEventListener('click', () => enviarTubular(MANUAL_URL, false));
  document.getElementById('g2Volantes')?.addEventListener('click', () => enviarTubular(VOLANTES_URL, true));
  document.getElementById('g2JaSaiu')?.addEventListener('click', jaSaiu);

  function abrir() {
    if (root.dataset.pronto === '1') return;
    root.dataset.pronto = '1';
    const mesEl = document.getElementById('g2Mes');
    if (mesEl && window.MesSorteSelect) {
      MesSorteSelect.fillFromApi(mesEl, '/geradores-elite', { defaultPrefer: 'atrasado' }).catch(() => {});
    }
    if (window.ExtraAnaliseSelect) {
      const timeEl = document.getElementById('g2Time');
      const trevoEl = document.getElementById('g2Trevo');
      if (timeEl) ExtraAnaliseSelect.fillFromApi(timeEl, 'time').catch(() => {});
      if (trevoEl) ExtraAnaliseSelect.fillFromApi(trevoEl, 'trevo').catch(() => {});
    }
  }
  window.g2a1Abrir = abrir;
  if (root.dataset.autoload !== '0') abrir();
})();
