import requests
import pprint

# === Telegram ===
BOT_TOKEN = "YOUR_TOKEN"

kaliningrad_url = "https://www.iqair.com/ru/russia/kaliningrad/kaliningrad"
temp_kaliningrad_url = "https://rp5.ru/%D0%9F%D0%BE%D0%B3%D0%BE%D0%B4%D0%B0_%D0%B2_%D0%9A%D0%B0%D0%BB%D0%B8%D0%BD%D0%B8%D0%BD%D0%B3%D1%80%D0%B0%D0%B4%D0%B5"
weather_kaliningrad_url = "https://www.gismeteo.ru/weather-kaliningrad-4225/now/"

DB_FILE = "db.json"

OPENWEATHER_API_KEY = "YOUR_API_KEY"
Kaliningrad_lat = 54.705421
Kaliningrad_lon = 20.508170

default_city = 'Kaliningrad'

def get_city_ru(city):
    if city == None:
        return 'not defined'
    r = requests.get(f'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ru&dt=t&q={city}')
    data = r.json()
    city_ru = data[0][0][0]

    return city_ru
