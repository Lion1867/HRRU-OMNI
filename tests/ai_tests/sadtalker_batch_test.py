'''import torch
torch.cuda.is_available = lambda: False  # Force CPU

import os
import sys
import subprocess
import argparse
import glob
import warnings
import pandas as pd
from datetime import datetime
import random
import shutil
from pathlib import Path

warnings.filterwarnings('ignore')

# === Проверка syncnet-python ===
try:
    from syncnet_python import SyncNetPipeline
except ImportError:
    print("Библиотека 'syncnet-python' не установлена.")
    print("Установите: pip install syncnet-python")
    print("Также нужен ffmpeg в PATH.")
    sys.exit(1)

# === Аргументы ===
parser = argparse.ArgumentParser(description="Пакетное тестирование SadTalker + LSE-D")
parser.add_argument("--image_dir", type=str, required=True, help="Папка с изображениями (.jpg, .png)")
parser.add_argument("--audio_dir", type=str, required=True, help="Папка с аудио (.wav, 16kHz, mono)")
parser.add_argument("--num_samples", type=int, default=50, help="Количество случайных пар для обработки")
parser.add_argument("--result_dir", type=str, default="batch_results", help="Папка для сохранения видео и результатов")
parser.add_argument("--seed", type=int, default=42, help="Фиксированный seed для воспроизводимости")
args = parser.parse_args()

# === Установка seed ===
random.seed(args.seed)

# === Пути ===
IMAGE_DIR = args.image_dir
AUDIO_DIR = args.audio_dir
NUM_SAMPLES = args.num_samples
RESULT_DIR = args.result_dir
os.makedirs(RESULT_DIR, exist_ok=True)

# === Веса SyncNet ===
WEIGHTS_DIR = "syncnet_weights"
os.makedirs(WEIGHTS_DIR, exist_ok=True)
SFD_WEIGHTS = os.path.join(WEIGHTS_DIR, "sfd_face.pth")
SYNCNET_WEIGHTS = os.path.join(WEIGHTS_DIR, "syncnet_v2.model")

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
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"SadTalker ошибка для {os.path.basename(image_path)}")
        return False
    return True

def find_generated_video(result_dir, image_path, audio_path):
    image_base = Path(image_path).stem
    audio_base = Path(audio_path).stem
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
    return None

def compute_lse_d_syncnet(video_path: str, audio_path: str, sfd_weights, syncnet_weights) -> float:
    try:
        pipeline = SyncNetPipeline(
            s3fd_weights=sfd_weights,
            syncnet_weights=syncnet_weights,
            device="cpu"
        )
        results = pipeline.inference(video_path=video_path, audio_path=audio_path)
        offset_list, confidence_list, _, _, _, _, success = results
        if not success or len(confidence_list) == 0:
            return float('inf')
        confidence = confidence_list[0]
        lse_d = 1.0 - min(1.0, max(0.0, confidence / 10.0))
        return float(lse_d)
    except Exception:
        return float('inf')

def main():
    print("=" * 70)
    print("ПАКЕТНОЕ ТЕСТИРОВАНИЕ SADTALKER + LSE-D")
    print("=" * 70)
    print(f"Изображения: {IMAGE_DIR}")
    print(f"Аудио:       {AUDIO_DIR}")
    print(f"Выборка:     {NUM_SAMPLES} пар")
    print(f"Результаты:  {RESULT_DIR}")
    print("=" * 70)

    # Собираем списки файлов
    image_files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.jpg")) + glob.glob(os.path.join(IMAGE_DIR, "*.png")))
    audio_files = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.wav")))

    if not image_files or not audio_files:
        print(" Не найдены изображения или аудио!")
        sys.exit(1)

    print(f"Найдено: {len(image_files)} изображений, {len(audio_files)} аудио")

    # Выбираем случайные пары (без повторений)
    min_count = min(len(image_files), len(audio_files), NUM_SAMPLES)
    indices = list(range(min(len(image_files), len(audio_files))))
    random.shuffle(indices)
    selected_indices = indices[:min_count]

    pairs = [(image_files[i], audio_files[i]) for i in selected_indices]
    print(f"Выбрано {len(pairs)} пар для обработки.")

    # Инициализация SyncNet один раз
    if not (os.path.exists(SFD_WEIGHTS) and os.path.exists(SYNCNET_WEIGHTS)):
        print("Веса SyncNet не найдены! Скачайте их вручную в папку 'syncnet_weights':")
        print("  sfd_face.pth: https://huggingface.co/lithiumice/syncnet/resolve/main/sfd_face.pth")
        print("  syncnet_v2.model: http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model")
        sys.exit(1)

    results_list = []

    for idx, (img_path, aud_path) in enumerate(pairs, 1):
        print(f"\n--- [{idx}/{len(pairs)}] Обработка: {os.path.basename(img_path)} + {os.path.basename(aud_path)} ---")
        
        # Временная папка для этого запуска
        temp_result_dir = os.path.join(RESULT_DIR, f"run_{idx:03d}")
        os.makedirs(temp_result_dir, exist_ok=True)

        # Запуск SadTalker
        success = run_sadtalker(img_path, aud_path, temp_result_dir)
        if not success:
            lse_score = float('inf')
            video_path = None
        else:
            # Поиск видео
            video_path = find_generated_video(temp_result_dir, img_path, aud_path)
            if not video_path:
                lse_score = float('inf')
            else:
                # Оценка SyncNet
                lse_score = compute_lse_d_syncnet(video_path, aud_path, SFD_WEIGHTS, SYNCNET_WEIGHTS)

        # Сохраняем результат
        results_list.append({
            'sample_id': idx,
            'image_path': img_path,
            'audio_path': aud_path,
            'video_path': video_path,
            'lse_d_syncnet': lse_score,
            'success': lse_score != float('inf')
        })

        print(f"LSE-D: {'{:.4f}'.format(lse_score) if lse_score != float('inf') else 'FAIL'}")

    # Фильтруем успешные результаты
    valid_scores = [r['lse_d_syncnet'] for r in results_list if r['success']]
    all_scores = [r['lse_d_syncnet'] if r['success'] else None for r in results_list]

    # Статистика
    print("\n" + "=" * 70)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)
    print(f"Всего пар:          {len(pairs)}")
    print(f"Успешно обработано: {len(valid_scores)}")
    print(f"Ошибок:             {len(pairs) - len(valid_scores)}")

    if valid_scores:
        import numpy as np
        scores_np = np.array(valid_scores)
        print(f"\nСтатистика LSE-D (меньше — лучше):")
        print(f"  Среднее:   {scores_np.mean():.4f}")
        print(f"  Медиана:   {np.median(scores_np):.4f}")
        print(f"  Std:       {scores_np.std():.4f}")
        print(f"  Min:       {scores_np.min():.4f}")
        print(f"  Max:       {scores_np.max():.4f}")
        print(f"\nИнтерпретация:")
        print(f"  Хорошо: < 0.3, Средне: 0.3–0.5, Плохо: > 0.5")
    else:
        print("\nНи одна пара не обработана успешно!")

    # Сохранение полного CSV
    results_df = pd.DataFrame(results_list)
    output_csv = os.path.join(RESULT_DIR, "batch_sadtalker_lse_results.csv")
    results_df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"\nВсе результаты сохранены в: {output_csv}")

if __name__ == "__main__":
    main()'''

import os
import sys
import subprocess
import argparse
import glob
import warnings
import random
import pandas as pd
from datetime import datetime
import numpy as np

from syncnet_python import SyncNetPipeline

warnings.filterwarnings('ignore')

# === Имитация CPU-only для SyncNet ===
import torch
torch.cuda.is_available = lambda: False

# === Аргументы ===
parser = argparse.ArgumentParser(description="Пакетный тест SadTalker + LSE-D через SyncNet")
parser.add_argument("--images_dir", type=str, required=True, help="Папка с изображениями (.jpg, .png)")
parser.add_argument("--audios_dir", type=str, required=True, help="Папка с аудиофайлами (.wav, 16kHz, mono)")
parser.add_argument("--output_dir", type=str, default="sadtalker_batch_results", help="Папка для сохранения видео и результатов")
parser.add_argument("--num_samples", type=int, default=2, help="Количество случайных пар для тестирования")
parser.add_argument("--seed", type=int, default=42, help="Сид для воспроизводимости")
args = parser.parse_args()

IMAGES_DIR = args.images_dir
AUDIOS_DIR = args.audios_dir
OUTPUT_DIR = args.output_dir
NUM_SAMPLES = args.num_samples
SEED = args.seed

random.seed(SEED)
np.random.seed(SEED)

# === Веса SyncNet ===
WEIGHTS_DIR = "syncnet_weights"
os.makedirs(WEIGHTS_DIR, exist_ok=True)
SFD_WEIGHTS = os.path.join(WEIGHTS_DIR, "sfd_face.pth")
SYNCNET_WEIGHTS = os.path.join(WEIGHTS_DIR, "syncnet_v2.model")

# Убедитесь, что веса существуют (можно раскомментировать загрузку при первом запуске)
if not os.path.exists(SYNCNET_WEIGHTS) or not os.path.exists(SFD_WEIGHTS):
    print("Веса SyncNet не найдены. Поместите их в папку 'syncnet_weights':")
    print(f"  - {SYNCNET_WEIGHTS}")
    print(f"  - {SFD_WEIGHTS}")
    print("Ссылки:")
    print("  syncnet_v2.model → http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/syncnet_v2.model")
    print("  sfd_face.pth      → http://www.robots.ox.ac.uk/~vgg/software/lipsync/data/sfd_face.pth")
    sys.exit(1)

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
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка SadTalker для {os.path.basename(image_path)} + {os.path.basename(audio_path)}: {e}")
        return False
    return True

def find_generated_video(result_dir, image_path, audio_path):
    image_base = os.path.splitext(os.path.basename(image_path))[0]
    audio_base = os.path.splitext(os.path.basename(audio_path))[0]
    candidates = [
        f"{image_base}#{audio_base}.mp4",
        f"{image_base}##{audio_base}.mp4",
        f"{image_base}##{audio_base}_full.mp4"
    ]
    for name in candidates:
        path = os.path.join(result_dir, name)
        if os.path.isfile(path):
            return path
    mp4s = glob.glob(os.path.join(result_dir, "*.mp4"))
    return mp4s[0] if mp4s else None

def compute_lse_d_syncnet(video_path: str, audio_path: str, sfd_weights, syncnet_weights) -> float:
    try:
        pipeline = SyncNetPipeline(
            s3fd_weights=sfd_weights,
            syncnet_weights=syncnet_weights,
            device="cpu"
        )
        results = pipeline.inference(video_path=video_path, audio_path=audio_path)
        offset_list, confidence_list, min_dist_list, best_conf, best_min_dist, _, success = results

        if not success or not confidence_list:
            return float('inf')
        confidence = confidence_list[0]
        lse_d = 1.0 - min(1.0, max(0.0, confidence / 10.0))
        return float(lse_d)
    except Exception as e:
        print(f"SyncNet ошибка: {e}")
        return float('inf')

# === Основной поток ===
if __name__ == "__main__":
    print("=" * 70)
    print("ПАКЕТНЫЙ ТЕСТ SADTALKER + LSE-D (SyncNet-PyPI)")
    print(f"Изображения: {IMAGES_DIR}")
    print(f"Аудио:       {AUDIOS_DIR}")
    print(f"Кол-во образцов: {NUM_SAMPLES}")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Получаем списки файлов
    image_files = sorted([f for f in glob.glob(os.path.join(IMAGES_DIR, "*")) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    audio_files = sorted([f for f in glob.glob(os.path.join(AUDIOS_DIR, "*")) if f.lower().endswith(".wav")])

    if not image_files or not audio_files:
        print("Папки не содержат подходящих файлов.")
        sys.exit(1)

    print(f"Найдено: {len(image_files)} изображений, {len(audio_files)} аудиофайлов")

    # Выбираем случайные пары
    all_pairs = [(img, aud) for img in image_files for aud in audio_files]
    if len(all_pairs) < NUM_SAMPLES:
        print(f"Доступно только {len(all_pairs)} уникальных пар. Используем все.")
        samples = all_pairs
    else:
        samples = random.sample(all_pairs, NUM_SAMPLES)

    results = []

    for i, (img_path, aud_path) in enumerate(samples, 1):
        print(f"\n--- Пример {i}/{len(samples)} ---")
        print(f"Изображение: {os.path.basename(img_path)}")
        print(f"Аудио:       {os.path.basename(aud_path)}")

        temp_video_dir = os.path.join(OUTPUT_DIR, f"run_{i}")
        os.makedirs(temp_video_dir, exist_ok=True)

        success = run_sadtalker(img_path, aud_path, temp_video_dir)
        if not success:
            lse = float('inf')
            video_path = None
        else:
            video_path = find_generated_video(temp_video_dir, img_path, aud_path)
            if not video_path:
                lse = float('inf')
            else:
                print("Видео найдено. Вычисление LSE-D...")
                lse = compute_lse_d_syncnet(video_path, aud_path, SFD_WEIGHTS, SYNCNET_WEIGHTS)

        result_entry = {
            'image_path': img_path,
            'audio_path': aud_path,
            'video_path': video_path,
            'lse_d': lse,
            'success': lse != float('inf'),
            'timestamp': datetime.now().isoformat()
        }
        results.append(result_entry)
        print(f"LSE-D: {lse:.4f}" if lse != float('inf') else "LSE-D: ❌ Не удалось оценить")

    # Сохраняем детали
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "batch_lse_results.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\nДетальные результаты сохранены: {csv_path}")

    # Статистика по валидным LSE-D
    valid_scores = [r['lse_d'] for r in results if r['success']]
    if valid_scores:
        mean_score = np.mean(valid_scores)
        median_score = np.median(valid_scores)
        min_score = np.min(valid_scores)
        max_score = np.max(valid_scores)

        stats = {
            'num_samples': len(samples),
            'valid_results': len(valid_scores),
            'mean_lse_d': mean_score,
            'median_lse_d': median_score,
            'min_lse_d': min_score,
            'max_lse_d': max_score,
            'timestamp': datetime.now().isoformat()
        }

        stats_df = pd.DataFrame([stats])
        stats_path = os.path.join(OUTPUT_DIR, "batch_lse_summary.csv")
        stats_df.to_csv(stats_path, index=False, encoding='utf-8')

        print("\nСводка LSE-D:")
        print(f"  Всего:       {len(samples)}")
        print(f"  Успешно:     {len(valid_scores)}")
        print(f"  Среднее:     {mean_score:.4f}")
        print(f"  Медиана:     {median_score:.4f}")
        print(f"  Минимум:     {min_score:.4f}")
        print(f"  Максимум:    {max_score:.4f}")
        print(f"\nСводка сохранена: {stats_path}")
    else:
        print("\nНи один пример не удалось оценить.")