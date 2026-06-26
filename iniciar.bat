@echo off
title Downfy Server
echo Iniciando o servidor do Downfy...
start http://127.0.0.1:8000
python -m uvicorn main:app --port 8000
pause
