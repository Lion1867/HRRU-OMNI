'''import requests
import json

# URL API Ollama
URL = "http://localhost:11434/api/generate"

# Заголовки запроса
HEADERS = {
    "Content-Type": "application/json",
}

def generate_interview_questions(position: str, skills: str):
    """
    Отправляет запрос к Ollama для генерации вопросов собеседования.

    :param position: Должность (например, 'Python-разработчик')
    :param skills: Навыки через запятую (например, 'FastAPI, PostgreSQL, Docker')
    :return: Словарь с 15 вопросами в формате {номер: вопрос}
    """

    # Формируем промпт
    prompt = (
        f"Ты - ИИ-ассистент, проводящий собеседование соискателя на должность {position}. "
        f"Задавай вопросы соискателю, чтобы понять его владение инструментами {skills}. "
        "Вопросы должны быть ясными, лаконичными и точными. Пиши вопросы на русском языке. "
        "Поприветствуй соискателя, спроси о предыдущем опыте работы, целях и мотивации работать в твоей компании. "
        "Поддерживай деловой стиль общения. Ответь в формате JSON: "
        '{"1": "вопрос1", "2": "вопрос2", ..., "15": "вопрос15"}'
    )

    # Данные запроса
    data = {
        "model": "qwen2.5:14b",
        "prompt": prompt,
        "stream": False  # Отключаем потоковый вывод
    }

    # Отправка POST-запроса
    response = requests.post(URL, headers=HEADERS, json=data)

    # Проверка статуса ответа
    if response.status_code == 200:
        # Извлекаем JSON-ответ
        response_data = response.json()
        try:
            # Парсим JSON-ответ (Ollama может вернуть строку)
            questions = json.loads(response_data.get("response", "{}"))
            return questions
        except json.JSONDecodeError:
            print("Ошибка: Модель вернула некорректный JSON.")
            return {}
    else:
        print("Ошибка запроса:", response.status_code, response.text)
        return {}
'''
'''
# Пример использования
position = "Data Scientist"
skills = "Python, машинное обучение, нейросети, SQL"

questions_json = generate_interview_questions(position, skills)
print(json.dumps(questions_json, indent=2, ensure_ascii=False))  # Выводим в красивом формате
'''

import requests
import json

# URL API Ollama
URL = "http://localhost:11434/api/generate"

# Заголовки запроса
HEADERS = {
    "Content-Type": "application/json",
}

def generate_interview_questions(position: str, skills: str, num_questions: int):
    """
    Отправляет запрос к Ollama для генерации вопросов собеседования.

    :param position: Должность (например, 'Python-разработчик')
    :param skills: Навыки через запятую (например, 'FastAPI, PostgreSQL, Docker')
    :param num_questions: Количество вопросов, которые нужно сгенерировать
    :return: Словарь с вопросами в формате {номер: вопрос}
    """

    # Формируем промпт
    prompt = (
        f"Ты - ИИ-ассистент, проводящий собеседование соискателя на должность {position}. "
        f"Задавай вопросы соискателю, чтобы понять его владение инструментами {skills}. "
        "Вопросы должны быть ясными, лаконичными и точными. Пиши вопросы на русском языке. "
        "Поприветствуй соискателя, спроси о предыдущем опыте работы, целях и мотивации работать в твоей компании. "
        "Вопросы должны быть направлены на количественную оценку уровня владения навыками. "
        "Поддерживай деловой стиль общения. Ответь в формате JSON: "
        f'{{"1": "вопрос1", "2": "вопрос2", ..., "{num_questions}": "вопрос{num_questions}"}}'
    )

    # Данные запроса
    data = {
        "model": "qwen2.5:14b",
        "prompt": prompt,
        "stream": False  # Отключаем потоковый вывод
    }

    # Отправка POST-запроса
    response = requests.post(URL, headers=HEADERS, json=data)

    # Проверка статуса ответа
    if response.status_code == 200:
        # Извлекаем JSON-ответ
        response_data = response.json()
        try:
            # Парсим JSON-ответ (Ollama может вернуть строку)
            questions = json.loads(response_data.get("response", "{}"))
            return questions
        except json.JSONDecodeError:
            print("Ошибка: Модель вернула некорректный JSON.")
            return {}
    else:
        print("Ошибка запроса:", response.status_code, response.text)
        return {}