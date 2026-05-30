import os
import glob
import json
import re
import shutil
import requests
from datetime import datetime, timedelta
from faster_whisper import WhisperModel

# ========== НАСТРОЙКИ ==========
WHISPER_MODEL = "base"
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Папки
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INCOMING_DIR = os.path.join(BASE_DIR, "core", "data", "incoming")
PROCESSED_DIR = os.path.join(BASE_DIR, "core", "data", "processed")
FAILED_DIR = os.path.join(BASE_DIR, "core", "data", "failed")
LOGS_DIR = os.path.join(BASE_DIR, "core", "data", "logs")

# Telegram (заполнишь потом)
TELEGRAM_TOKEN = "8653669908:AAH0XMZbIx4eVIVf8Hw1l-nLKbqfyQUPA6I"
TELEGRAM_CHAT_ID = "1022165128"

# Удалять файлы старше N дней
DAYS_TO_KEEP = 30
# ===============================

def init_dirs():
    for d in [INCOMING_DIR, PROCESSED_DIR, FAILED_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    with open(os.path.join(LOGS_DIR, "monitor.log"), "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        log_message(f"Telegram error: {e}")

def clean_old_files():
    cutoff = datetime.now() - timedelta(days=DAYS_TO_KEEP)
    for folder in [PROCESSED_DIR, FAILED_DIR]:
        for file in glob.glob(os.path.join(folder, "*")):
            if os.path.getmtime(file) < cutoff.timestamp():
                os.remove(file)
                log_message(f"Удалён старый файл: {file}")

def analyze_with_ollama(text):
    prompt = f"""Ты — эксперт по оценке качества звонков в ресторан. 
Верни ТОЛЬКО JSON. Без лишних слов.

Пример: {{"greeting": true, "restaurant_name": true, "additional_offer": true, "farewell": true}}

Правила:
- greeting: поздоровался ли сотрудник
- restaurant_name: назвал ли ресторан или слово "кальянная", "бар"
- additional_offer: предложил ли доп. услуги, акцию
- farewell: попрощался ли

Текст: {text}

JSON:"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "num_predict": 150}},
            timeout=90
        )
        if response.status_code != 200:
            return {}
        raw = response.json().get('response', '')
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {}
    except Exception as e:
        log_message(f"Ollama error: {e}")
        return {}

def generate_comment(analysis, text):
    low = text.lower()
    issues = []
    if not analysis.get('greeting'): issues.append("❌ не поздоровался")
    if not analysis.get('restaurant_name'): issues.append("❌ не назвал ресторан")
    if not analysis.get('additional_offer'): issues.append("❌ ничего не предложил")
    if not analysis.get('farewell'): issues.append("❌ не попрощался")
    
    bad_words = ["опиздал", "хуй", "попукать", "жопа", "какашка", "перни" "пидор" "бля" "блят"]
    if any(w in low for w in bad_words):
        return "🚨 Сотрудник грубил! Нужно провести беседу."
    if issues:
        return f"⚠️ Нарушения: {', '.join(issues)}."
    return "✅ Отлично! Звонок проведён по стандарту."

def process_file(filepath):
    filename = os.path.basename(filepath)
    log_message(f"Обработка: {filename}")
    
    try:
        # Распознавание
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(filepath, beam_size=5, language="ru")
        text = "".join(segment.text for segment in segments)
        
        # Анализ
        analysis = analyze_with_ollama(text)
        if not analysis:
            low = text.lower()
            analysis = {
                "greeting": any(w in low for w in ["добрый день", "здравствуйте", "алло"]),
                "restaurant_name": any(w in low for w in ["кальян", "бар", "ресторан"]),
                "additional_offer": any(w in low for w in ["акция", "скидка", "предложить"]),
                "farewell": any(w in low for w in ["до свидания", "всего доброго"])
            }
        
        comment = generate_comment(analysis, text)
        
        # Отчёт
        report = f"📞 {filename}\n"
        report += f"{'✅' if analysis.get('greeting') else '❌'} Приветствие\n"
        report += f"{'✅' if analysis.get('restaurant_name') else '❌'} Название\n"
        report += f"{'✅' if analysis.get('additional_offer') else '❌'} Предложение\n"
        report += f"{'✅' if analysis.get('farewell') else '❌'} Прощание\n"
        report += f"\n💬 {comment}"
        
        send_telegram(report)
        log_message(f"Успешно: {filename}")
        
        # Перемещаем в processed
        shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
        
    except Exception as e:
        log_message(f"Ошибка {filename}: {e}")
        shutil.move(filepath, os.path.join(FAILED_DIR, filename))

def main():
    init_dirs()
    log_message("Запуск мониторинга")
    
    # Очистка старых файлов
    clean_old_files()
    
    # Обработка новых файлов
    files = glob.glob(os.path.join(INCOMING_DIR, "*.mp3")) + \
            glob.glob(os.path.join(INCOMING_DIR, "*.wav")) + \
            glob.glob(os.path.join(INCOMING_DIR, "*.m4a"))
    
    if not files:
        log_message("Нет новых файлов")
    else:
        log_message(f"Найдено файлов: {len(files)}")
        for file in files:
            process_file(file)
    
    log_message("Завершено")

if __name__ == "__main__":
    main()
