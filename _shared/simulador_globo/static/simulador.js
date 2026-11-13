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

    function raizSimulador() {
        var path = window.location.pathname || "";
        var marca = "/simulador-globo";
        var i = path.indexOf(marca);
        if (i < 0) return marca;
        return path.slice(0, i + marca.length);
    }

    function urlApi(caminho) {
        var extra = String(caminho || "");
        if (extra.charAt(0) !== "/") extra = "/" + extra;
        return raizSimulador() + extra;
    }

    function lerJson(r) {
        return r.text().then(function (texto) {
            var data = null;
            try { data = texto ? JSON.parse(texto) : null; } catch (e) { data = null; }
            if (!r.ok || !data || typeof data !== "object") {
                throw new Error((data && data.erro) || ("A simulação não respondeu (" + r.status + ")."));
            }
            return data;
        });
    }

    function fmtPct(n) {
        return Number(n).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
    }

    function post(caminho, corpo) {
        return fetch(urlApi(caminho), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(corpo || {}),
        }).then(lerJson);
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

    function resetarHero() {
        var hero = $("sg-hero");
        hero.style.background = "#f3f3f3";
        hero.style.color = "#666";
        $("sg-hero-bola").textContent = "—";
        $("sg-hero-bola").style.background = "transparent";
        $("sg-hero-bola").style.color = "#666";
        $("sg-hero-cor").textContent = "Aguardando o sorteio";
    }

    function limparResultado() {
        S.grupos = {};
        $("sg-resultado").innerHTML = "";
        $("sg-final").hidden = true;
        $("sg-final").innerHTML = "";
        resetarHero();
    }

    function chip(bola, grande) {
        bola = pintarMes(bola);
        var el = document.createElement("span");
        el.className = grande ? "sg-mini" : "sg-chip";
        el.style.background = bola.hex;
        el.style.color = bola.texto;
        el.style.boxShadow = "inset 0 -4px 8px rgba(0,0,0,.18)";
        el.textContent = bola.rotulo;
        return el;
    }

    var CORES_FINAL = {
        "1": ["#E53935", "#ffffff"], "2": ["#FDD835", "#212121"], "3": ["#43A047", "#ffffff"],
        "4": ["#6D4C41", "#ffffff"], "5": ["#1E88E5", "#ffffff"], "6": ["#EC407A", "#ffffff"],
        "7": ["#212121", "#ffffff"], "8": ["#9E9E9E", "#212121"], "9": ["#FB8C00", "#212121"],
        "0": ["#F7F7F7", "#212121"]
    };
    var MES_NUM = {
        Jan: 1, Fev: 2, Mar: 3, Abr: 4, Mai: 5, Jun: 6,
        Jul: 7, Ago: 8, Set: 9, Out: 10, Nov: 11, Dez: 12
    };
    var MES_NOME = {
        Jan: "Janeiro", Fev: "Fevereiro", Mar: "Março", Abr: "Abril", Mai: "Maio", Jun: "Junho",
        Jul: "Julho", Ago: "Agosto", Set: "Setembro", Out: "Outubro", Nov: "Novembro", Dez: "Dezembro"
    };

    function corDoToken(tok) {
        if (MES_NUM[tok]) {
            var m = (BOOT.cores_meses && BOOT.cores_meses[tok]) || {};
            var par = MES_HEX[tok] || CORES_FINAL[String(MES_NUM[tok] % 10)];
            var hex = m.hex || (par && par[0]) || "#9e9e9e";
            var texto = m.texto || (par && par[1]) || "#ffffff";
            return { hex: hex, texto: texto, mes: true, nome: m.nome || MES_NOME[tok] };
        }
        var final = String(tok).slice(-1);
        var c = CORES_FINAL[final] || ["#e0e0e0", "#212121"];
        return { hex: c[0], texto: c[1], mes: false, nome: tok };
    }

    function adicionarResultado(bola) {
        var id = bola.fase_id || "dezenas";
        var ehMes = id === "mes" || bola.grupo === "mes";
        if (!S.grupos[id]) {
            var box = document.createElement("div");
            box.className = ehMes ? "sg-mes" : "sg-canal";
            var chips = document.createElement("div");
            chips.className = "sg-chips";
            box.appendChild(chips);
            $("sg-resultado").appendChild(box);
            S.grupos[id] = chips;
        }
        bola = pintarMes(bola);
        var item = document.createElement("span");
        item.className = "sg-chip sg-desce";
        item.style.background = bola.hex;
        item.style.color = bola.texto;
        item.title = (bola.ordem || "") + "ª · " + (bola.cor_nome || "");
        item.textContent = bola.rotulo;
        item.title = ehMes ? (bola.nome || bola.rotulo) : item.title;
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

    var MES_HEX = {
        Jan: ["#030303", "#ffffff"], Fev: ["#9b59b6", "#ffffff"], Mar: ["#3498db", "#ffffff"],
        Abr: ["#e67e22", "#ffffff"], Mai: ["#f1c40f", "#212121"], Jun: ["#2ecc71", "#ffffff"],
        Jul: ["#1abc9c", "#ffffff"], Ago: ["#34495e", "#ffffff"], Set: ["#196f3d", "#ffffff"],
        Out: ["#d35400", "#ffffff"], Nov: ["#8e44ad", "#ffffff"], Dez: ["#c0392b", "#ffffff"]
    };

    function ehMes(b) {
        return !!(b && (b.grupo === "mes" || b.fase_id === "mes" || MES_NUM[b.rotulo]));
    }

    function pintarFase(fase) {
        if (!fase) return fase;
        var copia = JSON.parse(JSON.stringify(fase));
        if (copia.bolas) copia.bolas = copia.bolas.map(pintarMes);
        return copia;
    }

    function pintarMes(bola) {
        if (!ehMes(bola)) return bola;
        var tok = bola.rotulo;
        var m = (BOOT.cores_meses && BOOT.cores_meses[tok]) || null;
        var par = MES_HEX[tok];
        return Object.assign({}, bola, {
            hex: (m && m.hex) || (par && par[0]) || bola.hex,
            texto: (m && m.texto) || (par && par[1]) || bola.texto,
        });
    }

    function textoCrescente(b) {
        if (b.grupo === "digito") return String(b.rotulo);
        var n = Number(b.numero);
        if (!isFinite(n)) return String(b.rotulo || "");
        return (n < 10 ? "0" : "") + String(n);
    }

    function linhaCrescente(seq) {
        var linha = document.createElement("div");
        linha.className = "sg-ordem";
        var dezenas = seq.filter(function (b) {
            return !ehMes(b) && b.grupo !== "trevo" && b.grupo !== "time";
        });
        var extras = seq.filter(function (b) {
            return ehMes(b) || b.grupo === "trevo" || b.grupo === "time";
        });
        dezenas.sort(function (a, b) { return Number(a.numero) - Number(b.numero); });
        dezenas.forEach(function (b) {
            var n = document.createElement("span");
            n.className = "sg-ordem-n";
            n.textContent = textoCrescente(b);
            linha.appendChild(n);
        });
        extras.forEach(function (b) { linha.appendChild(chip(b, true)); });
        return linha;
    }

    function diagonaisDia(nums) {
        var rows = [[1, 10], [11, 20], [21, 30], [31, 31]];
        var pmap = {};
        rows.forEach(function (ab, r) {
            for (var n = ab[0]; n <= ab[1]; n++) pmap[n] = [r, n - ab[0]];
        });
        function geomDir(list) {
            var cells = list.map(function (n) { return pmap[n]; }).filter(Boolean);
            cells.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
            if (cells.length < 2) return "down";
            var first = cells[0], last = cells[cells.length - 1];
            if (last[1] > first[1]) return "down";
            if (last[1] < first[1]) return "up";
            return "down";
        }
        function orderGeom(list) {
            return list.filter(function (n) { return pmap[n]; }).sort(function (a, b) {
                var pa = pmap[a], pb = pmap[b];
                return pa[0] - pb[0] || pa[1] - pb[1] || a - b;
            });
        }
        var down = {}, up = {};
        rows.forEach(function (ab, r) {
            for (var n = ab[0]; n <= ab[1]; n++) {
                var c = n - ab[0];
                (down[c - r] || (down[c - r] = [])).push({ n: n, r: r, c: c });
                (up[c + r] || (up[c + r] = [])).push({ n: n, r: r, c: c });
            }
        });
        var lines = [];
        function flush(mapa) {
            Object.keys(mapa).forEach(function (k) {
                var arr = mapa[k].slice().sort(function (a, b) { return a.r - b.r || a.c - b.c; });
                var run = [];
                function fechar() {
                    if (run.length >= 2) lines.push(run.map(function (x) { return x.n; }));
                }
                arr.forEach(function (cell) {
                    if (!run.length || cell.r === run[run.length - 1].r + 1) run.push(cell);
                    else { fechar(); run = [cell]; }
                });
                fechar();
            });
        }
        flush(down);
        flush(up);
        var chosen = {};
        nums.forEach(function (n) { chosen[Number(n)] = true; });
        var runs = [], seen = {};
        lines.forEach(function (line) {
            var cur = [];
            function fechar() {
                if (cur.length < 2) return;
                var ordered = orderGeom(cur);
                var dir = geomDir(ordered);
                var key = dir + ":" + ordered.join("-");
                if (seen[key]) return;
                seen[key] = true;
                runs.push({ dir: dir, nums: ordered });
            }
            line.forEach(function (n) {
                if (chosen[n]) cur.push(n);
                else { fechar(); cur = []; }
            });
            fechar();
        });
        runs.sort(function (a, b) {
            return b.nums.length - a.nums.length || a.nums[0] - b.nums[0];
        });
        return runs;
    }

    function montarVolante(dezenas) {
        var escolhidas = {};
        dezenas.forEach(function (n) { escolhidas[Number(n)] = true; });
        var runs = diagonaisDia(Object.keys(escolhidas).map(Number));
        var naDiag = {};
        runs.forEach(function (r) { r.nums.forEach(function (n) { naDiag[n] = true; }); });
        var wrap = document.createElement("div");
        wrap.className = "sg-volante";
        var grade = document.createElement("div");
        grade.className = "sg-vol-grade";
        grade.setAttribute("aria-label", "Volante");
        for (var n = 1; n <= 31; n++) {
            var cel = document.createElement("span");
            cel.className = "sg-vol-cel" + (escolhidas[n] ? " saiu" : "") + (naDiag[n] ? " diag" : "");
            cel.textContent = (n < 10 ? "0" : "") + n;
            grade.appendChild(cel);
        }
        wrap.appendChild(grade);
        var leg = document.createElement("p");
        leg.className = "sg-diags";
        if (!runs.length) leg.textContent = "Sem diagonal neste volante.";
        else runs.forEach(function (r) {
            var s = document.createElement("span");
            s.textContent = (r.dir === "up" ? "↗ " : "↘ ") + r.nums.map(function (n) {
                return (n < 10 ? "0" : "") + n;
            }).join("-");
            leg.appendChild(s);
        });
        wrap.appendChild(leg);
        return wrap;
    }

    function faixaChips(bolas) {
        var faixa = document.createElement("div");
        faixa.className = "sg-chips sg-final-faixa";
        bolas.forEach(function (b) { faixa.appendChild(chip(b, true)); });
        return faixa;
    }

    function volanteFaixa(min, max, escolhidas) {
        var total = max - min + 1;
        var cols = total === 25 ? 5 : (total <= 10 ? total : 10);
        var wrap = document.createElement("div");
        wrap.className = "sg-volante";
        var grade = document.createElement("div");
        grade.className = "sg-vol-grade";
        grade.style.gridTemplateColumns = "repeat(" + cols + ", minmax(0, 1fr))";
        for (var n = min; n <= max; n++) {
            var cel = document.createElement("span");
            cel.className = "sg-vol-cel" + (escolhidas[n] ? " saiu" : "");
            cel.textContent = (max >= 10 && n < 10 ? "0" : "") + n;
            grade.appendChild(cel);
        }
        wrap.appendChild(grade);
        return wrap;
    }

    function volanteDaFase(faseId, bolas) {
        var dezenas = bolas.filter(function (b) {
            return b.grupo === "dezena" || b.grupo === "digito";
        });
        if (!dezenas.length) return null;
        if (dezenas[0].grupo === "digito") return volanteColunas(dezenas);
        var fase = (BOOT.fases || []).filter(function (f) { return f.id === faseId; })[0];
        var universo = (fase && fase.bolas || []).map(function (b) { return Number(b.numero); });
        var nums = dezenas.map(function (b) { return Number(b.numero); });
        var base = universo.length ? universo : nums;
        var escolhidas = {};
        nums.forEach(function (n) { escolhidas[n] = true; });
        return volanteFaixa(Math.min.apply(null, base), Math.max.apply(null, base), escolhidas);
    }

    function volanteColunas(seq) {
        var porColuna = {};
        seq.forEach(function (b) { porColuna[Number(b.coluna) || 0] = Number(b.numero); });
        var wrap = document.createElement("div");
        wrap.className = "sg-volante";
        var grade = document.createElement("div");
        grade.className = "sg-vol-grade";
        grade.style.gridTemplateColumns = "repeat(7, minmax(0, 1fr))";
        for (var col = 1; col <= 7; col++) {
            var bloco = document.createElement("div");
            bloco.style.display = "grid";
            bloco.style.gap = "3px";
            for (var d = 0; d <= 9; d++) {
                var cel = document.createElement("span");
                cel.className = "sg-vol-cel" + (porColuna[col] === d ? " saiu" : "");
                cel.textContent = String(d);
                bloco.appendChild(cel);
            }
            grade.appendChild(bloco);
        }
        wrap.appendChild(grade);
        return wrap;
    }

    function volanteTrevos(seq) {
        var saiu = {};
        seq.forEach(function (b) { saiu[Number(b.numero)] = true; });
        var wrap = document.createElement("div");
        wrap.className = "sg-volante";
        var grade = document.createElement("div");
        grade.className = "sg-vol-grade";
        grade.style.gridTemplateColumns = "repeat(6, minmax(0, 1fr))";
        for (var n = 1; n <= 6; n++) {
            var cel = document.createElement("span");
            cel.className = "sg-vol-cel" + (saiu[n] ? " saiu" : "");
            cel.textContent = String(n);
            grade.appendChild(cel);
        }
        wrap.appendChild(grade);
        return wrap;
    }

    function gruposDaSequencia(seq) {
        var ordem = [];
        var mapa = {};
        seq.forEach(function (b) {
            var id = b.fase_id || "dezenas";
            if (!mapa[id]) {
                mapa[id] = [];
                ordem.push(id);
            }
            mapa[id].push(b);
        });
        return ordem.map(function (id) { return { id: id, bolas: mapa[id] }; });
    }

    function mostrarFinal(data) {
        var box = $("sg-final");
        var seq = (data && data.sequencia) || [];
        var titulo = data && data.status === "completa" ? "Resultado completo" : "Resultado parcial";
        box.hidden = false;
        box.innerHTML = "";
        var h = document.createElement("strong");
        h.textContent = titulo;
        box.appendChild(h);
        if (S.modalidade === "diadesorte") {
            box.appendChild(faixaChips(seq));
            box.appendChild(linhaCrescente(seq));
            var nums = seq.filter(function (b) { return !ehMes(b); }).map(function (b) { return Number(b.numero); });
            box.appendChild(montarVolante(nums));
            return;
        }
        var grupos = gruposDaSequencia(seq);
        grupos.forEach(function (g) {
            if (grupos.length > 1) {
                var sub = document.createElement("strong");
                sub.textContent = (g.bolas[0] && g.bolas[0].fase_titulo) || "";
                box.appendChild(sub);
            }
            box.appendChild(faixaChips(g.bolas));
            var temNumero = g.bolas.some(function (b) {
                return b.grupo === "dezena" || b.grupo === "digito";
            });
            if (g.bolas[0] && g.bolas[0].grupo === "digito") {
                var linha = document.createElement("div");
                linha.className = "sg-ordem";
                g.bolas.forEach(function (b) {
                    var n = document.createElement("span");
                    n.className = "sg-ordem-n";
                    n.textContent = textoCrescente(b);
                    linha.appendChild(n);
                });
                box.appendChild(linha);
            } else if (temNumero) {
                box.appendChild(linhaCrescente(g.bolas));
            }
            var grade = volanteDaFase(g.id, g.bolas);
            if (grade) box.appendChild(grade);
            if (g.bolas.some(function (b) { return b.grupo === "trevo"; })) {
                box.appendChild(volanteTrevos(g.bolas));
            }
        });
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
            var data = await post("api/proxima", { id: S.simId, velocidade_ms: S.velocidade });
            mostrarErro("");
            await S.globo.retirar(data.bola);
            adicionarResultado(data.bola);
            aplicarContagem(data);
            if (data.fase_encerrada && data.proxima_fase && !data.concluida) {
                if (S.status === "em_andamento") await esperar(650);
                await S.globo.carregar(pintarFase(data.proxima_fase));
                S.globo.definirGiro(S.status === "em_andamento");
            }
            if (data.concluida) {
                S.status = "completa";
                S.globo.definirGiro(false);
                data.sequencia = data.sequencia || [];
                mostrarFinal(data);
                resetarHero();
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
            var data = await post("api/preparar", { velocidade_ms: S.velocidade });
            S.simId = data.id;
            S.status = "preparada";
            S.previstas = data.previstas;
            limparResultado();
            await S.globo.carregar(pintarFase(data.fase));
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
            var data = await post("api/finalizar", { id: S.simId });
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
                if (fase) await S.globo.carregar(pintarFase(fase));
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
        resetarHero();
        statusTexto();
        atualizarBotoes();
    }

    function carregarHistorico() {
        fetch(urlApi("api/historico"))
            .then(lerJson)
            .then(function (data) {
                var corpo = $("sg-hist-corpo");
                var itens = data.itens || [];
                if (!itens.length) {
                    corpo.innerHTML = '<tr><td colspan="6" class="sg-vazio">Nenhuma simulação registrada ainda.</td></tr>';
                    return;
                }
                corpo.innerHTML = itens.map(function (item) {
                    var vel = (item.velocidade_ms / 1000).toLocaleString("pt-BR") + " s";
                    var toks = String(item.resumo || "").split(/\s+/).filter(Boolean);
                    var nMes = toks.filter(function (t) { return !!MES_NUM[t]; }).length;
                    var nDez = toks.length - nMes;
                    var previstasDez = Number(item.sorteadas_previstas) > nDez + nMes ? 7 : Number(item.sorteadas_previstas);
                    var saida = nMes ? (nDez + " + mês") : (nDez + " / " + previstasDez);
                    var seq = toks.map(function (t) {
                        var c = corDoToken(t);
                        return '<span class="sg-mini' + (c.mes ? " sg-mini-mes" : "") + '" style="background:' + c.hex + ';color:' + c.texto + '" title="' +
                            c.nome + '">' + t + "</span>";
                    }).join("");
                    return "<tr><td>" + item.criado_em + "</td><td>" + item.status + "</td><td>" +
                        saida + "</td><td>" + vel +
                        "</td><td>" + seq + "</td><td><button type=\"button\" class=\"sg-btn secundario\" data-ver=\"" +
                        item.id + "\">Ver</button></td></tr>";
                }).join("");
            })
            .catch(function () { mostrarErro("Não foi possível ler o histórico."); });
    }

    function verHistorico(id) {
        fetch(urlApi("api/historico/" + id))
            .then(lerJson)
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
    var GIRO_NOME = { 1: "devagar", 2: "leve", 3: "normal", 4: "rápido", 5: "bem rápido" };
    function aplicarGiro(valor) {
        var n = Number(valor) || 3;
        if (S.globo && S.globo.definirRitmo) S.globo.definirRitmo(n / 3);
        $("sg-giro-lbl").textContent = GIRO_NOME[n] || String(n);
    }
    $("sg-giro").addEventListener("input", function (ev) { aplicarGiro(ev.target.value); });

    $("sg-velocidade").addEventListener("input", function (ev) {
        S.velocidade = Number(ev.target.value);
        $("sg-velocidade-lbl").textContent = (S.velocidade / 1000).toLocaleString("pt-BR") + " s";
        if (S.simId && S.status !== "ocioso") {
            post("api/velocidade", { id: S.simId, velocidade_ms: S.velocidade }).catch(function () {});
        }
    });
    $("sg-hist-corpo").addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-ver]");
        if (!btn) return;
        verHistorico(btn.getAttribute("data-ver"));
    });

    S.globo = new GloboCena($("sg-arena"));
    aplicarGiro($("sg-giro").value);
    renderPainel(BOOT.painel);
    $("sg-sim-nota").textContent = (BOOT.painel && BOOT.painel.nota) || "";
    statusTexto();
    atualizarBotoes();
})();
