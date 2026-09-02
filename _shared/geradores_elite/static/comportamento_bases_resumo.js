/**
 * Painel de resumo Geral / Vencedores / Acumulados (Dia de Sorte e modalidades compatíveis).
 */
(function (global) {
    'use strict';

    function fmtNum(n) {
        if (n == null || n === '') return '—';
        return Number(n).toLocaleString('pt-BR');
    }

    function fmtPct(n) {
        if (n == null || n === '') return '—';
        const v = Number(n);
        if (Number.isNaN(v)) return '—';
        return v % 1 === 0 ? String(v) : v.toFixed(1).replace('.', ',');
    }

    function render(meta, baseAtiva) {
        const painel = document.getElementById('painelBasesResumo');
        if (!painel || !meta || !meta.suporta_bases) {
            if (painel) painel.classList.add('d-none');
            return;
        }
        painel.classList.remove('d-none');
        painel.classList.toggle('bases-incompletas', (meta.pendentes_ganhadores || 0) > 0);

        const pctV = meta.pct_vencedores;
        const pctA = meta.pct_acumulados;
        const completo = meta.bases_completas && pctV != null && pctA != null;

        const headline = document.getElementById('basesResumoHeadline');
        if (headline && completo) {
            headline.innerHTML =
                `Em <strong>${fmtPct(pctA)}%</strong> dos sorteios <strong>não houve ganhador</strong> (acumulou); ` +
                `em <strong>${fmtPct(pctV)}%</strong> houve <strong>pelo menos 1 vencedor</strong>.`;
        }

        const barAcum = document.getElementById('basesBarAcum');
        const barVenc = document.getElementById('basesBarVenc');
        if (barAcum && barVenc && pctA != null && pctV != null) {
            barAcum.style.flex = `${pctA} 1 0`;
            barVenc.style.flex = `${pctV} 1 0`;
            barAcum.textContent = `${fmtPct(pctA)}%`;
            barVenc.textContent = `${fmtPct(pctV)}%`;
        }

        const setText = (id, txt) => {
            const el = document.getElementById(id);
            if (el) el.textContent = txt;
        };
        setText('basesLegAcum', fmtNum(meta.total_acumulados));
        setText('basesLegVenc', fmtNum(meta.total_vencedores));
        setText('basesNumGeral', fmtNum(meta.total_geral));
        setText('basesNumVenc', fmtNum(meta.total_vencedores));
        setText('basesNumAcum', fmtNum(meta.total_acumulados));

        const pctVencEl = document.getElementById('basesPctVenc');
        const pctAcumEl = document.getElementById('basesPctAcum');
        if (pctVencEl) {
            pctVencEl.textContent = pctV != null ? `${fmtPct(pctV)}% do histórico` : '—';
        }
        if (pctAcumEl) {
            pctAcumEl.textContent = pctA != null ? `${fmtPct(pctA)}% do histórico` : '—';
        }

        document.querySelectorAll('.bases-stat[data-base-stat]').forEach(el => {
            el.classList.toggle('ativo', el.getAttribute('data-base-stat') === (baseAtiva || 'geral'));
        });

        const avisoEl = document.getElementById('basesResumoAviso');
        if (avisoEl) {
            const pend = meta.pendentes_ganhadores || 0;
            if (pend > 0) {
                avisoEl.textContent =
                    `${fmtNum(pend)} concurso(s) ainda sem classificação de ganhadores — ` +
                    'execute o backfill para bases Vencedores/Acumulados completas.';
                avisoEl.classList.remove('d-none');
            } else {
                avisoEl.classList.add('d-none');
                avisoEl.textContent = '';
            }
        }

        atualizarBadgesAbas(meta);
    }

    function atualizarBadgesAbas(meta) {
        if (!meta || !meta.suporta_bases) return;
        const map = {
            geral: meta.total_geral,
            vencedores: meta.total_vencedores,
            acumulados: meta.total_acumulados,
        };
        document.querySelectorAll('.base-tab-btn[data-base]').forEach(btn => {
            const base = btn.getAttribute('data-base');
            if (!base || base === 'panorama') return;
            let badge = btn.querySelector('.base-tab-count');
            const n = map[base];
            if (n == null) return;
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'base-tab-count';
                btn.appendChild(badge);
            }
            badge.textContent = `(${fmtNum(n)})`;
        });
    }

    function initFromUi() {
        const ui = global.__COMPORTAMENTO_UI__ || {};
        if (ui.meta_bases) {
            render(ui.meta_bases, 'geral');
        }
    }

    global.ComportamentoBasesResumo = {
        render,
        initFromUi,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFromUi);
    } else {
        initFromUi();
    }
})(typeof window !== 'undefined' ? window : this);
