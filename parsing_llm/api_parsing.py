from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import tempfile
import json
from fastapi.middleware.cors import CORSMiddleware
from parsing_documents import read_docx_file, summarize_resume

app = FastAPI(
    title="Resume Parser API",
    description="API для загрузки резюме (.docx/.rtf) и получения структурированного JSON-анализа",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],  # Разрешаем только ваш фронтенд
    allow_credentials=True,
    allow_methods=["*"],  # Можно сузить до ["POST"]
    allow_headers=["*"],  # Можно сузить до ["Content-Type"]
)

@app.post("/parse-resume", summary="Загрузить резюме и получить JSON-анализ")
async def parse_resume(file: UploadFile = File(...)):
    """
    Принимает файл резюме (.docx или .rtf), извлекает текст и возвращает структурированный JSON с анализом.
    """
    if not file.filename.lower().endswith(('.docx', '.rtf')):
        raise HTTPException(status_code=400, detail="Поддерживаются только .docx и .rtf файлы")

    # Сохраняем временно загруженный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # Используем вашу функцию без изменений
        resume_text = read_docx_file(tmp_file_path)
        if not resume_text:
            raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла")

        # Анализируем через вашу функцию
        result = summarize_resume(resume_text)
        if not result:
            raise HTTPException(status_code=500, detail="Не удалось проанализировать резюме")

        # Сохраняем в файл (как в вашем оригинальном коде)
        with open("resume_analysis.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")

    finally:
        # Удаляем временный файл
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


# Для локального тестирования (не обязательно)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)