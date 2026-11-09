@echo off
REM ============================================================
REM  scripts\build.bat - Gera o executavel AnotacoesHospitalares.exe
REM  Pode ser executado com duplo clique (Windows).
REM
REM  Requer Python 3.10 ou superior instalado NESTE computador
REM  (o computador que vai USAR o programa nao precisa de Python).
REM
REM  Recursos (pasta assets\):
REM    icone.ico -> icone do executavel e da janela
REM    logo.png  -> (opcional) logotipo padrao da barra lateral
REM ============================================================

REM Vai para a raiz do repositorio (a pasta acima de "scripts")
cd /d "%~dp0.."

REM --- Localiza o Python (ignora o atalho falso da Microsoft Store) ---
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY goto sempython

echo Usando: %PY%
echo.
echo [1/3] Instalando dependencias...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements-dev.txt
if errorlevel 1 goto erro

echo.
echo [2/3] Gerando o executavel com PyInstaller...
set OPCOES=--noconfirm --clean --onefile --windowed --name "AnotacoesHospitalares" --collect-all customtkinter --hidden-import PIL._tkinter_finder
if exist assets\icone.ico set OPCOES=%OPCOES% --icon "assets\icone.ico" --add-data "assets\icone.ico;."
if exist assets\logo.png set OPCOES=%OPCOES% --add-data "assets\logo.png;."

%PY% -m PyInstaller %OPCOES% main.py
if errorlevel 1 goto erro

echo.
echo [3/3] Concluido!
echo O executavel esta em: dist\AnotacoesHospitalares.exe
echo O banco de dados sera criado na pasta "dados", ao lado do executavel.
pause
exit /b 0

:sempython
echo.
echo ERRO: Python nao encontrado neste computador.
echo Instale o Python em https://www.python.org/downloads/
echo marcando a opcao "Add Python to PATH" e execute este arquivo novamente.
echo (Nao instale pela Microsoft Store.)
pause
exit /b 1

:erro
echo.
echo ERRO: a compilacao falhou. Verifique as mensagens acima.
pause
exit /b 1
