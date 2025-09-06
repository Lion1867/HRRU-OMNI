import os
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")
CATALOG_ID = os.getenv("CATALOG_ID")

if not OAUTH_TOKEN or not CATALOG_ID:
    raise ValueError("Проверьте ваш .env файл: OAUTH_TOKEN или CATALOG_ID не найдены.")

# ===== Получение IAM-токена =====
def get_iam_token(oauth_token):
    iam_url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    headers = {"Content-Type": "application/json"}
    data = {"yandexPassportOauthToken": oauth_token}
    response = requests.post(iam_url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["iamToken"]
    else:
        print("Ошибка получения IAM токена:", response.text)
        return None

# ===== Запрос к YandexGPT =====
def generate_text(prompt):
    iam_token = get_iam_token(OAUTH_TOKEN)
    if not iam_token:
        raise ValueError("Не удалось получить IAM-токен.")

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{CATALOG_ID}/yandexgpt",
        "completionOptions": {
            "maxTokens": 200,  # Уменьшаем количество токенов для краткости
            "temperature": 0.7,
            "stream": False
        },
        "messages": [{"role": "user", "text": prompt}]
    }

    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['result']['alternatives'][0]['message']['text']
    else:
        print("Ошибка генерации текста:", response.text)
        return None

# ===== Генерация вопросов для навыков =====
def generate_question(skill):
    prompt = f"Сформулируй краткий вопрос для собеседования, который проверяет навык '{skill}' у кандидата, в одном предложении. Но не проси написать код."
    return generate_text(prompt)

# ===== Тестирование через консоль =====
def run_interview(skills):
    chat_history = ""
    total_score = 0
    total_skills = len(skills)

    for skill in skills:
        print(f"- {skill}")

    skill_questions = {}
    for skill in skills:
        question = generate_question(skill)
        print(f"Вопрос для навыка '{skill}': {question}")
        skill_questions[skill] = question

    # Интервью
    print("\n=== Начинаем интервью с пользователем: ===")
    for skill in skills:
        print(f"\n=== Навык: {skill} ===")
        print(f"Вопрос: {skill_questions[skill]}")
        user_answer = input("Ваш ответ: ")

        chat_history += f"\nНавык: {skill}\nВопрос: {skill_questions[skill]}\nОтвет: {user_answer}\n"

        score = rate_answer(skill, user_answer)
        print("Оценка:", score)

        total_score += score

        if (score == 3) or (score == 4):  # Уточняющий вопрос только для оценки 3 или 4
            followup = generate_text(
                f"На основе следующей истории диалога с кандидатом:\n{chat_history}\n"
                f"Сформулируй один уточняющий вопрос, чтобы глубже проверить навык '{skill}', если это необходимо. Но не проси написать код."
            )
            print("Уточняющий вопрос:", followup)
            followup_answer = input("Ответ: ")
            chat_history += f"Уточнение: {followup}\nОтвет: {followup_answer}\n"

            followup_score = rate_answer(skill, followup_answer)
            final_score = max(score, followup_score)
        else:
            final_score = score

        print(f"Финальная оценка навыка '{skill}': {final_score}/5")

    # Рассчитываем общий процент
    percentage_score = (total_score / (total_skills * 5)) * 100
    print(f"\nОбщий процент соответствия вакансии: {percentage_score:.2f}%")

# ===== Оценка ответа =====
def rate_answer(skill, answer):
    prompt = (
        f"Оцени по шкале от 1 до 5, насколько хорошо кандидат продемонстрировал навык '{skill}' в этом ответе:\n"
        f"Ответ: {answer}\n"
        f"Ответь одним числом. Оценка должна учитывать конкретность, примеры и глубину ответа."
    )
    score_text = generate_text(prompt)
    try:
        return int(score_text.strip())
    except:
        return 3

# ===== Получение навыков из описания вакансии =====
def analyze_job_requirements(desc):
    prompt = f"Проанализируй следующее описание вакансии и выдели только ключевые навыки (игнорируя описание вакансии):\n{desc}"
    return generate_text(prompt)

# Фильтрация навыков
def clean_skills(raw_skills):
    skills = [s.strip("-• ").strip() for s in raw_skills.split("\n") if s.strip() and "Ищем" not in s and not s.lower().startswith("ключевые навыки")]
    return skills

# Пример использования
if __name__ == "__main__":
    job_description = """
    Мы ищем ML-инженера, который превращает идеи в работающие модели и масштабируемые решения.  
    Важна способность не только разрабатывать алгоритмы, но и интегрировать их в production, обеспечивая стабильность и высокую производительность.  
    Ожидаем, что вы уверенно владеете Python, понимаете математическую основу моделей машинного обучения и умеете работать с фреймворками TensorFlow или PyTorch.  
    Также от вас потребуется:  
    - Опыт построения конвейеров обработки данных (ETL).  
    - Знание облачных платформ (AWS, GCP, Azure) для развертывания моделей.  
    - Умение оптимизировать код для работы с большими объемами данных.  
    - Понимание принципов CI/CD для автоматизации процессов обучения и развертывания.  
    Умение тестировать модели и проводить A/B-тестирование — большой плюс.  
    """

    # Получаем список навыков из описания вакансии
    raw_skills = analyze_job_requirements(job_description)
    skills_list = clean_skills(raw_skills)

    run_interview(skills_list)




