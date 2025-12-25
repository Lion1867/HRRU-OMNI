import requests
from decouple import config

def text_to_audio(text: str, voice: str = "alyss") -> bytes:
    """
    Синтез речи через Yandex SpeechKit REST API.
    Возвращает аудио в формате ogg/opus (байты).
    """
    oauth_token = config("OAUTH_TOKEN")
    folder_id = config("CATALOG_ID")

    # 1. Получаем IAM-токен
    iam_resp = requests.post(
        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        json={"yandexPassportOauthToken": oauth_token}
    )
    iam_resp.raise_for_status()
    iam_token = iam_resp.json()["iamToken"]

    # 2. Запрос синтеза речи
    tts_resp = requests.post(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        headers={"Authorization": f"Bearer {iam_token}"},
        data={
            "text": text.strip(),
            "lang": "ru-RU",
            "voice": voice,
            "folderId": folder_id,
            "format": "oggopus",
            "sampleRateHertz": "48000"
        }
    )
    tts_resp.raise_for_status()

    return tts_resp.content  # байты oggopus