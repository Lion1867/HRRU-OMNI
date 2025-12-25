import sys
import os
import subprocess
import configparser
from datetime import datetime

def ansi_to_html(text):
    replacements = {
        '\033[92m': '<span style="color: green;">',
        '\033[91m': '<span style="color: red;">',
        '\033[93m': '<span style="color: orange;">',
        '\033[94m': '<span style="color: blue;">',
        '\033[0m': '</span>',
    }
    for ansi, html in replacements.items():
        text = text.replace(ansi, html)
    return text

def run_test(cmd, title, logfile=None):
    log_lines = [f"\n<h2>{title}</h2>", "<pre>"]
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        output = result.stdout + "\n" + result.stderr
        if logfile:
            with open(logfile, "w", encoding="utf-8") as f:
                f.write(output)
    except Exception as e:
        output = f"Ошибка запуска: {e}"
    output = ansi_to_html(output)
    log_lines.append(output)
    log_lines.append("</pre><hr>")
    return "\n".join(log_lines)

def main(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)

    tests_dir = config['paths']['tests_dir']
    venv_activate = config['paths']['venv_path']

    # Работаем из папки тестов
    os.chdir(tests_dir)

    html_parts = []
    html_parts.append(f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>AI Тесты — Отчёт</title>
        <style>
            body {{ font-family: Consolas, monospace; background: #f8f9fa; padding: 20px; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            h2 {{ color: #3498db; margin-top: 30px; }}
            pre {{ background: #fff; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            hr {{ border: 0; border-top: 1px solid #eee; margin: 30px 0; }}
        </style>
    </head>
    <body>
        <h1>Отчёт по AI-тестам</h1>
        <p>Время генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
    """)

    # --- TTS ---
    n_tts = config['general']['num_samples_tts']
    cmd_tts = f'"{venv_activate}" && python yandex_speechkit_tts_test.py --num_samples {n_tts}'
    html_parts.append(run_test(cmd_tts, "Yandex TTS", "tts_last_run.log"))

    # --- STT ---
    n_stt = config['general']['num_samples_stt']
    cmd_stt = f'"{venv_activate}" && python whisper_stt_test.py --max_samples {n_stt}'
    html_parts.append(run_test(cmd_stt, "Whisper STT", "stt_last_run.log"))

    # --- LLM ---
    n_llm = config['general']['num_samples_llm']
    cmd_llm = f'"{venv_activate}" && python yandex_llm_test.py --num_samples {n_llm}'
    html_parts.append(run_test(cmd_llm, "Yandex LLM", "llm_last_run.log"))

    # --- SadTalker ---
    sad = config['sadtalker']
    n_sad = config['general']['num_samples_sadtalker']
    cmd_sad = (
        f'"{venv_activate}" && python sadtalker_batch_test.py '
        f'--images_dir "{sad["images_dir"]}" '
        f'--audios_dir "{sad["audios_dir"]}" '
        f'--output_dir "{sad["output_dir"]}" '
        f'--num_samples {n_sad}'
    )
    html_parts.append(run_test(cmd_sad, "SadTalker (LipSync)", "sadtalker_last_run.log"))

    html_parts.append("</body></html>")

    report_path = config['output']['report_html']
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"Отчёт сохранён: {report_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python generate_ai_report.py config.ini")
        sys.exit(1)
    main(sys.argv[1])