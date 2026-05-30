# analyzer.py
from rapidfuzz import fuzz

def check_rules(text, rules, threshold=80):
    """
    Проверяет текст по заданным правилам.
    Возвращает словарь: название_правила -> True/False
    """
    results = {}
    words = text.lower().split()
    for rule_name, keywords in rules.items():
        found = False
        for keyword in keywords:
            # Проверяем, содержится ли ключевое слово (с ошибками) в тексте
            for word in words:
                if fuzz.partial_ratio(keyword, word) > threshold:
                    found = True
                    break
            if found:
                break
        results[rule_name] = found
    return results

# Наши правила для контроля качества
RESTAURANT_RULES = {
    "Вежливое приветствие": ["добрый день", "добрый вечер", "здравствуйте", "алло"],
    "Название ресторана": ["кальянная", "шампура", "trendy shop"],
    "Предложение доп. услуг": ["кальян", "дополнительно", "акция", "скидка", "рекомендую", "попробуйте"],
    "Вежливое прощание": ["до свидания", "всего доброго", "всего хорошего", "обращайтесь"]
}
