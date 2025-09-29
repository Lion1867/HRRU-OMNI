import os
import whisper
import librosa

# Убедитесь, что путь к FFmpeg указан
os.environ["PATH"] += os.pathsep + r"E:\ffmpeg-7.1-full_build\bin"

# Загрузка модели Whisper (large-v3) с использованием GPU
# model = whisper.load_model("large-v3", device="cuda")
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("large-v3", device=device)


# Функция для загрузки аудиофайла
def load_audio(file_path):
    speech, rate = librosa.load(file_path, sr=16000)
    return speech, rate


# Функция для транскрипции с временными метками
def transcribe_audio(audio_file, language="ru"):
    """Функция для транскрипции аудио с временными метками."""

    print("Обработка началась...")

    # Запуск транскрипции с временными метками
    result = model.transcribe(
        audio_file,
        language=language,
        verbose=True,  # Показывать прогресс обработки
        fp16=True,  # Использовать GPU
        word_timestamps=True  # Включить временные метки для слов
    )

    print("\nИзвлечённый текст с временными метками:")
    full_text = ""
    for segment in result['segments']:
        full_text += segment['text'] + " "

    return full_text.strip()

'''
# Функция, принимающая .wav файл и возвращающая текст
def transcribe_wav_to_text(audio_file):
    """Принимает .wav файл, выполняет транскрипцию и возвращает текст."""

    text = transcribe_audio(audio_file, model)
    return text


# Пример использования
audio_file = "try/input.wav"
transcribed_text = transcribe_wav_to_text(audio_file)

print("\nТранскрибированный текст:")
print(transcribed_text)
'''