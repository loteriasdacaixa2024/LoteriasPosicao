(function () {
    var bootEl = document.getElementById("sg-boot");
    if (!bootEl) return;
    var BOOT = JSON.parse(bootEl.textContent);
    var S = {
        modalidade: BOOT.modalidade,
        nome: BOOT.nome,
        simId: null,
        status: "ocioso",
        velocidade: 5000,
        timer: null,
        ocupado: false,
        geracao: 0,
        replay: 0,
        previstas: 0,
        globo: null,
        charts: [],
        grupos: {},
    };

    function $(id) { return document.getElementById(id); }
    function esperar(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

    function fmtPct(n) {
        return Number(n).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
    }

    function post(caminho, corpo) {
        return fetch("/simulador-globo" + caminho, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(corpo || {}),
        }).then(function (r) {
            return r.json().then(function (data) {
                if (!r.ok) throw new Error((data && data.erro) || "Falha na simulação.");
                return data;
            });
        });
    }

    function mostrarErro(msg) {
        var el = $("sg-erro");
        if (!msg) { el.hidden = true; el.textContent = ""; return; }
        el.hidden = false;
        el.textContent = msg;
    }

    function statusTexto() {
        var mapa = {
            ocioso: "Pronto para preparar as bolas.",
            preparada: "Bolas no globo. Pode iniciar o sorteio.",
            em_andamento: "Sorteio em andamento.",
            pausada: "Sorteio pausado.",
            completa: "Sorteio encerrado.",
            interrompida: "Sorteio finalizado antes do fim.",
            revendo: "Revisão do resultado gravado.",
        };
        $("sg-status").textContent = mapa[S.status] || S.status;
    }

    function atualizarBotoes() {
        var st = S.status;
        $("sg-preparar").disabled = S.ocupado;
        $("sg-iniciar").disabled = S.ocupado || st !== "preparada";
        $("sg-pausar").disabled = st !== "em_andamento";
        $("sg-continuar").disabled = st !== "pausada";
        $("sg-reiniciar").disabled = S.ocupado || st === "ocioso";
        $("sg-finalizar").disabled = S.ocupado || !(st === "em_andamento" || st === "pausada" || st === "preparada");
    }

    function contagens(sorteadas, restantes, faltam) {
        $("sg-sorteadas").textContent = String(sorteadas || 0);
        $("sg-restantes").textContent = String(restantes == null ? 0 : restantes);
        $("sg-faltam").textContent = String(faltam == null ? 0 : faltam);
    }

    function limparResultado() {
        S.grupos = {};
        $("sg-resultado").innerHTML = "";
        $("sg-final").hidden = true;
        $("sg-final").innerHTML = "";
        var hero = $("sg-hero");
        hero.style.background = "#f3f3f3";
        hero.style.color = "#666";
        $("sg-hero-bola").textContent = "—";
        $("sg-hero-bola").style.background = "transparent";
        $("sg-hero-bola").style.color = "#666";
        $("sg-hero-cor").textContent = "Aguardando o sorteio";
    }

    function chip(bola, grande) {
        var el = document.createElement(grande ? "span" : "span");
        el.className = grande ? "sg-mini" : "sg-chip";
        el.style.background = bola.hex;
        el.style.color = bola.texto;
        el.style.boxShadow = "inset 0 -4px 8px rgba(0,0,0,.18)";
        if (grande) {
            el.textContent = bola.rotulo;
            return el;
        }
        el.innerHTML = "<span>" + bola.rotulo + "</span>";
        return el;
    }

    function adicionarResultado(bola) {
        var id = bola.fase_id || "dezenas";
        if (!S.grupos[id]) {
            var box = document.createElement("div");
            box.className = "sg-grupo";
            var h = document.createElement("h4");
            h.textContent = bola.fase_titulo || "Sorteio";
            var chips = document.createElement("div");
            chips.className = "sg-chips";
            box.appendChild(h);
            box.appendChild(chips);
            $("sg-resultado").appendChild(box);
            S.grupos[id] = chips;
        }
        var item = document.createElement("span");
        item.className = "sg-chip";
        item.style.background = bola.hex;
        item.style.color = bola.texto;
        item.title = (bola.ordem || "") + "ª · " + (bola.cor_nome || "");
        item.textContent = bola.rotulo;
        S.grupos[id].appendChild(item);
        var hero = $("sg-hero");
        hero.style.background = bola.hex;
        hero.style.color = bola.texto;
        var hb = $("sg-hero-bola");
        hb.textContent = bola.rotulo;
        hb.style.background = "rgba(255,255,255,.18)";
        hb.style.color = bola.texto;
        var extra = bola.coluna ? " · coluna " + bola.coluna : "";
        $("sg-hero-cor").textContent = (bola.ordem || "") + "ª · " + (bola.cor_nome || "") + extra;
        $("sg-live").textContent = "Saiu " + bola.rotulo + ", cor " + (bola.cor_nome || "") + ", ordem " + (bola.ordem || "");
    }

    function mostrarFinal(data) {
        var box = $("sg-final");
        var seq = (data && data.sequencia) || [];
        var titulo = data && data.status === "completa" ? "Resultado completo" : "Resultado parcial";
        box.hidden = false;
        box.innerHTML = "<strong>" + titulo + "</strong>";
        seq.forEach(function (b) { box.appendChild(chip(b, true)); });
    }

    function destruirGraficos() {
        S.charts.forEach(function (c) { try { c.destroy(); } catch (e) {} });
        S.charts = [];
    }

    function desenharGraficos(painel) {
        destruirGraficos();
        if (!window.Chart) return;
        var labels = painel.cores.map(function (c) { return c.nome; });
        var valores = painel.cores.map(function (c) { return c.quantidade; });
        var cores = painel.cores.map(function (c) { return c.hex; });
        var comum = {
            responsive: true,
            plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } },
        };
        S.charts.push(new Chart($("sg-chart-rosca"), {
            type: "doughnut",
            data: { labels: labels, datasets: [{ data: valores, backgroundColor: cores, borderColor: "#fff", borderWidth: 1 }] },
            options: comum,
        }));
        S.charts.push(new Chart($("sg-chart-barras"), {
            type: "bar",
            data: { labels: labels, datasets: [{ label: "Dezenas", data: valores, backgroundColor: cores, borderRadius: 6 }] },
            options: Object.assign({}, comum, {
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
            }),
        }));
    }

    function renderPainel(p) {
        $("sg-painel-nome").textContent = p.nome;
        $("sg-painel-universo").textContent = p.universo + " bolas · universo " + p.universo_label;
        $("sg-painel-resumo").textContent = "Sorteio previsto: " + p.resumo + ".";
        $("sg-painel-nota").textContent = p.nota || "";
        $("sg-cores").innerHTML = (p.cores || []).map(function (c) {
            return '<article class="sg-cor">' +
                '<header><span class="sg-bolinha" style="background:' + c.hex + ';color:' + c.texto + '">' +
                c.nome.slice(0, 3) + '</span><div><strong>' + c.nome + '</strong><small>' +
                c.quantidade + " · " + fmtPct(c.percentual) + "</small></div></header>" +
                "<p>" + (c.dezenas || []).join(" ") + "</p>" +
                (c.detalhe ? "<em>" + c.detalhe + "</em>" : "") +
                "</article>";
        }).join("");
        var tbody = $("sg-tabela-cores").querySelector("tbody");
        tbody.innerHTML = (p.cores || []).map(function (c) {
            return "<tr><td>" + c.nome + "</td><td>" + (c.dezenas || []).join(" ") + "</td><td>" +
                c.quantidade + "</td><td>" + fmtPct(c.percentual) + "</td></tr>";
        }).join("");
        desenharGraficos(p);
        var abrir = $("sg-abrir");
        if (!p.url || p.key === S.modalidade || p.atual) {
            abrir.hidden = true;
        } else {
            abrir.hidden = false;
            abrir.href = p.url;
            abrir.textContent = "Abrir o simulador da " + p.nome;
        }
    }

    function preencherSeletor() {
        var sel = $("sg-modalidade");
        sel.innerHTML = (BOOT.modalidades || []).map(function (m) {
            return '<option value="' + m.key + '"' + (m.key === S.modalidade ? " selected" : "") + ">" +
                m.nome + " · " + m.universo_label + "</option>";
        }).join("");
        sel.addEventListener("change", function () {
            fetch("/simulador-globo/api/painel/" + encodeURIComponent(sel.value))
                .then(function (r) { return r.json(); })
                .then(renderPainel)
                .catch(function () { mostrarErro("Não foi possível carregar a modalidade."); });
        });
    }

    function ativarAba(nome) {
        document.querySelectorAll(".sg-aba").forEach(function (b) {
            b.classList.toggle("ativa", b.getAttribute("data-aba") === nome);
        });
        document.querySelectorAll(".sg-painel").forEach(function (p) {
            p.classList.toggle("ativo", p.id === "sg-aba-" + nome);
        });
        if (nome === "historico") carregarHistorico();
        if (nome === "simulador" && S.globo && S.globo._resize) S.globo._resize();
        if (nome === "cores") {
            S.charts.forEach(function (c) { try { c.resize(); } catch (e) {} });
        }
    }

    function pararTimer() {
        S.geracao += 1;
        if (S.timer) clearTimeout(S.timer);
        S.timer = null;
    }

    function agendar() {
        var visto = S.geracao;
        S.timer = setTimeout(function () { tick(visto); }, S.velocidade);
    }

    function aplicarContagem(data) {
        contagens(data.sorteadas, data.restantes_globo, data.faltam);
        if (data.previstas) S.previstas = data.previstas;
    }

    async function tick(visto) {
        if (S.status !== "em_andamento" || visto !== S.geracao) return;
        S.ocupado = true;
        atualizarBotoes();
        try {
            var data = await post("/api/proxima", { id: S.simId, velocidade_ms: S.velocidade });
            mostrarErro("");
            await S.globo.retirar(data.bola);
            adicionarResultado(data.bola);
            aplicarContagem(data);
            if (data.fase_encerrada && data.proxima_fase && !data.concluida) {
                if (S.status === "em_andamento") await esperar(650);
                await S.globo.carregar(data.proxima_fase);
                S.globo.definirGiro(S.status === "em_andamento");
            }
            if (data.concluida) {
                S.status = "completa";
                S.globo.definirGiro(false);
                data.sequencia = data.sequencia || [];
                mostrarFinal(data);
                return;
            }
        } catch (e) {
            mostrarErro(e.message);
            S.status = "pausada";
            S.globo.definirGiro(false);
        } finally {
            S.ocupado = false;
            statusTexto();
            atualizarBotoes();
        }
        if (S.status === "em_andamento" && visto === S.geracao) agendar();
    }

    async function preparar() {
        pararTimer();
        S.replay += 1;
        mostrarErro("");
        S.ocupado = true;
        atualizarBotoes();
        try {
            var data = await post("/api/preparar", { velocidade_ms: S.velocidade });
            S.simId = data.id;
            S.status = "preparada";
            S.previstas = data.previstas;
            limparResultado();
            await S.globo.carregar(data.fase);
            S.globo.definirGiro(false);
            aplicarContagem(data);
            $("sg-faltam").textContent = String(data.previstas || 0);
        } catch (e) {
            mostrarErro(e.message);
        } finally {
            S.ocupado = false;
            statusTexto();
            atualizarBotoes();
        }
    }

    function iniciar() {
        if (S.status !== "preparada") return;
        mostrarErro("");
        S.status = "em_andamento";
        S.globo.definirGiro(true);
        statusTexto();
        atualizarBotoes();
        agendar();
    }

    function pausar() {
        if (S.status === "revendo") {
            S.replay += 1;
            S.status = "ocioso";
            if (S.globo) S.globo.definirGiro(false);
            statusTexto();
            atualizarBotoes();
            return;
        }
        if (S.status !== "em_andamento") return;
        pararTimer();
        S.status = "pausada";
        if (S.globo) S.globo.definirGiro(false);
        statusTexto();
        atualizarBotoes();
    }

    function continuar() {
        if (S.status !== "pausada") return;
        S.status = "em_andamento";
        S.globo.definirGiro(true);
        statusTexto();
        atualizarBotoes();
        agendar();
    }

    async function finalizar() {
        pararTimer();
        S.replay += 1;
        if (!S.simId) {
            S.status = "ocioso";
            statusTexto();
            atualizarBotoes();
            return;
        }
        S.ocupado = true;
        try {
            var data = await post("/api/finalizar", { id: S.simId });
            S.status = data.status;
            if (S.globo) S.globo.definirGiro(false);
            if ((data.sequencia || []).length) mostrarFinal(data);
        } catch (e) {
            mostrarErro(e.message);
        } finally {
            S.ocupado = false;
            statusTexto();
            atualizarBotoes();
        }
    }

    async function rever(seq) {
        pararTimer();
        var token = ++S.replay;
        ativarAba("simulador");
        S.simId = null;
        S.status = "revendo";
        limparResultado();
        statusTexto();
        atualizarBotoes();
        var faseAtual = null;
        S.globo.definirGiro(true);
        for (var i = 0; i < seq.length; i++) {
            if (token !== S.replay) return;
            var bola = seq[i];
            if (bola.fase_id !== faseAtual) {
                faseAtual = bola.fase_id;
                var fase = (BOOT.fases || []).find(function (f) { return f.id === bola.fase_id; });
                if (fase) await S.globo.carregar(JSON.parse(JSON.stringify(fase)));
                S.globo.definirGiro(true);
                await esperar(350);
            }
            if (token !== S.replay) return;
            await S.globo.retirar(bola);
            adicionarResultado(bola);
            contagens(i + 1, "—", seq.length - i - 1);
            await esperar(Math.min(S.velocidade, 1600));
        }
        if (token !== S.replay) return;
        S.globo.definirGiro(false);
        S.status = "ocioso";
        mostrarFinal({ status: "completa", sequencia: seq });
        statusTexto();
        atualizarBotoes();
    }

    function carregarHistorico() {
        fetch("/simulador-globo/api/historico")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var corpo = $("sg-hist-corpo");
                var itens = data.itens || [];
                if (!itens.length) {
                    corpo.innerHTML = '<tr><td colspan="6" class="sg-vazio">Nenhuma simulação registrada ainda.</td></tr>';
                    return;
                }
                corpo.innerHTML = itens.map(function (item) {
                    var vel = (item.velocidade_ms / 1000).toLocaleString("pt-BR") + " s";
                    return "<tr><td>" + item.criado_em + "</td><td>" + item.status + "</td><td>" +
                        item.quantidade_sorteada + " / " + item.sorteadas_previstas + "</td><td>" + vel +
                        "</td><td>" + item.resumo + "</td><td><button type=\"button\" class=\"sg-btn secundario\" data-ver=\"" +
                        item.id + "\">Ver</button></td></tr>";
                }).join("");
            })
            .catch(function () { mostrarErro("Não foi possível ler o histórico."); });
    }

    function verHistorico(id) {
        fetch("/simulador-globo/api/historico/" + id)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var box = $("sg-hist-detalhe");
                box.innerHTML = "";
                var titulo = document.createElement("p");
                titulo.className = "sg-nota";
                titulo.textContent = "Simulação " + data.id + " · " + data.criado_em + " · " + data.status +
                    " · intervalo " + (data.velocidade_ms / 1000).toLocaleString("pt-BR") + " s";
                var faixa = document.createElement("div");
                faixa.className = "sg-chips";
                (data.sequencia || []).forEach(function (b) {
                    var c = chip(b, true);
                    c.title = (b.ordem || "") + "ª · " + (b.cor_nome || "") + (b.fase_titulo ? " · " + b.fase_titulo : "");
                    faixa.appendChild(c);
                });
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "sg-btn";
                btn.style.margin = ".6rem 0";
                btn.textContent = "Rever no globo";
                btn.addEventListener("click", function () { rever(data.sequencia || []); });
                box.appendChild(titulo);
                box.appendChild(faixa);
                box.appendChild(btn);
            });
    }

    document.querySelectorAll(".sg-aba").forEach(function (b) {
        b.addEventListener("click", function () { ativarAba(b.getAttribute("data-aba")); });
    });
    $("sg-preparar").addEventListener("click", preparar);
    $("sg-iniciar").addEventListener("click", iniciar);
    $("sg-pausar").addEventListener("click", pausar);
    $("sg-continuar").addEventListener("click", continuar);
    $("sg-reiniciar").addEventListener("click", preparar);
    $("sg-finalizar").addEventListener("click", finalizar);
    $("sg-velocidade").addEventListener("input", function (ev) {
        S.velocidade = Number(ev.target.value);
        $("sg-velocidade-lbl").textContent = (S.velocidade / 1000).toLocaleString("pt-BR") + " s";
        if (S.simId && S.status !== "ocioso") {
            post("/api/velocidade", { id: S.simId, velocidade_ms: S.velocidade }).catch(function () {});
        }
    });
    $("sg-hist-corpo").addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-ver]");
        if (!btn) return;
        verHistorico(btn.getAttribute("data-ver"));
    });

    S.globo = new GloboCena($("sg-arena"));
    preencherSeletor();
    renderPainel(BOOT.painel);
    var nota = (BOOT.modalidades || []).find(function (m) { return m.key === S.modalidade; });
    $("sg-sim-nota").textContent = nota ? nota.nota : "";
    statusTexto();
    atualizarBotoes();
})();
