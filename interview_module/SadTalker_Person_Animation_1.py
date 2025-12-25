import os
import glob
import subprocess
from argparse import ArgumentParser
import time
import argparse

# Директории
TEMP_AUDIO_DIR = 'TEMP_AUDIO'
TEMP_VIDEO_DIR = 'TEMP_VIDEO'


# Добавляем аргумент для пути к изображению
parser = argparse.ArgumentParser()
parser.add_argument("--image_path", type=str, required=True, help="Path to the source image")
args = parser.parse_args()

# Используем переданный путь к изображению
SOURCE_IMAGE_PATH = args.image_path

# Остальной код скрипта остается без изменений

# Параметры для запуска CLI
POSE_STYLE = 0  # Стиль позы (можно настроить)
BATCH_SIZE = 2  # Размер пакета
SIZE = 256  # Размер изображения
EXPRESSION_SCALE = 1.0  # Масштаб выражения
PREPROCESS = 'full'  # Метод предварительной обработки
STILL_MODE = True  # Режим неподвижного тела
CHECKPOINT_DIR = 'SadTalker/checkpoints'  # Путь к контрольным точкам
RESULT_DIR = TEMP_VIDEO_DIR  # Путь к результатам
VENV_PATH = 'SadTalker/venv/Scripts/activate.bat'  # Путь к активации виртуальной среды (для Windows)

# Убедимся, что папка для видео существует
os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)


# Функция для обработки аудио через CLI интерфейс SadTalker
def process_audio_with_sadtalker(audio_path, image_path, output_video_path):
    # Формируем команду для вызова inference.py с активацией виртуальной среды
    command = f'"{VENV_PATH}" && python SadTalker/inference.py ' \
              f'--driven_audio {audio_path} ' \
              f'--source_image {image_path} ' \
              f'--checkpoint_dir {CHECKPOINT_DIR} ' \
              f'--result_dir {RESULT_DIR} ' \
              f'--pose_style {POSE_STYLE} ' \
              f'--batch_size {BATCH_SIZE} ' \
              f'--size {SIZE} ' \
              f'--expression_scale {EXPRESSION_SCALE} ' \
              f'--preprocess {PREPROCESS} ' \
              f'--still' if STILL_MODE else ''


    # Запуск процесса с помощью subprocess
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при обработке аудио: {audio_path}")
        print(e)


# Получаем список всех аудио файлов в папке и сортируем их по номеру
audio_files = sorted(glob.glob(os.path.join(TEMP_AUDIO_DIR, "*.wav")),
                     key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))

# Обрабатываем каждый аудио файл
for audio_file in audio_files:
    # Получаем индекс аудио файла из его имени
    audio_index = os.path.basename(audio_file).split('_')[1].split('.')[0]
    output_video_path = os.path.join(TEMP_VIDEO_DIR, f"question_{audio_index}.mp4")

    # Обработка аудио
    print(f"Обработка аудио файла: {audio_file}")
    process_audio_with_sadtalker(audio_file, SOURCE_IMAGE_PATH, output_video_path)
