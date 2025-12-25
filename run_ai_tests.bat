@echo off
@chcp 65001 >nul
title AI Tests Runner + Report Viewer (Port 7025)

set "ROOT_DIR=%~dp0"
set "CONFIG_FILE=%ROOT_DIR%config_ai_tests.ini"
set "TESTS_DIR=%ROOT_DIR%tests\ai_tests"

if not exist "%CONFIG_FILE%" (
    echo Не найден config_ai_tests.ini в %ROOT_DIR%
    pause
    exit /b 1
)

:: Чтение параметров из конфига
for /f "delims=" %%i in ('python "%ROOT_DIR%read_config.py" "%CONFIG_FILE%" report_html') do set "REPORT_FILE=%%i"
for /f "delims=" %%i in ('python "%ROOT_DIR%read_config.py" "%CONFIG_FILE%" server_port') do set "SERVER_PORT=%%i"

if "%REPORT_FILE%"=="" (
    echo Не удалось прочитать report_html из конфига.
    pause
    exit /b 1
)
if "%SERVER_PORT%"=="" (
    echo Не удалось прочитать server_port из конфига.
    pause
    exit /b 1
)

echo.
echo Конфигурация загружена.
echo Отчёт: %REPORT_FILE%
echo Порт:  %SERVER_PORT%
echo.

:: === Проверка виртуального окружения ===
set "VENV_ACTIVATE=%TESTS_DIR%\.ai_venv\Scripts\activate.bat"
if not exist "%VENV_ACTIVATE%" (
    echo Виртуальное окружение не найдено:
    echo     %VENV_ACTIVATE%
    echo Убедитесь, что .ai_venv создан в папке ai_tests.
    pause
    exit /b 1
)

:: === Проверка тестовых скриптов ===
if not exist "%TESTS_DIR%\yandex_speechkit_tts_test.py" (
    echo Не найден yandex_speechkit_tts_test.py
    pause
    exit /b 1
)

:: === Переход в папку тестов и активация окружения ===
cd /d "%TESTS_DIR%"
call "%VENV_ACTIVATE%"

:: === Запуск генератора отчёта (он сам знает, где брать скрипты) ===
python "%ROOT_DIR%generate_ai_report.py" "%CONFIG_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo Ошибка при генерации отчёта.
    pause
    exit /b 1
)

:: === Запуск сервера из корня (чтобы report.html был доступен) ===
cd /d "%ROOT_DIR%"
echo.
echo Запуск мини-сервера на порту %SERVER_PORT%...
:: start "AI Report Server" python -m http.server %SERVER_PORT% --directory "%ROOT_DIR%"
start "AI Report Server" python -m http.server 7025 --directory "E:\diplom_final_project"

timeout /t 2 >nul
start "" "http://127.0.0.1:%SERVER_PORT%/ai_test_report.html"

echo.
echo Отчёт готов и открыт в браузере.
echo.
pause