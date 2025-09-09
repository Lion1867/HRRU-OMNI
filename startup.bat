@echo off
echo Запуск всех сервисов...

:: Django
start "Django Server" cmd /k "cd /d E:\diplom_final_project\IT-WorkRu\myplatform && E:\diplom_final_project\IT-WorkRu\platform_venv\Scripts\python.exe manage.py runserver"

:: Text/Audio API
start "Text Audio API" cmd /k "cd /d E:\diplom_final_project\interview_module && E:\diplom_final_project\interview_module\.venv\Scripts\python.exe text_audio_questions_api.py"

:: Talking Avatar API
start "Real Time HR" cmd /k "cd /d E:\diplom_final_project\Real_time_HR && E:\diplom_final_project\Real_time_HR\.venv\Scripts\python.exe real_talking_avatar_api.py"

:: Parsing Resume API
start "Parsing LLM" cmd /k "cd /d E:\diplom_final_project\parsing_llm && E:\diplom_final_project\parsing_llm\.venv\Scripts\python.exe api_parsing.py"

echo Все сервисы запущены.
exit
