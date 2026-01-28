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
    CELEBRAS_API_KEY, moscow_url_air, spb_air_url, pskov_air_url, barnaul_air_url, kazan_air_url, vladivostok_air_url
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

def get_or_create_daily_value(city: str) -> int:
    today = datetime.now().strftime("%Y-%m-%d")

    with open(DB2_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    city_key = city.lower()

    if city_key in data and today in data[city_key]:
        return data[city_key][today]

    value = random.randint(20, 60)

    if city_key not in data:
        data[city_key] = {}

    data[city_key][today] = value

    with open(DB2_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return value


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

    elif city in ['Moscow', 'moscow']:
        url = moscow_url_air
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."
    elif city in ['St-Petersburg', 'St Petersburg', 'Saint-Petersburg', 'Saint Petersburg']:
        url = spb_air_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."

    elif city in ['Pskov', 'pskov']:
        url = pskov_air_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."

    elif city in ['Barnaul', 'barnaul']:
        url = barnaul_air_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."

    elif city in ['Kazan', 'kazan']:
        url = kazan_air_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        element = soup.select_one(".text-lg.font-medium")
        if element:
            return element.text.strip('*')
        else:
            return "Не удалось получить данные..."

    elif city in ['Vladivostok', 'vladivostok']:
        url = vladivostok_air_url
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
        return f"{get_or_create_daily_value(city)}"


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

        url = gdansk_pollution_url   🔹

        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        div = soup.find('div', {'id': 'water_quality'})

        if div:
            value = div.get('aria-valuenow')
            return value
        else:
            return 00.00
    else:
        return 00.00




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
        "Введите новый город на <b>английском</b> (например: <code>Moscow</code>, <code>Kaliningrad</code>, <code>Saint Petersburg</code>, <code>Pskov</code>, <code>Barnaul</code>, <code>Kazan</code>, <code>Vladivostok</code>):"
        "\n\n<i>‼️ Корректное значение ИКВ отображается только для городов из указанного списка. Для остальных городов это значение является случайным (демо-функция). <u>Все остальные значения отображаются корректно для всех городов!</u></i>", parse_mode="html"
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

            if humidity < 40:
                recommendations.append("<b>🌵 Сосна или можжевельник</b> — хорошо чувствуют себя при низкой влажности.")
            elif humidity > 80:
                recommendations.append("<b>🌾 Ива белая </b>— любит влажные почвы и понижает уровень загрязнений.")

            if wind_speed > 8:
                recommendations.append("<b>🌲 Посадите еловые или сосновые ряды</b> — они служат отличной ветрозащитой.")

            if int(air_quality) >= 60:
                recommendations.append(
                    "🌿 Рекомендуется <b>больше зелёных насаждений с крупной листвой</b>: клён, каштан, липа.")
            elif int(air_quality) <= 59:
                recommendations.append(
                    "🌼<b> Подойдут плодовые деревья</b> — яблони, груши: они улавливают пыль и очищают воздух.")

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

            if humidity < 40:
                fertilizers.append("💦 В сухую погоду вносите удобрения <b>только после полива</b>, иначе корни могут пострадать.")
                fertilizers.append("🌿 Подойдут <b>жидкие удобрения с микроэлементами (Mg, Zn, Fe).</b>")
            elif humidity > 80:
                fertilizers.append("🌧 При высокой влажности <b>избегайте азотных удобрений — используйте калийные и фосфорные</b> для укрепления корней.")

            if wind_speed > 8:
                fertilizers.append("💨 В ветреную погоду <b>не распыляйте листовые удобрения</b> — лучше использовать <b>гранулированные в почву.</b>")

            if int(air_quality) >= 60:
                fertilizers.append("🩺 Рекомендуются <b>удобрения с повышенным содержанием кальция и магния</b> — они помогают растениям справляться с загрязнением воздуха.")
            elif int(air_quality) < 60:
                fertilizers.append("🌼 Хорошо подойдут <b>органические удобрения и гуматы</b> — они повышают иммунитет растений к неблагоприятным факторам.")

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


