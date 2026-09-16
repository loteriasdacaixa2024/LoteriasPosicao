@echo off
set BASE=D:\Loterias\LoteriasExtras\estrategias
set VENV=D:\Loterias\LoteriasExtras\conferencias\venv-modalidades

echo [LotoCheck] Iniciando Central e Estrategias (Com Navegador)...

wt ^
new-tab --title "CENTRAL (8084)" cmd /k "color 0F && cd /d "%BASE%\Central-Estrategias" && set SKIP_CHILD_SERVICES=1 && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Lotofacil (5565)" cmd /k "color 5F && cd /d "%BASE%\lotofacil" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Dia de Sorte (5566)" cmd /k "color 6F && cd /d "%BASE%\diadesorte" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Quina (5567)" cmd /k "color 1F && cd /d "%BASE%\quina" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Mega-Sena (5568)" cmd /k "color 2F && cd /d "%BASE%\megasena" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Lotomania (5569)" cmd /k "color 6E && cd /d "%BASE%\lotomania" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Timemania (5570)" cmd /k "color E0 && cd /d "%BASE%\timemania" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Dupla Sena (5571)" cmd /k "color 4F && cd /d "%BASE%\duplasena" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Mais Milionaria (5572)" cmd /k "color 1B && cd /d "%BASE%\maismilionaria" && call "%VENV%\Scripts\activate" && python app.py" ; ^
new-tab --title "Super Sete (5573)" cmd /k "color A0 && cd /d "%BASE%\supersete" && call "%VENV%\Scripts\activate" && python app.py"

timeout /t 12 /nobreak >nul
start http://localhost:8084

echo Concluido! Verifique as abas do Windows Terminal e seu navegador.
