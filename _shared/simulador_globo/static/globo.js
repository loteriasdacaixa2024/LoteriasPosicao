/* Globo transparente: Three.js quando o navegador permite, disco 2D caso contrário. */
(function () {
    function webglOk() {
        try {
            var c = document.createElement("canvas");
            return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
        } catch (e) {
            return false;
        }
    }

    function texturaNumero(rotulo, tinta) {
        var c = document.createElement("canvas");
        c.width = 256;
        c.height = 128;
        var g = c.getContext("2d");
        g.clearRect(0, 0, 256, 128);
        g.textAlign = "center";
        g.textBaseline = "middle";
        var tamanho = String(rotulo).length > 3 ? 54 : (String(rotulo).length > 2 ? 72 : 92);
        g.font = "800 " + tamanho + "px Inter, Segoe UI, sans-serif";
        g.lineWidth = 10;
        g.strokeStyle = "rgba(0,0,0,.55)";
        g.strokeText(String(rotulo), 128, 68);
        g.fillStyle = tinta || "#fff";
        g.fillText(String(rotulo), 128, 68);
        var tex = new THREE.CanvasTexture(c);
        tex.needsUpdate = true;
        return tex;
    }

    function pontoDentro(raio) {
        var v = new THREE.Vector3(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1);
        if (v.lengthSq() < 1e-4) v.set(0.3, 0.2, 0.1);
        v.normalize().multiplyScalar(Math.random() * raio);
        return v;
    }

    function raioBola(qtd, R) {
        if (qtd <= 12) return R * 0.22;
        if (qtd > 80) return R * 0.068;
        if (qtd > 40) return R * 0.082;
        if (qtd > 20) return R * 0.1;
        return R * 0.12;
    }

    class GloboCena {
        constructor(el) {
            this.el = el;
            this.bolas = [];
            this.geracao = 0;
            this.girando = false;
            this.ritmo = 1;
            this.modo = "2d";
            this._ultimo = 0;
            this.faseTitulo = "";
            this._montarDom();
            if (window.THREE && webglOk()) {
                try {
                    this._init3d();
                    this.modo = "3d";
                } catch (e) {
                    this.modo = "2d";
                }
            }
            this.tag.textContent = this.modo === "3d" ? "Globo tridimensional" : "Globo em vista simplificada";
            this._loop = this._loop.bind(this);
            requestAnimationFrame(this._loop);
        }

        _montarDom() {
            this.el.innerHTML = "";
            this.tag = document.createElement("div");
            this.tag.className = "sg-arena-tag";
            this.faseEl = document.createElement("div");
            this.faseEl.className = "sg-fase-tag";
            this.lista = document.createElement("div");
            this.lista.className = "sg-lista";
            this.lista.hidden = true;
            this.disco = document.createElement("div");
            this.disco.className = "sg-disco";
            this.disco.hidden = true;
            this.el.appendChild(this.tag);
            this.el.appendChild(this.faseEl);
            this.el.appendChild(this.lista);
            this.el.appendChild(this.disco);
        }

        _init3d() {
            var w = this.el.clientWidth || 640;
            var h = this.el.clientHeight || 560;
            this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            this.renderer.setSize(w, h, false);
            this.renderer.setClearColor(0x000000, 0);
            this.el.insertBefore(this.renderer.domElement, this.tag);
            this.scene = new THREE.Scene();
            this.camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 50);
            this.camera.position.set(0, 0.35, 6.6);
            this.camera.lookAt(0, 0, 0);
            this.scene.add(new THREE.AmbientLight(0xffffff, 0.72));
            var dir = new THREE.DirectionalLight(0xffffff, 0.9);
            dir.position.set(4, 6, 5);
            this.scene.add(dir);
            var fill = new THREE.DirectionalLight(0x9ec9ff, 0.35);
            fill.position.set(-5, -1, -3);
            this.scene.add(fill);
            this.root = new THREE.Group();
            this.scene.add(this.root);
            var self = this;
            this._noResize = function () { self._resize(); };
            window.addEventListener("resize", this._noResize);
        }

        _resize() {
            if (!this.renderer) return;
            var w = this.el.clientWidth || 640;
            var h = this.el.clientHeight || 560;
            this.renderer.setSize(w, h, false);
            this.camera.aspect = w / Math.max(h, 1);
            this.camera.updateProjectionMatrix();
        }

        definirGiro(ativo) {
            this.girando = !!ativo;
        }

        definirRitmo(fator) {
            var n = Number(fator);
            if (!n || n < 0.25) n = 0.25;
            if (n > 2) n = 2;
            this.ritmo = n;
        }

        _limpar() {
            this.bolas.forEach(function (b) {
                if (b.sprite) {
                    if (b.sprite.parent) b.sprite.parent.remove(b.sprite);
                    if (b.sprite.material.map) b.sprite.material.map.dispose();
                    b.sprite.material.dispose();
                }
                if (!b.mesh) return;
                if (b.numeroGeo) b.numeroGeo.dispose();
                if (b.numeroMat) {
                    if (b.numeroMat.map) b.numeroMat.map.dispose();
                    b.numeroMat.dispose();
                }
                if (b.mesh.geometry) b.mesh.geometry.dispose();
                var mat = b.mesh.material;
                if (mat && mat.map) mat.map.dispose();
                if (mat && mat.dispose) mat.dispose();
            });
            this.bolas = [];
            this.lista.innerHTML = "";
            this.disco.innerHTML = "";
            this.lista.hidden = true;
            this.disco.hidden = this.modo === "3d";
            if (this.root) {
                while (this.root.children.length) {
                    this.root.remove(this.root.children[0]);
                }
            }
            if (this.renderer) this.renderer.domElement.style.visibility = "visible";
        }

        carregar(fase) {
            this.geracao += 1;
            this._limpar();
            this.spinIndividual = false;
            if (this.root) this.root.rotation.set(0, 0, 0);
            if (this._resize) this._resize();
            this.faseTitulo = (fase && fase.titulo) || "";
            this.faseEl.textContent = this.faseTitulo;
            if (!fase) return Promise.resolve();
            if (fase.tipo === "lista") return this._carregarLista(fase);
            if (fase.tipo === "colunas") return this._carregarColunas(fase);
            return this._carregarGlobo(fase);
        }

        _enquadrar(span) {
            var w = this.el.clientWidth || 960;
            var h = this.el.clientHeight || 400;
            this.camera.aspect = w / Math.max(h, 1);
            this.camera.fov = 32;
            this.camera.updateProjectionMatrix();
            var halfH = (this.camera.fov * Math.PI / 180) / 2;
            var halfW = Math.atan(Math.tan(halfH) * this.camera.aspect);
            var z = (span * 0.56) / Math.tan(halfW * 0.96);
            this.camera.position.set(0, 0.02, Math.max(z, 3.5));
            this.camera.lookAt(0, 0, 0);
        }

        _material(bola) {
            return new THREE.MeshPhongMaterial({
                color: new THREE.Color(bola.hex),
                shininess: 36,
                specular: new THREE.Color("#777777"),
            });
        }

        _globoMalha(R) {
            var g = new THREE.Group();
            g.add(new THREE.Mesh(
                new THREE.SphereGeometry(R, 42, 28),
                new THREE.MeshPhongMaterial({
                    color: 0xd7ecff,
                    transparent: true,
                    opacity: 0.1,
                    shininess: 140,
                    specular: new THREE.Color("#ffffff"),
                    side: THREE.DoubleSide,
                    depthWrite: false,
                })
            ));
            g.add(new THREE.Mesh(
                new THREE.SphereGeometry(R * 1.008, 16, 10),
                new THREE.MeshBasicMaterial({
                    color: 0xd5eeff,
                    wireframe: true,
                    transparent: true,
                    opacity: 0.07,
                })
            ));
            return g;
        }

        _addBola3d(pai, bola, R, qtd) {
            var rb = raioBola(qtd, R);
            var mesh = new THREE.Mesh(new THREE.SphereGeometry(rb, qtd > 60 ? 14 : 18, qtd > 60 ? 12 : 16), this._material(bola));
            var maxR = R - rb - 0.02;
            mesh.position.copy(pontoDentro(maxR * 0.92));
            mesh.userData.chave = bola.chave;
            pai.add(mesh);
            var vel = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5);
            vel.setLength(2.6 + Math.random() * 1.6);
            function giro() { return (Math.random() < 0.5 ? -1 : 1) * (2.4 + Math.random() * 2.2); }
            var matNum = new THREE.MeshBasicMaterial({
                map: texturaNumero(bola.rotulo, bola.texto),
                transparent: true,
                depthWrite: false,
                side: THREE.DoubleSide,
            });
            var geoNum = new THREE.PlaneGeometry(rb * 1.65, rb * 0.88);
            var frente = new THREE.Mesh(geoNum, matNum);
            frente.position.z = rb * 1.04;
            frente.renderOrder = 2;
            mesh.add(frente);
            var verso = new THREE.Mesh(geoNum, matNum);
            verso.position.z = -rb * 1.04;
            verso.rotation.y = Math.PI;
            verso.renderOrder = 2;
            mesh.add(verso);
            this.bolas.push({
                chave: bola.chave, mesh: mesh, sprite: null, rb: rb,
                vel: vel, maxR: maxR, saindo: false, local: true,
                spin: new THREE.Vector3(giro(), giro(), giro() * 0.55),
                numeroMat: matNum, numeroGeo: geoNum,
            });
        }

        _syncNumeros() {
            if (!this._p) {
                this._p = new THREE.Vector3();
                this._dir = new THREE.Vector3();
            }
            for (var i = 0; i < this.bolas.length; i++) {
                var b = this.bolas[i];
                if (!b.sprite || !b.mesh) continue;
                if (!b.mesh.visible) {
                    b.sprite.visible = false;
                    continue;
                }
                b.mesh.getWorldPosition(this._p);
                this._dir.copy(this.camera.position).sub(this._p);
                var dist = this._dir.length() || 1;
                this._dir.multiplyScalar(1 / dist);
                var escala = b.mesh.scale.x || 1;
                b.sprite.position.copy(this._p).addScaledVector(this._dir, b.rb * escala * 1.04);
                b.sprite.scale.set(b.rb * 1.55 * escala, b.rb * 0.82 * escala, 1);
                b.sprite.visible = true;
            }
        }

        _carregarGlobo(fase) {
            var bolas = fase.bolas || [];
            if (this.modo !== "3d") return this._carregar2d(bolas, 1);
            this.el.style.minHeight = "560px";
            this.camera.fov = 42;
            this.camera.updateProjectionMatrix();
            var R = bolas.length > 70 ? 2.35 : 2.15;
            this.camera.position.set(0, 0.42, bolas.length > 70 ? 7.5 : 6.5);
            this.camera.lookAt(0, 0, 0);
            var grupo = this._globoMalha(R);
            this.root.add(grupo);
            var anel = new THREE.Mesh(
                new THREE.TorusGeometry(R * 0.72, 0.035, 12, 40),
                new THREE.MeshPhongMaterial({ color: 0x8fb4c9, shininess: 40 })
            );
            anel.rotation.x = Math.PI / 2;
            anel.position.y = -R * 1.12;
            this.root.add(anel);
            var self = this;
            bolas.forEach(function (b) { self._addBola3d(grupo, b, R, bolas.length); });
            this.disco.hidden = true;
            return Promise.resolve();
        }

        _carregarColunas(fase) {
            var colunas = fase.colunas || [];
            if (this.modo !== "3d") {
                var todas = [];
                colunas.forEach(function (col) { (col.bolas || []).forEach(function (b) { todas.push(b); }); });
                return this._carregar2d(todas, 7);
            }
            this.spinIndividual = true;
            this.el.style.minHeight = "380px";
            var R = 0.9;
            var spacing = 2.05;
            this._enquadrar((colunas.length - 1) * spacing + R * 2.4);
            var self = this;
            colunas.forEach(function (col, i) {
                var grupo = self._globoMalha(R);
                grupo.position.x = (i - (colunas.length - 1) / 2) * spacing;
                self.root.add(grupo);
                (col.bolas || []).forEach(function (b) { self._addBola3d(grupo, b, R, 10); });
            });
            return Promise.resolve();
        }

        _carregarLista(fase) {
            if (this.renderer) this.renderer.domElement.style.visibility = "hidden";
            this.lista.hidden = false;
            this.disco.hidden = true;
            var self = this;
            (fase.bolas || []).forEach(function (b) {
                var el = document.createElement("div");
                el.className = "sg-time";
                el.textContent = b.rotulo;
                el.dataset.chave = b.chave;
                el.style.borderColor = b.hex;
                self.lista.appendChild(el);
                self.bolas.push({ chave: b.chave, el: el, lista: true });
            });
            return Promise.resolve();
        }

        _carregar2d(bolas, grupos) {
            this.disco.hidden = false;
            if (this.renderer) this.renderer.domElement.style.visibility = "hidden";
            var rect = this.el.getBoundingClientRect();
            var w = rect.width || 640;
            var h = rect.height || 520;
            var colunas = Math.max(1, grupos);
            var self = this;
            bolas.forEach(function (b, i) {
                var el = document.createElement("div");
                el.className = "sg-bola2";
                el.textContent = b.rotulo;
                el.dataset.chave = b.chave;
                el.style.background = b.hex;
                el.style.color = b.texto;
                var lado = colunas > 1 ? Math.min(w, h) / 9 : (bolas.length > 70 ? 28 : 36);
                el.style.width = lado + "px";
                el.style.height = lado + "px";
                el.style.fontSize = (lado < 32 ? 9 : 12) + "px";
                var faixa = w / colunas;
                var cx = colunas > 1 ? (Math.floor(i / 10) + 0.5) * faixa : w / 2;
                var cy = h / 2;
                var alcance = colunas > 1 ? faixa * 0.32 : Math.min(w, h) * 0.34;
                var ang = Math.random() * Math.PI * 2;
                var dist = Math.random() * alcance;
                var x = cx + Math.cos(ang) * dist;
                var y = cy + Math.sin(ang) * dist * 0.72;
                el.style.left = x + "px";
                el.style.top = y + "px";
                self.disco.appendChild(el);
                self.bolas.push({
                    chave: b.chave,
                    el: el,
                    x: x,
                    y: y,
                    vx: (Math.random() - 0.5) * 160,
                    vy: (Math.random() - 0.5) * 160,
                    ang: Math.random() * Math.PI * 2,
                    vang: (Math.random() < 0.5 ? -1 : 1) * (4 + Math.random() * 5),
                    cx: cx,
                    cy: cy,
                    alcance: alcance,
                    lado: lado,
                    saindo: false,
                });
            });
            return Promise.resolve();
        }

        retirar(bola) {
            var g = this.geracao;
            var item = null;
            for (var i = 0; i < this.bolas.length; i++) {
                if (this.bolas[i].chave === bola.chave) { item = this.bolas[i]; break; }
            }
            if (!item) return Promise.resolve();
            var self = this;
            if (item.lista) {
                item.el.classList.add("sai");
                return new Promise(function (resolve) {
                    setTimeout(function () {
                        if (item.el && item.el.parentNode) item.el.parentNode.removeChild(item.el);
                        resolve();
                    }, 420);
                });
            }
            if (item.mesh) {
                item.saindo = true;
                var inicio = performance.now();
                var origem = new THREE.Vector3();
                item.mesh.getWorldPosition(origem);
                if (item.mesh.parent) this.scene.attach(item.mesh);
                var fundo = -(item.maxR + item.rb + 1.35);
                var destino = new THREE.Vector3(origem.x * 0.08, fundo, 0.35);
                return new Promise(function (resolve) {
                    function step(now) {
                        if (self.geracao !== g) { resolve(); return; }
                        var k = Math.min(1, (now - inicio) / 880);
                        var e = 1 - Math.pow(1 - k, 3);
                        item.mesh.position.lerpVectors(origem, destino, e);
                        item.mesh.scale.setScalar(1 + e * 0.7);
                        if (k < 1) requestAnimationFrame(step);
                        else {
                            item.mesh.visible = false;
                            resolve();
                        }
                    }
                    requestAnimationFrame(step);
                });
            }
            item.saindo = true;
            var el = item.el;
            var x0 = item.x, y0 = item.y;
            var t0 = performance.now();
            var fundo = (self.el.clientHeight || 520) - item.lado - 18;
            var centro = (self.el.clientWidth || 640) * 0.5;
            return new Promise(function (resolve) {
                function step(now) {
                    if (self.geracao !== g) { resolve(); return; }
                    var k = Math.min(1, (now - t0) / 700);
                    var e = 1 - Math.pow(1 - k, 3);
                    el.style.left = (x0 + (centro - x0) * e) + "px";
                    el.style.top = (y0 + (fundo - y0) * e) + "px";
                    el.style.transform = "scale(" + (1 + e * 0.45) + ")";
                    if (k < 1) requestAnimationFrame(step);
                    else {
                        el.style.visibility = "hidden";
                        resolve();
                    }
                }
                requestAnimationFrame(step);
            });
        }

        _loop(t) {
            var dt = Math.min(0.033, this._ultimo ? (t - this._ultimo) / 1000 : 0.016);
            this._ultimo = t;
            if (this.girando && this.modo === "3d" && this.root) {
                if (this.spinIndividual) {
                    this.root.children.forEach(function (ch) { ch.rotation.y += dt * 0.7; });
                } else {
                    this.root.rotation.y += dt * 2.2 * this.ritmo;
                }
                for (var i = 0; i < this.bolas.length; i++) {
                    var b = this.bolas[i];
                    if (!b.mesh) continue;
                    if (b.spin) {
                        b.mesh.rotation.x += b.spin.x * dt * this.ritmo;
                        b.mesh.rotation.y += b.spin.y * dt * this.ritmo;
                        b.mesh.rotation.z += b.spin.z * dt * this.ritmo;
                    }
                    if (b.saindo) continue;
                    b.mesh.position.addScaledVector(b.vel, dt * this.ritmo);
                    var len = b.mesh.position.length();
                    if (len > b.maxR) {
                        b.mesh.position.setLength(b.maxR);
                        var n = b.mesh.position.clone().normalize();
                        var vn = b.vel.dot(n);
                        if (vn > 0) b.vel.addScaledVector(n, -1.9 * vn);
                    }
                    b.vel.multiplyScalar(0.998);
                    if (b.vel.length() < 1.8) {
                        b.vel.x += (Math.random() - 0.5) * 1.6;
                        b.vel.y += (Math.random() - 0.5) * 1.6;
                        b.vel.z += (Math.random() - 0.5) * 1.6;
                    }
                }
            }
            if (this.girando && this.modo === "2d") {
                for (var j = 0; j < this.bolas.length; j++) {
                    var d = this.bolas[j];
                    if (!d.el || d.saindo || d.lista) continue;
                    var ritmo = this.ritmo || 1;
                    d.x += d.vx * dt * ritmo;
                    d.y += d.vy * dt * ritmo;
                    var dx = d.x - d.cx;
                    var dy = (d.y - d.cy) / 0.72;
                    if (dx * dx + dy * dy > d.alcance * d.alcance) {
                        var ang = Math.atan2(d.y - d.cy, d.x - d.cx);
                        d.vx = -Math.cos(ang) * (110 + Math.random() * 70);
                        d.vy = -Math.sin(ang) * (110 + Math.random() * 70);
                    }
                    d.ang += d.vang * dt * ritmo;
                    d.el.style.left = d.x + "px";
                    d.el.style.top = d.y + "px";
                    d.el.style.transform = "rotate(" + (d.ang * 180 / Math.PI) + "deg)";
                }
            }
            if (this.modo === "3d" && this.scene) this._syncNumeros();
            if (this.renderer && this.scene) this.renderer.render(this.scene, this.camera);
            requestAnimationFrame(this._loop);
        }
    }

    window.GloboCena = GloboCena;
})();
