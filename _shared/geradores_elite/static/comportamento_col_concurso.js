/**
 * Coluna Concurso padronizada: #NNNN + badge do mês alinhados entre abas.
 */
(function (global) {
    'use strict';

    function htmlConcursoCol(row, opts) {
        opts = opts || {};
        const showMes = opts.showMes !== false;
        const num = row && row.concurso != null ? `#${row.concurso}` : '—';
        let mesHtml = '<span class="comp-concurso-mes-ph"></span>';
        if (showMes && row && typeof opts.badgeMes === 'function') {
            const badge = opts.badgeMes(row);
            if (badge) mesHtml = badge;
        }
        return (
            `<div class="comp-concurso-wrap">` +
            `<span class="comp-concurso-num">${num}</span>` +
            `<span class="comp-concurso-mes">${mesHtml}</span>` +
            `</div>`
        );
    }

    global.ComportamentoColConcurso = { html: htmlConcursoCol };
})(typeof window !== 'undefined' ? window : this);
