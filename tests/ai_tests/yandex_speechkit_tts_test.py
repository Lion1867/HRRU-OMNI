'''import os
import sys
import tempfile
import shutil  # для копирования
import pytest
from pydub import AudioSegment
import librosa
import torch

# Добавляем путь к interview_module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'interview_module')))
from Yandex_TTS1 import text_to_audio


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_text_to_audio_returns_bytes():
    audio = text_to_audio("Привет, дорогие коллеги, с наступающим, друзья!", "oksana")
    assert isinstance(audio, bytes) and len(audio) > 0


def test_text_to_audio_generates_valid_ogg():
    audio = text_to_audio("Привет, дорогие коллеги, с наступающим, друзья!", "oksana")
    assert audio.startswith(b"OggS"), "Аудио не в формате Ogg Opus"


def test_utmos_score_for_tts_audio(temp_dir):
    """Тест качества TTS через UTMOS22 (SpeechMOS) — без fairseq!"""
    text = "Привет, дорогие коллеги, с наступающим, друзья!"
    voice = "oksana"

    # 1. Получаем аудио от Yandex TTS
    audio_bytes = text_to_audio(text, voice)
    ogg_path = os.path.join(temp_dir, "speech.ogg")
    with open(ogg_path, "wb") as f:
        f.write(audio_bytes)

    # 2. Конвертируем Ogg Opus → 16kHz mono WAV
    wav_path = os.path.join(temp_dir, "speech.wav")
    audio = AudioSegment.from_ogg(ogg_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(wav_path, format="wav")

    assert os.path.exists(wav_path) and os.path.getsize(wav_path) > 0

    # 3. (Опционально) Сохранить аудио для прослушивания
    SAVE_AUDIO_FOR_LISTENING = os.getenv("SAVE_TTS_AUDIO", "0") == "1"
    if SAVE_AUDIO_FOR_LISTENING:
        # Папка для сохранённых аудио рядом с тестом
        output_dir = os.path.join(os.path.dirname(__file__), "saved_audio")
        os.makedirs(output_dir, exist_ok=True)
        saved_wav = os.path.join(output_dir, "latest_tts_output.wav")
        shutil.copy2(wav_path, saved_wav)
        print(f"\n🔊 Аудиофайл сохранён для прослушивания: {saved_wav}")

    # 4. Загружаем UTMOS22 через torch.hub
    predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True)

    # 5. Загружаем аудио и предсказываем MOS
    wave, sr = librosa.load(wav_path, sr=None, mono=True)
    with torch.no_grad():
        score_tensor = predictor(torch.from_numpy(wave).unsqueeze(0), sr)
    mos_pred = score_tensor.item()

    print(f"\n[UTMOS22] Predicted MOS: {mos_pred:.3f}")

    # 6. Проверки
    assert 1.0 <= mos_pred <= 5.0, f"MOS вышел за допустимые границы: {mos_pred:.3f}"
    assert mos_pred > 3.0, f"MOS слишком низкий: {mos_pred:.3f}"'''



'''import torch
import librosa

# Загрузка аудиофайла (должен быть WAV, желательно 16 кГц, моно — librosa сама конвертирует)
wave, sr = librosa.load("temp_16k_mono.wav", sr=None, mono=True)

# Загрузка модели UTMOS через torch.hub
predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True)

# Предсказание MOS (важно: добавить batch dimension через unsqueeze(0))
with torch.no_grad():
    score = predictor(torch.from_numpy(wave).unsqueeze(0), sr)

# Вывод результата
mos_value = score.item()
print(f"🎙️ UTMOS (SpeechMOS): {mos_value:.3f}")'''


'''
import os
import sys
import tempfile
import pandas as pd
import numpy as np
import torch
import librosa
from pydub import AudioSegment
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'interview_module')))
from Yandex_TTS1 import text_to_audio

def load_transcript(file_path, max_samples=None):
    """Загружает тексты из файла transcript.txt"""
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    text = parts[1].strip()
                    if text:
                        texts.append(text)
        
        if max_samples and len(texts) > max_samples:
            texts = texts[:max_samples]
        
        print(f"Загружено {len(texts)} текстов из {file_path}")
        return texts
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}")
        return []

def evaluate_tts_on_transcript(transcript_file, num_samples=50, save_samples=10):
    """Основная функция оценки"""
    # Загружаем тексты
    texts = load_transcript(transcript_file, num_samples)
    if not texts:
        print("Не удалось загрузить тексты")
        return
    
    # Загружаем модель MOS
    print("Загрузка модели MOS...")
    mos_predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True)
    mos_predictor.eval()
    
    # Распределяем голоса 50/50
    voices = ["oksana", "zahar"]
    voice_assignment = []
    for i in range(len(texts)):
        voice_assignment.append(voices[0] if i < len(texts) // 2 else voices[1])
    random.shuffle(voice_assignment)
    
    print(f"Распределение: {voice_assignment.count(voices[0])}x {voices[0]}, "
          f"{voice_assignment.count(voices[1])}x {voices[1]}")
    
    results = []
    
    # Создаем папку для сохранения аудио
    if save_samples > 0:
        os.makedirs("results\\tts_samples", exist_ok=True)
    
    # Обработка текстов
    for i, (text, voice) in enumerate(zip(texts, voice_assignment)):
        try:
            print(f"\n[{i+1}/{len(texts)}] {voice}: {text[:50]}...")
            
            # Синтез
            audio_bytes = text_to_audio(text, voice)
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
                f.write(audio_bytes)
                ogg_path = f.name
            
            # Конвертируем в WAV
            wav_path = ogg_path.replace('.ogg', '.wav')
            audio = AudioSegment.from_ogg(ogg_path)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            audio.export(wav_path, format="wav")
            
            # Оценка MOS
            wave, sr = librosa.load(wav_path, sr=16000, mono=True)
            with torch.no_grad():
                mos_score = mos_predictor(torch.from_numpy(wave).unsqueeze(0), sr)
            
            # Сохраняем аудио если нужно
            saved_path = None
            if i < save_samples:
                timestamp = datetime.now().strftime("%H%M%S")
                save_path = f"results\\tts_samples\\{voice}_{i:03d}_{timestamp}.wav"
                import shutil
                shutil.copy2(wav_path, save_path)
                saved_path = save_path
            
            results.append({
                "text": text,
                "voice": voice,
                "mos_score": mos_score.item(),
                "sample_id": i,
                "audio_path": saved_path
            })
            
            print(f"  MOS: {mos_score.item():.3f}")
            
            # Очистка
            os.unlink(ogg_path)
            os.unlink(wav_path)
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  Ошибка: {e}")
            continue
    
    # Анализ результатов
    if results:
        df = pd.DataFrame(results)
        
        print("\n" + "="*50)
        print("РЕЗУЛЬТАТЫ:")
        print("="*50)
        
        for voice in voices:
            voice_df = df[df["voice"] == voice]
            if len(voice_df) > 0:
                scores = voice_df["mos_score"]
                print(f"\n{voice.upper()}: {len(voice_df)} примеров")
                print(f"  Средний: {scores.mean():.3f}")
                print(f"  Лучший: {scores.max():.3f}")
                print(f"  Худший: {scores.min():.3f}")
        
        print(f"\nОБЩИЙ СРЕДНИЙ: {df['mos_score'].mean():.3f}")
        
        # Сохраняем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_csv(f"results\\tts_results_{timestamp}.csv", index=False, encoding='utf-8')
        print(f"\nРезультаты сохранены в tts_results_{timestamp}.csv")

if __name__ == "__main__":
    transcript_file = os.path.join("data", "speech_dataset", "ru", "transcript.txt")
    
    evaluate_tts_on_transcript(transcript_file, num_samples=50, save_samples=15)'''

import os
import sys
import tempfile
import pandas as pd
import numpy as np
import torch
import librosa
from pydub import AudioSegment
import time
import random
from datetime import datetime
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'interview_module')))
from Yandex_TTS1 import text_to_audio

def load_transcript(file_path, max_samples=None):
    """Загружает тексты из файла transcript.txt"""
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    text = parts[1].strip()
                    if text:
                        texts.append(text)
        
        if max_samples and len(texts) > max_samples:
            texts = texts[:max_samples]
        
        print(f"Загружено {len(texts)} текстов из {file_path}")
        return texts
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}")
        return []

def evaluate_tts_on_transcript(transcript_file, num_samples=50, save_samples=10, 
                               voices=None, model_name="utmos22_strong", 
                               sleep_time=0.3, output_dir="results"):
    """
    Основная функция оценки TTS
    
    Args:
        transcript_file: путь к файлу с транскриптами
        num_samples: количество примеров для оценки
        save_samples: количество аудиофайлов для сохранения
        voices: список голосов для тестирования
        model_name: название модели MOS
        sleep_time: пауза между запросами (секунды)
        output_dir: директория для сохранения результатов
    """
    # Проверяем параметры по умолчанию
    if voices is None:
        voices = ["oksana", "zahar"]
    
    # Создаем папку для результатов
    tts_samples_dir = os.path.join(output_dir, "tts_samples")
    os.makedirs(tts_samples_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Загружаем тексты
    texts = load_transcript(transcript_file, num_samples)
    if not texts:
        print("Не удалось загрузить тексты")
        return None
    
    # Загружаем модель MOS
    print(f"Загрузка модели MOS ({model_name})...")
    try:
        mos_predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", model_name, trust_repo=True)
        mos_predictor.eval()
    except Exception as e:
        print(f"Ошибка загрузки модели MOS: {e}")
        print("Пробую загрузить с skip_validation...")
        mos_predictor = torch.hub.load("tarepan/SpeechMOS:v1.2.0", model_name, 
                                      trust_repo=True, skip_validation=True)
        mos_predictor.eval()
    
    # Распределяем голоса
    voice_assignment = []
    half_samples = len(texts) // 2
    
    # Первая половина - первый голос
    for i in range(half_samples):
        voice_assignment.append(voices[0])
    
    # Вторая половина - второй голос
    for i in range(len(texts) - half_samples):
        voice_assignment.append(voices[1])
    
    # Перемешиваем
    random.shuffle(voice_assignment)
    
    print(f"Распределение голосов: {voice_assignment.count(voices[0])}x {voices[0]}, "
          f"{voice_assignment.count(voices[1])}x {voices[1]}")
    
    results = []
    successful_count = 0
    failed_count = 0
    
    print(f"\nНачинаю оценку {len(texts)} примеров...")
    print("="*60)
    
    # Обработка текстов
    for i, (text, voice) in enumerate(zip(texts, voice_assignment)):
        try:
            print(f"\n[{i+1}/{len(texts)}] {voice}: {text[:50]}...")
            
            # Синтез
            audio_bytes = text_to_audio(text, voice)
            
            if not audio_bytes or len(audio_bytes) == 0:
                print("  Ошибка: пустой ответ от TTS")
                failed_count += 1
                continue
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
                f.write(audio_bytes)
                ogg_path = f.name
            
            # Конвертируем в WAV
            wav_path = ogg_path.replace('.ogg', '.wav')
            try:
                audio = AudioSegment.from_ogg(ogg_path)
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                audio.export(wav_path, format="wav")
            except Exception as e:
                print(f"  Ошибка конвертации аудио: {e}")
                os.unlink(ogg_path)
                failed_count += 1
                continue
            
            # Оценка MOS
            try:
                wave, sr = librosa.load(wav_path, sr=16000, mono=True)
                with torch.no_grad():
                    mos_score = mos_predictor(torch.from_numpy(wave).unsqueeze(0), sr)
            except Exception as e:
                print(f"  Ошибка оценки MOS: {e}")
                mos_score = torch.tensor([0.0])
            
            # Сохраняем аудио если нужно
            saved_path = None
            if i < save_samples:
                timestamp = datetime.now().strftime("%H%M%S")
                save_path = os.path.join(tts_samples_dir, f"{voice}_{i:03d}_{timestamp}.wav")
                import shutil
                try:
                    shutil.copy2(wav_path, save_path)
                    saved_path = save_path
                except Exception as e:
                    print(f"  Ошибка сохранения аудио: {e}")
            
            results.append({
                "text": text,
                "voice": voice,
                "mos_score": mos_score.item(),
                "sample_id": i,
                "audio_path": saved_path,
                "text_length": len(text),
                "timestamp": datetime.now().isoformat()
            })
            
            successful_count += 1
            print(f"  MOS: {mos_score.item():.3f}")
            
            # Очистка временных файлов
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            
            # Пауза между запросами
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"  Ошибка: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
            continue
    
    # Анализ результатов
    if results:
        df = pd.DataFrame(results)
        
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ОЦЕНКИ TTS")
        print("="*60)
        
        print(f"\nОбщая статистика:")
        print(f"  Всего примеров: {len(texts)}")
        print(f"  Успешно обработано: {successful_count}")
        print(f"  Не удалось обработать: {failed_count}")
        print(f"  Успешность: {successful_count/len(texts)*100:.1f}%")
        
        for voice in voices:
            voice_df = df[df["voice"] == voice]
            if len(voice_df) > 0:
                scores = voice_df["mos_score"]
                print(f"\nГолос: {voice.upper()}")
                print(f"  Примеров: {len(voice_df)}")
                print(f"  Средний MOS: {scores.mean():.3f}")
                print(f"  Стандартное отклонение: {scores.std():.3f}")
                print(f"  Лучший: {scores.max():.3f}")
                print(f"  Худший: {scores.min():.3f}")
                print(f"  Медиана: {scores.median():.3f}")
        
        print(f"\nОБЩИЙ СРЕДНИЙ MOS: {df['mos_score'].mean():.3f}")
        
        # Статистика по длине текста
        if 'text_length' in df.columns:
            print(f"\nСтатистика по длине текста:")
            print(f"  Средняя длина текста: {df['text_length'].mean():.1f} символов")
            print(f"  Минимальная длина: {df['text_length'].min()} символов")
            print(f"  Максимальная длина: {df['text_length'].max()} символов")
            
            # Корреляция между длиной текста и MOS
            correlation = df['text_length'].corr(df['mos_score'])
            print(f"  Корреляция длина-MOS: {correlation:.3f}")
        
        # Сохраняем результаты
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV с результатами
        csv_filename = os.path.join(output_dir, f"tts_results_{timestamp}.csv")
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"\nПолные результаты сохранены в: {csv_filename}")
        
        # TXT со статистикой
        stats_filename = os.path.join(output_dir, f"tts_stats_{timestamp}.txt")
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА ОЦЕНКИ TTS КАЧЕСТВА\n")
            f.write("="*60 + "\n")
            f.write(f"Дата оценки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Файл транскриптов: {transcript_file}\n")
            f.write(f"Количество примеров: {len(texts)}\n")
            f.write(f"Успешно обработано: {successful_count}\n")
            f.write(f"Голоса: {', '.join(voices)}\n")
            f.write(f"Распределение: 50% {voices[0]}, 50% {voices[1]}\n")
            f.write(f"Модель MOS: {model_name}\n\n")
            
            for voice in voices:
                voice_df = df[df["voice"] == voice]
                if len(voice_df) > 0:
                    scores = voice_df["mos_score"]
                    f.write(f"ГОЛОС: {voice.upper()}\n")
                    f.write(f"  Примеров: {len(voice_df)}\n")
                    f.write(f"  Средний MOS: {scores.mean():.3f}\n")
                    f.write(f"  Стандартное отклонение: {scores.std():.3f}\n")
                    f.write(f"  Минимум: {scores.min():.3f}\n")
                    f.write(f"  Максимум: {scores.max():.3f}\n")
                    f.write(f"  Медиана: {scores.median():.3f}\n\n")
            
            f.write(f"ОБЩИЙ СРЕДНИЙ: {df['mos_score'].mean():.3f}\n")
        
        print(f"Статистика сохранена в: {stats_filename}")
        
        # README файл
        readme_filename = os.path.join(output_dir, f"README_{timestamp}.txt")
        with open(readme_filename, 'w', encoding='utf-8') as f:
            f.write("ОПИСАНИЕ ЭКСПЕРИМЕНТА\n")
            f.write("="*60 + "\n")
            f.write("Цель: Оценка качества синтеза речи (TTS) с помощью метрики MOS\n")
            f.write("TTS система: Yandex SpeechKit\n")
            f.write(f"Модель MOS: {model_name}\n")
            f.write(f"Файл с текстами: {os.path.basename(transcript_file)}\n")
            f.write(f"Голоса: {', '.join(voices)}\n")
            f.write("Распределение: 50% на каждый голос\n")
            f.write(f"\nСозданные файлы:\n")
            f.write(f"1. {os.path.basename(csv_filename)} - полные результаты\n")
            f.write(f"2. {os.path.basename(stats_filename)} - статистика\n")
            f.write(f"3. Папка 'tts_samples' - примеры синтезированного аудио\n")
        
        print(f"Описание эксперимента сохранено в: {readme_filename}")
        
        return df
    else:
        print("\nНет результатов для анализа")
        return None

def main():
    """Основная функция с CLI интерфейсом"""
    parser = argparse.ArgumentParser(
        description='Оценка качества TTS с помощью метрики MOS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python tts_evaluator.py                    # Быстрый тест (10 примеров)
  python tts_evaluator.py -n 50              # 50 примеров
  python tts_evaluator.py -n 100 -s 20       # 100 примеров, сохранить 20 аудио
  python tts_evaluator.py -v oksana alena    # Тестировать голоса oksana и alena
  python tts_evaluator.py -t custom.txt      # Использовать свой файл транскриптов
  python tts_evaluator.py -m utmos22_weak    # Использовать другую модель MOS
  python tts_evaluator.py --sleep 0.5        # Пауза 0.5 сек между запросами
        
По умолчанию:
  Файл транскриптов: data/speech_dataset/ru/transcript.txt
  Голоса: oksana, zahar (50/50 распределение)
  Модель MOS: utmos22_strong
        """
    )
    
    # Основные параметры
    parser.add_argument('-t', '--transcript', type=str, 
                       default=os.path.join("data", "speech_dataset", "ru", "transcript.txt"),
                       help='Путь к файлу transcript.txt')
    parser.add_argument('-n', '--num_samples', type=int, default=10,
                       help='Количество примеров для оценки (по умолчанию: 10)')
    parser.add_argument('-s', '--save_samples', type=int, default=5,
                       help='Количество аудиофайлов для сохранения (по умолчанию: 5)')
    
    # Параметры голосов
    parser.add_argument('-v', '--voices', nargs=2, default=['oksana', 'zahar'],
                       help='Два голоса для тестирования (по умолчанию: oksana zahar)')
    
    # Параметры модели
    parser.add_argument('-m', '--model', type=str, default='utmos22_strong',
                       choices=['utmos22_strong', 'utmos22_weak', 'uTMOS'],
                       help='Модель для оценки MOS (по умолчанию: utmos22_strong)')
    
    # Параметры производительности
    parser.add_argument('--sleep', type=float, default=0.3,
                       help='Пауза между запросами TTS в секундах (по умолчанию: 0.3)')
    
    # Параметры вывода
    parser.add_argument('-o', '--output', type=str, default='results',
                       help='Директория для сохранения результатов (по умолчанию: results)')
    
    # Быстрый тест
    parser.add_argument('--quick', action='store_true',
                       help='Быстрый тест (5 примеров, 2 аудио)')
    
    # Подробный вывод
    parser.add_argument('--verbose', action='store_true',
                       help='Подробный вывод процесса')
    
    args = parser.parse_args()
    
    # Проверка файла транскриптов
    if not os.path.exists(args.transcript):
        print(f"Ошибка: файл не найден: {args.transcript}")
        print("Проверьте путь или укажите другой файл с помощью -t")
        return
    
    # Настройки быстрого теста
    if args.quick:
        args.num_samples = 5
        args.save_samples = 2
        args.sleep = 0.2
        print("Режим быстрого теста: 5 примеров, 2 аудиофайла")
    
    # Вывод информации о запуске
    print("="*60)
    print("ОЦЕНКА КАЧЕСТВА TTS (СИНТЕЗ РЕЧИ)")
    print("="*60)
    print(f"Файл транскриптов: {args.transcript}")
    print(f"Количество примеров: {args.num_samples}")
    print(f"Сохранить аудио: {args.save_samples}")
    print(f"Голоса: {args.voices[0]} и {args.voices[1]} (50/50 распределение)")
    print(f"Модель MOS: {args.model}")
    print(f"Пауза между запросами: {args.sleep} сек")
    print(f"Директория результатов: {args.output}")
    print("="*60)
    
    # Запускаем оценку
    try:
        results = evaluate_tts_on_transcript(
            transcript_file=args.transcript,
            num_samples=args.num_samples,
            save_samples=args.save_samples,
            voices=args.voices,
            model_name=args.model,
            sleep_time=args.sleep,
            output_dir=args.output
        )
        
        if results is not None:
            print("\n" + "="*60)
            print("ОЦЕНКА ЗАВЕРШЕНА УСПЕШНО!")
            print("="*60)
            print(f"\nРезультаты сохранены в папке: {args.output}")
            print("Содержимое:")
            print(f"  1. tts_results_*.csv - полные результаты")
            print(f"  2. tts_stats_*.txt - статистика")
            print(f"  3. README_*.txt - описание эксперимента")
            print(f"  4. tts_samples/ - примеры синтезированного аудио")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\nОценка прервана пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Устанавливаем seed для воспроизводимости
    random.seed(42)
    np.random.seed(42)
    
    # Запускаем с CLI
    main()