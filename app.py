from flask import Flask, request, jsonify
import requests
import json
import os
import re
from datetime import datetime

app = Flask(__name__)

# ==================== НАСТРОЙКИ ====================
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', 'your_token_here')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('PHONE_ID', '1074769115709415')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')

# Контакты ОсОО "Арай групп" (единственные разрешенные)
ARAY_PHONE = "996555386983"
ARAY_PHONE_DISPLAY = "0(555) 38 69 83"

# OpenRouter для ИИ (бесплатно)
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_KEY', 'your_key_here')

# Хранилище сессий и истории диалогов
user_sessions = {}
user_dialog_history = {}  # Для отправки менеджеру

# ==================== ПРОМПТ ДЛЯ ИИ ====================
SYSTEM_PROMPT = """Ты — AI-ассистент ОсОО "Арай групп", официального агента страховой компании "Бакай Иншуренс" (15 лет опыта).

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

1. ЯЗЫК: Отвечай СТРОГО на том языке, которым пишет клиент (русский, кыргызский, английский, китайский).

2. КРАТКОСТЬ: Максимум 2-4 предложения на сообщение.

3. ЭМОДЗИ: Только ОДИН эмодзи в конце сообщения (😊, 🚗, 🛡️, 💰).

4. КЭШБЭК 10% до 31 августа 2026года: через 3 сообщения упоминай эксклюзивный кэшбэк 10% от ОсОО "Арай групп"!

5. ОСАГО: Активно предлагай оформить ОСАГО через заявку в чате.

6. ЦЕНА: Если спрашивают цену — не называй суммы наугад. Скажи, что нужны параметры для точного расчёта, и запроси:
   - Опыт вождения
   - Государственный номер
   - Объём двигателя

7. КОНТАКТЫ: ТОЛЬКО контакты ОсОО "Арай групп":
   - Телефон/WhatsApp: 0(555) 38 69 83
   - График: Пн-Вс 9:00-18:00
   ЗАПРЕЩЕНО давать контакты Бакай напрямую!

8. ПРОДУКТЫ:
   - ОСАГО: от 1,800 сом/год (с кэшбэком ещё дешевле!)
   - КАСКО: от 15,000 сом/год

9. САЙТ: Можешь ссылаться на insurancebakai.kg для информации об услугах.

10. ЦЕЛЬ: Собрать данные клиента и передать менеджеру."""

# ==================== ОПРЕДЕЛЕНИЕ ЯЗЫКА ====================
def detect_language(text):
    """Определение языка текста"""
    text_lower = text.lower()
    
    # Кыргызский
    if any(char in text for char in 'ңүөһ'):
        return 'ky'
    
    # Китайский
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return 'zh'
    
    # Английский (если нет кириллицы)
    if re.match(r'^[a-zA-Z\s\d\W]+$', text) and not re.search(r'[а-яё]', text_lower):
        return 'en'
    
    # Русский по умолчанию
    return 'ru'

# ==================== ИИ ФУНКЦИЯ ====================
def get_ai_response(user_message, history, lang='ru'):
    """Получение ответа от ИИ через OpenRouter"""
    try:
        # Добавляем указание языка в промпт
        lang_names = {
            'ru': 'русском',
            'ky': 'кыргызском', 
            'en': 'английском',
            'zh': 'китайском'
        }
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nВАЖНО: Отвечай строго на {lang_names.get(lang, 'русском')} языке!"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aray-group.kg",
            "X-Title": "Aray Group Bot"
        }
        
        messages = [{"role": "system", "content": full_prompt}]
        
        # Добавляем историю (последние 3 пары)
        for msg in history[-6:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 250,
                "temperature": 0.7
            },
            timeout=15
        )
        
        if response.status_code == 200:
            ai_text = response.json()['choices'][0]['message']['content']
            # Убедимся что только один эмодзи
            return clean_emoji(ai_text)
        else:
            return fallback_response(user_message, lang)
            
    except Exception as e:
        print(f"ИИ ошибка: {e}")
        return fallback_response(user_message, lang)

def clean_emoji(text):
    """Оставляем только один эмодзи в конце"""
    import emoji
    # Находим все эмодзи
    emojis = [c for c in text if c in emoji.EMOJI_DATA]
    # Удаляем все эмодзи из текста
    text_clean = ''.join(c for c in text if c not in emoji.EMOJI_DATA)
    # Добавляем один эмодзи в конец если был
    if emojis:
        return text_clean.strip() + " " + emojis[0]
    return text_clean.strip() + " 😊"

def fallback_response(text, lang='ru'):
    """Запасные ответы если ИИ не работает"""
    text_lower = text.lower()
    
    responses = {
        'ru': {
            'price': f"""Для точного расчёта ОСАГО мне нужно узнать:

1️⃣ Ваш опыт вождения
2️⃣ Государственный номер авто
3️⃣ Объём двигателя

И не забудьте — у нас кэшбэк 10% от ОсОО «Арай групп»! только до 31 августа 2026года

Напишите ОФОРМИТЬ, чтобы я собрал данные.""",
            
            'hello': f"""Здравствуйте! 👋

Я — ассистент ОсОО «Арай групп», официального агента «Бакай Иншуренс».

Оформим ОСАГО? Напишите ОФОРМИТЬ 😊""",
            
            'contact': f"""📞 ОсОО «Арай групп»

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
График: Пн-Вс 9:00-18:00

Кэшбэк 10% на все полисы! только до 31го Августа 2026года""",
            
            'default': f"""Я помогу с оформлением ОСАГО или КАСКО через «Бакай Иншуренс».
 

Напишите ОФОРМИТЬ или задайте вопрос 🛡️"""
        },
        
        'ky': {
            'price': f"""ОСАГОну даярдаш үчүн мен төмөнкүлөрдү билишим керек:

1️⃣ Айдоо тажрыйбаңыз
2️⃣ Унаанын мамлекеттик номери
3️⃣ Кыймылдаткычтын көлөмү

Бизде 10% кэшбэк 2026чы жылдын Августтун 31не чейин гана бар! 

Дайындоо үчүн ТАПШЫРМА жазыңыз.""",
            
            'hello': f"""Саламатсызбы! 👋

Мен «Арай групп» ЖЧКнун ассистентимин, «Бакай Иншуренс»тин расмий агенти.

ОСАГОну дайындайлыбы? ТАПШЫРМА жазыңыз 😊""",
            
            'contact': f"""📞 «Арай групп» ЖОО

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
Иш убактысы: Дш-Жм 9:00-18:00

Бардык полистерге 10% кэшбэк! 31 август 2026 чейин""",
            
            'default': f"""Мен «Бакай Иншуренс» аркылуу ОСАГО же КАСКО дайындоого жардам берем.

ТАПШЫРМА - деп жазыңыз 🛡️"""
        },
        
        'en': {
            'price': f"""For accurate OSAGO calculation, I need:

1️⃣ Your driving experience
2️⃣ Car license plate number
3️⃣ Engine volume

We have 10% cashback! 💰

Write APPLY to start.""",
            
            'hello': f"""Hello! 👋

I'm an assistant from Aray Group, official agent of Bakai Insurance.

Let's get OSAGO? Write APPLY 😊""",
            
            'contact': f"""📞 Aray Group LLC

Phone/WhatsApp: {ARAY_PHONE_DISPLAY}
Hours: Mon-Sun 9:00-18:00

10% cashback on all policies! only till 31 August 2026""",
            
            'default': f"""I'll help you get OSAGO or KASKO through Bakai Insurance.

Write APPLY 🛡️"""
        },
        
        'zh': {
            'price': f"""为了准确计算OSAGO，我需要：

1️⃣ 您的驾驶经验
2️⃣ 车牌号
3️⃣ 发动机排量

我们有10%返现！до 31 августа 2026года💰

写"申请"开始办理。""",
            
            'hello': f"""您好！👋

我是Aray Group的助理，Bakai Insurance的官方代理。

办理OSAGO享受10%返现？写"申请" 😊""",
            
            'contact': f"""📞 Aray Group有限责任公司

电话/WhatsApp：{ARAY_PHONE_DISPLAY}
工作时间：周一至周日 9:00-18:00

所有保单10%返现！💰""",
            
            'default': f"""我可以帮您通过Bakai Insurance办理OSAGO或KASKO。

我们提供独家10%返现！

写"申请"或提问 🛡️"""
        }
    }
    
    lang_responses = responses.get(lang, responses['ru'])
    
    if any(word in text_lower for word in ['цена', 'стоимость', 'сколько', 'баа', 'price', '多少钱', 'cost']):
        return lang_responses['price']
    elif any(word in text_lower for word in ['привет', 'салам', 'hello', '你好', 'здравствуй']):
        return lang_responses['hello']
    elif any(word in text_lower for word in ['телефон', 'контакт', 'phone', '联系', 'номер']):
        return lang_responses['contact']
    else:
        return lang_responses['default']

# ==================== WHATSAPP ФУНКЦИИ ====================
def send_whatsapp_message(phone, message):
    """Отправка сообщения клиенту"""
    to_number = phone.replace("+", "")
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"📤 Отправлено {phone}: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def send_lead_to_manager(client_phone, dialog_history, collected_data):
    """Отправка полной информации о клиенте менеджеру"""
    
    # Формируем историю диалога
    dialog_text = ""
    for i, msg in enumerate(dialog_history[-20:], 1):  # Последние 20 сообщений
        role = "Клиент" if msg['role'] == 'user' else "Бот"
        dialog_text += f"{i}. {role}: {msg['content']}\n"
    
    # Формируем сообщение для менеджера
    message = f"""🚨 *НОВЫЙ ЛИД — ОсОО «Арай групп»*

📱 *WhatsApp клиента:* +{client_phone}
🕐 *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

{'='*30}
📋 *СОБРАННЫЕ ДАННЫЕ:*
{'='*30}
"""
    
    # Добавляем собранные данные
    if collected_data:
        for key, value in collected_data.items():
            labels = {
                'name': '👤 Имя',
                'experience_years': '📅 Стаж вождения',
                'license_plate': '🔢 Госномер',
                'engine_volume': '⚙️ Объём двигателя',
                'car_brand': '🚗 Марка',
                'car_model': '📦 Модель',
                'car_year': '📅 Год',
                'phone': '📞 Телефон для связи'
            }
            label = labels.get(key, key)
            message += f"\n{label}: {value}"
    else:
        message += "\n(Данные не собраны — клиент только начал диалог)"
    
    message += f"""

{'='*30}
💬 *ИСТОРИЯ ДИАЛОГА:*
{'='*30}
{dialog_text}

⚡ *Действие:* Перезвоните клиенту!
📞 {ARAY_PHONE_DISPLAY}"""
    
    # Отправляем менеджеру
    success = send_whatsapp_message(ARAY_PHONE, message)
    
    if success:
        print(f"✅ Лид отправлен менеджеру: {ARAY_PHONE}")
    else:
        print(f"❌ Не удалось отправить лид")
    
    return success

# ==================== FLASK ROUTES ====================
@app.route("/")
def home():
    return "Aray Group Bot is running! ✅"

@app.route("/webhook", methods=["GET"])
def verify():
    """Верификация от Meta"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ WEBHOOK VERIFIED!")
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """Обработка входящих сообщений"""
    try:
        data = request.get_json()
        
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if "messages" not in value:
            return "OK", 200
            
        message = value["messages"][0]
        phone = message.get("from")
        text = message.get("text", {}).get("body", "").strip()
        
        if not text:
            return "OK", 200
        
        print(f"\n{'='*50}")
        print(f"📩 [{datetime.now()}] От {phone}: {text}")
        
        # Определяем язык
        lang = detect_language(text)
        print(f"🌐 Язык: {lang}")
        
        # Инициализируем сессию
        if phone not in user_sessions:
            user_sessions[phone] = {
                "state": "ai_chat",
                "data": {},
                "history": [],
                "lang": lang
            }
            user_dialog_history[phone] = []
        
        session = user_sessions[phone]
        session['lang'] = lang  # Обновляем язык
        
        # Сохраняем в историю диалога
        user_dialog_history[phone].append({
            "role": "user",
            "content": text,
            "time": datetime.now().isoformat()
        })
        
        # Обработка сообщения
        response = process_message(phone, text, session, lang)
        
        # Сохраняем ответ бота
        user_dialog_history[phone].append({
            "role": "assistant",
            "content": response,
            "time": datetime.now().isoformat()
        })
        
        # Ограничиваем историю (последние 50 сообщений)
        user_dialog_history[phone] = user_dialog_history[phone][-50:]
        
        # Отправляем ответ
        send_whatsapp_message(phone, response)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return "OK", 200

def process_message(phone, text, session, lang):
    """Главная логика обработки сообщений"""
    text_lower = text.lower()
    state = session.get("state", "ai_chat")
    data = session.get("data", {})
    
    # Команда "оформить" — начинаем сбор данных
    apply_words = {
        'ru': ['оформить', 'заявка', 'начать', 'start', 'apply'],
        'ky': ['тапшырма', 'дайындоо', 'баштоо'],
        'en': ['apply', 'start', 'form', 'get'],
        'zh': ['申请', '办理', '开始']
    }
    
    current_apply_words = apply_words.get(lang, apply_words['ru'])
    
    if any(word in text_lower for word in current_apply_words):
        session["state"] = "collect_experience"
        session["data"] = {"start_time": datetime.now().isoformat()}
        
        prompts = {
            'ru': f"""📝 *Оформление ОСАГО через ОсОО «Арай групп»*

Отлично! Соберу информацию для точного расчёта. 

Какой у вас стаж вождения? (например: 3 года) 🚗""",
            
            'ky': f"""📝 «Арай групп» аркылуу ОСАГО дайындоо

Сонун! Такыба үчүн маалымат чогултайын.

Айдоо тажрыйбаңыз канча жыл? (мисал: 3 жыл) 🚗""",
            
            'en': f"""📝 OSAGO application via Aray Group

Great! I'll collect information for accurate calculation.

What's your driving experience? (e.g., 3 years) 🚗""",
            
            'zh': f"""📝 通过Aray Group办理OSAGO

很好！我来收集信息以准确计算。

您的驾驶经验是多少年？（例如：3年）🚗"""
        }
        
        return prompts.get(lang, prompts['ru'])
    
    # Команда "человек/менеджер"
    human_words = {
        'ru': ['человек', 'менеджер', 'агент', 'оператор', 'позвонить'],
        'ky': ['адам', 'менеджер', 'агент', 'чалуу'],
        'en': ['human', 'manager', 'agent', 'call'],
        'zh': ['人工', '经理', '代理', '打电话']
    }
    
    current_human_words = human_words.get(lang, human_words['ru'])
    
    if any(word in text_lower for word in current_human_words):
        # Отправляем текущий диалог менеджеру
        if len(user_dialog_history.get(phone, [])) > 0:
            send_lead_to_manager(phone, user_dialog_history[phone], session.get("data", {}))
        
        responses = {
            'ru': f"""📞 *Связь с менеджером ОсОО «Арай групп»*

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
График: Пн-Вс 9:00-18:00

Я передал вашу переписку менеджеру — он скоро свяжется! 😊""",
            
            'ky': f"""📞 «Арай групп» менеджери менен байланышуу

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
Иш убактысы: Дш-Жм 9:00-18:00

Сиздин сүйлөшүүңүздү менеджерге жөнөттүм — ал жакында чалат! 😊""",
            
            'en': f"""📞 Contact Aray Group manager

Phone/WhatsApp: {ARAY_PHONE_DISPLAY}
Hours: Mon-Sun 9:00-18:00

I've forwarded your chat to the manager — they'll contact you soon! 😊""",
            
            'zh': f"""📞 联系Aray Group经理

电话/WhatsApp：{ARAY_PHONE_DISPLAY}
工作时间：周一至周日 9:00-18:00

我已将您的对话转给经理——他会尽快联系您！😊"""
        }
        
        return responses.get(lang, responses['ru'])
    
    # Если в режиме сбора данных
    if state != "ai_chat":
        return process_data_collection(phone, text, session, lang)
    
    # ИИ-режим (обычный диалог)
    history = session.get("history", [])
    response = get_ai_response(text, history, lang)
    
    # Сохраняем историю для контекста
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})
    session["history"] = history[-10:]  # Последние 10 сообщений
    
    return response

def process_data_collection(phone, text, session, lang):
    """Пошаговый сбор данных от клиента"""
    state = session.get("state")
    data = session.get("data", {})
    
    # Шаг 1: Стаж вождения
    if state == "collect_experience":
        data["experience_years"] = text
        session["data"] = data
        session["state"] = "collect_plate"
        
        prompts = {
            'ru': "✅ Записал! Теперь госномер авто? (например: 01 KG 123 ABC) 🔢",
            'ky': "✅ Каттадым! Эми унаанын номери? (мисал: 01 KG 123 ABC) 🔢",
            'en': "✅ Noted! Now the license plate? (e.g., 01 KG 123 ABC) 🔢",
            'zh': "✅ 已记录！现在车牌号？（例如：01 KG 123 ABC）🔢"
        }
        return prompts.get(lang, prompts['ru'])
    
    # Шаг 2: Госномер
    elif state == "collect_plate":
        data["license_plate"] = text.upper()
        session["data"] = data
        session["state"] = "collect_engine"
        
        prompts = {
            'ru': "✅ Отлично! Объём двигателя? (например: 2.0 или 2000 см³) ⚙️",
            'ky': "✅ Сонун! Кыймылдаткычтын көлөмү? (мисал: 2.0 же 2000 см³) ⚙️",
            'en': "✅ Great! Engine volume? (e.g., 2.0 or 2000 cc) ⚙️",
            'zh': "✅ 很好！发动机排量？（例如：2.0 或 2000 cc）⚙️"
        }
        return prompts.get(lang, prompts['ru'])
    
    # Шаг 3: Объём двигателя
    elif state == "collect_engine":
        data["engine_volume"] = text
        session["data"] = data
        session["state"] = "collect_phone"
        
        prompts = {
            'ru': "✅ Принято! Ваш номер телефона для связи? 📞",
            'ky': "✅ Кабыл алынды! Байланыш үчүн телефон номериңиз? 📞",
            'en': "✅ Got it! Your phone number for contact? 📞",
            'zh': "✅ 收到！您的联系电话？📞"
        }
        return prompts.get(lang, prompts['ru'])
    
    # Шаг 4: Телефон (финальный)
    elif state == "collect_phone":
        data["phone"] = text
        data["whatsapp"] = phone  # Сохраняем WhatsApp номер
        
        # Дополнительно спрашиваем марку авто
        session["data"] = data
        session["state"] = "collect_brand"
        
        prompts = {
            'ru': "✅ Последний вопрос: марка и модель авто? (например: Toyota Camry) 🚗",
            'ky': "✅ Акыркы суроо: унаанын маркасы жана модели? (мисал: Toyota Camry) 🚗",
            'en': "✅ Last question: car brand and model? (e.g., Toyota Camry) 🚗",
            'zh': "✅ 最后一个问题：汽车品牌和型号？（例如：Toyota Camry）🚗"
        }
        return prompts.get(lang, prompts['ru'])
    
    # Шаг 5: Марка авто (финальный)
    elif state == "collect_brand":
        data["car_brand_model"] = text
        
        # Отправляем лид менеджеру
        send_lead_to_manager(phone, user_dialog_history.get(phone, []), data)
        
        # Сбрасываем состояние
        session["state"] = "ai_chat"
        session["data"] = {}
        
        prompts = {
            'ru': f"""🎉 *Заявка отправлена!*

Все данные переданы менеджеру ОсОО «Арай групп».

Он перезвонит вам в течение 15 минут для точного расчёта и оформления с кэшбэком 10%! 💰

Телефон: {ARAY_PHONE_DISPLAY} 😊""",
            
            'ky': f"""🎉 *Тапшырма жөнөтүлдү!*

Бардык маалыматтар «Арай групп» менеджерине жөнөтүлдү.

Ал 10% кэшбэк менен так эсептөө жана дайындоо үчүн 15 мүнөт ичинде чалат! 💰

Телефон: {ARAY_PHONE_DISPLAY} 😊""",
            
            'en': f"""🎉 *Application sent!*

All data forwarded to Aray Group manager.

He'll call within 15 minutes for exact calculation and application with 10% cashback! 💰

Phone: {ARAY_PHONE_DISPLAY} 😊""",
            
            'zh': f"""🎉 *申请已发送！*

所有数据已转给Aray Group经理。

他将在15分钟内致电进行准确计算和办理，享受10%返现！💰

电话：{ARAY_PHONE_DISPLAY} 😊"""
        }
        
        return prompts.get(lang, prompts['ru'])
    
    return "Продолжаем... / Continuing..."

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    print("="*60)
    print("ОСОО «АРАЙ ГРУПП» — AI АССИСТЕНТ 🤖")
    print("Официальный агент Бакай Иншуренс")
    print("="*60)
    print(f"📞 Менеджер: {ARAY_PHONE_DISPLAY}")
    print(f"💰 Кэшбэк: 10%")
    print("="*60)
    app.run(debug=False, host="0.0.0.0", port=5000)
