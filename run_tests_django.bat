@echo off
title Django Test Runner + Mini Server (Port 7024)

:: Пути
set ROOT=E:\diplom_final_project\IT-WorkRu
set REPORT=%ROOT%\report.html
set HTMLCOV=%ROOT%\htmlcov
set PORT=7024

echo Переход в корень проекта...
cd /d %ROOT%

echo Активация виртуального окружения...
call .\platform_venv\Scripts\activate

echo Переход в директорию Django-приложения...
cd myplatform

echo Запуск тестов с отчётами...
pytest ../../tests --ds=myplatform.settings -v ^
--html="%REPORT%" --self-contained-html ^
--cov=. --cov-report=term-missing:skip-covered --cov-report=html:"%HTMLCOV%"

echo.
echo Проверка наличия HTML-отчётов...

if exist "%REPORT%" (
    echo HTML-отчёт найден: %REPORT%
) else (
    echo HTML-отчёт НЕ найден!
)

if exist "%HTMLCOV%\index.html" (
    echo Coverage-отчёт найден: %HTMLCOV%\index.html
) else (
    echo Coverage-отчёт НЕ найден!
)

echo.
echo Поднимаем мини-сервер на порту %PORT%...

:: Запуск мини-сервера Python в фоне
start "" python -m http.server %PORT% --directory "%ROOT%"

:: Открываем отчёты через локальный сервер
start "" "http://127.0.0.1:%PORT%\report.html"
start "" "http://127.0.0.1:%PORT%\htmlcov\index.html"

echo.
echo Мини-сервер запущен на порту %PORT%.
echo Для остановки сервера используйте Ctrl+C в окне Python или закройте процесс.
pause
