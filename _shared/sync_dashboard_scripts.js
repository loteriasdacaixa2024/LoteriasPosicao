/* Padrão Mega-Sena: incluir no {% block scripts %} de cada modalidade */
async function carregarStatusBanco() {
    const box = document.getElementById('statusBanco');
    const progWrap = document.getElementById('syncProgressWrap');
    const progBar = document.getElementById('syncProgressBar');
    const log = document.getElementById('syncLog');
    if (!box) return null;
    try {
        const r = await fetch('/api/status-banco');
        const raw = await r.text();
        let d;
        try { d = JSON.parse(raw); } catch (_) {
            throw new Error(r.status === 404
                ? 'Rota /api/status-banco não encontrada — reinicie o Flask desta modalidade.'
                : 'Resposta inválida do servidor. Reinicie o Flask e use Ctrl+F5.');
        }
        if (!r.ok || d.status !== 'success') throw new Error(d.message || `HTTP ${r.status}`);
        const api = d.ultimo_concurso_api || '—';
        if (d.completo) {
            box.className = 'alert alert-success py-2 small mb-3';
            box.innerHTML = `<strong>Base completa:</strong> ${d.total_registros.toLocaleString()} concursos (1 a ${api}).`;
            if (progWrap && progBar) { progWrap.classList.remove('d-none'); progBar.style.width = '100%'; }
            if (log) {
                log.innerHTML = `<span class="text-success"><i class="fas fa-cloud-download-alt me-1"></i>Base completa: ${d.total_registros.toLocaleString()} concursos (1 a ${api}).</span>`
                    + `<br><span class="text-success fw-bold">Total importado nesta sessão: 0</span>`;
            }
        } else {
            box.className = 'alert alert-warning py-2 small mb-3';
            const alvo = d.alvo_sincronizacao || api || d.concurso_maximo;
            let txt = `<strong>Atenção:</strong> só <strong>${d.total_registros.toLocaleString()}</strong> concursos gravados, `
                + `mas o intervalo vai até <strong>#${alvo}</strong>. `
                + `Faltam <strong>${d.concursos_faltantes.toLocaleString()}</strong> concursos no meio do histórico.`;
            if (d.api_offline) txt += ` <span class="text-danger">(API Caixa indisponível agora — tente de novo.)</span>`;
            txt += ` Clique em <strong>Sincronizar</strong> abaixo.`;
            box.innerHTML = txt;
            if (progWrap) progWrap.classList.add('d-none');
            if (log) log.innerHTML = '';
        }
        return d;
    } catch (e) {
        box.className = 'alert alert-danger py-2 small mb-3';
        box.textContent = 'Erro ao verificar base: ' + e.message;
        return null;
    }
}

async function sincronizar() {
    const btn = document.getElementById('btnSync'), btn2 = document.getElementById('btnSyncMain'), log = document.getElementById('syncLog');
    const progWrap = document.getElementById('syncProgressWrap'), progBar = document.getElementById('syncProgressBar');
    [btn, btn2].forEach(b => { if (b) { b.disabled = true; b.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sincronizando...'; } });
    progWrap.classList.remove('d-none');
    let continuar = true, totalImportado = 0, faltantesInicial = 0;
    try {
        while (continuar) {
            log.innerHTML = '<i class="fas fa-spinner fa-spin me-2 text-warning"></i>Baixando lote da API Caixa...';
            const r = await fetch('/api/sincronizar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ modo: 'completo', limite: 80 }),
            });
            const d = await r.json();
            if (d.status === 'error') throw new Error(d.message);
            if (!faltantesInicial && d.faltantes_total) faltantesInicial = d.faltantes_total;
            totalImportado += d.news || 0;
            continuar = !!d.continuar;
            const total = faltantesInicial || d.faltantes_total || 1;
            const feito = total - (d.faltantes_restantes || 0);
            progBar.style.width = Math.min(100, Math.round((feito / total) * 100)) + '%';
            log.innerHTML = `<span class="text-success"><i class="fas fa-cloud-download-alt me-1"></i>${d.message}</span>`;
            await carregarStats();
            if (!continuar) break;
            await new Promise(res => setTimeout(res, 400));
        }
        await carregarStatusBanco();
        await carregarUltimos();
        if (totalImportado > 0) log.innerHTML += `<br><span class="text-success fw-bold">Total importado nesta sessão: ${totalImportado}</span>`;
    } catch (e) {
        log.innerHTML = `<span class="text-danger">${e.message}</span>`;
    } finally {
        [btn, btn2].forEach(b => {
            if (b) {
                b.disabled = false;
                b.innerHTML = b.id === 'btnSync'
                    ? '<i class="fas fa-satellite-dish me-1"></i>Sincronizar Dados'
                    : '<i class="fas fa-cloud-download-alt me-2"></i>Sincronizar histórico completo';
            }
        });
    }
}

async function carregarStats() {
    try {
        const st = await fetch('/api/status-banco').then(r => r.json());
        if (st.status === 'success') {
            document.getElementById('statConcursos').textContent = st.total_registros.toLocaleString();
            document.getElementById('statUltimo').textContent = '#' + (st.ultimo_concurso_api || st.concurso_maximo);
        }
    } catch (e) { }
}
