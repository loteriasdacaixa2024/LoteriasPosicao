# NSSM — Central 8083, Locais 8085, Bolões 8086

Arquivo de referência. **Não cria serviço.** Só copia os campos/comandos quando for instalar.

NSSM neste PC: `D:\Nssm-2.24_\win64\nssm.exe`  
Prompt: **Administrador**  
Python: use o `python.exe` do `venv` (não `pythonw.exe` — o log do NSSM fica vazio).

Não suba o `.bat` de iniciar **e** o serviço NSSM ao mesmo tempo na mesma porta.

Atalho:

```bat
set NSSM=D:\Nssm-2.24_\win64\nssm.exe
```

Pastas de log (criar antes do primeiro `nssm start`):

```bat
mkdir "d:\Loterias\LoteriasPosicao\logs"
mkdir "d:\Loterias\LoteriasLocaisDaSorte\instance\logs"
mkdir "d:\Loterias\LoteriasBoloesDaSorte\instance\logs"
```

O Nginx (`Proxy-Nginx`) é outro serviço. Ele só encaminha o caminho público para estas portas.

---

## Resumo

| Serviço (chave NSSM) | App | Porta local | URL local | URL pública |
|---|---|---|---|---|
| `AnalisePorPosicao_TodasModalidades` | Central modalidades | 8083 | http://localhost:8083/ | https://marciofernandomaia.com.br/centralmodalidades/ |
| `Central_LocaisDaSorte` | Locais da Sorte | 8085 (+ 5574) | http://localhost:8085/ | https://marciofernandomaia.com.br/centrallocaisdasorte/ |
| `Central_BoloesDaSorte` | Bolões da Sorte | 8086 (+ 5575) | http://localhost:8086/ | https://marciofernandomaia.com.br/centralbolaodasorte/ |

Locais: análise em http://localhost:5574/ → público `/centrallocaisdasorte/analise/`  
Bolões: análise em http://localhost:5575/boloes → público `/centralbolaodasorte/boloes/`  
Central 8083: as modalidades 5152–5160 sobem no mesmo processo (um serviço basta). No remoto elas entram por `/centralmodalidades/m/<modalidade>/`.

---

## 1. Análise Por Posição — todas as modalidades (8083)

Application Path: 		d:\Loterias\LoteriasPosicao\VenvLoterias\Scripts\python.exe  
Startup Directory:		d:\Loterias\LoteriasPosicao\AnalisePorPosicao-Central  
Arguments:				app.py  
Detail Display Name:    Análise Por Posição - Todas as modalidades  
Description:			Central modalidades — http://localhost:8083/ — /centralmodalidades/  
Startup type:			Automatic  
Input:					(vazio)  
Output: 				d:\Loterias\LoteriasPosicao\logs\stdout.log  
Error:					d:\Loterias\LoteriasPosicao\logs\stderr.log  

```bat
"%NSSM%" install AnalisePorPosicao_TodasModalidades "d:\Loterias\LoteriasPosicao\VenvLoterias\Scripts\python.exe" app.py
"%NSSM%" set AnalisePorPosicao_TodasModalidades AppDirectory "d:\Loterias\LoteriasPosicao\AnalisePorPosicao-Central"
"%NSSM%" set AnalisePorPosicao_TodasModalidades DisplayName "Análise Por Posição - Todas as modalidades"
"%NSSM%" set AnalisePorPosicao_TodasModalidades Description "Central modalidades — http://localhost:8083/ — https://marciofernandomaia.com.br/centralmodalidades/"
"%NSSM%" set AnalisePorPosicao_TodasModalidades Start SERVICE_AUTO_START
"%NSSM%" set AnalisePorPosicao_TodasModalidades AppStdout "d:\Loterias\LoteriasPosicao\logs\stdout.log"
"%NSSM%" set AnalisePorPosicao_TodasModalidades AppStderr "d:\Loterias\LoteriasPosicao\logs\stderr.log"
"%NSSM%" set AnalisePorPosicao_TodasModalidades AppRotateFiles 1
"%NSSM%" set AnalisePorPosicao_TodasModalidades AppRotateBytes 1048576
```

Local: http://localhost:8083/  
Público: https://marciofernandomaia.com.br/centralmodalidades/

---

## 2. Central Locais da Sorte (8085)

Application Path: 		d:\Loterias\LoteriasLocaisDaSorte\venv\Scripts\python.exe  
Startup Directory:		d:\Loterias\LoteriasLocaisDaSorte  
Arguments:				servidor.py  
Detail Display Name:    Central Locais da Sorte  
Description:			Central Locais da Sorte — http://localhost:8085/ — /centrallocaisdasorte/  
Startup type:			Automatic  
Input:					(vazio)  
Output: 				d:\Loterias\LoteriasLocaisDaSorte\instance\logs\stdout.log  
Error:					d:\Loterias\LoteriasLocaisDaSorte\instance\logs\stderr.log  

`servidor.py` sobe 8085 (central) e 5574 (análise) no mesmo processo — igual ao `Iniciar_LocaisDaSorte_Central.bat`.

```bat
"%NSSM%" install Central_LocaisDaSorte "d:\Loterias\LoteriasLocaisDaSorte\venv\Scripts\python.exe" servidor.py
"%NSSM%" set Central_LocaisDaSorte AppDirectory "d:\Loterias\LoteriasLocaisDaSorte"
"%NSSM%" set Central_LocaisDaSorte DisplayName "Central Locais da Sorte"
"%NSSM%" set Central_LocaisDaSorte Description "Central Locais da Sorte — http://localhost:8085/ — https://marciofernandomaia.com.br/centrallocaisdasorte/"
"%NSSM%" set Central_LocaisDaSorte Start SERVICE_AUTO_START
"%NSSM%" set Central_LocaisDaSorte AppEnvironmentExtra LOCAIS_SORTE_SILENCIOSO=1
"%NSSM%" set Central_LocaisDaSorte AppStdout "d:\Loterias\LoteriasLocaisDaSorte\instance\logs\stdout.log"
"%NSSM%" set Central_LocaisDaSorte AppStderr "d:\Loterias\LoteriasLocaisDaSorte\instance\logs\stderr.log"
"%NSSM%" set Central_LocaisDaSorte AppRotateFiles 1
"%NSSM%" set Central_LocaisDaSorte AppRotateBytes 1048576
```

Local: http://localhost:8085/  ·  http://localhost:5574/  
Público: https://marciofernandomaia.com.br/centrallocaisdasorte/  
Análise pública: https://marciofernandomaia.com.br/centrallocaisdasorte/analise/

---

## 3. Central Bolões da Sorte (8086)

Application Path: 		d:\Loterias\LoteriasBoloesDaSorte\venv\Scripts\python.exe  
Startup Directory:		d:\Loterias\LoteriasBoloesDaSorte  
Arguments:				servidor.py  
Detail Display Name:    Central Bolões da Sorte  
Description:			Central Bolões da Sorte — http://localhost:8086/ — /centralbolaodasorte/  
Startup type:			Automatic  
Input:					(vazio)  
Output: 				d:\Loterias\LoteriasBoloesDaSorte\instance\logs\stdout.log  
Error:					d:\Loterias\LoteriasBoloesDaSorte\instance\logs\stderr.log  

`servidor.py` sobe 8086 (central) e 5575 (análise/bolões) no mesmo processo — igual ao `Iniciar_BoloesDaSorte_Central.bat`.

```bat
"%NSSM%" install Central_BoloesDaSorte "d:\Loterias\LoteriasBoloesDaSorte\venv\Scripts\python.exe" servidor.py
"%NSSM%" set Central_BoloesDaSorte AppDirectory "d:\Loterias\LoteriasBoloesDaSorte"
"%NSSM%" set Central_BoloesDaSorte DisplayName "Central Bolões da Sorte"
"%NSSM%" set Central_BoloesDaSorte Description "Central Bolões da Sorte — http://localhost:8086/ — https://marciofernandomaia.com.br/centralbolaodasorte/"
"%NSSM%" set Central_BoloesDaSorte Start SERVICE_AUTO_START
"%NSSM%" set Central_BoloesDaSorte AppEnvironmentExtra BOLOES_SORTE_SILENCIOSO=1
"%NSSM%" set Central_BoloesDaSorte AppStdout "d:\Loterias\LoteriasBoloesDaSorte\instance\logs\stdout.log"
"%NSSM%" set Central_BoloesDaSorte AppStderr "d:\Loterias\LoteriasBoloesDaSorte\instance\logs\stderr.log"
"%NSSM%" set Central_BoloesDaSorte AppRotateFiles 1
"%NSSM%" set Central_BoloesDaSorte AppRotateBytes 1048576
```

Local: http://localhost:8086/  ·  http://localhost:5575/boloes  
Público: https://marciofernandomaia.com.br/centralbolaodasorte/  
Bolões públicos: https://marciofernandomaia.com.br/centralbolaodasorte/boloes/

---

## Depois de instalar (quando for a hora)

```bat
"%NSSM%" start AnalisePorPosicao_TodasModalidades
"%NSSM%" start Central_LocaisDaSorte
"%NSSM%" start Central_BoloesDaSorte

sc query AnalisePorPosicao_TodasModalidades
sc query Central_LocaisDaSorte
sc query Central_BoloesDaSorte
```

Parar:

```bat
"%NSSM%" stop AnalisePorPosicao_TodasModalidades
"%NSSM%" stop Central_LocaisDaSorte
"%NSSM%" stop Central_BoloesDaSorte
```

Remover (só para reinstalar):

```bat
"%NSSM%" stop NOME_DO_SERVICO
"%NSSM%" remove NOME_DO_SERVICO confirm
```

Tela gráfica (mesmos campos do `nssm.txt`):

```bat
"%NSSM%" edit NOME_DO_SERVICO
```

No crash o NSSM já reinicia por padrão (`AppExit` = Restart).
