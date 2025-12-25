import os
import sys
import pandas as pd
import numpy as np
import torch
import librosa
import time
import re
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')
import random
# Добавляем путь к вашему модулю Whisper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'interview_module')))
from openai_whisper_STT import transcribe_audio

# Для метрик WER/CER
try:
    import jiwer
    from jiwer import wer, cer
    JIWER_AVAILABLE = True
except ImportError:
    print("Установите jiwer для метрик WER/CER: pip install jiwer")
    JIWER_AVAILABLE = False

try:
    import evaluate
    EVALUATE_AVAILABLE = True
except ImportError:
    print("Установите evaluate для дополнительных метрик: pip install evaluate")
    EVALUATE_AVAILABLE = False

class WhisperEvaluator:
    """Класс для оценки качества распознавания речи Whisper"""
    
    def __init__(self, model_name="large-v3", language="ru", use_gpu=True):
        """
        Инициализация оценщика STT
        
        Args:
            model_name: название модели Whisper
            language: язык распознавания
            use_gpu: использовать ли GPU
        """
        self.device = "cuda" if torch.cuda.is_available() and use_gpu else "cpu"
        self.language = language
        print(f"Устройство: {self.device}")
        print(f"Язык: {language}")
        
        # Загружаем модель Whisper (уже загружена в импортированном модуле)
        # Функция transcribe_audio уже использует загруженную модель
        print("Модель Whisper готова к использованию")
        
        # Подготовка метрик
        self.metrics = {}
        self.metrics['wer'] = evaluate.load("wer")
        self.metrics['cer'] = evaluate.load("cer")
        print("Метрики evaluate загружены")
    
    def preprocess_text(self, text):
        """Предобработка текста для вычисления метрик"""
        # Приводим к нижнему регистру
        text = text.lower()
        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        # Удаляем пунктуацию (можно настроить по необходимости)
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def load_audio_dataset(self, base_dir, transcript_file, max_samples_per_folder=None):
        """
        Загружает аудиофайлы и соответствующие тексты
        
        Args:
            base_dir: базовая директория с папками аудио
            transcript_file: файл с транскриптами
            max_samples_per_folder: максимальное количество примеров из каждой папки
            
        Returns:
            список словарей с путями к аудио и соответствующими текстами
        """
        print(f"Загрузка датасета из {base_dir}")
        
        # Сначала загружаем все транскрипты
        transcripts = self.load_transcripts(transcript_file)
        print(f"Загружено {len(transcripts)} транскриптов")
        
        # Папки для обработки
        folders = [
            "early_short_stories",
            "icemarch", 
            "shortstories_childrenadults"
        ]
        
        dataset = []
        total_files = 0
        
        for folder in folders:
            folder_path = os.path.join(base_dir, folder)
            if not os.path.exists(folder_path):
                print(f"Папка не найдена: {folder_path}")
                continue
                
            # Ищем все MP3 файлы в папке
            audio_files = list(Path(folder_path).glob("*.mp3"))
            if not audio_files:
                print(f"MP3 файлы не найдены в {folder_path}")
                # Пробуем WAV
                audio_files = list(Path(folder_path).glob("*.wav"))
            
            print(f"Найдено {len(audio_files)} аудиофайлов в {folder}")
            
            # Ограничиваем количество если нужно
            if max_samples_per_folder and len(audio_files) > max_samples_per_folder:
                import random
                audio_files = random.sample(audio_files, max_samples_per_folder)
                print(f"Ограничили до {max_samples_per_folder} файлов")
            
            for audio_file in audio_files:
                # Формируем ключ для поиска в транскриптах
                # Например: early_short_stories/early_short_stories_0001.mp3
                rel_path = f"{folder}/{audio_file.name}"
                
                # Ищем соответствующий текст в транскриптах
                # Проверяем разные варианты имени файла
                possible_keys = [
                    rel_path,
                    rel_path.replace('.mp3', '.wav'),
                    audio_file.name,
                    audio_file.name.replace('.mp3', '.wav')
                ]
                
                ground_truth = None
                for key in possible_keys:
                    if key in transcripts:
                        ground_truth = transcripts[key]
                        break
                
                if ground_truth:
                    dataset.append({
                        'audio_path': str(audio_file),
                        'ground_truth': ground_truth,
                        'folder': folder,
                        'filename': audio_file.name
                    })
                    total_files += 1
                else:
                    print(f"Транскрипт не найден для: {rel_path}")
        
        print(f"Итого загружено {total_files} аудиофайлов с транскриптами")
        return dataset
    
    def load_transcripts(self, transcript_file):
        """
        Загружает транскрипты из файла
        
        Returns:
            словарь {имя_файла: текст}
        """
        transcripts = {}
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Формат: путь|текст1|текст2|длительность
                    parts = line.split('|')
                    if len(parts) >= 3:
                        file_path = parts[0].strip()
                        # Берем второй текст (похоже, это ground truth)
                        text = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                        
                        # Нормализуем путь
                        file_path = file_path.replace('\\', '/')
                        
                        # Извлекаем имя файла
                        filename = os.path.basename(file_path)
                        # Также сохраняем полный путь для поиска
                        transcripts[file_path] = text
                        transcripts[filename] = text
                        
        except Exception as e:
            print(f"Ошибка загрузки транскриптов: {e}")
        
        return transcripts
    
    def transcribe_audio_file(self, audio_path):
        """Транскрибирует аудиофайл с помощью Whisper"""
        try:
            # Проверяем существование файла
            if not os.path.exists(audio_path):
                print(f"Файл не найден: {audio_path}")
                return None
            
            # Проверяем расширение файла
            if not audio_path.lower().endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
                print(f"Неподдерживаемый формат: {audio_path}")
                return None
            
            print(f"Транскрибирую: {os.path.basename(audio_path)}")
            
            # Вызываем функцию транскрипции
            start_time = time.time()
            transcribed_text = transcribe_audio(audio_path, language=self.language)
            transcription_time = time.time() - start_time
            
            print(f"  Время: {transcription_time:.2f} сек")
            print(f"  Результат: {transcribed_text[:50]}...")
            
            return transcribed_text
            
        except Exception as e:
            print(f"Ошибка транскрипции {audio_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def compute_wer_jiwer(self, reference, hypothesis):
        """Вычисляет WER с помощью jiwer"""
        if not JIWER_AVAILABLE:
            return None
        
        try:
            # Предобработка текстов
            ref_processed = self.preprocess_text(reference)
            hyp_processed = self.preprocess_text(hypothesis)
            
            # Вычисляем WER
            wer_score = wer(ref_processed, hyp_processed)
            return wer_score
        except Exception as e:
            print(f"Ошибка вычисления WER: {e}")
            return None
    
    def compute_cer_jiwer(self, reference, hypothesis):
        """Вычисляет CER с помощью jiwer"""
        if not JIWER_AVAILABLE:
            return None
        
        try:
            # Предобработка текстов
            ref_processed = self.preprocess_text(reference)
            hyp_processed = self.preprocess_text(hypothesis)
            
            # Вычисляем CER
            cer_score = cer(ref_processed, hyp_processed)
            return cer_score
        except Exception as e:
            print(f"Ошибка вычисления CER: {e}")
            return None
    
    def compute_word_accuracy_from_wer(self, wer_score):
        """Преобразует WER в Word Accuracy (clamped to [0, 1])"""
        if wer_score is None:
            return None
        accuracy = 1.0 - wer_score
        return max(0.0, min(1.0, accuracy))
    
    def evaluate_on_dataset(self, dataset, max_samples=None, save_results=True):
        """
        Оценивает Whisper на датасете
        
        Args:
            dataset: список словарей с аудио и текстами
            max_samples: максимальное количество примеров
            save_results: сохранять ли результаты
            
        Returns:
            DataFrame с результатами
        """
        if not dataset:
            print("Датасет пуст!")
            return None
        
        # Ограничиваем количество примеров если нужно
        if max_samples and len(dataset) > max_samples:
            import random
            dataset = random.sample(dataset, max_samples)
            print(f"Ограничили до {max_samples} примеров")
        
        results = []
        all_references = []
        all_hypotheses = []
        
        print(f"\nНачинаю оценку на {len(dataset)} примерах...")
        print("="*60)
        
        for i, item in enumerate(dataset):
            print(f"\n[{i+1}/{len(dataset)}] {item['filename']}")
            print(f"  Папка: {item['folder']}")
            print(f"  Ground truth: {item['ground_truth'][:50]}...")
            
            # Транскрибируем аудио
            hypothesis = self.transcribe_audio_file(item['audio_path'])
            
            if hypothesis is None:
                print("  Пропуск: ошибка транскрипции")
                continue
            
            # Вычисляем метрики
            metrics = {
                'audio_path': item['audio_path'],
                'folder': item['folder'],
                'filename': item['filename'],
                'ground_truth': item['ground_truth'],
                'transcription': hypothesis,
                'ground_truth_length': len(item['ground_truth']),
                'transcription_length': len(hypothesis)
            }
            
            # WER с jiwer
            wer_score = self.compute_wer_jiwer(item['ground_truth'], hypothesis)
            if wer_score is not None:
                metrics['wer'] = wer_score
                metrics['wer_percent'] = wer_score * 100
                word_acc = self.compute_word_accuracy_from_wer(wer_score)
                metrics['word_accuracy'] = word_acc
                metrics['word_accuracy_percent'] = word_acc * 100
            
            # CER с jiwer
            cer_score = self.compute_cer_jiwer(item['ground_truth'], hypothesis)
            if cer_score is not None:
                metrics['cer'] = cer_score
                metrics['cer_percent'] = cer_score * 100
            
            # Сохраняем для пакетных вычислений
            all_references.append(item['ground_truth'])
            all_hypotheses.append(hypothesis)
            
            results.append(metrics)
            
            # Выводим промежуточные результаты
            if 'wer' in metrics:
                print(f"  WER: {metrics['wer_percent']:.2f}%")
            if 'cer' in metrics:
                print(f"  CER: {metrics['cer_percent']:.2f}%")
            if 'word_accuracy' in metrics:
                print(f"  Word Accuracy: {metrics['word_accuracy_percent']:.2f}%")
            
            # Небольшая пауза между обработкой файлов
            time.sleep(0.1)
        
        
        # Создаем DataFrame
        if results:
            df = pd.DataFrame(results)
            
            # Выводим общую статистику
            self.print_statistics(df)
            
            # Сохраняем результаты если нужно
            if save_results:
                self.save_results(df)
            
            return df
        else:
            print("\nНет результатов для анализа")
            return None
    
    def print_statistics(self, df):
        """Выводит статистику по результатам"""
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ОЦЕНКИ WHISPER")
        print("="*60)
        
        print(f"\nОбщие результаты:")
        print(f"  Всего примеров: {len(df)}")
        
        if 'wer' in df.columns:
            print(f"\nМетрика WER (Word Error Rate):")
            print(f"  Средний: {df['wer_percent'].mean():.2f}%")
            print(f"  Стандартное отклонение: {df['wer_percent'].std():.2f}%")
            print(f"  Минимум: {df['wer_percent'].min():.2f}%")
            print(f"  Максимум: {df['wer_percent'].max():.2f}%")
            print(f"  Медиана: {df['wer_percent'].median():.2f}%")
        
        if 'cer' in df.columns:
            print(f"\nМетрика CER (Character Error Rate):")
            print(f"  Средний: {df['cer_percent'].mean():.2f}%")
            print(f"  Стандартное отклонение: {df['cer_percent'].std():.2f}%")
            print(f"  Минимум: {df['cer_percent'].min():.2f}%")
            print(f"  Максимум: {df['cer_percent'].max():.2f}%")
            print(f"  Медиана: {df['cer_percent'].median():.2f}%")
        
        if 'word_accuracy' in df.columns:
            print(f"\nWord Accuracy:")
            print(f"  Средний: {df['word_accuracy_percent'].mean():.2f}%")
            print(f"  Стандартное отклонение: {df['word_accuracy_percent'].std():.2f}%")
            print(f"  Минимум: {df['word_accuracy_percent'].min():.2f}%")
            print(f"  Максимум: {df['word_accuracy_percent'].max():.2f}%")
        
        # Статистика по папкам
        if 'folder' in df.columns:
            print(f"\nРезультаты по папкам:")
            for folder in df['folder'].unique():
                folder_df = df[df['folder'] == folder]
                print(f"\n  Папка: {folder}")
                print(f"    Примеров: {len(folder_df)}")
                
                if 'wer_percent' in df.columns:
                    print(f"    Средний WER: {folder_df['wer_percent'].mean():.2f}%")
                if 'cer_percent' in df.columns:
                    print(f"    Средний CER: {folder_df['cer_percent'].mean():.2f}%")
        
        # Лучшие и худшие результаты
        if 'wer' in df.columns and len(df) >= 5:
            print(f"\nТОП-5 лучших результатов (низкий WER):")
            best_results = df.nsmallest(5, 'wer')
            for idx, row in best_results.iterrows():
                print(f"  {row['filename']}: WER={row['wer_percent']:.2f}%")
                print(f"    Текст: {row['ground_truth'][:50]}...")
            
            print(f"\nТОП-5 худших результатов (высокий WER):")
            worst_results = df.nlargest(5, 'wer')
            for idx, row in worst_results.iterrows():
                print(f"  {row['filename']}: WER={row['wer_percent']:.2f}%")
                print(f"    Текст: {row['ground_truth'][:50]}...")
    
    def save_results(self, df):
        """Сохраняет результаты в файлы"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем папку для результатов
        results_dir = "results/whisper_evaluation"
        os.makedirs(results_dir, exist_ok=True)
        
        # Сохраняем полные результаты в CSV
        csv_filename = f"{results_dir}/whisper_results_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        print(f"\nПолные результаты сохранены в: {csv_filename}")
        
        # Сохраняем сводную статистику
        stats_filename = f"{results_dir}/whisper_stats_{timestamp}.txt"
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write("СВОДНАЯ СТАТИСТИКА ОЦЕНКИ WHISPER\n")
            f.write("="*60 + "\n")
            f.write(f"Дата оценки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Модель: Whisper large-v3\n")
            f.write(f"Язык: {self.language}\n")
            f.write(f"Устройство: {self.device}\n")
            f.write(f"Всего примеров: {len(df)}\n\n")
            
            if 'wer_percent' in df.columns:
                f.write("Метрика WER (Word Error Rate):\n")
                f.write(f"  Средний: {df['wer_percent'].mean():.2f}%\n")
                f.write(f"  Стандартное отклонение: {df['wer_percent'].std():.2f}%\n")
                f.write(f"  Минимум: {df['wer_percent'].min():.2f}%\n")
                f.write(f"  Максимум: {df['wer_percent'].max():.2f}%\n")
                f.write(f"  Медиана: {df['wer_percent'].median():.2f}%\n\n")
            
            if 'cer_percent' in df.columns:
                f.write("Метрика CER (Character Error Rate):\n")
                f.write(f"  Средний: {df['cer_percent'].mean():.2f}%\n")
                f.write(f"  Стандартное отклонение: {df['cer_percent'].std():.2f}%\n")
                f.write(f"  Минимум: {df['cer_percent'].min():.2f}%\n")
                f.write(f"  Максимум: {df['cer_percent'].max():.2f}%\n")
                f.write(f"  Медиана: {df['cer_percent'].median():.2f}%\n\n")
            if 'word_accuracy_percent' in df.columns:
                f.write("Word Accuracy (1 - WER):\n")
                f.write(f"  Средний: {df['word_accuracy_percent'].mean():.2f}%\n")
                f.write(f"  Стандартное отклонение: {df['word_accuracy_percent'].std():.2f}%\n")
                f.write(f"  Минимум: {df['word_accuracy_percent'].min():.2f}%\n")
                f.write(f"  Максимум: {df['word_accuracy_percent'].max():.2f}%\n")
                f.write(f"  Медиана: {df['word_accuracy_percent'].median():.2f}%\n\n")
                
        print(f"Статистика сохранена в: {stats_filename}")


def main():
    """Основная функция для запуска оценки"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Оценка качества распознавания речи Whisper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python whisper_evaluator.py                    # Быстрый тест (10 примеров)
  python whisper_evaluator.py --max_samples 50   # 50 примеров
  python whisper_evaluator.py --max_per_folder 10  # 10 примеров из каждой папки
        
Пути по умолчанию:
  Базовая директория: data/speech_dataset/ru/
  Файл транскриптов: data/speech_dataset/ru/transcript.txt
        """
    )
    
    parser.add_argument('--base_dir', type=str, 
                       default=os.path.join("data", "speech_dataset", "ru"),
                       help='Базовая директория с аудиофайлами')
    parser.add_argument('--transcript', type=str, 
                       default=os.path.join("data", "speech_dataset", "ru", "transcript.txt"),
                       help='Путь к файлу transcript.txt')
    parser.add_argument('--max_samples', type=int, default=None,
                       help='Общее максимальное количество примеров')
    parser.add_argument('--max_per_folder', type=int, default=20,
                       help='Максимальное количество примеров из каждой папки')
    parser.add_argument('--language', type=str, default='ru',
                       help='Язык для распознавания (по умолчанию: ru)')
    parser.add_argument('--no_gpu', action='store_true',
                       help='Не использовать GPU даже если доступен')
    parser.add_argument('--quick_test', action='store_true',
                       help='Быстрый тест (5 примеров из каждой папки)')
    
    args = parser.parse_args()
    
    # Для быстрого теста
    if args.quick_test:
        args.max_per_folder = 5
        args.max_samples = 15
    
    # Проверяем существование путей
    if not os.path.exists(args.base_dir):
        print(f"Ошибка: базовая директория не найдена: {args.base_dir}")
        return
    
    if not os.path.exists(args.transcript):
        print(f"Ошибка: файл транскриптов не найден: {args.transcript}")
        return
    
    print("="*60)
    print("ОЦЕНКА КАЧЕСТВА WHISPER (РАСПОЗНАВАНИЕ РЕЧИ)")
    print("="*60)
    print(f"Базовая директория: {args.base_dir}")
    print(f"Файл транскриптов: {args.transcript}")
    print(f"Максимум на папку: {args.max_per_folder}")
    
    # Создаем оценщик
    evaluator = WhisperEvaluator(
        language=args.language,
        use_gpu=not args.no_gpu
    )
    
    # Загружаем датасет
    dataset = evaluator.load_audio_dataset(
        base_dir=args.base_dir,
        transcript_file=args.transcript,
        max_samples_per_folder=args.max_per_folder
    )
    
    if not dataset:
        print("Не удалось загрузить датасет")
        return
    
    # Запускаем оценку
    results = evaluator.evaluate_on_dataset(
        dataset=dataset,
        max_samples=args.max_samples,
        save_results=True
    )
    
    return results


if __name__ == "__main__":
    # Устанавливаем seed для воспроизводимости
    random.seed(42)
    np.random.seed(42)
    
    # Запускаем оценку
    try:
        results = main()
        
        if results is not None:
            print("\n" + "="*60)
            print("ОЦЕНКА ЗАВЕРШЕНА УСПЕШНО!")
            print("="*60)
            print("\nСозданные файлы в папке results/whisper_evaluation/:")
            print("1. whisper_results_*.csv - полные результаты")
            print("2. whisper_stats_*.txt - сводная статистика")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()