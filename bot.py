import telebot
import requests
from bs4 import BeautifulSoup
from telebot import types
from pprint import pprint
import json, os

from config import BOT_TOKEN, kaliningrad_url, weather_kaliningrad_url, temp_kaliningrad_url, OPENWEATHER_API_KEY, \
    Kaliningrad_lon, Kaliningrad_lat, default_city, get_city_ru, DB_FILE
import time

bot = telebot.TeleBot(BOT_TOKEN)
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def save_user(user_id, city):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[str(user_id)] = {"city": city}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_city(user_id):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(str(user_id), {}).get("city")


# ====== 1. Функция парсинга ======
def get_air_quality():
    url = kaliningrad_url
    headers = {"User-Agent": "Mozilla/5.0"}  # чтобы сайт не блокировал запрос
    response = requests.get(url, headers=headers, timeout=10)

    soup = BeautifulSoup(response.text, "html.parser")

    # Ищем элемент, где хранится индекс AQI
    element = soup.select_one(".text-lg.font-medium")
    if element:
        return element.text.strip()
    else:
        return "Не удалось получить данные..."

def get_text_quality(quality):
    quality = quality.strip("*")
    quality = int(quality)
    if quality <= 50:
        return ", хорошее 🟢"
    elif 51 <= quality <= 100:
        return ", приемлемое 🟡"
    elif 101 <= quality <= 151:
        return ", неприемлемо для чувствительных 🟠"
    elif 151 <= quality <= 200:
        return ", нездоровое 🟠"
    elif 201 <= quality <= 300:
        return ", очень нездоровое 🔴"
    elif 301 <= quality <= 500:
        return ", опасное для жизни 🔴⚠"

def get_weather(user_id):
    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={get_city(user_id)}&appid={OPENWEATHER_API_KEY}&units=metric")
    data = r.json()

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    pressure = data["main"]["pressure"]
    wind_speed = data["wind"]["speed"]
    deg_wind_direction = data["wind"]["deg"]
    visibility = data["visibility"]

    def get_wind_direction(azimuth: float) -> str:
        azimuth = azimuth % 360
        directions = [
            ("С ⬆️"),  # 0°
            ("СВ ↗️"),  # 45°
            ("В ➡️"),  # 90°
            ("ЮВ ↘️"),  # 135°
            ("Ю ⬇️"),  # 180°
            ("ЮЗ ↙️"),  # 225°
            ("З ⬅️"),  # 270°
            ("СЗ ↖️"),  # 315°
            ("С ⬆️")  # 360°
        ]
        index = int((azimuth + 22.5) // 45)
        direction = directions[index]
        return direction


    wind_direction = get_wind_direction(deg_wind_direction)

    return temp, humidity, pressure, wind_speed, wind_direction, visibility



# ====== 2. Кнопка для получения данных ======
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🌡 Текущая информация")
    btn2 = types.KeyboardButton("🗺 Карта")
    btn3 = types.KeyboardButton("⚙ Настройки")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "👋<b> Здравствуйте!</b>\n\n В <b>Windqualify</b> можно узнать"
                                      " информацию о качестве воздуха в <i>📍 Калининграде</i>, а так же"
                                      " других его параметрах и получить рекомендации по улучшению экологической обстановки (и не только).\n\n<b>></b> Город можно (будет) сменить в <b>⚙ Настройках</b>.", reply_markup=markup, parse_mode='html')

    save_user(user_id=message.chat.id, city=default_city)


# ====== 3. Ответ на нажатие кнопки ======
@bot.message_handler(func=lambda message: message.text == "🌡 Текущая информация")
def send_information(message):

    btn1 = types.InlineKeyboardButton("🌳 Высадка деревьев", callback_data="trees_for_planting")
    btn2 = types.InlineKeyboardButton("🚜 Рекомендуемые удобрения", callback_data="grow_catalizators")
    btn3 = types.InlineKeyboardButton("🌊 Качество морской воды", callback_data="sea_water_quality")
    btn4 = types.InlineKeyboardButton("🗑 Информация о загрязнениях", callback_data="pollution_info")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(btn1, btn2, btn3, btn4)

    todel = bot.send_message(message.chat.id, "⌛")
    quality = get_air_quality()
    temp, humidity, pressure, wind_speed, wind_direction, visibility = get_weather(message.chat.id)
    bot.send_message(message.chat.id, f"📍 <b>{get_city_ru(get_city(message.chat.id))}</b>\n\n"
                                      f"🍃 <b><u>Качество воздуха</u></b>: <b>{quality}</b>{get_text_quality(quality)}\n\n"
                                      f"🌡 <u>Температура</u>: <b>{temp}</b> °С\n"
                                      f"💨 <u>Ветер</u>: <b>{wind_speed}</b> м/с, {wind_direction}\n"
                                      f"♨ <u>Давление</u>: <b>{round(int(pressure) * 0.75006, 1)}</b> мм рт. ст.\n"
                                      f"💧 <u>Влажность</u>: <b>{humidity}%</b>\n"
                                      f"🌫 <u>Видимость</u>: <b>{visibility}</b> м\n", parse_mode="html", reply_markup=markup)
    bot.delete_message(message.chat.id, todel.id)

@bot.message_handler(func=lambda message: message.text == "⚙ Настройки")
def send_settings(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📍 Ваш город", callback_data="another_city")
    markup.add(btn1)

    bot.send_message(message.chat.id, "👇 Выберите параметр, который хотите изменить:", reply_markup=markup, parse_mode="html")

def is_english(text):
    return all(c.isalpha() and c.isascii() or c.isspace() for c in text)

def save_city(message):
    user_id = message.from_user.id
    city = message.text

    if is_english(city) == True:
        save_user(user_id=user_id, city=city)
        bot.send_message(message.chat.id, f"✅ Ваш новый город: {get_city_ru(city)}.")
    else:
        bot.send_message(message.chat.id, f"❌ Город должен быть написан английскими буквами на английском "
                                          f"языке. Попробуйте снова в ⚙ Настройках")


# === ОБРАБОТЧИК КНОПОК ===
@bot.callback_query_handler(func=lambda c: c.data == "another_city")
def callback_change_city(c):
    bot.answer_callback_query(c.id)  # ← ОБЯЗАТЕЛЬНО!

    user_id = c.from_user.id
    current_city = get_city(user_id) or default_city

    msg = bot.send_message(
        c.message.chat.id,
        f"📍 Текущий город: *{get_city_ru(current_city)}*\n\n"
        "Введите новый город на **английском** (например: Moscow, Kaliningrad):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_city)  # ← ПРАВИЛЬНО


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            if call.data == 'trees_for_planting':
                bot.send_message(call.message.chat.id, '123')
            else:
                pass
        else:
            pass
    except Exception as e:
        print(e)

# ====== 4. Запуск ======
print("========================================< Бот запущен >========================================")


while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        time.sleep(3)


