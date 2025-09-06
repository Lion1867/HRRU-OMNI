import os
import glob
import subprocess

# Указываем путь к FFmpeg
FFMPEG_PATH = r"E:\ffmpeg-7.1-full_build\bin"
os.environ["PATH"] += os.pathsep + FFMPEG_PATH

# Директории
VIDEO_DIR = "TEMP_VIDEO"
FINAL_VIDEO_DIR = "TEMP_FINAL_VIDEO"

# Убедимся, что папка для итоговых видео существует
os.makedirs(FINAL_VIDEO_DIR, exist_ok=True)

# Функция конвертации MP4 → WebM
def convert_mp4_to_webm(input_path, output_path):
    command = f'ffmpeg -i "{input_path}" -c:v libvpx-vp9 -b:v 1M -c:a libopus "{output_path}" -y'
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ Конвертировано: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при конвертации {input_path}")
        print(e)


# Получаем список всех MP4-файлов
mp4_files = glob.glob(os.path.join(VIDEO_DIR, "*.mp4"))

if not mp4_files:
    print("⚠️ В папке TEMP_VIDEO нет MP4-файлов.")
else:
    for mp4_file in mp4_files:
        webm_file = os.path.join(FINAL_VIDEO_DIR, os.path.basename(mp4_file).replace(".mp4", ".webm"))
        print(f"🎬 Конвертация: {mp4_file} → {webm_file}")
        convert_mp4_to_webm(mp4_file, webm_file)

print("✅ Конвертация завершена!")
