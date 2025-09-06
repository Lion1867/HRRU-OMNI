import os
import shutil
import glob
from datetime import datetime
from try_TTS_Yandex import text_to_audio
from SadTalker_Person_Animation import process_audio_with_sadtalker, convert_mp4_to_webm
import time  # Импортируем модуль time для измерения времени

def generate_talking_head_video(image_path: str, gender: str, text: str) -> str:
    # === Начало измерения времени ===
    start_time = time.time()  # Засекаем начало выполнения

    # === Генерация уникальных путей ===
    temp_dir = "GREETINGS_TEMP"
    os.makedirs(temp_dir, exist_ok=True)
    session_id = os.urandom(4).hex()  # Случайный ID для файлов

    # === Синтез аудио ===
    audio_path = os.path.join(temp_dir, f"audio_{session_id}.ogg")
    print(f"[TTS] Синтез речи голосом '{gender}'...")
    audio_bytes = text_to_audio(text, "zahar" if gender == "male" else "oksana")
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    print(f"[TTS] Аудио сохранено: {audio_path}")

    # === Генерация видео ===
    video_mp4_path = os.path.join(temp_dir, f"video_{session_id}.mp4")
    print("[SadTalker] Создание анимации...")
    process_audio_with_sadtalker(audio_path, image_path, video_mp4_path)

    # === Поиск сгенерированного видео ===
    print("[SadTalker] Поиск видео...")
    search_pattern = os.path.join("**", "*.mp4")  # Ищем все MP4 во всех подпапках
    video_candidates = glob.glob(search_pattern, recursive=True)
    video_candidates = [v for v in video_candidates if "GREETINGS_TEMP" not in v]  # Исключаем временную папку

    if not video_candidates:
        raise FileNotFoundError("Видео не найдено!")

    # Выбираем самый свежий файл
    latest_video = max(video_candidates, key=os.path.getmtime)
    print(f"[SadTalker] Найдено видео: {latest_video}")

    # === Перемещение и конвертация ===
    final_mp4 = os.path.join(temp_dir, f"final_{session_id}.mp4")
    shutil.move(latest_video, final_mp4)
    print(f"[SadTalker] Видео перемещено: {final_mp4}")

    # Удаляем временную папку SadTalker
    temp_folder = os.path.dirname(latest_video)
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
        print(f"[CLEANUP] Удалена папка: {temp_folder}")

    # === Конвертация в WebM ===
    webm_path = final_mp4.replace(".mp4", ".webm")
    print(f"[WEBM] Конвертация в: {webm_path}")
    convert_mp4_to_webm(final_mp4, webm_path)

    # === Очистка ===
    os.remove(audio_path)
    os.remove(final_mp4)
    print(f"[CLEANUP] Временные файлы удалены")

    # === Завершение измерения времени ===
    end_time = time.time()  # Засекаем конец выполнения
    total_time = end_time - start_time  # Вычисляем общее время в секундах
    print(f"[INFO] Полное время выполнения: {total_time:.2f} секунд")

    return webm_path

if __name__ == "__main__":
    result = generate_talking_head_video(
        image_path="GREETINGS_TEMP/speaker.jpg",
        gender="male",
        text="Здравствуйте! Я ваш виртуальный HR-ассистент. Сегодня поговорим о вашем опыте и навыках, чтобы лучше понять, как они соотносятся с требованиями на позицию Data Scientist. Как могу к вам обращаться?"
    )
    print(f"✅ Готово! Итоговое видео: {result}")