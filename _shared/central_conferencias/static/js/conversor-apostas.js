/**
 * Conversor de Apostas — Mega-Sena (aba Central de Conferências)
 */
(function (global) {
    const API_BASE = '/central-conferencias/api/conversor';
    let dadosAtuais = null;
    let _inicializado = false;

    function showNotification(message, type = 'error') {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: type === 'error' ? 'error' : 'success',
                title: type === 'error' ? 'Erro' : 'Sucesso',
                text: message,
                timer: 3500,
                showConfirmButton: false,
            });
            return;
        }
        alert(message);
    }

    function bindUpload() {
        const uploadZone = document.getElementById('convUploadZone');
        const fileInput = document.getElementById('convFileInput');
        if (!uploadZone || !fileInput) return;

        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('conv-drag-over');
        });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('conv-drag-over'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('conv-drag-over');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                mostrarArquivo(e.dataTransfer.files[0]);
            }
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) mostrarArquivo(e.target.files[0]);
        });
    }

    function mostrarArquivo(file) {
        document.getElementById('convNomeArquivo').textContent = file.name;
        document.getElementById('convArquivoSel').style.display = 'block';
    }

    function aplicarConcursoBanco(ultimoBanco, proximo) {
        const input = document.getElementById('convNumeroConcurso');
        const instrucao = document.getElementById('convInstrucaoConcurso');
        const preview = document.getElementById('convConcursoPreview');
        const ultimoEl = document.getElementById('convUltimoBanco');
        if (!input) return;

        input.value = proximo;
        input.dispatchEvent(new Event('input'));

        if (preview) preview.textContent = proximo;
        if (ultimoEl) ultimoEl.textContent = ultimoBanco;

        if (instrucao) {
            instrucao.innerHTML =
                `<i class="fas fa-check-circle text-success"></i> ` +
                `Último no banco: <strong>#${ultimoBanco}</strong> → ` +
                `próximo sugerido: <strong>#${proximo}</strong> (${ultimoBanco} + 1). Confirme antes de processar.`;
        }
    }

    async function carregarProximoConcurso() {
        const instrucao = document.getElementById('convInstrucaoConcurso');
        try {
            const r = await fetch('/central-conferencias/api/proximo-concurso');
            const data = await r.json();
            if (data.sucesso && data.proximo_concurso) {
                aplicarConcursoBanco(data.ultimo_concurso_banco, data.proximo_concurso);
            } else if (instrucao) {
                instrucao.innerHTML =
                    `<i class="fas fa-exclamation-triangle text-warning"></i> ` +
                    (data.erro || 'Não foi possível ler o último concurso do banco.');
            }
        } catch (e) {
            if (instrucao) {
                instrucao.innerHTML =
                    `<i class="fas fa-exclamation-triangle text-danger"></i> Erro ao consultar o banco: ${e.message}`;
            }
        }
    }

    async function processarArquivo() {
        const fileInput = document.getElementById('convFileInput');
        const file = fileInput?.files[0];
        if (!file) return;

        const concurso = document.getElementById('convNumeroConcurso').value;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('concurso', concurso);

        try {
            const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
            const resultado = await response.json();
            if (resultado.sucesso) {
                dadosAtuais = resultado.dados;
                mostrarResultado(resultado);
            } else {
                showNotification(resultado.erro || 'Falha no processamento', 'error');
            }
        } catch (error) {
            showNotification('Erro ao processar arquivo: ' + error.message, 'error');
        }
    }

    async function converterTextoParaJson() {
        const texto = document.getElementById('convTextoApostas').value.trim();
        if (!texto) {
            showNotification('Cole o texto das apostas', 'error');
            return;
        }
        const concurso = parseInt(document.getElementById('convNumeroConcurso').value, 10) || 1;

        try {
            const response = await fetch(`${API_BASE}/texto-para-json`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto, concurso }),
            });
            const resultado = await response.json();
            if (resultado.sucesso) {
                dadosAtuais = resultado.dados;
                mostrarResultado(resultado);
            } else {
                showNotification(resultado.erro || 'Erro na conversão', 'error');
            }
        } catch (error) {
            showNotification('Erro ao converter: ' + error.message, 'error');
        }
    }

    function mostrarResultado(resultado) {
        const validacao = resultado.validacao;
        const dados = resultado.dados;
        document.getElementById('convAreaResultado').style.display = 'block';

        let infoHTML = '';
        if (validacao.valido) {
            infoHTML = `<div class="conv-badge conv-badge-ok mb-3">
                <i class="fas fa-check-circle"></i> ${validacao.total_apostas} apostas válidas
            </div>`;
        } else {
            infoHTML = `<div class="conv-badge conv-badge-err mb-3">
                <i class="fas fa-exclamation-triangle"></i> ${validacao.erros.length} erro(s)
            </div>
            <ul class="text-danger small">${validacao.erros.map(e => `<li>${e}</li>`).join('')}</ul>`;
        }
        if (validacao.avisos && validacao.avisos.length) {
            infoHTML += `<ul class="text-warning small">${validacao.avisos.map(e => `<li>${e}</li>`).join('')}</ul>`;
        }
        document.getElementById('convInfoValidacao').innerHTML = infoHTML;

        const temMes = dados.apostas.some(a => a.mes);
        let tabelaHTML = `
            <h5 class="fw-bold text-success">Concurso: ${dados.concurso}</h5>
            <table class="table table-sm conv-tabela mt-2">
                <thead><tr><th>#</th><th>Dezenas</th>${temMes ? '<th>Mês</th>' : ''}<th>Qtd</th></tr></thead>
                <tbody>`;
        dados.apostas.forEach(aposta => {
            const nums = aposta.numeros.map(n => String(n).padStart(2, '0')).join(', ');
            tabelaHTML += `<tr>
                <td>${aposta.numero}</td>
                <td class="font-monospace">${nums}</td>
                ${temMes ? `<td>${badgeMes(aposta.mes)}</td>` : ''}
                <td>${aposta.numeros.length}</td>
            </tr>`;
        });
        tabelaHTML += '</tbody></table>';
        document.getElementById('convConteudoResultado').innerHTML = tabelaHTML;
        document.getElementById('convAreaResultado').scrollIntoView({ behavior: 'smooth' });
    }

    function converterParaJson() {
        if (!dadosAtuais) return;
        const pre = document.createElement('pre');
        pre.className = 'conv-pre';
        pre.textContent = formatarJsonPreview(dadosAtuais);
        document.getElementById('convConteudoResultado').innerHTML = '<h5>Formato JSON</h5>';
        document.getElementById('convConteudoResultado').appendChild(pre);
    }

    const MESES_ABREV_PARA_NOME = {
        Jan: 'Janeiro', Fev: 'Fevereiro', Mar: 'Março', Abr: 'Abril',
        Mai: 'Maio', Jun: 'Junho', Jul: 'Julho', Ago: 'Agosto',
        Set: 'Setembro', Out: 'Outubro', Nov: 'Novembro', Dez: 'Dezembro',
    };
    const MESES_NOME_PARA_ABREV = Object.fromEntries(
        Object.entries(MESES_ABREV_PARA_NOME).map(([ab, nome]) => [nome, ab])
    );

    function nomeCompletoMes(mes) {
        if (!mes) return '';
        const raw = String(mes).trim();
        if (MESES_ABREV_PARA_NOME[raw]) return MESES_ABREV_PARA_NOME[raw];
        const cap = raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
        if (MESES_ABREV_PARA_NOME[cap]) return MESES_ABREV_PARA_NOME[cap];
        if (MESES_NOME_PARA_ABREV[raw]) return raw;
        const hit = Object.keys(MESES_NOME_PARA_ABREV).find(
            n => n.toLowerCase() === raw.toLowerCase() || n.toLowerCase().startsWith(raw.toLowerCase())
        );
        return hit || raw;
    }

    function abrevMes(mes) {
        const nome = nomeCompletoMes(mes);
        return MESES_NOME_PARA_ABREV[nome] || String(mes || '').slice(0, 3);
    }

    function badgeMes(mes) {
        if (!mes) return '—';
        const nome = nomeCompletoMes(mes);
        const abrev = abrevMes(mes);
        const cores = window.__MESES_CORES__ || {};
        const cor = cores[nome] || '';
        const style = cor ? ` style="background-color:${cor};color:#fff"` : '';
        return `<span class="mes-badge mes-nome-${nome}"${style} title="${nome}">${abrev}</span>`;
    }

    const MES_TOKEN_RE = /\b(Janeiro|Fevereiro|Março|Marco|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)\b/gi;

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function tokenMes(textoOriginal) {
        const nome = nomeCompletoMes(textoOriginal);
        const cores = window.__MESES_CORES__ || {};
        const cor = cores[nome] || '#6c757d';
        return `<span class="conv-mes-tok mes-nome-${nome}" style="background-color:${cor};color:#fff" title="${nome}">${escapeHtml(textoOriginal)}</span>`;
    }

    function destacarMesesNoTexto(texto) {
        return escapeHtml(texto).replace(MES_TOKEN_RE, (tok) => tokenMes(tok));
    }

    function temCoresMes() {
        return !!(window.__CONV_HAS_MES__ || (window.__MESES_CORES__ && Object.keys(window.__MESES_CORES__).length));
    }

    function destacarExemplo() {
        const el = document.getElementById('convExemploTxt');
        if (!el || !temCoresMes()) return;
        const raw = el.dataset.exemplo || '';
        if (!raw) return;
        const html = escapeHtml(raw).replace(MES_TOKEN_RE, (tok) => badgeMes(tok));
        el.innerHTML = 'Exemplo: ' + html;
    }

    function syncTextoHighlight() {
        const ta = document.getElementById('convTextoApostas');
        const hl = document.getElementById('convTextoHighlight');
        if (!ta || !hl || !temCoresMes()) return;
        const text = ta.value;
        if (!text) {
            hl.innerHTML = `<span class="text-muted">${escapeHtml(ta.placeholder || '')}</span>`;
        } else {
            hl.innerHTML = destacarMesesNoTexto(text) + (text.endsWith('\n') ? '\n' : '');
        }
        hl.scrollTop = ta.scrollTop;
        hl.scrollLeft = ta.scrollLeft;
        hl.style.height = ta.offsetHeight + 'px';
    }

    function bindTextoHighlight() {
        const ta = document.getElementById('convTextoApostas');
        const hl = document.getElementById('convTextoHighlight');
        const wrap = document.getElementById('convTextoWrap');
        if (!ta || !hl || !wrap || !temCoresMes()) return;
        wrap.classList.add('conv-texto-wrap--hl');
        hl.hidden = false;
        ta.addEventListener('input', syncTextoHighlight);
        ta.addEventListener('scroll', syncTextoHighlight);
        if (window.ResizeObserver) {
            new ResizeObserver(syncTextoHighlight).observe(ta);
        }
        syncTextoHighlight();
    }

    function formatarJsonPreview(dados) {
        let s = '{\n';
        s += `  "concurso": ${dados.concurso},\n`;
        s += '  "apostas": [\n';
        dados.apostas.forEach((a, i) => {
            const nums = a.numeros.join(', ');
            const virg = i < dados.apostas.length - 1 ? ',' : '';
            const mes = a.mes ? `, "mes": "${a.mes}"` : '';
            s += `    {"numero": ${a.numero}, "numeros": [${nums}]${mes}}${virg}\n`;
        });
        s += '  ]\n}';
        return s;
    }

    async function converterParaTexto() {
        if (!dadosAtuais) return;
        try {
            const response = await fetch(`${API_BASE}/json-para-texto`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dadosAtuais),
            });
            const resultado = await response.json();
            if (resultado.sucesso) {
                document.getElementById('convConteudoResultado').innerHTML =
                    `<h5>Formato TXT</h5><pre class="conv-pre">${resultado.texto}</pre>`;
            }
        } catch (error) {
            showNotification('Erro: ' + error.message, 'error');
        }
    }

    async function downloadJSON() {
        if (!dadosAtuais) return;
        try {
            const response = await fetch(`${API_BASE}/download/json`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dadosAtuais),
            });
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'apostas.json';
            a.click();
        } catch (error) {
            showNotification('Erro ao baixar: ' + error.message, 'error');
        }
    }

    async function downloadTXT() {
        if (!dadosAtuais) return;
        try {
            const response = await fetch(`${API_BASE}/download/txt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dadosAtuais),
            });
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'apostas.txt';
            a.click();
        } catch (error) {
            showNotification('Erro ao baixar: ' + error.message, 'error');
        }
    }

    function limparTexto() {
        document.getElementById('convTextoApostas').value = '';
        document.getElementById('convAreaResultado').style.display = 'none';
        dadosAtuais = null;
        syncTextoHighlight();
    }

    function init() {
        if (_inicializado) return;
        _inicializado = true;

        bindUpload();
        destacarExemplo();
        bindTextoHighlight();

        const inputConcurso = document.getElementById('convNumeroConcurso');
        if (inputConcurso) {
            inputConcurso.addEventListener('input', function () {
                const prev = document.getElementById('convConcursoPreview');
                if (prev) prev.textContent = this.value || '---';
            });
            carregarProximoConcurso();
        }

        global.convProcessarArquivo = processarArquivo;
        global.convConverterTexto = converterTextoParaJson;
        global.convLimparTexto = limparTexto;
        global.convVerJson = converterParaJson;
        global.convVerTxt = converterParaTexto;
        global.convDownloadJson = downloadJSON;
        global.convDownloadTxt = downloadTXT;
        global.convRecarregarConcurso = carregarProximoConcurso;
    }

    global.ConversorApostas = { init, recarregarConcurso: () => carregarProximoConcurso() };
})(window);
