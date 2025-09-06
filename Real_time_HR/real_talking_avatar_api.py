'''from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import FileResponse
import os
import shutil
import subprocess
import librosa
from datetime import datetime
from dotenv import load_dotenv
from try_TTS_Yandex import text_to_audio  # Импортируем функцию синтеза речи
from try_generation_Yandex import generate_text  # Импортируем функцию генерации текста
from openai_whisper_STT import transcribe_wav_to_text  # Импортируем функцию распознавания речи
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import time  # Для измерения времени

# Убедитесь, что путь к FFmpeg указан
os.environ["PATH"] += os.pathsep + r"E:\ffmpeg-7.1-full_build\bin"

# Загрузка переменных окружения
load_dotenv()

# Пути к директориям
GREETINGS_TEMP = "GREETINGS_TEMP"
TEMP_INFERENCE = "TEMP_INFERENCE"
os.makedirs(GREETINGS_TEMP, exist_ok=True)
os.makedirs(TEMP_INFERENCE, exist_ok=True)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    #allow_origins=["http://127.0.0.1:8000"],  # или ["*"] для всех
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Кэш сессий
session_cache = set()
session_gender_map = {}
session_skills_map = {}
session_title_map = {}

# Хранение истории диалога по session_id
session_history_map = {}  # { session_id: [ {"user": "...", "ai": "..."}, ... ] }

# Счётчик вопросов по каждому навыку
session_skill_question_count_map = {}  # { session_id: { "skill1": 0, "skill2": 0 } }

import uuid

import requests
@app.post("/upload_video_link/")
async def upload_video_link(request: Request):
    data = await request.json()
    video_url = data.get("video_url")
    gender = data.get("gender")  # Получаем пол
    skills = data.get('skills')
    title = data.get('title')

    if not video_url:
        return {"status": "Ссылка на видео не предоставлена"}

    print(f"Получена ссылка: {video_url}")
    print(f"Пол: {gender}")
    print(f"Навыки: {skills}")
    print(f"Название вакансии: {title}")

    session_id = str(uuid.uuid4())
    session_gender_map[session_id] = gender
    session_skills_map[session_id] = skills
    session_title_map[session_id] = title

    video_file_path = os.path.join(GREETINGS_TEMP, f"uploaded_video_{session_id}.webm")

    try:
        response = requests.get("http://127.0.0.1:8000/" + video_url, stream=True)
        #response = requests.get("https://disruptively-trustful-oryx.cloudpub.ru/" + video_url, stream=True)
        response.raise_for_status()

        with open(video_file_path, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    video_file.write(chunk)

        print(f"Видео сохранено: {video_file_path}")
        # Передайте пол дальше (можно сохранить в БД, передать в очередь, или сразу использовать)
        return {
            "status": "Видео успешно загружено",
            "session_id": session_id,
            "gender": gender,  # Передаем обратно (если нужно)
            "skills": skills,
            "title": title
        }

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при скачивании видео: {e}")
        return {"status": "Ошибка при скачивании видео", "error": str(e)}


# Функция для замены аудиодорожки в видео
def replace_audio_in_video(template_video, new_audio, output_video):
    """
    Заменяет аудиодорожку в существующем видео.
    :param template_video: Путь к шаблонному видео.
    :param new_audio: Путь к новому аудиофайлу.
    :param output_video: Путь для сохранения результата.
    """
    command = (
        f'ffmpeg -i "{template_video}" -i "{new_audio}" '
        f'-c:v copy -map 0:v:0 -map 1:a:0 -shortest "{output_video}" -y'
    )
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"🎥 Видео с новым аудио создано: {output_video}")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке видео: {e}")

# Функция для изменения длительности видео под аудио
def adjust_video_duration(video_path, audio_path, output_video):
    """
    Изменяет длительность видео, чтобы она соответствовала длительности аудио.
    :param video_path: Путь к исходному видео.
    :param audio_path: Путь к аудиофайлу.
    :param output_video: Путь для сохранения результата.
    """
    # Получаем длительность аудио
    audio_duration = librosa.get_duration(path=audio_path)

    # Создаем команду FFmpeg для изменения длительности видео
    command = (
        f'ffmpeg -stream_loop -1 -i "{video_path}" -i "{audio_path}" '
        f'-c:v libvpx-vp9 -t {audio_duration} -c:a libopus "{output_video}" -y'
    )
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"🎬 Видео адаптировано под аудио: {output_video}")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при адаптации видео: {e}")

# Промпт для собеседования
interview_prompt = """
Ты проводишь интервью на позицию {title}.

Кандидат должен обладать следующими ключевыми навыками: {skills_list}

Сценарий интервью:
1. Поочередно задавай вопросы по каждому из перечисленных навыков.
2. Для каждого навыка:
   - Задай один основной вопрос.
   - Если ответ соискателя был полным, задай 1–2 коротких уточняющих вопроса.
   - После исчерпывающего диалога переходи к следующему навыку.
3. Отвечай кратко, ясно и профессионально. Используй естественную речь, как реальный HR или технический специалист.
4. Не повторяй вопросы. Не используй списки или маркированные пункты. Говори "по-человечески".

Пример:
Навык: Python
— Расскажите о вашем опыте использования Python?
— Какие фреймворки вы применяли?
— Есть ли у вас опыт оптимизации производительности на Python?

Первый вопрос должен быть:
Расскажите о вашем опыте работы с [первый навык]?

Если все навыки уже обсуждены:
— Благодарю за интервью. У вас были исчерпывающие ответы по всем ключевым навыкам. Мы свяжемся с вами в ближайшее время.

История предыдущих вопросов и ответов:
{history}
"""

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...),
    session_id: str = Form(...)):
    """
    Обрабатывает аудиофайл и возвращает видео.
    """
    try:
        start_time = time.time()  # Начало замера времени
        print("⏳ Начало обработки запроса...")

        # === Шаг 1: Сохранение загруженного аудио ===
        audio_file_path = os.path.join(GREETINGS_TEMP, "user_input.wav")
        with open(audio_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # === Шаг 2: Распознавание речи ===
        print("[STT] Распознавание речи...")
        user_text = transcribe_wav_to_text(audio_file_path)
        print(f"[STT] Распознанный текст: {user_text}")

        # === Шаг 3: Генерация ответа с помощью YandexGPT ===
        print("[AI] Генерация ответа...")
        skills = session_skills_map.get(session_id)
        title = session_title_map.get(session_id)

        #response_text = generate_text(skills + interview_prompt + user_text)

        if not skills:
            raise ValueError("Навыки для этой сессии не найдены")

            # Разделяем навыки на список
        skills_list = [s.strip() for s in skills.split(',') if s.strip()]
        if not skills_list:
            raise ValueError("Список навыков пуст")

        # Инициализируем историю и счётчики по навыкам
        if session_id not in session_history_map:
            session_history_map[session_id] = []

        if session_id not in session_skill_question_count_map:
            session_skill_question_count_map[session_id] = {skill: 0 for skill in skills_list}

        history = session_history_map[session_id]

        # Формируем историю для подстановки в промпт
        history_str = ""
        for entry in history:
            history_str += f"Вы: {entry['ai']}\n"
            history_str += f"Соискатель: {entry['user']}\n"

        # Подставляем данные в промпт
        filled_prompt = interview_prompt.format(
            title=title or "не указана",
            skills_list=", ".join(skills_list),
            history=history_str
        )

        # Генерируем ответ от AI
        response_text = generate_text(filled_prompt + "\n\n" + user_text)
        print(f"[AI] Сгенерированный ответ: {response_text}")

        # Сохраняем в историю
        history.append({"user": user_text, "ai": response_text})

        # Определяем, нужно ли увеличивать счётчик по текущему навыку
        # (упрощённая логика: последовательно проходим по навыкам)
        current_skill_index = len(history) % len(skills_list)
        current_skill = skills_list[current_skill_index]
        session_skill_question_count_map[session_id][current_skill] += 1

        # Проверяем, закончились ли вопросы
        total_questions_asked = sum(session_skill_question_count_map[session_id].values())
        max_questions_per_skill = 3  # 1 базовый + 2 уточняющих
        all_skills_covered = all(
            count >= max_questions_per_skill for count in session_skill_question_count_map[session_id].values()
        )

        if all_skills_covered:
            print("✅ Все навыки обсуждены. Интервью завершено.")
            response_text += "\n\nБлагодарю за интервью. Мы свяжемся с вами в ближайшее время."

        print(f"[AI] Сгенерированный ответ: {response_text}")

        # === Шаг 4: Синтез речи ===
        print("[TTS] Синтез речи...")
        # session_id = os.urandom(4).hex()
        audio_path = os.path.join(GREETINGS_TEMP, f"response_audio_{session_id}.ogg")

        #audio_bytes = text_to_audio(response_text, voice="zahar")  # Используем голос "zahar"
        gender = session_gender_map.get(session_id)
        voice = "zahar" if gender == "МУЖ" else "oksana"

        # Синтез речи с выбранным голосом
        audio_bytes = text_to_audio(response_text, voice=voice)



        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        print(f"[TTS] Аудио сохранено: {audio_path}")

        # === Шаг 5: Поиск шаблона видео ===
        # Поиск нужного шаблона видео по session_id
        video_filename = f"uploaded_video_{session_id}.webm"
        template_video = os.path.join(GREETINGS_TEMP, video_filename)
        if not os.path.exists(template_video):
            raise FileNotFoundError(f"Видео для сессии {session_id} не найдено: {template_video}")
        print(f"[VIDEO] Используется шаблонное видео: {template_video}")

        adjusted_video = os.path.join(GREETINGS_TEMP, f"adjusted_video_{session_id}.webm")
        adjust_video_duration(template_video, audio_path, adjusted_video)

        output_video = os.path.join(TEMP_INFERENCE, f"final_response_{session_id}.webm")
        replace_audio_in_video(adjusted_video, audio_path, output_video)

        print("✅ Готово! Итоговое видео: ", output_video)

        end_time = time.time()  # Конец замера времени
        total_time = end_time - start_time
        print(f"⏱️ Общее время выполнения: {total_time:.2f} секунд")

        # === Возвращаем видео как ответ ===
        return FileResponse(output_video, media_type="video/webm", filename="response_video.webm")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8101)'''

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import FileResponse
import os
import shutil
import subprocess
import librosa
import uuid
import time
import requests

# Импорты из ваших модулей
from try_TTS_Yandex import text_to_audio
from try_generation_Yandex import generate_text
from openai_whisper_STT import transcribe_wav_to_text

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Настройки ---
os.environ["PATH"] += os.pathsep + r"E:\ffmpeg-7.1-full_build\bin"
os.makedirs("GREETINGS_TEMP", exist_ok=True)
os.makedirs("TEMP_INFERENCE", exist_ok=True)

# --- Сессии ---
session_gender_map = {}
session_skills_map = {}
session_title_map = {}

# Хранение данных по сессиям
session_history_map = {}  # история диалога
session_base_questions_map = {}  # базовые вопросы
session_question_stage_map = {}  # этапы по навыкам (0=базовый, 1-3=уточнения)
session_skill_scores_map = {}  # оценки по каждому ответу
session_first_answer_map = {}  # флаг первого сообщения
session_completed_map = {}  # флаг завершения интервью
session_address_map = {}  # { session_id: "Иван Петрович" }
session_address_extracted_map = {}

# --- Промпты ---
BASE_QUESTIONS_PROMPT = """
Создайте по одному базовому вопросу для каждого из следующих навыков на позицию "{title}". Не проси написать код.
Навыки: {skills_list}
Формат вывода:
[навык]: [вопрос]
"""

CLARIFYING_QUESTION_PROMPT = """
На основе ответа "{answer}" на вопрос "{question}" по навыку "{skill}" сгенерируйте один уточняющий вопрос. Не проси написать код.
Требования:
- Вопрос должен быть коротким и точным
- Не повторять предыдущие вопросы
- Сфокусироваться на деталях ответа
"""

EVALUATION_PROMPT = """
Оцените ответ на вопрос "{question}" по шкале от 1 до 10.
Контекст навыка: {skill}
Ответ кандидата: {answer}
Формат ответа:
Оценка: [1-10]
Комментарий: [краткий анализ]
"""

EXTRACT_ADDRESS_PROMPT = """
Проанализируйте следующий текст и определите, как к человеку лучше обращаться.

Если имя или отчество указаны — используйте их.
Если не указаны — верните стандартное обращение, например: «Кандидат».

Примеры:
Текст: «Здравствуйте, меня зовут Иван Петрович Смирнов» → Ответ: «Иван Петрович»
Текст: «Привет! Я Максим» → Ответ: «Максим»
Текст: «Здравствуйте, готов начать» → Ответ: «Кандидат»

Текст: "{user_text}"

Ответ:
"""

import re


def clean_response_text(text):
    # Удаляем все ёлочки (« и ») из текста
    text = text.replace('«', '').replace('»', '')

    # Также можно убрать лишние пробелы после знаков препинания
    text = re.sub(r'\s+([.,!?])', r'\1', text)

    # Ищем индекс первой запятой
    comma_index = text.find(',')

    if comma_index != -1:
        # Часть до запятой оставляем как есть
        before_comma = text[:comma_index]

        # Часть после запятой приводим к нижнему регистру
        after_comma = text[comma_index:].lower()

        # Склеиваем обратно
        text = before_comma + after_comma
    else:
        # Если запятых нет — всё в нижнем регистре
        text = text.lower()

    # Делаем первую букву предложения заглавной
    if text:
        text = text[0].upper() + text[1:]

    # Убираем лишние пробелы в начале и конце
    text = text.strip()

    return text

@app.post("/upload_video_link/")
async def upload_video_link(request: Request):
    data = await request.json()
    video_url = data.get("video_url")
    gender = data.get("gender")
    skills = data.get("skills")
    title = data.get("title")
    interview_unique_link = data.get("interview_unique_link")

    print(f"Получена ссылка: {video_url}")
    print(f"Пол: {gender}")
    print(f"Навыки: {skills}")
    print(f"Название вакансии: {title}")

    if not video_url or not skills or not interview_unique_link:
        raise HTTPException(status_code=400, detail="Не переданы обязательные параметры")

    # session_id = str(uuid.uuid4())
    session_id = interview_unique_link
    session_gender_map[session_id] = gender
    session_skills_map[session_id] = skills
    session_title_map[session_id] = title
    session_first_answer_map[session_id] = True  # Добавлено

    # Сохраняем видео
    video_path = os.path.join("GREETINGS_TEMP", f"uploaded_video_{session_id}.webm")
    response = requests.get(f"http://127.0.0.1:8000/{video_url}", stream=True)
    with open(video_path, "wb") as f:
        for chunk in response.iter_content(1024):
            if chunk:
                f.write(chunk)

    # Генерируем базовые вопросы
    skills_list = [s.strip() for s in skills.split(',') if s.strip()]
    filled_prompt = BASE_QUESTIONS_PROMPT.format(title=title, skills_list=", ".join(skills_list))
    base_questions_text = generate_text(filled_prompt)

    # Парсим вопросы
    base_questions = {}
    for line in base_questions_text.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            skill = parts[0].strip()
            question = parts[1].strip()
            base_questions[skill] = question

    # Инициализируем данные сессии
    session_base_questions_map[session_id] = base_questions
    session_question_stage_map[session_id] = {skill: 0 for skill in base_questions}
    session_skill_scores_map[session_id] = {skill: [] for skill in base_questions}
    session_history_map[session_id] = []

    return {
        "status": "Видео успешно загружено",
        "session_id": session_id,
        "base_questions": base_questions
    }


def get_next_skill(session_id):
    stages = session_question_stage_map.get(session_id, {})
    for skill, stage in stages.items():
        if stage < 3:  # Теперь этапы: 0 (базовый), 1 (1-е уточнение), 2 (2-е уточнение)
            return skill
    return None


def evaluate_answer(session_id, skill, question, answer):
    filled_prompt = EVALUATION_PROMPT.format(question=question, skill=skill, answer=answer)
    evaluation_text = generate_text(filled_prompt)

    try:
        score_line = [line for line in evaluation_text.split("\n") if "Оценка:" in line][0]
        score_str = score_line.split(":")[1].strip()

        # Удаляем точку в конце, если она есть
        if score_str.endswith("."):
            score_str = score_str[:-1]

        score = int(score_str)
        session_skill_scores_map[session_id][skill].append(score)

        # Логирование оценки
        print(f"[ОЦЕНКА] {skill}: {score} | Ответ: {answer[:30]}...")
    except Exception as e:
        print(f"❌ Ошибка парсинга оценки: {e}")


@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...), session_id: str = Form(...)):
    if session_id in session_completed_map:
        raise HTTPException(status_code=400, detail="Интервью уже завершено")
    try:
        start_time = time.time()
        print("⏳ Начало обработки запроса...")

        # === Шаг 1: Сохранение аудио ===
        audio_file_path = os.path.join("GREETINGS_TEMP", "user_input.wav")
        with open(audio_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # === Шаг 2: Распознавание речи ===
        user_text = transcribe_wav_to_text(audio_file_path)
        print(f"[STT] Распознанный текст: {user_text}")

        # === Шаг 3: Ответ от AI ===
        if session_id not in session_base_questions_map:
            raise ValueError("Базовые вопросы не найдены для этой сессии")

        history = session_history_map[session_id]
        history.append({"user": user_text})

        is_first_answer = session_first_answer_map.get(session_id, False)

        # Это первый ответ — извлекаем обращение
        if is_first_answer:
            if session_address_map.get(session_id) is None:
                filled_prompt = EXTRACT_ADDRESS_PROMPT.format(user_text=user_text)
                address_response = generate_text(filled_prompt)
                address = address_response.strip()
                session_address_map[session_id] = address
                print(f"[INFO] Обращение установлено: {address}")

            # Помечаем, что первый ответ уже был
            session_first_answer_map[session_id] = True

        current_skill = get_next_skill(session_id)

        if not current_skill:
            address = session_address_map.get(session_id, "Кандидат")
            response_text = f"{address}, благодарю за интервью. Мы свяжемся с вами в ближайшее время."
            response_text = clean_response_text(response_text)
            history[-1]["ai"] = response_text

            session_completed_map[session_id] = True

            # Печать итоговых результатов
            scores = session_skill_scores_map[session_id]
            total_score = sum(sum(scores[skill]) for skill in scores)
            max_score = sum(10 * 3 for skill in scores)  # 3 оценки × 10 баллов
            percentage_score = (total_score / max_score) * 100

            print("\n📊 ИТОГОВАЯ ОЦЕНКА:")
            print(f"Общий балл: {total_score}/{max_score}")
            print(f"Процент соответствия: {percentage_score:.2f}%\n")

            for skill, skill_scores in scores.items():
                print(f"🔹 {skill}: {sum(skill_scores)} баллов")
                print(f"   Подробности: {skill_scores}")

        else:
            base_questions = session_base_questions_map[session_id]
            stages = session_question_stage_map[session_id]
            stage = stages[current_skill]

            if stage == 0:
                address = session_address_map.get(session_id, "Кандидат")
                response_text = f"{address}, {base_questions[current_skill]}"
                response_text = clean_response_text(response_text)
                evaluate_answer(session_id, current_skill, response_text, user_text)
                stages[current_skill] = 1
            elif stage in [1, 2, 3]:  # Теперь обрабатываем 3 этапа
                last_answer = user_text
                filled_prompt = CLARIFYING_QUESTION_PROMPT.format(
                    answer=last_answer,
                    question=base_questions[current_skill],
                    skill=current_skill
                )
                response_text = generate_text(filled_prompt)
                response_text = clean_response_text(response_text)
                evaluate_answer(session_id, current_skill, response_text, user_text)
                stages[current_skill] += 1
            else:
                response_text = "Перейдем к следующему навыку."
                stages[current_skill] = 3  # помечаем как завершённый

            history[-1]["ai"] = response_text
            session_history_map[session_id] = history
            session_question_stage_map[session_id] = stages

        # === Шаг 4: Синтез речи ===
        audio_path = os.path.join("GREETINGS_TEMP", f"response_audio_{session_id}.ogg")
        gender = session_gender_map.get(session_id)
        voice = "zahar" if gender == "МУЖ" else "oksana"
        audio_bytes = text_to_audio(response_text, voice=voice)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # === Шаг 5: Обработка видео ===
        video_filename = f"uploaded_video_{session_id}.webm"
        template_video = os.path.join("GREETINGS_TEMP", video_filename)
        adjusted_video = os.path.join("GREETINGS_TEMP", f"adjusted_video_{session_id}.webm")
        output_video = os.path.join("TEMP_INFERENCE", f"final_response_{session_id}.webm")

        adjust_video_duration(template_video, audio_path, adjusted_video)
        replace_audio_in_video(adjusted_video, audio_path, output_video)

        end_time = time.time()
        total_time = end_time - start_time
        print(f"⏱️ Общее время выполнения: {total_time:.2f} секунд")

        return FileResponse(output_video, media_type="video/webm", filename="response_video.webm")

    except Exception as e:
        print(f"❌ Ошибка в /process_audio/: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")


def adjust_video_duration(video_path, audio_path, output_video):
    audio_duration = librosa.get_duration(path=audio_path)
    command = (
        f'ffmpeg -stream_loop -1 -i "{video_path}" -i "{audio_path}" '
        f'-c:v libvpx-vp9 -t {audio_duration} -c:a libopus "{output_video}" -y'
    )
    subprocess.run(command, check=True, shell=True)


def replace_audio_in_video(template_video, new_audio, output_video):
    command = (
        f'ffmpeg -i "{template_video}" -i "{new_audio}" '
        f'-c:v copy -map 0:v:0 -map 1:a:0 -shortest "{output_video}" -y'
    )
    subprocess.run(command, check=True, shell=True)


@app.get("/get_results/{session_id}")
async def get_results(session_id: str):
    if session_id not in session_skill_scores_map:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    scores = session_skill_scores_map[session_id]
    history = session_history_map[session_id]
    total_score = sum(sum(scores[skill]) for skill in scores)
    max_score = sum(10 * 3 for skill in scores)  # 3 оценки × 10 баллов
    percentage_score = (total_score / max_score) * 100

    # Суммаризация ответов пользователя
    user_answers = [item["user"] for item in history if "user" in item]
    combined_user_answers = " ".join(user_answers)

    # Пример суммаризации через генерацию текста (можно улучшить с NLP)
    summarization_prompt = f"""
На основе следующих ответов кандидата сделайте краткую выжимку о том, какие технологии и инструменты он знает и в чём разбирается тезисно:
"{combined_user_answers}"
Не используй символы * и ** в ответе. Вместо символов * пиши нумерованными списками.
"""

    try:
        summary_text = generate_text(summarization_prompt)
    except:
        summary_text = "Не удалось сгенерировать суммаризацию."

    # Формируем полную историю диалога
    conversation_log = []
    for entry in history:
        if "user" in entry:
            conversation_log.append(f"Пользователь: {entry['user']}")
        if "ai" in entry:
            conversation_log.append(f"Бот: {entry['ai']}")

    return {
        "session_id": session_id,
        "scores_by_skill": scores,
        "percentage_match": f"{percentage_score:.2f}%",
        "summary": summary_text,
        "conversation_log": conversation_log
    }

@app.get("/current_question/{session_id}")
async def get_current_question(session_id: str):
    """
    Возвращает последний сгенерированный вопрос по session_id.
    """

    if session_id not in session_history_map:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    history = session_history_map[session_id]

    if not history:
        return {"question": "Нет активных вопросов"}

    last_ai_message = ""
    for entry in reversed(history):  # ищем последнее сообщение от AI
        if "ai" in entry:
            last_ai_message = entry["ai"]
            break

    if not last_ai_message or "Благодарю за интервью" in last_ai_message:
        return {"question": "Интервью завершено"}

    return {
        "question": clean_response_text(last_ai_message),
        "session_id": session_id
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8101)

