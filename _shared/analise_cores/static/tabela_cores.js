(function () {
    "use strict";

    var root = document.getElementById("tc-root");
    if (!root) return;
    var API = window.__TC_API__ || root.getAttribute("data-api");
    var dados = null;
    var modelo = "crescente";
    var ORDEM = {
        principal: { key: "concurso", dir: "asc" },
        intervalos: { key: "ordem", dir: "asc" },
        meses: { key: "ordem", dir: "asc" },
        aposta: { key: "ordem", dir: "asc" }
    };

    function $(id) { return document.getElementById(id); }

    function esc(v) {
        return String(v == null ? "" : v)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function num(v) {
        if (v == null || v === "") return "—";
        var n = Number(v);
        if (!isFinite(n)) return "—";
        return n.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 1 });
    }

    function tinta(hex, alpha) {
        var h = String(hex || "#ccc").replace("#", "");
        var r = parseInt(h.slice(0, 2), 16);
        var g = parseInt(h.slice(2, 4), 16);
        var b = parseInt(h.slice(4, 6), 16);
        return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
    }

    function bola(b, extra) {
        var cls = "tc-bola" + (extra ? " " + extra : "");
        return '<span class="' + cls + '" style="background:' + esc(b.hex) + ";color:" + esc(b.texto) +
            '" title="' + esc(b.nome || b.cor_nome || "") + '">' + esc(b.rotulo || b.abrev || b.n) + "</span>";
    }

    function thOrd(tabela, chave, rotulo) {
        var st = ORDEM[tabela] || { key: "", dir: "asc" };
        var ativo = st.key === chave;
        var cls = ativo ? (st.dir === "asc" ? " ai-sort-asc" : " ai-sort-desc") : "";
        var ind = ativo ? (st.dir === "asc" ? "▲" : "▼") : "⇅";
        return '<th class="ai-sort' + cls + '" data-sort="' + esc(chave) + '" data-table="' + esc(tabela) +
            '" title="Clique para ordenar">' + esc(rotulo) + ' <span class="ai-sort-ind">' + ind + "</span></th>";
    }

    function ordenar(lista, tabela, valor) {
        var st = ORDEM[tabela];
        if (!st || !st.key) return lista.slice();
        var mult = st.dir === "asc" ? 1 : -1;
        return lista.slice().sort(function (a, b) {
            var va = valor(a, st.key);
            var vb = valor(b, st.key);
            if (va == null) va = "";
            if (vb == null) vb = "";
            if (typeof va === "number" && typeof vb === "number") return (va - vb) * mult;
            return String(va).localeCompare(String(vb), "pt-BR", { numeric: true }) * mult;
        });
    }

    function preencherConcursos(lista, de, ate) {
        var a = $("tcDe");
        var b = $("tcAte");
        var html = lista.map(function (c) {
            return '<option value="' + c + '">' + c + "</option>";
        }).join("");
        a.innerHTML = html;
        b.innerHTML = html;
        if (de != null) a.value = String(de);
        if (ate != null) b.value = String(ate);
    }

    function marcarJanela(n) {
        Array.prototype.forEach.call(document.querySelectorAll("#tcJanelas button"), function (btn) {
            btn.classList.toggle("btn-primary", String(btn.getAttribute("data-n")) === String(n));
            btn.classList.toggle("btn-outline-secondary", String(btn.getAttribute("data-n")) !== String(n));
        });
    }

    function carregar(de, ate) {
        var url = API;
        if (de != null && ate != null) url += "?de=" + encodeURIComponent(de) + "&ate=" + encodeURIComponent(ate);
        $("tcTabela").innerHTML = '<p class="text-muted small">Carregando…</p>';
        return fetch(url).then(function (r) { return r.json(); }).then(function (d) {
            if (!d || !d.sucesso) throw new Error((d && d.erro) || "Não foi possível ler os concursos.");
            dados = d;
            preencherConcursos(d.concursos || [], d.de, d.ate);
            $("tcFaixa").textContent = d.vazio ? "Sem concursos" : (d.total + " concursos · " + d.de + " a " + d.ate);
            $("tcNota").textContent = d.nota || $("tcNota").textContent;
            desenhar();
        }).catch(function (err) {
            $("tcTabela").innerHTML = '<p class="text-danger small">' + esc(err.message || err) + "</p>";
        });
    }

    function desenhar() {
        if (!dados) return;
        desenharTabela();
        desenharGrupos();
        desenharIntervalos();
        desenharMeses();
        var saida = $("tcApostaSaida");
        if (saida && saida.dataset.pronta === "1") conferirAposta();
    }

    function desenharTabela() {
        if (dados.vazio) {
            $("tcTabela").innerHTML = '<p class="text-muted small">Nenhum concurso nesse intervalo.</p>';
            return;
        }
        var detalhe = modelo === "detalhado";
        var linhas = ordenar(dados.linhas, "principal", function (linha, chave) {
            if (chave === "concurso") return linha.concurso;
            if (chave === "dezenas") return (linha.crescente || []).map(function (b) { return b.rotulo; }).join(" ");
            if (chave === "mes") return linha.mes ? linha.mes.n : -1;
            if (chave.indexOf("q") === 0) return linha.quantidades[Number(chave.slice(1))] || 0;
            if (chave === "repetiu_cores") return linha.repetiu_cores == null ? -1 : linha.repetiu_cores;
            if (chave === "repetiu_bolas") return linha.repetiu_bolas == null ? -1 : linha.repetiu_bolas;
            return "";
        });
        var html = '<table class="tc-tab"><thead><tr>';
        html += thOrd("principal", "concurso", "Concurso");
        html += thOrd("principal", "dezenas", "Dezenas sorteadas");
        if (dados.tem_mes !== false) html += thOrd("principal", "mes", "Mês");
        dados.cores.forEach(function (cor, i) { html += thOrd("principal", "q" + i, cor.nome); });
        if (detalhe) {
            html += thOrd("principal", "repetiu_cores", "Cores repetidas");
            html += thOrd("principal", "repetiu_bolas", "Bolas na cor anterior");
        }
        html += "</tr></thead><tbody>";
        linhas.forEach(function (linha) {
            var bolas = modelo === "crescente" ? linha.crescente : linha.ordem;
            html += "<tr>";
            html += '<td class="tc-zebra">' + linha.concurso + (linha.etiqueta ? " · " + esc(linha.etiqueta) : "") + "</td>";
            html += '<td class="tc-zebra" style="text-align:left;white-space:nowrap">' + bolas.map(bola).join("") + "</td>";
            if (dados.tem_mes !== false) {
                html += '<td class="tc-zebra">' + (linha.mes ? bola(linha.mes, "tc-mes") : "—") + "</td>";
            }
            linha.quantidades.forEach(function (q, i) {
                var cor = dados.cores[i];
                var fundo = q ? tinta(cor.hex, 0.34) : "transparent";
                html += '<td class="tc-qtd" style="background:' + fundo + '">' + q + "</td>";
            });
            if (detalhe) {
                html += "<td>" + (linha.repetiu_cores == null ? "—" : linha.repetiu_cores) + "</td>";
                html += "<td>" + (linha.repetiu_bolas == null ? "—" : linha.repetiu_bolas) + "</td>";
            }
            html += "</tr>";
        });
        html += '</tbody><tfoot>';
        html += '<tr><td colspan="3">Médias por cor</td>';
        dados.medias.forEach(function (m) { html += "<td>" + num(m) + "</td>"; });
        if (detalhe) html += "<td colspan=\"2\"></td>";
        html += "</tr><tr><td colspan=\"3\">Total por cor</td>";
        dados.totais.forEach(function (t) { html += "<td>" + t + "</td>"; });
        if (detalhe) html += "<td colspan=\"2\"></td>";
        html += "</tr></tfoot></table>";
        $("tcTabela").innerHTML = html;
    }

    function desenharGrupos() {
        var box = $("tcGrupos");
        if (!dados.grupos || !dados.grupos.length) { box.innerHTML = ""; return; }
        box.innerHTML = dados.grupos.map(function (g, gi) {
            var tabela = "g" + gi;
            if (!ORDEM[tabela]) ORDEM[tabela] = { key: "quantidade", dir: "asc" };
            var dist = ordenar(g.distribuicao, tabela, function (d, chave) { return d[chave]; });
            var linhas = dist.map(function (d) {
                return "<tr><td style=\"color:" + esc(g.hex) + ";font-weight:800\">" + d.quantidade + " " + esc(g.nome) +
                    "</td><td>" + d.vezes + "x</td><td><div class=\"tc-bar\"><span style=\"width:" + d.pct +
                    "%;background:" + esc(g.hex) + "\"></span></div></td><td>" + num(d.pct) + "%</td></tr>";
            }).join("");
            return '<article class="tc-card"><h3>Cor ' + esc(g.nome) + " " + g.bolas.map(bola).join("") +
                '</h3><table class="tc-tab tc-mini"><thead><tr>' +
                thOrd(tabela, "quantidade", "Quantidade") + thOrd(tabela, "vezes", "Vezes") +
                thOrd(tabela, "pct", "Percentual") + "<th></th></tr></thead><tbody>" +
                linhas + "</tbody></table></article>";
        }).join("");
    }

    function desenharIntervalos() {
        var rep = dados.repeticao || {};
        $("tcRepKpi").innerHTML = [
            ["Comparações", rep.comparacoes],
            ["Média de cores repetidas", num(rep.media_cores)],
            ["Média de bolas na cor anterior", num(rep.media_bolas)]
        ].map(function (par) {
            return '<div class="col-6 col-md-4"><div class="tc-kpi"><div class="lbl">' + par[0] +
                '</div><div class="val">' + par[1] + "</div></div></div>";
        }).join("");
        if (!dados.intervalos || !dados.intervalos.length) {
            $("tcIntervalos").innerHTML = "";
            return;
        }
        var linhas = ordenar(dados.intervalos.map(function (c, i) {
            return Object.assign({ ordem: i }, c);
        }), "intervalos", function (c, chave) {
            if (chave === "bolas") return (c.bolas || []).join(" ");
            if (chave === "pct") return c.pct;
            var v = c[chave];
            return v == null ? (chave === "ordem" ? 0 : -1) : v;
        });
        var html = '<table class="tc-tab"><thead><tr>' +
            thOrd("intervalos", "ordem", "Cor") + thOrd("intervalos", "bolas", "Dezenas") +
            thOrd("intervalos", "presencas", "Presenças") + thOrd("intervalos", "pct", "%") +
            thOrd("intervalos", "intervalo_medio", "Intervalo médio") +
            thOrd("intervalos", "maior_intervalo", "Maior intervalo") +
            thOrd("intervalos", "atraso", "Atraso na janela") + "</tr></thead><tbody>";
        linhas.forEach(function (c) {
            html += "<tr><td class=\"tc-qtd\" style=\"background:" + tinta(c.hex, 0.34) + "\">" + esc(c.nome) +
                "</td><td>" + esc((c.bolas || []).join(" ")) + "</td><td>" + c.presencas + "</td><td>" +
                num(c.pct) + "%</td><td>" + num(c.intervalo_medio) + "</td><td>" + num(c.maior_intervalo) +
                "</td><td>" + c.atraso + "</td></tr>";
        });
        html += "</tbody></table>";
        html += '<p class="small text-muted mt-2 mb-0">Intervalo 1 significa que a cor saiu em concursos seguidos. Atraso 0 significa que ela saiu no último concurso da janela.</p>';
        $("tcIntervalos").innerHTML = html;
    }

    function desenharMeses() {
        var secao = $("tc-mes");
        var link = document.querySelector('#tc-root a[href="#tc-mes"]');
        if (dados.tem_mes === false) {
            if (secao) secao.hidden = true;
            if (link) link.hidden = true;
            $("tcMeses").innerHTML = "";
            return;
        }
        if (secao) secao.hidden = false;
        if (link) link.hidden = false;
        if (!dados.meses || !dados.meses.length) { $("tcMeses").innerHTML = ""; return; }
        var linhas = ordenar(dados.meses.map(function (c, i) {
            return Object.assign({ ordem: i }, c);
        }), "meses", function (c, chave) {
            return chave === "pct" || chave === "vezes" || chave === "ordem" ? c[chave] : c.nome;
        });
        var html = '<table class="tc-tab"><thead><tr>' +
            thOrd("meses", "ordem", "Cor do mês") + thOrd("meses", "vezes", "Vezes") +
            thOrd("meses", "pct", "Percentual") + "<th></th></tr></thead><tbody>";
        linhas.forEach(function (c) {
            html += "<tr><td class=\"tc-qtd\" style=\"background:" + tinta(c.hex, 0.34) + "\">" + esc(c.nome) +
                "</td><td>" + c.vezes + "</td><td><div class=\"tc-bar\"><span style=\"width:" + c.pct +
                "%;background:" + esc(c.hex) + "\"></span></div></td><td>" + num(c.pct) + "%</td></tr>";
        });
        html += "</tbody></table>";
        $("tcMeses").innerHTML = html;
    }

    function conferirAposta() {
        var bruto = ($("tcAposta").value || "").trim();
        var partes = bruto.split(/[^0-9]+/).filter(Boolean).map(function (x) { return parseInt(x, 10); });
        var saida = $("tcApostaSaida");
        var unicos = {};
        var ok = partes.length === 7 && partes.every(function (n) {
            if (n < 1 || n > 31 || unicos[n]) return false;
            unicos[n] = true;
            return true;
        });
        if (!ok) {
            saida.dataset.pronta = "";
            saida.innerHTML = '<p class="text-danger small mb-0">Informe 7 dezenas diferentes, de 01 a 31.</p>';
            return;
        }
        if (!dados || !dados.cores) return;
        var qtd = dados.cores.map(function () { return 0; });
        var bolas = partes.slice().sort(function (a, b) { return a - b; }).map(function (n) {
            var final = n % 10;
            var cor = dados.cores.filter(function (c) { return c.final === final; })[0];
            var i = dados.cores.indexOf(cor);
            qtd[i] += 1;
            return { rotulo: (n < 10 ? "0" : "") + n, hex: cor.hex, texto: cor.texto, nome: cor.nome };
        });
        var linhasCor = ordenar(dados.cores.map(function (cor, i) {
            return { ordem: i, nome: cor.nome, qtd: qtd[i], media: dados.medias[i] };
        }), "aposta", function (c, chave) {
            if (chave === "qtd") return c.qtd;
            if (chave === "media") return c.media;
            if (chave === "ordem") return c.ordem;
            return c.nome;
        });
        var html = '<div class="tc-card"><div class="mb-2">' + bolas.map(bola).join("") + "</div>";
        html += '<table class="tc-tab tc-mini"><thead><tr>' +
            thOrd("aposta", "ordem", "Cor") + thOrd("aposta", "qtd", "Nesta aposta") +
            thOrd("aposta", "media", "Média da janela") + "</tr></thead><tbody>";
        linhasCor.forEach(function (cor) {
            html += "<tr><td>" + esc(cor.nome) + "</td><td class=\"tc-qtd\">" + cor.qtd + "</td><td>" + num(cor.media) + "</td></tr>";
        });
        html += "</tbody></table></div>";
        saida.dataset.pronta = "1";
        saida.innerHTML = html;
    }

    $("tcOk").addEventListener("click", function () {
        marcarJanela("");
        carregar($("tcDe").value, $("tcAte").value);
    });
    $("tcModelo").addEventListener("change", function () {
        modelo = $("tcModelo").value;
        desenharTabela();
    });
    $("tcJanelas").addEventListener("click", function (ev) {
        var btn = ev.target.closest("button");
        if (!btn || !dados || !dados.concursos || !dados.concursos.length) return;
        var n = parseInt(btn.getAttribute("data-n"), 10);
        var lista = dados.concursos;
        var de = n > 0 ? lista[Math.max(0, lista.length - n)] : lista[0];
        var ate = lista[lista.length - 1];
        marcarJanela(n);
        carregar(de, ate);
    });
    $("tcConferir").addEventListener("click", conferirAposta);
    $("tcAposta").addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") conferirAposta();
    });

    root.addEventListener("click", function (ev) {
        var celula = ev.target.closest("th.ai-sort");
        if (!celula) return;
        var tabela = celula.getAttribute("data-table");
        var chave = celula.getAttribute("data-sort");
        if (!tabela || !chave) return;
        if (!ORDEM[tabela]) ORDEM[tabela] = { key: chave, dir: "asc" };
        if (ORDEM[tabela].key === chave) ORDEM[tabela].dir = ORDEM[tabela].dir === "asc" ? "desc" : "asc";
        else {
            ORDEM[tabela].key = chave;
            ORDEM[tabela].dir = "desc";
        }
        desenhar();
    });

    marcarJanela(10);
    carregar(null, null);
})();
