import os
import glob
import subprocess
from argparse import ArgumentParser

# Указываем путь к FFmpeg
FFMPEG_PATH = r"E:\ffmpeg-7.1-full_build\bin"
os.environ["PATH"] += os.pathsep + FFMPEG_PATH

# Добавляем аргумент для пути к изображению
parser = ArgumentParser()
parser.add_argument("--image_path", type=str, required=False, help="Path to the source image")
args = parser.parse_args()

# Если аргумент не передан через командную строку, используем тестовое значение
SOURCE_IMAGE_PATH = args.image_path if args.image_path else "speaker.jpg"

# Параметры для запуска CLI SadTalker
POSE_STYLE = 0  # Стиль позы (можно настроить)
BATCH_SIZE = 2  # Размер пакета
SIZE = 256  # Размер изображения
EXPRESSION_SCALE = 1.0  # Масштаб выражения
PREPROCESS = 'full'  # Метод предварительной обработки
STILL_MODE = True  # Режим неподвижного тела
CHECKPOINT_DIR = 'SadTalker/checkpoints'  # Путь к контрольным точкам
VENV_PATH = 'SadTalker/venv/Scripts/activate.bat'  # Путь к активации виртуальной среды (для Windows)

# Функция для обработки аудио через CLI интерфейс SadTalker
def process_audio_with_sadtalker(audio_path, image_path, output_video_path):
    # Формируем команду для вызова inference.py с активацией виртуальной среды
    command = f'"{VENV_PATH}" && python SadTalker/inference.py ' \
              f'--driven_audio {audio_path} ' \
              f'--source_image {image_path} ' \
              f'--checkpoint_dir {CHECKPOINT_DIR} ' \
              f'--result_dir . ' \
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


# Функция конвертации MP4 → WebM
def convert_mp4_to_webm(input_path, output_path):
    command = f'ffmpeg -i "{input_path}" -c:v libvpx-vp9 -b:v 1M -c:a libopus "{output_path}" -y'
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ Конвертировано: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при конвертации {input_path}")
        print(e)


# Тестирование через if __name__ == "__main__"
if __name__ == "__main__":
    # Тестовые значения
    test_image_path = "speaker.jpg"  # Путь к тестовому изображению
    test_audio_path = "audio.wav"    # Путь к тестовому аудио
    test_output_video_path = "test_output.mp4"  # Путь к выходному видео (в корне)

    # Обработка тестового аудио
    print(f"Тестирование с изображением: {test_image_path} и аудио: {test_audio_path}")
    process_audio_with_sadtalker(test_audio_path, test_image_path, test_output_video_path)

    # Конвертация MP4 в WebM
    mp4_files = glob.glob("*.mp4")  # Ищем все MP4-файлы в корне
    if not mp4_files:
        print("⚠️ В корне нет MP4-файлов.")
    else:
        for mp4_file in mp4_files:
            webm_file = mp4_file.replace(".mp4", ".webm")
            print(f"🎬 Конвертация: {mp4_file} → {webm_file}")
            convert_mp4_to_webm(mp4_file, webm_file)

    print("✅ Конвертация завершена!")