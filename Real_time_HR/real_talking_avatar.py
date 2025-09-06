'''import os
import subprocess
import librosa
from datetime import datetime
from dotenv import load_dotenv
from try_TTS_Yandex import text_to_audio  # Импортируем функцию синтеза речи
from try_generation_Yandex import generate_text  # Импортируем функцию генерации текста
from openai_whisper_STT import transcribe_wav_to_text  # Импортируем функцию распознавания речи
import sounddevice as sd
from scipy.io.wavfile import write

# Убедитесь, что путь к FFmpeg указан
os.environ["PATH"] += os.pathsep + r"E:\ffmpeg-7.1-full_build\bin"

# Загрузка переменных окружения
load_dotenv()

# Пути к директориям
GREETINGS_TEMP = "GREETINGS_TEMP"
TEMP_INFERENCE = "TEMP_INFERENCE"
os.makedirs(GREETINGS_TEMP, exist_ok=True)
os.makedirs(TEMP_INFERENCE, exist_ok=True)

# Функция для записи аудио
def record_audio(output_path, duration=10, sample_rate=44100):
    print("🎤 Начните говорить...")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    write(output_path, sample_rate, audio)
    print(f"🎧 Аудио записано: {output_path}")

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
        print(f"❌ Ошибка при обработке видео: {e}")

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
        print(f"❌ Ошибка при адаптации видео: {e}")

def process_user_input():
    """
    Основная функция для обработки пользовательского ввода и создания видеоответа.
    """
    # === Шаг 1: Запись аудио ===
    audio_file = os.path.join(GREETINGS_TEMP, "user_input.wav")
    record_audio(audio_file)

    # === Шаг 2: Распознавание речи ===
    print("[STT] Распознавание речи...")
    user_text = transcribe_wav_to_text(audio_file)  # Используем функцию распознавания речи
    print(f"[STT] Распознанный текст: {user_text}")

    # === Шаг 3: Генерация ответа с помощью YandexGPT ===
    print("[AI] Генерация ответа...")
    response_text = generate_text(user_text)  # Используем YandexGPT
    print(f"[AI] Сгенерированный ответ: {response_text}")

    # === Шаг 4: Синтез речи ===
    print("[TTS] Синтез речи...")
    session_id = os.urandom(4).hex()
    audio_path = os.path.join(GREETINGS_TEMP, f"response_audio_{session_id}.ogg")
    audio_bytes = text_to_audio(response_text, voice="zahar")  # Используем голос "zahar"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    print(f"[TTS] Аудио сохранено: {audio_path}")

    # === Шаг 5: Поиск шаблона видео ===
    template_videos = [f for f in os.listdir(GREETINGS_TEMP) if f.endswith(".webm")]
    if not template_videos:
        raise FileNotFoundError(f"Шаблонное видео не найдено в папке: {GREETINGS_TEMP}")

    # Берем первый найденный шаблон
    template_video_name = template_videos[0]
    template_video = os.path.join(GREETINGS_TEMP, template_video_name)
    print(f"[VIDEO] Используется шаблонное видео: {template_video}")

    # === Шаг 6: Адаптация видео под новую аудиодорожку ===
    adjusted_video = os.path.join(GREETINGS_TEMP, f"adjusted_video_{session_id}.webm")
    adjust_video_duration(template_video, audio_path, adjusted_video)

    # === Шаг 7: Замена аудиодорожки ===
    output_video = os.path.join(TEMP_INFERENCE, f"final_response_{session_id}.webm")
    replace_audio_in_video(adjusted_video, audio_path, output_video)

    # === Очистка временных файлов ===
    # Здесь больше нет удаления файлов, так как они нужны для дальнейшего использования
    print("⚠️ Временные файлы сохранены для последующего использования.")

    return output_video

if __name__ == "__main__":
    try:
        video_path = process_user_input()
        print(f"✅ Готово! Итоговое видео: {video_path}")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
'''
import numpy as np
import os
import subprocess
import librosa
from datetime import datetime
from dotenv import load_dotenv
from try_TTS_Yandex import text_to_audio  # Импортируем функцию синтеза речи
from try_generation_Yandex import generate_text  # Импортируем функцию генерации текста
from openai_whisper_STT import transcribe_wav_to_text  # Импортируем функцию распознавания речи
import sounddevice as sd
from scipy.io.wavfile import write
import time  # Добавляем модуль для замера времени

# Убедитесь, что путь к FFmpeg указан
os.environ["PATH"] += os.pathsep + r"E:\ffmpeg-7.1-full_build\bin"

# Загрузка переменных окружения
load_dotenv()

# Пути к директориям
GREETINGS_TEMP = "GREETINGS_TEMP"
TEMP_INFERENCE = "TEMP_INFERENCE"
os.makedirs(GREETINGS_TEMP, exist_ok=True)
os.makedirs(TEMP_INFERENCE, exist_ok=True)

# Функция для записи аудио
import os
import sounddevice as sd
from scipy.io.wavfile import write


def record_audio(output_path, sample_rate=44100):
    """
    Записывает аудио до тех пор, пока пользователь не нажмет Enter.
    :param output_path: Путь для сохранения записанного аудио.
    :param sample_rate: Частота дискретизации (по умолчанию 44100 Гц).
    """
    print("🎤 Начните говорить... Для остановки записи нажмите Enter в консоли.")

    # Создаем пустой список для хранения аудиоданных
    audio_frames = []

    # Функция обратного вызова для записи аудио в реальном времени
    def callback(indata, frames, time, status):
        if status:
            print(f"⚠️ Ошибка записи: {status}")
        audio_frames.append(indata.copy())  # Добавляем данные в буфер

    # Начинаем потоковую запись
    with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
        input("🎧 Нажмите Enter для остановки записи...\n")

    # Объединяем все фрагменты аудио в один массив
    audio_data = np.concatenate(audio_frames, axis=0)

    # Сохраняем записанное аудио в файл
    write(output_path, sample_rate, audio_data)
    print(f"🎧 Аудио записано: {output_path}")

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
        print(f"❌ Ошибка при обработке видео: {e}")

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
        print(f"❌ Ошибка при адаптации видео: {e}")

def process_user_input():
    """
    Основная функция для обработки пользовательского ввода и создания видеоответа.
    """

    # === Шаг 1: Запись аудио ===
    audio_file = os.path.join(GREETINGS_TEMP, "user_input.wav")
    record_audio(audio_file)

    # === Шаг 2: Распознавание речи ===
    start_time = time.time()  # Начало замера времени
    print("[STT] Распознавание речи...")
    user_text = transcribe_wav_to_text(audio_file)  # Используем функцию распознавания речи
    stt_end_time = time.time()  # Конец замера времени для STT
    print(f"[STT] Распознанный текст: {user_text}")

    # === Шаг 3: Генерация ответа с помощью YandexGPT ===
    ai_start_time = time.time()  # Начало замера времени для AI
    print("[AI] Генерация ответа...")
    response_text = generate_text(user_text)  # Используем YandexGPT
    ai_end_time = time.time()  # Конец замера времени для AI
    print(f"[AI] Сгенерированный ответ: {response_text}")
    print(f"[⏱️] Время генерации текста: {ai_end_time - ai_start_time:.2f} секунд")

    # === Шаг 4: Синтез речи ===
    tts_start_time = time.time()  # Начало замера времени для TTS
    print("[TTS] Синтез речи...")
    session_id = os.urandom(4).hex()
    audio_path = os.path.join(GREETINGS_TEMP, f"response_audio_{session_id}.ogg")
    audio_bytes = text_to_audio(response_text, voice="zahar")  # Используем голос "zahar"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    tts_end_time = time.time()  # Конец замера времени для TTS
    print(f"[TTS] Аудио сохранено: {audio_path}")
    print(f"[⏱️] Время синтеза речи: {tts_end_time - tts_start_time:.2f} секунд")

    # === Шаг 5: Поиск шаблона видео ===
    template_videos = [f for f in os.listdir(GREETINGS_TEMP) if f.endswith(".webm")]
    if not template_videos:
        raise FileNotFoundError(f"Шаблонное видео не найдено в папке: {GREETINGS_TEMP}")

    # Берем первый найденный шаблон
    template_video_name = template_videos[0]
    template_video = os.path.join(GREETINGS_TEMP, template_video_name)
    print(f"[VIDEO] Используется шаблонное видео: {template_video}")

    # === Шаг 6: Адаптация видео под новую аудиодорожку ===
    adjusted_video = os.path.join(GREETINGS_TEMP, f"adjusted_video_{session_id}.webm")
    adjust_video_duration(template_video, audio_path, adjusted_video)

    # === Шаг 7: Замена аудиодорожки ===
    output_video = os.path.join(TEMP_INFERENCE, f"final_response_{session_id}.webm")
    replace_audio_in_video(adjusted_video, audio_path, output_video)

    # === Общее время выполнения ===
    end_time = time.time()  # Конец замера времени
    total_time = end_time - start_time
    print(f"[⏱️] Общее время выполнения: {total_time:.2f} секунд")

    return output_video

if __name__ == "__main__":
    try:
        video_path = process_user_input()
        print(f"✅ Готово! Итоговое видео: {video_path}")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")