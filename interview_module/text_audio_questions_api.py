import os
import json
import shutil
import subprocess
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, List
from generation_first import generate_interview_questions
from Yandex_TTS import text_to_audio
from openai_whisper_STT import transcribe_audio
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
from pydantic import BaseModel, validator
from pathlib import Path
import base64
import re

TEMP_AUDIO_DIR = "TEMP_AUDIO"
TEMP_VIDEO_DIR = "TEMP_VIDEO"
TEMP_FINAL_VIDEO_DIR = "TEMP_FINAL_VIDEO"
TEMP_IMAGE_DIR = 'TEMP_IMAGE'
SPEAKERS_PHOTOS_DEFAULT = 'speakers_photos_default'

# Очистка временных директорий
def clear_temp_dirs():
    # Очистка всех временных папок
    # for dir_path in [TEMP_AUDIO_DIR, TEMP_VIDEO_DIR, TEMP_FINAL_VIDEO_DIR, TEMP_IMAGE_DIR]:
    for dir_path in [TEMP_AUDIO_DIR, TEMP_VIDEO_DIR, TEMP_IMAGE_DIR]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path, exist_ok=True)

clear_temp_dirs()  # Очистить директории сразу при старте

app = FastAPI()
from fastapi.staticfiles import StaticFiles
app.mount("/static/videos", StaticFiles(directory=TEMP_FINAL_VIDEO_DIR), name="videos")

# Разрешаем CORS для определенных доменов (например, для 127.0.0.1:8000)
app.add_middleware(
    CORSMiddleware,
    #allow_origins=["http://127.0.0.1:8000"],  # Разрешаем запросы только с этого источника
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы HTTP
    allow_headers=["*"],  # Разрешаем все заголовки
)

from fastapi import HTTPException
import mimetypes

# Разрешенные MIME-типы и расширения
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

class Gender(str, Enum):
    female = "ЖЕН"
    male = "МУЖ"

class PriorityQuestions(BaseModel):
    questions: List[str]

from typing import Optional
import base64
import uuid

@app.post("/generate_interview/")
async def interview_pipeline(
    position: str = Form(..., description="Название вакансии (должность, на которую претендует соискатель)"),
    skills: str = Form(..., description="Навыки, которыми должен обладать соискатель, через запятую"),
    gender: Gender = Form(..., description="Пол HR-агента"),
    image: Optional[str] = Form("", description="Полный путь к фотографии HR-агента (формат .png, .jpg или .webp)"),
    priority_questions: str = Form("", description="Список приоритетных вопросов в формате JSON")
):
    """API-пайплайн: генерация вопросов, их редактирование и озвучка."""

    # Обработка приоритетных вопросов
    if priority_questions:
        try:
            priority_questions_obj = PriorityQuestions.model_validate_json(priority_questions)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Неверный формат данных для 'priority_questions': {str(e)}")
    else:
        # Если приоритетные вопросы не указаны, используем пустой список
        priority_questions_obj = PriorityQuestions(questions=[])

    # Очистка временной папки перед запуском сервиса
    clear_temp_dirs()

    unique_id = str(uuid.uuid4())
    session_dir = os.path.join(TEMP_FINAL_VIDEO_DIR, unique_id)
    os.makedirs(session_dir, exist_ok=True)

    '''
    # Обработка изображения
    if not image or image.strip() == "":
        # Если изображение не указано, выбираем фото по умолчанию в зависимости от пола
        default_image_name = "speaker_woman.jpg" if gender == Gender.female else "speaker_man.jpg"
        default_image_path = Path(SPEAKERS_PHOTOS_DEFAULT) / default_image_name

        # Копируем фото по умолчанию во временную папку
        image_path = os.path.join(TEMP_IMAGE_DIR, default_image_name)
        shutil.copy(default_image_path, image_path)
    else:
        # Проверяем расширение файла
        file_extension = os.path.splitext(image)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимое расширение файла. Разрешены только: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Проверяем, существует ли файл по указанному пути
        if not os.path.isfile(image):
            raise HTTPException(
                status_code=400,
                detail=f"Файл по указанному пути не существует: {image}"
            )

        # Проверяем MIME-тип файла
        mime_type, _ = mimetypes.guess_type(image)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый MIME-тип файла. Разрешены только: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        # Дополнительная проверка содержимого файла
        with open(image, "rb") as file:
            header = file.read(12)  # Читаем первые 12 байт файла
            if not header.startswith((b"\xFF\xD8", b"\x89PNG", b"RIFF", b"WEBP")):
                raise HTTPException(
                    status_code=400,
                    detail="Файл не является корректным изображением (JPEG, PNG или WEBP)."
                )

        # Копируем файл во временную папку
        image_path = os.path.join(TEMP_IMAGE_DIR, os.path.basename(image))
        shutil.copy(image, image_path)
    '''

    # Обработка изображения
    if not image or image.strip() == "":
        default_image_name = "speaker_woman.jpg" if gender == Gender.female else "speaker_man.jpg"
        default_image_path = Path(SPEAKERS_PHOTOS_DEFAULT) / default_image_name
        image_path = os.path.join(TEMP_IMAGE_DIR, default_image_name)
        shutil.copy(default_image_path, image_path)

    elif image.startswith("data:image"):  # Работаем с base64
        try:
            match = re.match(r"data:image/(?P<ext>\w+);base64,(?P<data>.+)", image)
            if not match:
                raise ValueError("Невалидная base64-строка")

            ext = match.group("ext").lower()
            if f".{ext}" not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Недопустимое расширение файла: .{ext}")

            image_data = base64.b64decode(match.group("data"))
            image_path = os.path.join(TEMP_IMAGE_DIR, f"uploaded_image.{ext}")

            with open(image_path, "wb") as f:
                f.write(image_data)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка при декодировании изображения: {str(e)}")

    else:  # Работаем с обычным путём
        file_extension = os.path.splitext(image)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Недопустимое расширение файла: {file_extension}")

        if not os.path.isfile(image):
            raise HTTPException(status_code=400, detail=f"Файл не существует: {image}")

        mime_type, _ = mimetypes.guess_type(image)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Недопустимый MIME-тип: {mime_type}")

        with open(image, "rb") as file:
            header = file.read(12)
            if not header.startswith((b"\xFF\xD8", b"\x89PNG", b"RIFF", b"WEBP")):
                raise HTTPException(status_code=400, detail="Файл не является корректным изображением")

        image_path = os.path.join(TEMP_IMAGE_DIR, os.path.basename(image))
        shutil.copy(image, image_path)

    # Шаг 1: Подсчет количества приоритетных вопросов
    num_priority_questions = len(priority_questions_obj.questions)
    remaining_questions = max(0, 15 - num_priority_questions)  # Оставшееся количество вопросов для генерации

    # Генерация вопросов
    # generated_questions = generate_interview_questions(position, skills, remaining_questions)
    generated_questions = {
        "question": f"Здравствуйте! Я ваш виртуальный HR-ассистент. Сегодня поговорим о вашем опыте и навыках, чтобы лучше понять, как они соотносятся с требованиями на позицию {position.lower()}. Как могу к вам обращаться?"
        #"question": f"Здравствуйте!"

    }

    # Если предоставлены приоритетные вопросы, добавляем их в конец списка
    all_questions = {str(i + 1): q for i, q in enumerate(generated_questions.values())}
    all_questions.update(
        {str(i + len(generated_questions) + 1): q for i, q in enumerate(priority_questions_obj.questions)}
    )

    # Шаг 2: Создание аудиофайлов с учетом пола говорящего
    audio_files = generate_audio(all_questions, gender)

    for item in os.listdir(TEMP_FINAL_VIDEO_DIR):
        item_path = os.path.join(TEMP_FINAL_VIDEO_DIR, item)
        if os.path.isfile(item_path):
            os.remove(item_path)

    # Шаг 3: Запуск скриптов для анимации и конвертации
    generate_videos(image_path)  # Передаем путь к изображению

    default_output_dir = os.path.join(TEMP_FINAL_VIDEO_DIR)  # Это твоя папка типа static/videos/

    for filename in os.listdir(default_output_dir):
        if filename.endswith(".webm"):
            src_path = os.path.join(default_output_dir, filename)
            dst_path = os.path.join(session_dir, filename)
            shutil.copy2(src_path, dst_path)

    # Формирование ответа с видео
    response = {
        "original_questions": all_questions,
        "video_files": []
    }
    '''
    # Добавляем файлы видео в ответ
    for num in range(1, len(audio_files) + 1):
        video_file_path = os.path.join(TEMP_FINAL_VIDEO_DIR, f"question_{num}.webm")
        response["video_files"].append(FileResponse(video_file_path, media_type="video/webm", filename=f"question_{num}.webm"))
    
    for num in range(1, len(audio_files) + 1):
        video_url = f"http://127.0.0.1:8122/static/videos/question_{num}.webm"
        response["video_files"].append(video_url)
    '''
    for filename in os.listdir(session_dir):
        if filename.endswith(".webm"):
            video_url = f"http://127.0.0.1:8122/static/videos/{unique_id}/{filename}"
            response["video_files"].append(video_url)

    return response


def generate_audio(questions: dict, gender: Gender) -> Dict[str, str]:
    audio_files = {}
    voice = "zahar" if gender == Gender.male else "oksana"

    for num, question in questions.items():
        audio = text_to_audio(question, voice)
        if not audio:
            continue

        audio_file_path = os.path.join(TEMP_AUDIO_DIR, f"question_{num}.wav")
        with open(audio_file_path, 'wb') as f:
            f.write(audio)

        audio_files[num] = audio_file_path

    return audio_files


def generate_videos(image_path: str):
    # Запускаем скрипт для анимации с переданным изображением
    subprocess.run(["python", "SadTalker_Person_Animation.py", "--image_path", image_path])

    # Запускаем скрипт для конвертации в видео
    subprocess.run(["python", "convertate.py"])


@app.post("/transcribe_wav/")
async def transcribe_wav(file: UploadFile = File(...)):
    """Роут для получения аудиофайла .wav и возврата текста."""

    # Сохраняем загруженный файл во временную папку
    audio_path = os.path.join(TEMP_AUDIO_DIR, file.filename)
    with open(audio_path, "wb") as f:
        f.write(await file.read())

    # Получаем транскрипцию с помощью функции из openai-whisper_STT.py
    text = transcribe_audio(audio_path)

    # Удаляем файл после обработки
    os.remove(audio_path)

    # Возвращаем текст
    return {"transcribed_text": text}

from interview_analyzing import analyze_interview

# Роут для анализа интервью
@app.post("/analyze_interview/")
async def analyze_interview_route(
    position: str = Form(..., description="Название вакансии (должность, на которую претендует соискатель)"),
    skills: str = Form(..., description="Навыки, которыми должен обладать соискатель, через запятую"),
    interview_data: str = Form(..., description="Данные интервью в формате JSON")
):
    """
    Роут для анализа ответов соискателя на вопросы интервью.
    Принимает данные в формате Form:
    - position: Должность кандидата.
    - skills: Список навыков через запятую.
    - interview_data: JSON-строка с вопросами и ответами интервью.
    Возвращает оценки по каждому навыку в формате JSON.
    """
    try:
        # Парсим JSON из строки interview_data
        try:
            interview_content = json.loads(interview_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Некорректный формат JSON в данных интервью")

        # Проверяем структуру JSON
        if "questions" not in interview_content or "answers" not in interview_content:
            raise HTTPException(status_code=400, detail="JSON должен содержать поля 'questions' и 'answers'")

        # Вызываем функцию analyze_interview для анализа данных
        result = analyze_interview(position, skills, interview_content, retry_attempts=2)

        # Возвращаем результат анализа
        return {"analysis_result": result}

    except Exception as e:
        # Логируем ошибку и возвращаем HTTP 500
        print(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при анализе интервью")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8122)