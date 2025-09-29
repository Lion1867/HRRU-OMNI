FROM pytorch/pytorch:2.2.2-cuda12.1-cudnn8-runtime

# Установка системных и build-зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    portaudio19-dev \
    libasound2-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .


RUN pip install --no-cache-dir protobuf==4.25.3
RUN pip install --no-cache-dir grpcio==1.60.0 grpcio-tools==1.60.0

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

EXPOSE 8122

CMD ["python", "text_audio_questions_api.py"]