'''from speechkit import Session, SpeechSynthesis

oauth_token = "y0__xDk9KOfBxjB3RMgrPGlnBLttboKFOOCVbn30elawsBFeU3bdQ"
catalog_id = "b1g2ui4nghmpit376hbf"

session = Session.from_yandex_passport_oauth_token(oauth_token, catalog_id)
synthesizeAudio = SpeechSynthesis(session)

synthesizeAudio.synthesize(
    'alena_good.wav',
    text='Какие инструменты Python вы используете для анализа данных? Процитируйте пример использования библиотеки Pandas или Scikit-learn в реальном проекте.',
    voice='alena', # == oksana для старых проектов пока поддерживается и дешевле стоит - 0.14 рублей за 1 генерацию примерно (до 250 символов) --- 2,06 рублей за интервью (15 вопросов)
    emotion='good',
    format='oggopus',
    sampleRateHertz='48000'
)

'''
from speechkit import Session, SpeechSynthesis
from decouple import config
import tempfile

def text_to_audio(text: str, voice: str):
    """Функция синтеза речи с выбором голоса."""
    oauth_token = config("OAUTH_TOKEN")
    catalog_id = config("CATALOG_ID")

    session = Session.from_yandex_passport_oauth_token(oauth_token, catalog_id)
    synthesizeAudio = SpeechSynthesis(session)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        temp_audio_path = temp_audio.name

    synthesizeAudio.synthesize(
        temp_audio_path,
        text=f"{text.strip()}",
        voice=voice,  # Передаем выбранный голос
        format="oggopus",
        sampleRateHertz="48000"
    )

    with open(temp_audio_path, "rb") as f:
        audio_bytes = f.read()

    return audio_bytes

'''
# Пример использования:
text = "Какие инструменты Python вы используете для анализа данных? Процитируйте пример использования библиотеки Pandas или Scikit-learn в реальном проекте."
audio = text_to_audio(text)
'''

'''from speechkit import Session, SpeechSynthesis
from decouple import config
import os

def text_to_audio(text: str):
    oauth_token = config("OAUTH_TOKEN")
    catalog_id = config("CATALOG_ID")

    # Создание сессии
    session = Session.from_yandex_passport_oauth_token(oauth_token, catalog_id)
    synthesizeAudio = SpeechSynthesis(session)

    # Определяем путь к файлу в корне проекта
    audio_file_path = os.path.join(os.getcwd(), "ermil.ogg")

    # Синтез речи в файл
    synthesizeAudio.synthesize(
        audio_file_path,
        text=f"{text.strip()}",  # Убрал лишние пробелы
        voice="ermil",
        format="oggopus",
        sampleRateHertz="48000"
    )

    # Чтение аудиофайла
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()

    return audio_file_path, audio_bytes


# Пример использования:
text = "Какие инструменты Python вы используете для анализа данных? Процитируйте пример использования библиотеки Pandas или Scikit-learn в реальном проекте."
audio_file_path, audio = text_to_audio(text)

print(f"Аудиофайл сохранен по пути: {audio_file_path}")'''