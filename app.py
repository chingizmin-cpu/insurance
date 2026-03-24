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

# Контакты ОсОО "Арай групп"
ARAY_PHONE = "996555386983"
ARAY_PHONE_DISPLAY = "0(555) 38 69 83"

# OpenRouter для ИИ
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_KEY', 'your_key_here')

# Хранилище сессий
user_sessions = {}
user_dialog_history = {}

# ==================== ЯЗЫКИ И ПЕРЕВОДЫ ====================
LANGUAGES = {
    'zh': {'name': '中国人', 'flag': '🇨🇳', 'welcome': '您好！请选择您的语言'},
    'en': {'name': 'English', 'flag': '🇬🇧', 'welcome': 'Hello! Please select your language'},
    'ru': {'name': 'Русский', 'flag': '🇷🇺', 'welcome': 'Здравствуйте! Выберите язык'},
    'tr': {'name': 'Türkçe', 'flag': '🇹🇷', 'welcome': 'Merhaba! Lütfen dilinizi seçin'},
    'ky': {'name': 'Кыргызча', 'flag': '🇰🇬', 'welcome': 'Саламатсызбы! Тилди тандаңыз'}
}

# Типы страхования и вопросы для каждого
INSURANCE_TYPES = {
    'osago': {
        'ru': {'name': '🚗 ОСАГО', 'desc': 'Обязательное автострахование от 1,800 сом/год'},
        'ky': {'name': '🚗 ОСАГО', 'desc': 'Милдеттүү автостраховка 1,800 сом/жылдан'},
        'en': {'name': '🚗 OSAGO', 'desc': 'Mandatory auto insurance from 1,800 KGS/year'},
        'tr': {'name': '🚗 OSAGO', 'desc': 'Zorunlu araç sigortası 1,800 KGS/yıldan'},
        'zh': {'name': '🚗 车辆强制险', 'desc': '强制汽车保险 每年1,800索姆起'}
    },
    'kasko': {
        'ru': {'name': '🛡️ КАСКО', 'desc': 'Полное КАСКО от 15,000 сом/год'},
        'ky': {'name': '🛡️ КАСКО', 'desc': 'Толук КАСКО 15,000 сом/жылдан'},
        'en': {'name': '🛡️ KASKO', 'desc': 'Full CASCO from 15,000 KGS/year'},
        'tr': {'name': '🛡️ KASKO', 'desc': 'Tam kasko 15,000 KGS/yıldan'},
        'zh': {'name': '🛡️ 车辆全险', 'desc': '全险 每年15,000索姆起'}
    },
    'travel': {
        'ru': {'name': '✈️ Путешествия', 'desc': 'Страхование выезжающих за рубеж'},
        'ky': {'name': '✈️ Саякат', 'desc': 'Чет өлкөгө чыгып кетүүчүлөрдү камсыздоо'},
        'en': {'name': '✈️ Travel', 'desc': 'Travel insurance abroad'},
        'tr': {'name': '✈️ Seyahat', 'desc': 'Yurtdışı seyahat sigortası'},
        'zh': {'name': '✈️ 旅行险', 'desc': '境外旅行保险'}
    },
    'property': {
        'ru': {'name': '🏠 Имущество', 'desc': 'Страхование квартиры и дома'},
        'ky': {'name': '🏠 Мүлк', 'desc': 'Батир жана үйдү камсыздоо'},
        'en': {'name': '🏠 Property', 'desc': 'Home and apartment insurance'},
        'tr': {'name': '🏠 Mülk', 'desc': 'Ev ve daire sigortası'},
        'zh': {'name': '🏠 财产险', 'desc': '房屋和公寓保险'}
    }
}

# Вопросы для сбора данных по каждому типу страхования
COLLECTION_QUESTIONS = {
    'osago': {
        'ru': [
            ('experience_years', '1️⃣ Какой у вас стаж вождения? (например: 3 года)'),
            ('license_plate', '2️⃣ Государственный номер авто? (например: 01 KG 123 ABC)'),
            ('engine_volume', '3️⃣ Объём двигателя? (например: 2.0 или 2000 см³)'),
            ('car_brand', '4️⃣ Марка и модель авто? (например: Toyota Camry)')
        ],
        'ky': [
            ('experience_years', '1️⃣ Айдоо тажрыйбаңыз канча жыл? (мисал: 3 жыл)'),
            ('license_plate', '2️⃣ Унаанын мамлекеттик номери? (мисал: 01 KG 123 ABC)'),
            ('engine_volume', '3️⃣ Кыймылдаткычтын көлөмү? (мисал: 2.0 же 2000 см³)'),
            ('car_brand', '4️⃣ Унаанын маркасы жана модели? (мисал: Toyota Camry)')
        ],
        'en': [
            ('experience_years', '1️⃣ What is your driving experience? (e.g., 3 years)'),
            ('license_plate', '2️⃣ License plate number? (e.g., 01 KG 123 ABC)'),
            ('engine_volume', '3️⃣ Engine volume? (e.g., 2.0 or 2000 cc)'),
            ('car_brand', '4️⃣ Car brand and model? (e.g., Toyota Camry)')
        ],
        'tr': [
            ('experience_years', '1️⃣ Sürücü deneyiminiz nedir? (örn., 3 yıl)'),
            ('license_plate', '2️⃣ Plaka numarası? (örn., 01 KG 123 ABC)'),
            ('engine_volume', '3️⃣ Motor hacmi? (örn., 2.0 veya 2000 cc)'),
            ('car_brand', '4️⃣ Araç marka ve modeli? (örn., Toyota Camry)')
        ],
        'zh': [
            ('experience_years', '1️⃣ 您的驾驶经验是多少年？（例如：3年）'),
            ('license_plate', '2️⃣ 车牌号？（例如：01 KG 123 ABC）'),
            ('engine_volume', '3️⃣ 发动机排量？（例如：2.0 或 2000 cc）'),
            ('car_brand', '4️⃣ 汽车品牌和型号？（例如：Toyota Camry）')
        ]
    },
    'kasko': {
        'ru': [
            ('car_brand', '1️⃣ Марка и модель авто? (например: Toyota Camry 2020)'),
            ('car_value', '2️⃣ Рыночная стоимость авто в USD? (например: 15000)'),
            ('driver_age', '3️⃣ Возраст водителя? (например: 35)'),
            ('usage_type', '4️⃣ Тип использования? (личное/такси/прокат)')
        ],
        'ky': [
            ('car_brand', '1️⃣ Унаанын маркасы жана модели? (мисал: Toyota Camry 2020)'),
            ('car_value', '2️⃣ Унаанын базар баасы USD? (мисал: 15000)'),
            ('driver_age', '3️⃣ Айдоочунун жашы? (мисал: 35)'),
            ('usage_type', '4️⃣ Колдонуу түрү? (жеке/такси/прокат)')
        ],
        'en': [
            ('car_brand', '1️⃣ Car brand and model? (e.g., Toyota Camry 2020)'),
            ('car_value', '2️⃣ Market value in USD? (e.g., 15000)'),
            ('driver_age', '3️⃣ Driver age? (e.g., 35)'),
            ('usage_type', '4️⃣ Usage type? (personal/taxi/rental)')
        ],
        'tr': [
            ('car_brand', '1️⃣ Araç marka ve modeli? (örn., Toyota Camry 2020)'),
            ('car_value', '2️⃣ Piyasa değeri USD? (örn., 15000)'),
            ('driver_age', '3️⃣ Sürücü yaşı? (örn., 35)'),
            ('usage_type', '4️⃣ Kullanım tipi? (kişisel/taksi/kiralık)')
        ],
        'zh': [
            ('car_brand', '1️⃣ 汽车品牌和型号？（例如：Toyota Camry 2020）'),
            ('car_value', '2️⃣ 市场价值（美元）？（例如：15000）'),
            ('driver_type', '3️⃣ 驾驶员年龄？（例如：35）'),
            ('usage_type', '4️⃣ 使用类型？（个人/出租车/租赁）')
        ]
    },
    'travel': {
        'ru': [
            ('destination', '1️⃣ Страна назначения? (например: Турция)'),
            ('duration', '2️⃣ Срок поездки? (например: 14 дней)'),
            ('traveler_age', '3️⃣ Возраст путешественника? (например: 30)'),
            ('trip_purpose', '4️⃣ Цель поездки? (туризм/бизнес/учёба)')
        ],
        'ky': [
            ('destination', '1️⃣ Бара турган өлкө? (мисал: Түркия)'),
            ('duration', '2️⃣ Сапардын убактысы? (мисал: 14 күн)'),
            ('traveler_age', '3️⃣ Саякатчынын жашы? (мисал: 30)'),
            ('trip_purpose', '4️⃣ Сапардын максаты? (туризм/бизнес/окуу)')
        ],
        'en': [
            ('destination', '1️⃣ Destination country? (e.g., Turkey)'),
            ('duration', '2️⃣ Trip duration? (e.g., 14 days)'),
            ('traveler_age', '3️⃣ Traveler age? (e.g., 30)'),
            ('trip_purpose', '4️⃣ Trip purpose? (tourism/business/study)')
        ],
        'tr': [
            ('destination', '1️⃣ Hedef ülke? (örn., Türkiye)'),
            ('duration', '2️⃣ Seyahat süresi? (örn., 14 gün)'),
            ('traveler_age', '3️⃣ Seyahatçi yaşı? (örn., 30)'),
            ('trip_purpose', '4️⃣ Seyahat amacı? (turizm/iş/öğrenim)')
        ],
        'zh': [
            ('destination', '1️⃣ 目的地国家？（例如：土耳其）'),
            ('duration', '2️⃣ 旅行时长？（例如：14天）'),
            ('traveler_age', '3️⃣ 旅行者年龄？（例如：30）'),
            ('trip_purpose', '4️⃣ 旅行目的？（旅游/商务/学习）')
        ]
    },
    'property': {
        'ru': [
            ('property_type', '1️⃣ Тип недвижимости? (квартира/дом/офис)'),
            ('area', '2️⃣ Площадь в кв.м? (например: 65)'),
            ('construction_year', '3️⃣ Год постройки? (например: 2015)'),
            ('address', '4️⃣ Адрес объекта? (город/район)')
        ],
        'ky': [
            ('property_type', '1️⃣ Мүлк түрү? (батир/үй/офис)'),
            ('area', '2️⃣ Аянты чарчы метр? (мисал: 65)'),
            ('construction_year', '3️⃣ Курулган жылы? (мисал: 2015)'),
            ('address', '4️⃣ Объектин дареги? (шаар/район)')
        ],
        'en': [
            ('property_type', '1️⃣ Property type? (apartment/house/office)'),
            ('area', '2️⃣ Area in sq.m? (e.g., 65)'),
            ('construction_year', '3️⃣ Year built? (e.g., 2015)'),
            ('address', '4️⃣ Property address? (city/district)')
        ],
        'tr': [
            ('property_type', '1️⃣ Mülk tipi? (daire/ev/ofis)'),
            ('area', '2️⃣ Alan m²? (örn., 65)'),
            ('construction_year', '3️⃣ Yapım yılı? (örn., 2015)'),
            ('address', '4️⃣ Mülk adresi? (şehir/bölge)')
        ],
        'zh': [
            ('property_type', '1️⃣ 房产类型？（公寓/房屋/办公室）'),
            ('area', '2️⃣ 面积（平方米）？（例如：65）'),
            ('construction_year', '3️⃣ 建造年份？（例如：2015）'),
            ('address', '4️⃣ 房产地址？（城市/区域）')
        ]
    }
}

# ==================== ПРОМПТ ДЛЯ ИИ ====================
SYSTEM_PROMPT = """Ты — AI-ассистент ОсОО "Арай групп", официального агента страховой компании "Бакай Иншуренс" (15 лет опыта).

КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:

1. ЯЗЫК: Отвечай СТРОГО на том языке, которым пишет клиент. Используй тот же язык, что в системном сообщении.

2. КРАТКОСТЬ: Максимум 3-5 предложения на сообщение.

3. ЭМОДЗИ: Используй умеренно — 1-2 эмодзи на сообщение.

4. КЭШБЭК 10%: Упоминай эксклюзивный кэшбэк 10% от ОсОО "Арай групп" до 31 августа 2026 года!

5. ПРОДУКТЫ И НАПРАВЛЕНИЯ:
   - ОСАГО: от 1,800 сом/год (обязательное автострахование)
   - КАСКО: от 15,000 сом/год (полное КАСКО)
   - Путешествия: страхование выезжающих за рубеж
   - Имущество: страхование квартир и домов

6. ДЕЙСТВИЕ: Активно предлагай оформить заявку через чат. Для расчёта нужно собрать 4 параметра.

7. КОНТАКТЫ: ТОЛЬКО контакты ОсОО "Арай групп":
   - Телефон/WhatsApp: 0(555) 38 69 83
   - График: Пн-Вс 9:00-18:00

8. ЦЕЛЬ: Собрать данные клиента и передать менеджеру для расчёта."""

# ==================== WHATSAPP ФУНКЦИИ ====================
def send_whatsapp_message(phone, message, buttons=None):
    """Отправка сообщения клиенту"""
    to_number = phone.replace("+", "")
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Если есть кнопки — отправляем интерактивное сообщение
    if buttons:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {"buttons": buttons}
            }
        }
    else:
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

def send_language_selection(phone):
    """Отправка выбора языка с кнопками"""
    message = "🌍 Please select your language / Выберите язык / 请选择语言 / Dil seçin / Тилди тандаңыз"
    
    buttons = [
        {
            "type": "reply",
            "reply": {"id": "lang_zh", "title": "🇨🇳 中国人"}
        },
        {
            "type": "reply",
            "reply": {"id": "lang_en", "title": "🇬🇧 English"}
        },
        {
            "type": "reply",
            "reply": {"id": "lang_ru", "title": "🇷🇺 Русский"}
        }
    ]
    
    # Отправляем первое сообщение с 3 кнопками
    send_whatsapp_message(phone, message, buttons)
    
    # Отправляем второе сообщение с оставшимися языками
    buttons2 = [
        {
            "type": "reply",
            "reply": {"id": "lang_tr", "title": "🇹🇷 Turkce"}
        },
        {
            "type": "reply",
            "reply": {"id": "lang_ky", "title": "🇰🇬 Кыргызча"}
        }
    ]
    
    send_whatsapp_message(phone, "Или / Or / 或者 / Ya da / Же", buttons2)

def send_insurance_menu(phone, lang):
    """Отправка меню выбора типа страхования"""
    texts = {
        'ru': "📋 Выберите тип страхования:",
        'ky': "📋 Камсыздоо түрүн тандаңыз:",
        'en': "📋 Select insurance type:",
        'tr': "📋 Sigorta türünü seçin:",
        'zh': "📋 选择保险类型："
    }
    
    message = texts.get(lang, texts['ru'])
    
    buttons = [
        {
            "type": "reply",
            "reply": {"id": "type_osago", "title": INSURANCE_TYPES['osago'][lang]['name']}
        },
        {
            "type": "reply",
            "reply": {"id": "type_kasko", "title": INSURANCE_TYPES['kasko'][lang]['name']}
        }
    ]
    
    buttons2 = [
        {
            "type": "reply",
            "reply": {"id": "type_travel", "title": INSURANCE_TYPES['travel'][lang]['name']}
        },
        {
            "type": "reply",
            "reply": {"id": "type_property", "title": INSURANCE_TYPES['property'][lang]['name']}
        }
    ]
    
    send_whatsapp_message(phone, message, buttons)
    send_whatsapp_message(phone, "...", buttons2)

# ==================== ИИ ФУНКЦИЯ ====================
def get_ai_response(user_message, history, lang='ru'):
    """Получение ответа от ИИ через OpenRouter"""
    try:
        # Проверяем, есть ли API ключ
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == 'your_key_here':
            print("⚠️ OpenRouter API ключ не настроен!")
            return fallback_response(user_message, lang)
        
        # Добавляем указание языка в промпт
        lang_names = {
            'ru': 'русском',
            'ky': 'кыргызском', 
            'en': 'английском',
            'tr': 'турецком',
            'zh': 'китайском'
        }
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nВАЖНО: Отвечай строго на {lang_names.get(lang, 'русском')} языке! Не переключайся на другой язык."
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://aray-group.kg",
            "X-Title": "Aray Group Bot"
        }
        
        messages = [{"role": "system", "content": full_prompt}]
        
        # Добавляем историю (последние 6 пар)
        for msg in history[-6:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        print(f"🤖 Отправка запроса ИИ: {messages}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.7
            },
            timeout=15
        )
        
        print(f"🤖 Ответ ИИ: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                ai_text = data['choices'][0]['message']['content']
                print(f"🤖 Текст ответа: {ai_text[:100]}...")
                return clean_response(ai_text)
            else:
                print(f"⚠️ Нет choices в ответе: {data}")
                return fallback_response(user_message, lang)
        else:
            print(f"❌ Ошибка ИИ: {response.status_code} - {response.text}")
            return fallback_response(user_message, lang)
            
    except Exception as e:
        print(f"❌ ИИ ошибка: {e}")
        import traceback
        traceback.print_exc()
        return fallback_response(user_message, lang)

def clean_response(text):
    """Очистка ответа"""
    # Убираем лишние пробелы
    text = text.strip()
    # Ограничиваем длину
    if len(text) > 1000:
        text = text[:997] + "..."
    return text

def fallback_response(text, lang='ru'):
    """Запасные ответы если ИИ не работает"""
    text_lower = text.lower()
    
    responses = {
        'ru': {
            'price_osago': """💰 *ОСАГО — от 1,800 сом/год*

Для точного расчёта нужны:
• Стаж вождения
• Госномер авто  
• Объём двигателя
• Марка авто

Напишите ОФОРМИТЬ ОСАГО, чтобы собрать данные. Кэшбэк 10%! 💎""",
            
            'price_kasko': """💰 *КАСКО — от 15,000 сом/год*

Для расчёта нужны:
• Марка и модель авто
• Рыночная стоимость
• Возраст водителя
• Тип использования

Напишите ОФОРМИТЬ КАСКО для заявки. Кэшбэк 10%! 💎""",
            
            'price_travel': """✈️ *Страхование путешествий*

Для расчёта нужны:
• Страна назначения
• Срок поездки
• Возраст путешественника
• Цель поездки

Напишите ОФОРМИТЬ ПУТЕШЕСТВИЕ для заявки. Кэшбэк 10%! 💎""",
            
            'price_property': """🏠 *Страхование имущества*

Для расчёта нужны:
• Тип недвижимости
• Площадь
• Год постройки
• Адрес

Напишите ОФОРМИТЬ ИМУЩЕСТВО для заявки. Кэшбэк 10%! 💎""",
            
            'hello': """👋 Здравствуйте! Я ассистент ОсОО «Арай групп» — официального агента «Бакай Иншуренс».

Мы предлагаем:
🚗 ОСАГО от 1,800 сом/год
🛡️ КАСКО от 15,000 сом/год
✈️ Страхование путешествий
🏠 Страхование имущества

*Кэшбэк 10% до 31 августа 2026!*

Выберите тип страхования или задайте вопрос 😊""",
            
            'contact': f"""📞 *ОсОО «Арай групп»*

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
График: Пн-Вс 9:00-18:00

Кэшбэк 10% на все полисы! 💰""",
            
            'default': """Я помогу с оформлением страховки через «Бакай Иншуренс».

Доступные направления:
• 🚗 ОСАГО — авто обязательное
• 🛡️ КАСКО — авто полное
• ✈️ Путешествия — выезд за рубеж
• 🏠 Имущество — квартиры и дома

Напишите название интересующего типа или ОФОРМИТЬ для заявки 🛡️"""
        },
        
        'ky': {
            'price_osago': """💰 *ОСАГО — 1,800 сом/жылдан*

Такыба үчүн керек:
• Айдоо тажрыйба
• Унаа номери
• Кыймылдаткыч көлөмү
• Марка

ТАПШЫРМА ОСАГО деп жазыңыз. Кэшбэк 10%! 💎""",
            
            'price_kasko': """💰 *КАСКО — 15,000 сом/жылдан*

Такыба үчүн керек:
• Унаа маркасы
• Базар баасы
• Айдоочу жашы
• Колдонуу түрү

ТАПШЫРМА КАСКО деп жазыңыз. Кэшбэк 10%! 💎""",
            
            'price_travel': """✈️ *Саякат камсыздоо*

Такыба үчүн керек:
• Бара турган өлкө
• Сапар убактысы
• Саякатчы жашы
• Сапар максаты

ТАПШЫРМА САЯКАТ деп жазыңыз. Кэшбэк 10%! 💎""",
            
            'price_property': """🏠 *Мүлк камсыздоо*

Такыба үчүн керек:
• Мүлк түрү
• Аянты
• Курулган жылы
• Дарек

ТАПШЫРМА МҮЛК деп жазыңыз. Кэшбэк 10%! 💎""",
            
            'hello': f"""👋 Саламатсызбы! Мен «Арай групп» ЖЧКнун ассистентимин.

Сунуштар:
🚗 ОСАГО 1,800 сом/жылдан
🛡️ КАСКО 15,000 сом/жылдан
✈️ Саякат камсыздоо
🏠 Мүлк камсыздоо

Кэшбэк 10% 2026-жылдын 31-августуна чейин! 💰""",
            
            'contact': f"""📞 «Арай групп» ЖОО

Телефон/WhatsApp: {ARAY_PHONE_DISPLAY}
Иш убактысы: Дш-Жм 9:00-18:00

Бардык полистерге 10% кэшбэк! 💰""",
            
            'default': """Мен «Бакай Иншуренс» аркылуу камсыздоо менен жардам берем.

Түрлөрү:
• 🚗 ОСАГО — милдеттүү
• 🛡️ КАСКО — толук
• ✈️ Саякат — чет өлкө
• 🏠 Мүлк — батир жана үй

ТАПШЫРМА деп жазыңыз 🛡️"""
        },
        
        'en': {
            'price_osago': """💰 *OSAGO — from 1,800 KGS/year*

Need for calculation:
• Driving experience
• License plate
• Engine volume
• Car brand

Write APPLY OSAGO to start. 10% cashback! 💎""",
            
            'price_kasko': """💰 *KASKO — from 15,000 KGS/year*

Need for calculation:
• Car brand & model
• Market value
• Driver age
• Usage type

Write APPLY KASKO to start. 10% cashback! 💎""",
            
            'price_travel': """✈️ *Travel Insurance*

Need for calculation:
• Destination country
• Trip duration
• Traveler age
• Trip purpose

Write APPLY TRAVEL to start. 10% cashback! 💎""",
            
            'price_property': """🏠 *Property Insurance*

Need for calculation:
• Property type
• Area (sq.m)
• Year built
• Address

Write APPLY PROPERTY to start. 10% cashback! 💎""",
            
            'hello': f"""👋 Hello! I'm Aray Group assistant, official agent of Bakai Insurance.

We offer:
🚗 OSAGO from 1,800 KGS/year
🛡️ KASKO from 15,000 KGS/year
✈️ Travel insurance
🏠 Property insurance

10% cashback until Aug 31, 2026! 💰""",
            
            'contact': f"""📞 Aray Group LLC

Phone/WhatsApp: {ARAY_PHONE_DISPLAY}
Hours: Mon-Sun 9:00-18:00

10% cashback on all policies! 💰""",
            
            'default': """I'll help you get insurance through Bakai Insurance.

Available types:
• 🚗 OSAGO — mandatory auto
• 🛡️ KASKO — full auto
• ✈️ Travel — abroad
• 🏠 Property — homes

Write APPLY 🛡️"""
        },
        
        'tr': {
            'price_osago': """💰 *OSAGO — 1,800 KGS/yıldan*

Hesaplama için gerekli:
• Sürücü deneyimi
• Plaka numarası
• Motor hacmi
• Araç markası

BAŞVUR OSAGO yazın. 10% cashback! 💎""",
            
            'price_kasko': """💰 *KASKO — 15,000 KGS/yıldan*

Hesaplama için gerekli:
• Araç marka/model
• Piyasa değeri
• Sürücü yaşı
• Kullanım tipi

BAŞVUR KASKO yazın. 10% cashback! 💎""",
            
            'price_travel': """✈️ *Seyahat Sigortası*

Hesaplama için gerekli:
• Hedef ülke
• Seyahat süresi
• Seyahatçi yaşı
• Seyahat amacı

BAŞVUR SEYAHAT yazın. 10% cashback! 💎""",
            
            'price_property': """🏠 *Mülk Sigortası*

Hesaplama için gerekli:
• Mülk tipi
• Alan (m²)
• Yapım yılı
• Adres

BAŞVUR MÜLK yazın. 10% cashback! 💎""",
            
            'hello': f"""👋 Merhaba! Ben Aray Group asistanıyım, Bakai Insurance resmi acentesi.

Tekliflerimiz:
🚗 OSAGO 1,800 KGS/yıldan
🛡️ KASKO 15,000 KGS/yıldan
✈️ Seyahat sigortası
🏠 Mülk sigortası

%10 cashback 31 Ağustos 2026'ya kadar! 💰""",
            
            'contact': f"""📞 Aray Group LLC

Telefon/WhatsApp: {ARAY_PHONE_DISPLAY}
Çalışma saatleri: Pzt-Paz 9:00-18:00

Tüm poliçelerde %10 cashback! 💰""",
            
            'default': """Bakai Insurance aracılığıyla sigorta yaptırmanıza yardımcı olacağım.

Mevcut türler:
• 🚗 OSAGO — zorunlu araç
• 🛡️ KASKO — tam kasko
• ✈️ Seyahat — yurtdışı
• 🏠 Mülk — ev ve daire

BAŞVUR yazın 🛡️"""
        },
        
        'zh': {
            'price_osago': """💰 *车辆强制险 — 每年1,800索姆起*

计算需要：
• 驾驶经验
• 车牌号
• 发动机排量
• 汽车品牌

写"申请车辆强制险"开始。10%返现！💎""",
            
            'price_kasko': """💰 *车辆全险 — 每年15,000索姆起*

计算需要：
• 汽车品牌型号
• 市场价值
• 驾驶员年龄
• 使用类型

写"申请车辆全险"开始。10%返现！💎""",
            
            'price_travel': """✈️ *旅行保险*

计算需要：
• 目的地国家
• 旅行时长
• 旅行者年龄
• 旅行目的

写"申请旅行险"开始。10%返现！💎""",
            
            'price_property': """🏠 *财产保险*

计算需要：
• 房产类型
• 面积（平方米）
• 建造年份
• 地址

写"申请财产险"开始。10%返现！💎""",
            
            'hello': f"""👋 您好！我是Aray Group的助理，Bakai Insurance的官方代理。

我们提供：
🚗 车辆强制险 每年1,800索姆起
🛡️ 车辆全险 每年15,000索姆起
✈️ 旅行保险
🏠 财产保险

10%返现优惠至2026年8月31日！💰""",
            
            'contact': f"""📞 Aray Group有限责任公司

电话/WhatsApp：{ARAY_PHONE_DISPLAY}
工作时间：周一至周日 9:00-18:00

所有保单10%返现！💰""",
            
            'default': """我可以帮您通过Bakai Insurance办理保险。

可选类型：
• 🚗 车辆强制险 — 强制汽车保险
• 🛡️ 车辆全险 — 全险
• ✈️ 旅行险 — 境外旅行
• 🏠 财产险 — 房屋保险

写"申请"开始 🛡️"""
        }
    }
    
    lang_responses = responses.get(lang, responses['ru'])
    
    # Определяем тип запроса
    text_lower = text_lower
    
    # Проверяем ключевые слова для разных типов страхования
    if any(word in text_lower for word in ['осаго', 'osago', 'милдеттүү', '强制']):
        return lang_responses['price_osago']
    elif any(word in text_lower for word in ['каско', 'kasko', 'кasko', '全险']):
        return lang_responses['price_kasko']
    elif any(word in text_lower for word in ['путешеств', 'seyahat', 'travel', 'саякат', '旅行']):
        return lang_responses['price_travel']
    elif any(word in text_lower for word in ['имущество', 'мүлк', 'mülk', 'property', '财产', 'квартира', 'батир', 'ev', '房屋']):
        return lang_responses['price_property']
    elif any(word in text_lower for word in ['привет', 'салам', 'hello', '你好', 'здравствуй', 'merhaba']):
        return lang_responses['hello']
    elif any(word in text_lower for word in ['телефон', 'контакт', 'phone', '联系', 'номер', 'telefon']):
        return lang_responses['contact']
    else:
        return lang_responses['default']

def send_lead_to_manager(client_phone, dialog_history, collected_data, insurance_type):
    """Отправка полной информации о клиенте менеджеру"""
    
    type_names = {
        'osago': {'ru': 'ОСАГО', 'ky': 'ОСАГО', 'en': 'OSAGO', 'tr': 'OSAGO', 'zh': '车辆强制险'},
        'kasko': {'ru': 'КАСКО', 'ky': 'КАСКО', 'en': 'KASKO', 'tr': 'KASKO', 'zh': '车辆全险'},
        'travel': {'ru': 'Путешествия', 'ky': 'Саякат', 'en': 'Travel', 'tr': 'Seyahat', 'zh': '旅行险'},
        'property': {'ru': 'Имущество', 'ky': 'Мүлк', 'en': 'Property', 'tr': 'Mülk', 'zh': '财产险'}
    }
    
    # Формируем историю диалога
    dialog_text = ""
    for i, msg in enumerate(dialog_history[-20:], 1):
        role = "Клиент" if msg['role'] == 'user' else "Бот"
        dialog_text += f"{i}. {role}: {msg['content']}\n"
    
    type_name = type_names.get(insurance_type, {}).get('ru', insurance_type)
    
    # Формируем сообщение для менеджера
    message = f"""🚨 *НОВЫЙ ЛИД — ОсОО «Арай групп»*

📋 *Тип заявки:* {type_name}
📱 *WhatsApp клиента:* +{client_phone}
🕐 *Время:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

{'='*30}
📊 *СОБРАННЫЕ ДАННЫЕ:*
{'='*30}"""
    
    # Добавляем собранные данные
    if collected_data:
        for key, value in collected_data.items():
            message += f"\n• {key}: {value}"
    else:
        message += "\n(Данные не собраны)"
    
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
        print(f"📥 Получены данные: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        # Проверяем тип сообщения
        if "messages" in value:
            message = value["messages"][0]
            phone = message.get("from")
            
            # Проверяем тип сообщения (текст или кнопка)
            msg_type = message.get("type")
            
            if msg_type == "text":
                text = message.get("text", {}).get("body", "").strip()
            elif msg_type == "interactive":
                # Обработка нажатия кнопки
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    text = interactive.get("button_reply", {}).get("id", "")
                else:
                    text = ""
            else:
                text = ""
            
            if not text or not phone:
                return "OK", 200
            
            print(f"\n{'='*50}")
            print(f"📩 [{datetime.now()}] От {phone}: {text}")
            
            # Инициализируем сессию если новый пользователь
            if phone not in user_sessions:
                user_sessions[phone] = {
                    "state": "language_selection",
                    "data": {},
                    "history": [],
                    "lang": None,
                    "insurance_type": None,
                    "question_index": 0
                }
                user_dialog_history[phone] = []
                
                # Отправляем выбор языка
                send_language_selection(phone)
                return "OK", 200
            
            session = user_sessions[phone]
            
            # Сохраняем в историю диалога
            user_dialog_history[phone].append({
                "role": "user",
                "content": text,
                "time": datetime.now().isoformat()
            })
            
            # Обработка сообщения
            response = process_message(phone, text, session)
            
            # Сохраняем ответ бота
            if response:
                user_dialog_history[phone].append({
                    "role": "assistant",
                    "content": response,
                    "time": datetime.now().isoformat()
                })
                
                # Ограничиваем историю
                user_dialog_history[phone] = user_dialog_history[phone][-50:]
                
                # Отправляем ответ
                send_whatsapp_message(phone, response)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ Ошибка в webhook: {e}")
        import traceback
        traceback.print_exc()
        return "OK", 200

def process_message(phone, text, session):
    """Главная логика обработки сообщений"""
    text_lower = text.lower()
    state = session.get("state", "ai_chat")
    lang = session.get("lang")
    
    # === ОБРАБОТКА ВЫБОРА ЯЗЫКА ===
    if state == "language_selection":
        if text.startswith("lang_"):
            selected_lang = text.replace("lang_", "")
            if selected_lang in LANGUAGES:
                session["lang"] = selected_lang
                session["state"] = "menu_selection"
                
                welcome_texts = {
                    'ru': f"""🎉 Добро пожаловать! 

Я — ассистент ОсОО «Арай групп», официального агента «Бакай Иншуренс» (15 лет опыта).

💰 *Кэшбэк 10%* на все полисы до 31 августа 2026!

Выберите тип страхования 👇""",
                    
                    'ky': f"""🎉 Кош келдиңиз!

Мен «Арай групп» ЖЧКнун ассистентимин, «Бакай Иншуренс»тин расмий агенти (15 жыл тажрыйба).

💰 *10% кэшбэк* бардык полистерге 2026-жылдын 31-августуна чейин!

Камсыздоо түрүн тандаңыз 👇""",
                    
                    'en': f"""🎉 Welcome!

I'm Aray Group assistant, official agent of Bakai Insurance (15 years experience).

💰 *10% cashback* on all policies until August 31, 2026!

Select insurance type 👇""",
                    
                    'tr': f"""🎉 Hoş geldiniz!

Ben Aray Group asistanı, Bakai Insurance resmi acentesi (15 yıl deneyim).

💰 *%10 cashback* tüm poliçelerde 31 Ağustos 2026'ya kadar!

Sigorta türünü seçin 👇""",
                    
                    'zh': f"""🎉 欢迎！

我是Aray Group的助理，Bakai Insurance的官方代理（15年经验）。

💰 *10%返现* 所有保单至2026年8月31日！

选择保险类型 👇"""
                }
                
                send_whatsapp_message(phone, welcome_texts.get(selected_lang, welcome_texts['ru']))
                send_insurance_menu(phone, selected_lang)
                return None
        
        # Если не выбрал язык — напоминаем
        send_language_selection(phone)
        return None
    
    # === ОБРАБОТКА ВЫБОРА ТИПА СТРАХОВАНИЯ ===
    if state == "menu_selection":
        if text.startswith("type_"):
            insurance_type = text.replace("type_", "")
            if insurance_type in INSURANCE_TYPES:
                session["insurance_type"] = insurance_type
                session["state"] = "data_collection"
                session["question_index"] = 0
                session["data"] = {}
                
                # Отправляем первый вопрос
                questions = COLLECTION_QUESTIONS[insurance_type][lang]
                first_question = questions[0][1]
                
                intro_texts = {
                    'ru': f"""📝 *Оформление {INSURANCE_TYPES[insurance_type][lang]['name']}*

{INSURANCE_TYPES[insurance_type][lang]['desc']}

Отлично! Соберу информацию для точного расчёта. Кэшбэк 10% гарантирован! 💰

{first_question}""",
                    
                    'ky': f"""📝 *{INSURANCE_TYPES[insurance_type][lang]['name']} дайындоо*

{INSURANCE_TYPES[insurance_type][lang]['desc']}

Сонун! Такыба үчүн маалымат чогултайын. 10% кэшбэк кепилденген! 💰

{first_question}""",
                    
                    'en': f"""📝 *{INSURANCE_TYPES[insurance_type][lang]['name']} Application*

{INSURANCE_TYPES[insurance_type][lang]['desc']}

Great! I'll collect information for accurate calculation. 10% cashback guaranteed! 💰

{first_question}""",
                    
                    'tr': f"""📝 *{INSURANCE_TYPES[insurance_type][lang]['name']} Başvurusu*

{INSURANCE_TYPES[insurance_type][lang]['desc']}

Harika! Hesaplama için bilgi toplayacağım. %10 cashback garantili! 💰

{first_question}""",
                    
                    'zh': f"""📝 *办理{INSURANCE_TYPES[insurance_type][lang]['name']}*

{INSURANCE_TYPES[insurance_type][lang]['desc']}

很好！我来收集信息以准确计算。10%返现保证！💰

{first_question}"""
                }
                
                return intro_texts.get(lang, intro_texts['ru'])
        
        # Если выбрал не кнопкой — проверяем текстовые команды
        type_keywords = {
            'osago': ['осаго', 'osago', 'авто', 'машина', 'car'],
            'kasko': ['каско', 'kasko', 'полное', 'full'],
            'travel': ['путешеств', 'travel', 'саякат', 'seyahat', 'виза', 'visa'],
            'property': ['имущество', 'property', 'мүлк', 'mülk', 'квартира', 'дом']
        }
        
        for ins_type, keywords in type_keywords.items():
            if any(kw in text_lower for kw in keywords):
                session["insurance_type"] = ins_type
                session["state"] = "data_collection"
                session["question_index"] = 0
                session["data"] = {}
                
                questions = COLLECTION_QUESTIONS[ins_type][lang]
                return f"""📝 {INSURANCE_TYPES[ins_type][lang]['name']}

{INSURANCE_TYPES[ins_type][lang]['desc']}

{questions[0][1]}"""
        
        # Если не распознали — используем ИИ
        history = session.get("history", [])
        response = get_ai_response(text, history, lang)
        
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        session["history"] = history[-10:]
        
        # Добавляем подсказку о меню
        response += f"\n\n{'_'*20}\n"
        menu_hints = {
            'ru': "Выберите: ОСАГО | КАСКО | Путешествия | Имущество",
            'ky': "Тандаңыз: ОСАГО | КАСКО | Саякат | Мүлк",
            'en': "Select: OSAGO | KASKO | Travel | Property",
            'tr': "Seçin: OSAGO | KASKO | Seyahat | Mülk",
            'zh': "选择：车辆强制险 | 车辆全险 | 旅行险 | 财产险"
        }
        response += menu_hints.get(lang, menu_hints['ru'])
        
        return response
    
    # === СБОР ДАННЫХ ===
    if state == "data_collection":
        return process_data_collection(phone, text, session)
    
    # === AI РЕЖИМ (по умолчанию) ===
    history = session.get("history", [])
    response = get_ai_response(text, history, lang)
    
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})
    session["history"] = history[-10:]
    
    return response

def process_data_collection(phone, text, session):
    """Пошаговый сбор данных от клиента"""
    lang = session.get("lang", 'ru')
    insurance_type = session.get("insurance_type")
    question_index = session.get("question_index", 0)
    data = session.get("data", {})
    
    questions = COLLECTION_QUESTIONS[insurance_type][lang]
    
    # Сохраняем ответ на предыдущий вопрос
    if question_index > 0 and question_index <= len(questions):
        prev_key = questions[question_index - 1][0]
        data[prev_key] = text
        session["data"] = data
    
    # Проверяем, есть ли ещё вопросы
    if question_index < len(questions):
        # Отправляем следующий вопрос
        next_question = questions[question_index][1]
        session["question_index"] = question_index + 1
        return next_question
    
    # Все вопросы заданы — отправляем лид менеджеру
    send_lead_to_manager(phone, user_dialog_history.get(phone, []), data, insurance_type)
    
    # Сбрасываем состояние
    session["state"] = "ai_chat"
    session["question_index"] = 0
    
    success_texts = {
        'ru': f"""🎉 *Заявка отправлена!*

Все данные переданы менеджеру ОсОО «Арай групп».

Он перезвонит вам в течение 15 минут для точного расчёта и оформления с кэшбэком 10%! 💰

📞 {ARAY_PHONE_DISPLAY}

Нужна помощь с чем-то ещё? 😊""",
        
        'ky': f"""🎉 *Тапшырма жөнөтүлдү!*

Бардык маалыматтар «Арай групп» менеджерине жөнөтүлдү.

Ал 10% кэшбэк менен так эсептөө үчүн 15 мүнөт ичинде чалат! 💰

📞 {ARAY_PHONE_DISPLAY}

Башка жардам керекпи? 😊""",
        
        'en': f"""🎉 *Application sent!*

All data forwarded to Aray Group manager.

He'll call within 15 minutes for exact calculation with 10% cashback! 💰

📞 {ARAY_PHONE_DISPLAY}

Need help with anything else? 😊""",
        
        'tr': f"""🎉 *Başvuru gönderildi!*

Tüm bilgiler Aray Group yöneticisine iletildi.

15 dakika içinde %10 cashback ile hesaplama için arayacak! 💰

📞 {ARAY_PHONE_DISPLAY}

Başka bir konuda yardım ister misiniz? 😊""",
        
        'zh': f"""🎉 *申请已发送！*

所有数据已转给Aray Group经理。

他将在15分钟内致电进行准确计算，享受10%返现！💰

📞 {ARAY_PHONE_DISPLAY}

还需要其他帮助吗？😊"""
    }
    
    return success_texts.get(lang, success_texts['ru'])

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    print("="*60)
    print("ОСОО «АРАЙ ГРУПП» — AI АССИСТЕНТ 🤖")
    print("Официальный агент Бакай Иншуренс")
    print("="*60)
    print(f"📞 Менеджер: {ARAY_PHONE_DISPLAY}")
    print(f"💰 Кэшбэк: 10%")
    print(f"🌍 Языки: RU, KY, EN, TR, ZH")
    print("="*60)
    app.run(debug=False, host="0.0.0.0", port=5000)
