import os
from dotenv import load_dotenv
import requests

# Загрузка переменных окружения из .env файла
load_dotenv()

# Конфигурация
API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")  # Загружаем токен из .env
CATALOG_ID = os.getenv("CATALOG_ID")  # Загружаем ID каталога из .env

# Проверка загрузки переменных
if not OAUTH_TOKEN or not CATALOG_ID:
    raise ValueError("Проверьте ваш .env файл: OAUTH_TOKEN или CATALOG_ID не найдены.")


# Функция для получения IAM-токена из OAuth-токена
def get_iam_token(oauth_token):
    iam_url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "yandexPassportOauthToken": oauth_token
    }
    response = requests.post(iam_url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["iamToken"]
    else:
        print(f"Ошибка при получении IAM-токена: {response.status_code}")
        print(response.text)
        return None


# Функция для отправки запроса к YandexGPT
def generate_text(prompt):
    # Получаем IAM-токен
    iam_token = get_iam_token(OAUTH_TOKEN)
    if not iam_token:
        raise ValueError("Не удалось получить IAM-токен.")

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    data = {
        # Используем последнюю модель YandexGPT 5 Pro
        "modelUri": f"gpt://{CATALOG_ID}/yandexgpt",
        "completionOptions": {
            "maxTokens": 1000,  # Максимальное количество токенов в ответе
            "temperature": 0.7,  # Температура для управления случайностью
            "stream": False  # Отключаем потоковую передачу
        },
        "messages": [
            {
                "role": "user",
                "text": prompt  # Ваш запрос к модели
            }
        ]
    }

    response = requests.post(API_URL, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        return result['result']['alternatives'][0]['message']['text']  # Извлекаем текст ответа
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)
        return None


# Функция для управления интервью
def conduct_interview():
    # Начальный промпт для первого вопроса
    initial_prompt = (
        "Ты - виртуальный HR-ассистент. Твоя задача - провести интервью с кандидатом на позицию Data Scientist. "
        "Начни с приветствия и представься. Задай первый вопрос о том, как кандидат хочет, чтобы его называли."
    )

    # Список для хранения истории диалога
    conversation_history = []

    # Первый запрос к модели
    response = generate_text(initial_prompt)
    if not response:
        print("Ошибка при генерации текста.")
        return

    print("HR-ассистент:", response)  # Выводим первый вопрос
    conversation_history.append({"role": "assistant", "text": response})

    while True:
        # Получаем ответ пользователя
        user_response = input("Вы: ")
        if user_response.lower() in ["стоп", "выход", "закончить"]:
            print("HR-ассистент: Благодарю за участие в интервью! До новых встреч.")
            break

        # Добавляем ответ пользователя в историю
        conversation_history.append({"role": "user", "text": user_response})

        # Формируем новый промпт для модели
        prompt = (
            "Ты - виртуальный HR-ассистент. Продолжай интервью с кандидатом. "
            "Используй историю диалога ниже для контекста. Задай следующий вопрос или заверши интервью, если считаешь, что собрал достаточно информации.\n\n"
            f"История диалога:\n{conversation_history}"
        )

        # Генерация следующего ответа от модели
        assistant_response = generate_text(prompt)
        if not assistant_response:
            print("Ошибка при генерации текста.")
            break

        print("HR-ассистент:", assistant_response)
        conversation_history.append({"role": "assistant", "text": assistant_response})


# Запуск интервью
if __name__ == "__main__":
    print("Добро пожаловать на интервью!")
    conduct_interview()