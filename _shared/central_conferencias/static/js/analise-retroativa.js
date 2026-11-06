(function () {
    var ranking = [];
    var conjuntos = [];
    var detalhe = [];
    var melhorDetalhe = 0;
    var selecionada = "";
    var ordem = {
        ranking: { key: "melhor", dir: -1 },
        conjuntos: { key: "melhor", dir: -1 },
        detalhe: { key: "acertos", dir: -1 }
    };
    var textoChave = { dezenas: 1, coincidiram: 1, sorteadas: 1 };

    function el(id) {
        return document.getElementById(id);
    }

    function fmtNums(lista) {
        var posicional = window.__CC_MODALIDADE__ && window.__CC_MODALIDADE__.positional;
        return (lista || []).map(function (n) {
            var v = parseInt(n, 10);
            if (isNaN(v)) return String(n);
            if (posicional) return String(v);
            return v < 10 ? "0" + v : String(v);
        }).join(" ");
    }

    function esc(texto) {
        return String(texto == null ? "" : texto)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function chaveOrigem(origem) {
        var partes = String(origem || "").split("/");
        return (parseInt(partes[0], 10) || 0) * 1000 + (parseInt(partes[1], 10) || 0);
    }

    function valorCampo(item, key) {
        if (key === "origem") return chaveOrigem(item.origem);
        if (key === "dezenas") return fmtNums(item.numeros) + " " + (item.mes || "");
        if (key === "coincidiram" || key === "sorteadas") return (item[key] || []).join(" ");
        if (key === "real") return item.real == null ? null : item.real;
        var valor = item[key];
        return valor == null ? null : valor;
    }

    function ordenar(lista, tabela) {
        var est = ordem[tabela];
        return lista.slice().sort(function (a, b) {
            var va = valorCampo(a, est.key);
            var vb = valorCampo(b, est.key);
            if (va == null && vb == null) return 0;
            if (va == null) return 1;
            if (vb == null) return -1;
            if (va < vb) return -est.dir;
            if (va > vb) return est.dir;
            return (a._ordem || 0) - (b._ordem || 0);
        });
    }

    function marcarSetas(tabela) {
        var est = ordem[tabela];
        document.querySelectorAll("#panel-retroativa [data-ar-table='" + tabela + "']").forEach(function (btn) {
            var th = btn.parentElement;
            var ativo = btn.dataset.arSort === est.key;
            th.classList.toggle("ar-ativo", ativo);
            var seta = btn.querySelector(".ar-seta");
            if (seta) seta.textContent = ativo ? (est.dir < 0 ? "▼" : "▲") : "";
        });
    }

    function ordenarPor(tabela, key) {
        var est = ordem[tabela];
        if (est.key === key) est.dir = -est.dir;
        else {
            est.key = key;
            est.dir = textoChave[key] ? 1 : -1;
        }
        marcarSetas(tabela);
        if (tabela === "ranking") renderRanking();
        else if (tabela === "conjuntos") renderConjuntos();
        else renderDetalheCorpo();
    }

    function renderConjuntos() {
        var html = ordenar(conjuntos, "conjuntos").map(function (g) {
            return "<tr><td class='ar-num ar-origem'>" + esc(g.origem) + "</td><td class='ar-num'>" + g.apostas +
                "</td><td class='ar-num'>" + g.melhor + "</td><td class='ar-num'>" + g.media + "</td></tr>";
        }).join("");
        el("arConjuntos").innerHTML = html || "<tr><td colspan='4'>Nenhum conjunto.</td></tr>";
        el("arConjuntosCard").style.display = "block";
        marcarSetas("conjuntos");
    }

    function linhaRanking(item, pos) {
        var extra = item.mes ? " " + item.mes : "";
        var real = item.real == null ? "—" : item.real;
        var chave = item.origem + "#" + item.numero;
        var sel = chave === selecionada ? " ar-sel" : "";
        return "<tr class='" + sel + "' data-origem='" + esc(item.origem) + "' data-numero='" + esc(item.numero) + "'>" +
            "<td class='ar-mid'>" + pos + "</td>" +
            "<td class='ar-num ar-origem'>" + esc(item.origem) + "</td>" +
            "<td class='ar-num'>" + esc(item.numero) + "</td>" +
            "<td class='ar-dezenas'>" + esc(fmtNums(item.numeros) + extra) + "</td>" +
            "<td class='ar-num'>" + item.melhor + "</td>" +
            "<td class='ar-num'>" + item.no_melhor + "</td>" +
            "<td class='ar-num'>" + item.media + "</td>" +
            "<td class='ar-num'>" + item.concursos + "</td>" +
            "<td class='ar-num'>" + real + "</td></tr>";
    }

    function renderRanking() {
        var filtro = (el("arFiltro").value || "").trim().toLowerCase();
        var lista = ordenar(ranking, "ranking").filter(function (item) {
            if (!filtro) return true;
            var texto = (item.origem + " " + item.numero + " " + fmtNums(item.numeros) + " " + (item.mes || "")).toLowerCase();
            return texto.indexOf(filtro) !== -1;
        });
        var html = lista.map(function (item, i) { return linhaRanking(item, i + 1); });
        el("arRanking").innerHTML = html.join("") || "<tr><td colspan='9'>Nenhuma aposta nesse filtro.</td></tr>";
        el("arRankingCard").style.display = "block";
        marcarSetas("ranking");
    }

    function renderDetalheCorpo() {
        var linhas = ordenar(detalhe, "detalhe");
        el("arDetalhe").innerHTML = linhas.map(function (row) {
            var topo = row.acertos === melhorDetalhe && melhorDetalhe > 0 ? " class='ar-topo'" : "";
            return "<tr" + topo + "><td class='ar-num'>" + row.concurso + "</td><td class='ar-num'>" + row.acertos +
                "</td><td class='ar-dezenas'>" + esc((row.coincidiram || []).join(" ")) + "</td><td class='ar-dezenas'>" +
                esc((row.sorteadas || []).join(" ")) + "</td></tr>";
        }).join("") || "<tr><td colspan='4'>Nenhum concurso anterior.</td></tr>";
        marcarSetas("detalhe");
    }

    function renderDetalhe(dados) {
        var titulo = "Aposta " + dados.numero + " · origem " + dados.origem + " · " + (dados.numeros || []).join(" ");
        if (dados.mes) titulo += " " + dados.mes;
        if (dados.real) titulo += " · resultado real do " + dados.real.concurso + ": " + dados.real.acertos + " acertos";
        el("arDetalheTitulo").textContent = titulo;
        detalhe = (dados.comparacoes || []).map(function (row, i) {
            row._ordem = i;
            return row;
        });
        melhorDetalhe = 0;
        detalhe.forEach(function (row) {
            if (row.acertos > melhorDetalhe) melhorDetalhe = row.acertos;
        });
        ordem.detalhe = { key: "acertos", dir: -1 };
        el("arDetalheCard").style.display = "block";
        renderDetalheCorpo();
        el("arDetalheCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function executar() {
        var btn = el("arBtnExecutar");
        var status = el("arStatus");
        el("arErro").style.display = "none";
        btn.disabled = true;
        status.textContent = "Analisando pastas e concursos anteriores...";
        fetch("/central-conferencias/api/conferencia-apostas/analise-retroativa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}"
        }).then(function (r) { return r.json(); }).then(function (dados) {
            btn.disabled = false;
            if (!dados.sucesso) {
                status.textContent = "";
                el("arErro").style.display = "block";
                el("arErro").textContent = dados.mensagem || "Falha na análise.";
                return;
            }
            ranking = (dados.ranking || []).map(function (item, i) {
                item._ordem = i;
                return item;
            });
            conjuntos = (dados.conjuntos || []).map(function (item, i) {
                item._ordem = i;
                return item;
            });
            ordem.ranking = { key: "melhor", dir: -1 };
            ordem.conjuntos = { key: "melhor", dir: -1 };
            var resumo = dados.resumo || {};
            status.textContent = "Concluída em " + resumo.segundos + "s.";
            el("arResumo").style.display = "block";
            el("arResumo").textContent = resumo.total_apostas + " apostas em " + resumo.arquivos +
                " arquivos, contra " + resumo.sorteios_banco + " sorteios no banco. " +
                (resumo.ignoradas ? resumo.ignoradas + " linhas ignoradas." : "");
            renderConjuntos();
            renderRanking();
        }).catch(function () {
            btn.disabled = false;
            status.textContent = "";
            el("arErro").style.display = "block";
            el("arErro").textContent = "Não foi possível concluir a análise.";
        });
    }

    function abrirDetalhe(origem, numero) {
        selecionada = origem + "#" + numero;
        renderRanking();
        el("arStatus").textContent = "Carregando detalhe...";
        fetch("/central-conferencias/api/conferencia-apostas/analise-retroativa/detalhe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origem: origem, numero: numero })
        }).then(function (r) { return r.json(); }).then(function (dados) {
            el("arStatus").textContent = "";
            if (!dados.sucesso) {
                el("arErro").style.display = "block";
                el("arErro").textContent = dados.mensagem || "Falha no detalhe.";
                return;
            }
            el("arErro").style.display = "none";
            renderDetalhe(dados);
        }).catch(function () {
            el("arStatus").textContent = "";
            el("arErro").style.display = "block";
            el("arErro").textContent = "Não foi possível carregar o detalhe.";
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var btn = el("arBtnExecutar");
        if (!btn) return;
        btn.addEventListener("click", executar);
        el("arFiltro").addEventListener("input", renderRanking);
        el("arRanking").addEventListener("click", function (ev) {
            var tr = ev.target.closest("tr");
            if (!tr || !tr.dataset.origem) return;
            abrirDetalhe(tr.dataset.origem, parseInt(tr.dataset.numero, 10));
        });
        document.getElementById("panel-retroativa").addEventListener("click", function (ev) {
            var botao = ev.target.closest("[data-ar-sort]");
            if (!botao) return;
            ordenarPor(botao.dataset.arTable, botao.dataset.arSort);
        });
        marcarSetas("ranking");
        marcarSetas("conjuntos");
        marcarSetas("detalhe");
    });
})();
