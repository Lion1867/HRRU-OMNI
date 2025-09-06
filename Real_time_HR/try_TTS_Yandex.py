import os
from dotenv import load_dotenv
from speechkit import Session, SpeechSynthesis
import tempfile

# Загружаем переменные из .env
load_dotenv()


def text_to_audio(text: str, voice: str):
    """Функция синтеза речи с выбором голоса."""
    oauth_token = os.getenv("OAUTH_TOKEN")
    catalog_id = os.getenv("CATALOG_ID")

    if not oauth_token or not catalog_id:
        raise ValueError("Проверьте наличие OAUTH_TOKEN и CATALOG_ID в .env файле.")

    session = Session.from_yandex_passport_oauth_token(oauth_token, catalog_id)
    synthesizeAudio = SpeechSynthesis(session)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        temp_audio_path = temp_audio.name

    synthesizeAudio.synthesize(
        temp_audio_path,
        text=text.strip(),
        voice=voice,
        format="oggopus",
        sampleRateHertz="48000"
    )

    with open(temp_audio_path, "rb") as f:
        audio_bytes = f.read()

    # Удаляем временный файл после чтения
    os.remove(temp_audio_path)

    return audio_bytes


def test_text_to_audio_from_file(input_file_path: str, output_audio_path: str, voice: str = "oksana"):
    """
    Тестирует функцию text_to_audio, используя текст из файла.

    :param input_file_path: Путь к текстовому файлу с входным текстом.
    :param output_audio_path: Путь для сохранения результирующего аудиофайла.
    :param voice: Голос для синтеза речи (по умолчанию "oksana").
    """
    # Проверяем существование входного файла
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"Файл {input_file_path} не найден.")

    # Читаем текст из файла
    with open(input_file_path, "r", encoding="utf-8") as file:
        text = file.read()

    # Выполняем синтез речи
    try:
        audio_bytes = text_to_audio(text, voice)
    except Exception as e:
        print(f"Ошибка при синтезе речи: {e}")
        return

    # Сохраняем результат в файл
    with open(output_audio_path, "wb") as audio_file:
        audio_file.write(audio_bytes)

    print(f"Аудиофайл успешно сохранён: {output_audio_path}")


if __name__ == "__main__":
    # Путь к входному текстовому файлу
    input_file = "try_TTS_Yandex.txt"

    # Путь для сохранения выходного аудиофайла
    output_file = "output_audio.wav"

    # Выбираем голос "oksana"
    # voice = "oksana"
    voice = "zahar"

    # Тестируем функцию
    try:
        test_text_to_audio_from_file(input_file, output_file, voice)
    except Exception as e:
        print(f"Тестирование завершилось с ошибкой: {e}")