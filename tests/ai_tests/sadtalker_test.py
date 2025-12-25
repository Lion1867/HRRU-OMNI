'''import os
import sys
import subprocess
import argparse
import glob
import warnings
import librosa
import numpy as np
import pandas as pd
from datetime import datetime
import cv2
from scipy.interpolate import interp1d
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings('ignore')

# === Аргументы ===
parser = argparse.ArgumentParser(description="Генерация липсинка через SadTalker + оценка LSE-D")
parser.add_argument("--image_path", type=str, required=True, help="Путь к изображению лица")
parser.add_argument("--driven_audio", type=str, required=True, help="Путь к аудиофайлу (.wav, 16kHz, mono)")
parser.add_argument("--result_dir", type=str, default="TEMP_VIDEO", help="Папка для сохранения видео")
args = parser.parse_args()

SOURCE_IMAGE_PATH = args.image_path
AUDIO_PATH = args.driven_audio
RESULT_DIR = args.result_dir

# === Создаём директории ===
os.makedirs(RESULT_DIR, exist_ok=True)

# === Параметры SadTalker ===
POSE_STYLE = 0
BATCH_SIZE = 2
SIZE = 256
EXPRESSION_SCALE = 1.0
PREPROCESS = 'full'
STILL_MODE = True
CHECKPOINT_DIR = 'SadTalker/checkpoints'
VENV_PATH = 'SadTalker/venv/Scripts/activate.bat'

# === Запуск SadTalker ===
def run_sadtalker(image_path, audio_path, result_dir):
    still_flag = "--still" if STILL_MODE else ""
    command = (
        f'"{VENV_PATH}" && python SadTalker/inference.py '
        f'--driven_audio "{audio_path}" '
        f'--source_image "{image_path}" '
        f'--checkpoint_dir "{CHECKPOINT_DIR}" '
        f'--result_dir "{result_dir}" '
        f'--pose_style {POSE_STYLE} '
        f'--batch_size {BATCH_SIZE} '
        f'--size {SIZE} '
        f'--expression_scale {EXPRESSION_SCALE} '
        f'--preprocess {PREPROCESS} '
        f'{still_flag}'
    )
    print("Запуск SadTalker...")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка SadTalker: {e}")
        sys.exit(1)

# === Поиск сгенерированного видео ===
def find_generated_video(result_dir, image_path, audio_path):
    image_base = os.path.splitext(os.path.basename(image_path))[0]
    audio_base = os.path.splitext(os.path.basename(audio_path))[0]
    expected_name = f"{image_base}#{audio_base}.mp4"
    candidate = os.path.join(result_dir, expected_name)
    if os.path.isfile(candidate):
        return candidate
    # Если не нашли — ищем любой .mp4
    mp4_files = glob.glob(os.path.join(result_dir, "*.mp4"))
    if mp4_files:
        return mp4_files[0]
    raise FileNotFoundError(f"Не найдено видео в {result_dir}")

# === LSE-D: Lip Sync Error (Distance) ===
def compute_lse_d(video_path: str, audio_path: str) -> float:
    try:
        # Аудио: MFCC как приближение фонем
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        mfcc = librosa.feature.mfcc(y=audio, sr=16000, n_mfcc=13)
        audio_features = mfcc.T  # (time, 13)

        # Видео: извлекаем кадры губ (просто ресайзим всё лицо — как proxy)
        cap = cv2.VideoCapture(video_path)
        lip_frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            small = cv2.resize(frame, (96, 96))
            lip_frames.append(small.flatten())
        cap.release()

        if not lip_frames:
            raise ValueError("Видео пустое")

        lip_features = np.array(lip_frames)  # (N, 96*96*3)

        # Выравнивание по времени через интерполяцию
        x_old = np.linspace(0, 1, len(lip_features))
        x_new = np.linspace(0, 1, len(audio_features))
        lip_interp = interp1d(x_old, lip_features, axis=0, fill_value="extrapolate")(x_new)

        # Косинусное расстояние
        min_len = min(lip_interp.shape[0], audio_features.shape[0])
        lip_part = lip_interp[:min_len]
        audio_part = audio_features[:min_len]

        lip_norm = lip_part / (np.linalg.norm(lip_part, axis=1, keepdims=True) + 1e-8)
        audio_norm = audio_part / (np.linalg.norm(audio_part, axis=1, keepdims=True) + 1e-8)

        cos_sim = cosine_similarity(lip_norm, audio_norm).diagonal()
        lse_d = 1.0 - np.mean(cos_sim)
        return float(lse_d)

    except Exception as e:
        print(f"⚠️ Ошибка LSE-D: {e}")
        return float('inf')

# === Основной поток ===
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ SADTALKER + LSE-D ОЦЕНКА")
    print("=" * 60)

    # Запускаем генерацию
    run_sadtalker(SOURCE_IMAGE_PATH, AUDIO_PATH, RESULT_DIR)

    # Находим видео
    try:
        video_file = find_generated_video(RESULT_DIR, SOURCE_IMAGE_PATH, AUDIO_PATH)
        print(f"✅ Найдено видео: {video_file}")
    except FileNotFoundError as e:
        print(e)
        print("Содержимое папки результатов:")
        for f in os.listdir(RESULT_DIR):
            print(f"  - {f}")
        sys.exit(1)

    # Считаем LSE-D
    print("\nВычисление LSE-D...")
    lse_score = compute_lse_d(video_file, AUDIO_PATH)
    print(f"\n📊 LSE-D Скор: {lse_score:.4f}")
    print("  • Меньше = лучше синхронизация")
    print("  • Хорошо: < 0.3, Плохо: > 0.5")

    # Сохраняем результат
    results = pd.DataFrame([{
        'image_path': SOURCE_IMAGE_PATH,
        'audio_path': AUDIO_PATH,
        'video_path': video_file,
        'lse_d': lse_score,
        'timestamp': datetime.now().isoformat()
    }])
    results.to_csv("sadtalker_lse_results.csv", index=False, encoding='utf-8')
    print(f"\nРезультаты сохранены в: sadtalker_lse_results.csv")'''

import torch
torch.cuda.is_available = lambda: False  # Force CPU

import os
import sys
import subprocess
import argparse
import glob
import warnings
import pandas as pd
from datetime import datetime
import urllib.request
import shutil

warnings.filterwarnings('ignore')

# === Проверка и установка syncnet-python (опционально) ===
try:
    from syncnet_python import SyncNetPipeline
except ImportError:
    print("Библиотека 'syncnet-python' не установлена.")
    print("Установите её: pip install syncnet-python")
    print("Также убедитесь, что установлен ffmpeg.")
    sys.exit(1)

# === Аргументы ===
parser = argparse.ArgumentParser(description="Генерация липсинка через SadTalker + оценка LSE-D через SyncNet")
parser.add_argument("--image_path", type=str, required=True, help="Путь к изображению лица")
parser.add_argument("--driven_audio", type=str, required=True, help="Путь к аудиофайлу (.wav, 16kHz, mono)")
parser.add_argument("--result_dir", type=str, default="TEMP_VIDEO", help="Папка для сохранения видео")
args = parser.parse_args()

SOURCE_IMAGE_PATH = args.image_path
AUDIO_PATH = args.driven_audio
RESULT_DIR = args.result_dir

# === Создаём директории ===
os.makedirs(RESULT_DIR, exist_ok=True)

# === Веса SyncNet ===
WEIGHTS_DIR = "syncnet_weights"
os.makedirs(WEIGHTS_DIR, exist_ok=True)

SFD_WEIGHTS = os.path.join(WEIGHTS_DIR, "sfd_face.pth")
SYNCNET_WEIGHTS = os.path.join(WEIGHTS_DIR, "syncnet_v2.model")

def download_file(url, dest):
    if os.path.exists(dest):
        print(f"{os.path.basename(dest)} уже существует.")
        return
    print(f"Скачивание {os.path.basename(dest)}...")
    try:
        import urllib.request
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
            total_size = response.getheader('Content-Length')
            if total_size is None:
                out_file.write(response.read())
            else:
                total_size = int(total_size)
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
        print(f"{os.path.basename(dest)} успешно загружен.")
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        if os.path.exists(dest):
            os.remove(dest)
        raise
'''
# Скачиваем веса
download_file(
    "http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model",
    SYNCNET_WEIGHTS
)
download_file(
    "http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/sfd_face.pth",
    SFD_WEIGHTS
)
'''
# === Параметры SadTalker ===
POSE_STYLE = 0
BATCH_SIZE = 2
SIZE = 256
EXPRESSION_SCALE = 1.0
PREPROCESS = 'full'
STILL_MODE = True
CHECKPOINT_DIR = 'SadTalker/checkpoints'
VENV_PATH = 'SadTalker/venv/Scripts/activate.bat'

def run_sadtalker(image_path, audio_path, result_dir):
    still_flag = "--still" if STILL_MODE else ""
    command = (
        f'"{VENV_PATH}" && python SadTalker/inference.py '
        f'--driven_audio "{audio_path}" '
        f'--source_image "{image_path}" '
        f'--checkpoint_dir "{CHECKPOINT_DIR}" '
        f'--result_dir "{result_dir}" '
        f'--pose_style {POSE_STYLE} '
        f'--batch_size {BATCH_SIZE} '
        f'--size {SIZE} '
        f'--expression_scale {EXPRESSION_SCALE} '
        f'--preprocess {PREPROCESS} '
        f'{still_flag}'
    )
    print("Запуск SadTalker...")
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print("Ошибка SadTalker:", e)
        sys.exit(1)

def find_generated_video(result_dir, image_path, audio_path):
    image_base = os.path.splitext(os.path.basename(image_path))[0]
    audio_base = os.path.splitext(os.path.basename(audio_path))[0]
    possible_names = [
        f"{image_base}#{audio_base}.mp4",
        f"{image_base}##{audio_base}.mp4",
        f"{image_base}##{audio_base}_full.mp4"
    ]
    for name in possible_names:
        candidate = os.path.join(result_dir, name)
        if os.path.isfile(candidate):
            return candidate

    mp4_files = glob.glob(os.path.join(result_dir, "*.mp4"))
    if mp4_files:
        return mp4_files[0]
    raise FileNotFoundError("Не найдено видео в папке результатов")

def compute_lse_d_syncnet(video_path: str, audio_path: str) -> float:
    print("Инициализация SyncNet из PyPI...")
    try:
        pipeline = SyncNetPipeline(
            s3fd_weights=SFD_WEIGHTS,
            syncnet_weights=SYNCNET_WEIGHTS,
            device="cpu"
        )
        print("Анализ синхронизации...")
        results = pipeline.inference(video_path=video_path, audio_path=audio_path)
        
        # Распаковка результатов
        offset_list, confidence_list, min_dist_list, best_conf, best_min_dist, _, success = results
        
        if not success or len(confidence_list) == 0:
            print("SyncNet: не удалось обработать видео (возможно, нет лица)")
            return float('inf')
        
        confidence = confidence_list[0]
        print(f"SyncNet (PyPI): confidence = {confidence:.4f}")
        
        # LSE-D: меньше — лучше
        # В оригинале: confidence ~ [0, 10+] → нормализуем до [0, 1]
        lse_d = 1.0 - min(1.0, max(0.0, confidence / 10.0))
        return float(lse_d)
        
    except Exception as e:
        print(f"Ошибка syncnet-python: {e}")
        return float('inf')

# === Основной поток ===
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ SADTALKER + LSE-D (SyncNet-PyPI)")
    print("=" * 60)

    run_sadtalker(SOURCE_IMAGE_PATH, AUDIO_PATH, RESULT_DIR)

    try:
        video_file = find_generated_video(RESULT_DIR, SOURCE_IMAGE_PATH, AUDIO_PATH)
        print("Найдено видео:", video_file)
    except FileNotFoundError as e:
        print(e)
        for f in os.listdir(RESULT_DIR):
            print("  -", f)
        sys.exit(1)

    print("\nВычисление LSE-D через SyncNet (PyPI)...")
    lse_score = compute_lse_d_syncnet(video_file, AUDIO_PATH)
    print(f"\nLSE-D Скор: {lse_score:.4f}")
    print("  Меньше = лучше синхронизация")
    print("  Хорошо: < 0.3, Плохо: > 0.5")

    results = pd.DataFrame([{
        'image_path': SOURCE_IMAGE_PATH,
        'audio_path': AUDIO_PATH,
        'video_path': video_file,
        'lse_d_syncnet': lse_score,
        'timestamp': datetime.now().isoformat()
    }])
    results.to_csv("sadtalker_lse_syncnet_results.csv", index=False, encoding='utf-8')
    print("\nРезультаты сохранены в: sadtalker_lse_syncnet_results.csv")