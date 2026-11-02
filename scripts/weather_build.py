#!/usr/bin/env python3
"""Генератор api/weather.json для Джарвис (погодная сетка городов РФ).

Качает Locationforecast с api.met.no (без ключа, идентификация по User-Agent)
и собирает JSON в формате, который приложение ждёт от своего /api/weather:
  {"ts": <epoch>, "points": [{lat, lon, temp, code, night, desc, icon,
    windDir, wind, feels, tz, min, max, hourly: [{t, temp, code, pop, day}]}]}
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

UA = "JarvisChery-weather/11.11 (github.com/mazovckiy-star/jarvis-store)"
URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.4f}&lon={lon:.4f}"

# Крупные города РФ и СНГ (lat, lon)
CITIES = [
    (55.7558, 37.6173), (59.9386, 30.3141), (56.2965, 43.9361), (55.7887, 49.1221),
    (56.8519, 60.6122), (54.9885, 73.3242), (55.3547, 86.0873), (53.7576, 87.1366),
    (55.0415, 82.9346), (58.0105, 56.2502), (51.7682, 55.0969), (50.6297, 36.5802),
    (48.4802, 135.0719), (43.1155, 131.8855), (62.0278, 129.7326), (56.4846, 84.9486),
    (54.9833, 82.8964), (53.7198, 91.4294), (52.2864, 104.2807), (51.8345, 107.5846),
    (64.5393, 40.5187), (61.7891, 34.3596), (59.2181, 39.8884), (57.7672, 40.9269),
    (56.4150, 61.8784), (54.3142, 48.4031), (53.1959, 50.1002), (50.4510, 40.1356),
    (48.7080, 44.5133), (47.2224, 38.9705), (46.3480, 48.0303), (48.0356, 46.5469),
    (51.5924, 45.9678), (53.2521, 50.2212), (55.7963, 49.2088), (57.6261, 39.8845),
    (58.5228, 31.2698), (59.9452, 30.3897), (60.1695, 30.2061), (55.9228, 37.8552),
    (55.6784, 37.8937), (55.8412, 48.5039), (56.3287, 44.002), (55.5705, 42.0294),
    (54.6292, 39.7416), (52.7213, 41.4523), (50.6126, 36.5882), (45.0355, 38.9753),
    (44.5634, 33.8739), (43.5855, 39.7231), (43.4703, 43.5711), (44.6345, 40.1215),
    (44.6723, 34.5408), (45.3563, 36.4674), (46.6332, 32.6278), (47.8388, 35.1396),
    (50.0055, 36.2315), (49.9935, 36.2304), (47.8563, 35.1058), (46.9750, 31.9957),
    (49.2328, 28.481), (49.5535, 25.5948), (48.4500, 34.9833), (48.0213, 37.8052),
    (47.9105, 33.3918), (46.4825, 30.7233), (49.8167, 30.1167), (53.9000, 27.5667),
    (53.6833, 23.8333), (55.5333, 28.65), (53.9167, 30.35), (54.8000, 32.05),
    (56.1500, 28.1), (55.1667, 30.1333), (53.05, 26.3167), (52.1, 23.7333),
    (61.6667, 50.8167), (67.5667, 33.4), (69.7833, 61.55), (64.7333, 177.5167),
    (56.1333, 101.6167), (52.5, 103.8), (51.8333, 107.6), (62.0333, 129.7333),
    (66.4, 112.55), (71.55, 128.15),
]

DESC = {
    0: 'Ясно', 1: 'Почти ясно', 2: 'Переменная облачность', 3: 'Пасмурно',
    45: 'Туман', 48: 'Туман', 51: 'Морось', 61: 'Небольшой дождь', 63: 'Дождь',
    65: 'Сильный дождь', 66: 'Ледяной дождь', 67: 'Ледяной дождь', 71: 'Снег',
    73: 'Снег', 75: 'Снег', 77: 'Снег', 85: 'Снег', 86: 'Снег',
    95: 'Гроза', 96: 'Гроза', 99: 'Гроза',
}


def code(sym: str) -> int:
    s = sym or ''
    if 'thunder' in s:
        return 95
    if 'snow' in s:
        return 75 if 'heavy' in s else 71
    if 'sleet' in s:
        return 67 if 'heavy' in s else 66
    if 'rain' in s:
        if 'heavy' in s:
            return 65
        return 61 if 'light' in s else 63
    if 'drizzle' in s:
        return 51
    if 'fog' in s:
        return 45
    if 'cloudy' in s:
        return 3
    if 'partlycloudy' in s:
        return 2
    if 'fair' in s:
        return 1
    if 'clearsky' in s:
        return 0
    return 3


def fetch(lat: float, lon: float):
    req = urllib.request.Request(URL.format(lat=lat, lon=lon), headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def symbol(data: dict) -> str:
    for k in ('next_1_hours', 'next_6_hours', 'next_12_hours'):
        v = (data.get(k) or {}).get('summary') or {}
        if v.get('symbol_code'):
            return v['symbol_code']
    return ''


def build_point(lat: float, lon: float, doc: dict) -> dict:
    ts = doc['properties']['timeseries']
    t0 = ts[0]
    d0 = t0['data']
    det0 = d0['instant']['details']
    sym0 = symbol(d0)
    temp = round(det0['air_temperature'])
    hourly = []
    for entry in ts[:48]:
        t = entry['time']
        dt = datetime.strptime(t[:19], '%Y-%m-%dT%H:%M:%S')
        epoch = int(dt.replace(tzinfo=timezone.utc).timestamp())
        det = entry['data']['instant']['details']
        sym = symbol(entry['data']) or sym0
        n1 = entry['data'].get('next_1_hours') or entry['data'].get('next_6_hours') or {}
        precip = ((n1.get('details') or {}).get('precipitation_amount')) or 0.0
        hourly.append({
            't': epoch,
            'temp': round(det['air_temperature']),
            'code': code(sym),
            'pop': min(100, round(precip * 20)),
            'day': not sym.endswith('_night'),
        })
    n6 = (d0.get('next_6_hours') or {}).get('details') or {}
    p = {
        'lat': lat, 'lon': lon,
        'temp': temp,
        'code': code(sym0),
        'night': sym0.endswith('_night'),
        'desc': DESC.get(code(sym0), 'Облачно'),
        'icon': '',
        'windDir': round(det0.get('wind_from_direction', 0)),
        'wind': det0.get('wind_speed', 0.0),
        'feels': round(det0.get('apparent_air_temperature', det0['air_temperature'])),
        'hourly': hourly,
    }
    if 'air_temperature_min' in n6:
        p['min'] = round(n6['air_temperature_min'])
    if 'air_temperature_max' in n6:
        p['max'] = round(n6['air_temperature_max'])
    return p


def main():
    out = []
    fail = 0
    for lat, lon in CITIES:
        try:
            doc = fetch(lat, lon)
            out.append(build_point(lat, lon, doc))
        except Exception as e:
            fail += 1
            print(f"warn: {lat},{lon}: {e}", file=sys.stderr)
        time.sleep(0.25)  # бережём rate-limit met.no
    result = {'ts': int(time.time()), 'points': out}
    with open(sys.argv[1] if len(sys.argv) > 1 else 'weather.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
    print(f"ok: {len(out)} points, {fail} failed")


if __name__ == '__main__':
    main()
