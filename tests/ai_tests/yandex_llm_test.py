import os
import sys
import pandas as pd
import numpy as np
import time
import re
import random
from datetime import datetime
import warnings
import argparse
from typing import List, Dict, Optional

warnings.filterwarnings('ignore')

# Добавляем путь к модулю с Yandex LLM
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Real_time_HR')))
from try_generation_Yandex import generate_text

# === Импорты метрик ===
EVALUATE_AVAILABLE = False
NLTK_AVAILABLE = False
SBERT_AVAILABLE = False
sbert_model = None

try:
    import evaluate
    from evaluate import load
    EVALUATE_AVAILABLE = True
    print("Библиотека evaluate доступна")
except ImportError:
    print("Установите evaluate: pip install evaluate")

try:
    import nltk
    NLTK_AVAILABLE = True
    for res in ['punkt', 'wordnet', 'omw-1.4']:
        try:
            nltk.data.find(f'tokenizers/punkt' if res == 'punkt' else f'corpora/{res}')
        except LookupError:
            nltk.download(res, quiet=True)
except ImportError:
    print("Установите nltk: pip install nltk")

try:
    from sentence_transformers import SentenceTransformer, util
    sbert_model = SentenceTransformer('cointegrated/rubert-tiny2')
    SBERT_AVAILABLE = True
    print("SBERT модель загружена")
except Exception as e:
    print(f"Не удалось загрузить SBERT: {e}")

class YandexLLMEvaluator:
    def __init__(self, model_config: Dict = None):
        if model_config is None:
            model_config = {}
        self.config = {
            'max_tokens': model_config.get('max_tokens', 1000),
            'temperature': model_config.get('temperature', 0.7),
            'sleep_time': model_config.get('sleep_time', 1.0),
            'retry_attempts': model_config.get('retry_attempts', 3)
        }
        self.metrics = {}
        self._init_metrics()

    def _init_metrics(self):
        if not EVALUATE_AVAILABLE:
            return
       
    def load_ru_mt_bench_dataset(self, num_samples: int = None):
        from datasets import load_dataset
        dataset = load_dataset("t-tech/ru-mt-bench", split="train")
        df_raw = dataset.to_pandas()
        print(f"Датасет загружен. Размер: {len(df_raw)}")
        print(f"Колонки: {list(df_raw.columns)}")

        records = []
        for idx, row in df_raw.iterrows():
            turns = row.get('turns', [])
            refs = row.get('reference', [])

            # Обработка turns: превращаем в список строк
            if turns is None:
                turns_list = []
            elif isinstance(turns, str):
                turns_list = [turns]
            elif isinstance(turns, (list, tuple)):
                turns_list = [t for t in turns if isinstance(t, str) and t.strip()]
            elif hasattr(turns, '__iter__') and not isinstance(turns, (str, bytes)):
                # numpy array, pd.Series и т.п.
                turns_list = [t for t in turns if isinstance(t, str) and t.strip()]
            else:
                turns_list = []

            # Обработка reference
            if refs is None:
                refs_list = []
            elif isinstance(refs, str):
                refs_list = [refs]
            elif isinstance(refs, (list, tuple)):
                refs_list = [r for r in refs if isinstance(r, str) and r.strip()]
            elif hasattr(refs, '__iter__') and not isinstance(refs, (str, bytes)):
                refs_list = [r for r in refs if isinstance(r, str) and r.strip()]
            else:
                refs_list = []

            # Берём пары
            min_len = min(len(turns_list), len(refs_list))
            for i in range(min_len):
                records.append({
                    'prompt': turns_list[i],
                    'reference': refs_list[i],
                    'category': row.get('category', 'general')
                })

        df = pd.DataFrame(records)
        print(f"Преобразовано в {len(df)} корректных пар (prompt, reference)")

        if len(df) == 0:
            print("Датасет не содержит валидных данных. Используем тестовые данные.")
            return self._create_test_data(num_samples or 20)

        if num_samples and len(df) > num_samples:
            df = df.sample(n=num_samples, random_state=42).reset_index(drop=True)
            print(f"Ограничено до {num_samples} примеров")

        return df

    def preprocess_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text

    def generate_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        for attempt in range(max_retries):
            try:
                enhanced_prompt = f"{prompt}\n\nОтвечай кратко."
                response = generate_text(enhanced_prompt)
                if response and isinstance(response, str) and response.strip():
                    # Обрезаем слишком длинные ответы (первые 50 слов)
                    words = response.strip().split()
                    if len(words) > 50:
                        response = ' '.join(words[:50]) + "..."
                    return response
            except Exception as e:
                print(f"  Ошибка (попытка {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        return None

    def compute_semantic_similarity(self, references: List[str], hypotheses: List[str]):
        if not SBERT_AVAILABLE:
            return None
        try:
            similarities = []
            for ref, hyp in zip(references, hypotheses):
                e1 = sbert_model.encode(ref, convert_to_tensor=True)
                e2 = sbert_model.encode(hyp, convert_to_tensor=True)
                sim = util.pytorch_cos_sim(e1, e2).item()
                similarities.append(sim)
            return {
                'mean_similarity': float(np.mean(similarities)),
                'std_similarity': float(np.std(similarities)),
                'min_similarity': float(np.min(similarities)),
                'max_similarity': float(np.max(similarities))
            }
        except Exception as e:
            print(f"SBERT ошибка: {e}")
            return None

    def evaluate_on_dataset(self, dataset: pd.DataFrame, num_samples: int = None, save_results: bool = True):
        required = ['prompt', 'reference']
        if not all(col in dataset.columns for col in required):
            print(f"Ошибка: нужны колонки {required}, есть {list(dataset.columns)}")
            return None

        if num_samples and len(dataset) > num_samples:
            dataset = dataset.sample(n=num_samples, random_state=42).reset_index(drop=True)

        print(f"\nОценка на {len(dataset)} примерах...")
        results = []
        all_refs, all_hyps = [], []

        for i, row in dataset.iterrows():
            prompt, ref = row['prompt'], row['reference']
            print(f"\n[{i+1}/{len(dataset)}] Промпт: {prompt[:50]}...")

            start = time.time()
            hyp = self.generate_with_retry(prompt, self.config['retry_attempts'])
            gen_time = time.time() - start

            if hyp is None:
                continue

            all_refs.append(ref)
            all_hyps.append(hyp)

            results.append({
                'prompt': prompt,
                'reference': ref,
                'hypothesis': hyp,
                'generation_time': gen_time,
                'reference_length': len(ref.split()),
                'hypothesis_length': len(hyp.split()),
                'sample_id': i
            })

            time.sleep(self.config['sleep_time'])

        if not results:
            print("Нет результатов")
            return None

        print(f"\nВычисление метрик на {len(all_refs)} примерах...")
        batch_metrics = self.compute_all_metrics(all_refs, all_hyps)
        df_results = pd.DataFrame(results)
        self.print_statistics(df_results, batch_metrics)
        if save_results:
            self.save_results(df_results, batch_metrics)
        return df_results

    def compute_all_metrics(self, references: List[str], hypotheses: List[str]) -> Dict:
        metrics = {}
        sem_sim = self.compute_semantic_similarity(references, hypotheses)
        if sem_sim: metrics['semantic_similarity'] = sem_sim
        return metrics

    def print_statistics(self, df_results: pd.DataFrame, batch_metrics: Dict):
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ОЦЕНКИ YANDEX LLM")
        print("="*60)
        print(f"\nОбщая статистика:")
        print(f"  Примеров: {len(df_results)}")
        print(f"  Среднее время генерации: {df_results['generation_time'].mean():.2f} сек")
        print(f"  Средняя длина референса: {df_results['reference_length'].mean():.1f} слов")
        print(f"  Средняя длина гипотезы: {df_results['hypothesis_length'].mean():.1f} слов")

        print(f"\nМетрики качества:")
        
        if 'semantic_similarity' in batch_metrics:
            s = batch_metrics['semantic_similarity']
            print(f"  SBERT (семантическое сходство): {s.get('mean_similarity', 0):.4f}")


    def save_results(self, df_results: pd.DataFrame, batch_metrics: Dict):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = "results/llm_evaluation"
        os.makedirs(results_dir, exist_ok=True)

        csv_path = f"{results_dir}/llm_results_{timestamp}.csv"
        df_results.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"\nРезультаты: {csv_path}")

        txt_path = f"{results_dir}/llm_stats_{timestamp}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("ОЦЕНКА YANDEX LLM\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Примеров: {len(df_results)}\n\n")
            
            if 'semantic_similarity' in batch_metrics:
                f.write(f"SBERT: {batch_metrics['semantic_similarity'].get('mean_similarity', 0):.4f}\n")

        json_path = f"{results_dir}/llm_metrics_{timestamp}.json"
        import json
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(batch_metrics, f, ensure_ascii=False, indent=2)
        print(f"Метрики: {json_path}")


def main():
    parser = argparse.ArgumentParser(description='Оценка Yandex LLM')
    parser.add_argument('-n', '--num_samples', type=int, default=10)
    parser.add_argument('--max_tokens', type=int, default=1000)
    parser.add_argument('--temperature', type=float, default=0.7)
    parser.add_argument('--sleep', type=float, default=1.0)
    parser.add_argument('--retries', type=int, default=3)
    parser.add_argument('--quick', action='store_true')

    args = parser.parse_args()
    if args.quick:
        args.num_samples = 5
        args.sleep = 0.5

    print("="*60)
    print("ОЦЕНКА YANDEX LLM")
    print("="*60)

    model_config = {
        'max_tokens': args.max_tokens,
        'temperature': args.temperature,
        'sleep_time': args.sleep,
        'retry_attempts': args.retries
    }

    evaluator = YandexLLMEvaluator(model_config)
    dataset = evaluator.load_ru_mt_bench_dataset(args.num_samples)
    if dataset is not None:
        evaluator.evaluate_on_dataset(dataset, args.num_samples)


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)
    main()