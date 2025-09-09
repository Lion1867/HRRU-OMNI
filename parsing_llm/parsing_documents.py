import requests
import json
import os
from dotenv import load_dotenv
import docx2txt
from striprtf.striprtf import rtf_to_text

load_dotenv()
API_KEY = os.getenv('OPENROUTER_API_KEY')


def read_docx_file(file_path):
    """Чтение текста из файлов разных форматов"""
    try:
        if file_path.lower().endswith('.docx'):
            # Для DOCX
            return docx2txt.process(file_path)
        elif file_path.lower().endswith('.rtf'):
            # Для RTF
            return read_rtf_simple(file_path)
        else:
            print("Неподдерживаемый формат файла")
            return None
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return None


def read_rtf_simple(file_path):
    """Простое чтение RTF файла"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            rtf_content = f.read()
        text = rtf_to_text(rtf_content)
        return text
    except Exception as e:
        print(f"Ошибка при чтении RTF: {e}")
        return None


def summarize_resume(resume_text):
    """Отправка резюме на суммаризацию и получение структурированного JSON"""
    prompt = f"""
Проанализируй предоставленное резюме и верни структурированные данные в формате JSON.
ВСЕГДА возвращай ТОЛЬКО валидный JSON без каких-либо дополнительных комментариев.

{{
    "specialization": "string with candidate's main specialization",
    "key_skills": ["array", "of", "key", "skills"],
    "key_responsibilities": ["array", "of", "key", "responsibilities"],
    "work_experience": ["general", "experience"],
    "general_experience_number": ["general", "experience"]
}}


Если какая-то информация отсутствует в резюме, используй пустые строки или массивы.

Резюме для анализа:
{resume_text}
"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat-v3.1:free",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"}
            })
        )

        response.raise_for_status()

        result = response.json()
        #print(result)
        json_response = result['choices'][0]['message']['content']
        print("\nИзвлечённая строка для парсинга:")
        #print(repr(json_response))
        print(f"Тип данных json_response: {type(json_response)}")

        if isinstance(json_response, str):
            # Очищаем строку от Markdown-обертки ```json ... ```
            if json_response.startswith("```json"):
                json_response = json_response[7:]  # Удаляем "```json"
            if json_response.endswith("```"):
                json_response = json_response[:-3]  # Удаляем "```"
            # Также удаляем возможные пробелы в начале и конце
            json_response = json_response.strip()

            # Теперь парсим очищенную строку
            parsed_json = json.loads(json_response)
        else:
            parsed_json = json_response
        return parsed_json

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
    except KeyError as e:
        print(f"Ошибка в структуре ответа: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при разборе JSON: {e}")
        return None


# Тестовый локальный запуск

if __name__ == "__main__":
    #file_path = "resume.docx"
    file_path = "resume_1.rtf"
    resume_text = read_docx_file(file_path)

    if resume_text:
        print("Текст резюме прочитан успешно")
        print("Отправка на анализ...")

        result = summarize_resume(resume_text)

        if result:
            print("\nРезультат анализа:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            with open("resume_analysis.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("\nРезультат сохранен в resume_analysis.json")
    else:
        print("Не удалось прочитать файл резюме")