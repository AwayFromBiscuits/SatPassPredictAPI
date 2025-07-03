from fastapi import FastAPI, Request
from urllib.parse import parse_qs
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from logging.handlers import RotatingFileHandler
import numpy as np
import httpx
import os
import json
import asyncio
import logging

app = FastAPI()
tle_lines = {}
TLE_FILE = "tle_cache.txt"
sat_id_name_map = {}
TLE_NAME_FILE = "tle_name_cache.json"
API_KEYS_FILE = "api_keys.txt"

SPACE_TRACK_USER = "XXX" # spacetrack account
SPACE_TRACK_PASS = "XXX" # spacetrack account password
SAT_ID = [25544, 27607, 43017, 61781, 62690, 63492] # sat data
API_KEY_CHECK = True # api key settings
LOG_FILE = "access.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    encoding="utf-8"
)

handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[handler]
)

ids_str = ",".join(map(str, SAT_ID))

def az_compass(deg):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = int((deg + 11.25) // 22.5) % 16
    return dirs[ix]

async def load_tle_from_file():
    global tle_lines
    tle_lines.clear()
    if os.path.exists(TLE_FILE):
        with open(TLE_FILE) as f:
            lines = [line.strip() for line in f if line.strip()]
            for i in range(0, len(lines), 2):
                l1 = lines[i]
                l2 = lines[i+1]
                try:
                    satnum = int(l1[2:7])
                    name = sat_id_name_map.get(str(satnum))
                    if not name:
                        name = await fetch_sat_name_from_spacetrack(satnum)
                    tle_lines[satnum] = (name, l1, l2)
                except Exception as e:
                    print(f"Skipping bad TLE lines: {l1} {l2} due to {e}")
                    continue

def load_name_map():
    global sat_id_name_map
    if os.path.exists(TLE_NAME_FILE):
        with open(TLE_NAME_FILE, "r", encoding="utf-8") as f:
            sat_id_name_map = json.load(f)
    else:
        sat_id_name_map = {}

def save_name_map():
    with open(TLE_NAME_FILE, "w", encoding="utf-8") as f:
        json.dump(sat_id_name_map, f, indent=2, ensure_ascii=False)

async def fetch_tle_from_space_track():
    print(f"[{datetime.utcnow()}] Fetching TLE data from space-track.org...")
    login_url = "https://www.space-track.org/ajaxauth/login"
    tle_url = f"https://www.space-track.org/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{ids_str}/format/tle"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(login_url, data={
                "identity": SPACE_TRACK_USER,
                "password": SPACE_TRACK_PASS
            })
            if resp.status_code != 200:
                print("Login failed.")
                return

            tle_resp = await client.get(tle_url)
            if tle_resp.status_code == 200:
                with open(TLE_FILE, "w") as f:
                    f.write(tle_resp.text)
                print("TLE cache updated.")
                await load_tle_from_file()
            else:
                print("Failed to fetch TLE data.")
        except Exception as e:
            print(f"Error fetching TLE: {e}")

async def fetch_sat_name_from_spacetrack(satid: int) -> str:
    login_url = "https://www.space-track.org/ajaxauth/login"
    json_url = f"https://www.space-track.org/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{satid}/format/json"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            login = await client.post(login_url, data={
                "identity": SPACE_TRACK_USER,
                "password": SPACE_TRACK_PASS
            })
            if login.status_code != 200:
                print(f"Login failed while fetching name for {satid}")
                return f"SAT-{satid}"

            resp = await client.get(json_url)
            if resp.status_code == 200:
                data = resp.json()
                if data and "OBJECT_NAME" in data[0]:
                    name = data[0]["OBJECT_NAME"]
                    sat_id_name_map[str(satid)] = name
                    save_name_map()
                    return name
        except Exception as e:
            print(f"Error fetching sat name for {satid}: {e}")
    return f"SAT-{satid}"

# tle data initialization
@app.on_event("startup")
async def startup_event():
    load_name_map()
    if not os.path.exists(TLE_FILE):
        await fetch_tle_from_space_track()
    await load_tle_from_file()
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(fetch_tle_from_space_track()), 'interval', hours=2)
    scheduler.start()

def load_api_keys():
    if not os.path.exists(API_KEYS_FILE):
        return set()
    with open(API_KEYS_FILE) as f:
        return set(line.strip() for line in f if line.strip())

# api request parsing
@app.get("/{satid}/{lat}/{lon}/{alt}/{days}/{rest}")
async def predict_passes_route(
    request: Request,
    satid: int,
    lat: float,
    lon: float,
    alt: float,
    days: int,
    rest: str
):

    try:
        if '&' in rest:
            min_minutes_str, raw_query = rest.split('&', 1)
            min_minutes = int(min_minutes_str)

            query_dict = parse_qs(raw_query)
            api_key = query_dict.get("apikey", [""])[0] or query_dict.get("apiKey", [""])[0]
        else:
            min_minutes = int(rest)

            api_key = request.query_params.get("apiKey") or request.query_params.get("apikey")
    except Exception as e:
        return {"error": f"参数解析错误: {str(e)}"}



    if API_KEY_CHECK:
        if not api_key:
            return {"error": "缺少 API Key 参数"}
        valid_keys = load_api_keys()
        if api_key not in valid_keys:
            return {"error": "无效的API Key"}
    if satid not in tle_lines:
        return {"error": "未缓存此id的卫星！"}

    name, l1, l2 = tle_lines[satid]
    satellite = EarthSatellite(l1, l2, name)
    ts = load.timescale()

    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt * 1000)
    now_utc = datetime.now(timezone.utc)
    t0 = ts.utc(now_utc.year, now_utc.month, now_utc.day, now_utc.hour, now_utc.minute, now_utc.second)
    future_time = now_utc + timedelta(days=days)
    t1 = ts.utc(future_time.year, future_time.month, future_time.day, future_time.hour, future_time.minute, future_time.second)


    t, events = satellite.find_events(observer, t0, t1, altitude_degrees=0.0)

    passes = []
    this_pass = {}

    for ti, event in zip(t, events):
        alt, az, _ = (satellite - observer).at(ti).altaz()

        if event == 0:
            this_pass = {
                "startAz": round(az.degrees, 2),
                "startAzCompass": az_compass(az.degrees),
                "startUTC": int(ti.utc_datetime().timestamp())
            }
        elif event == 1:
            this_pass.update({
                "maxAz": round(az.degrees, 2),
                "maxAzCompass": az_compass(az.degrees),
                "maxEl": round(alt.degrees, 2),
                "maxUTC": int(ti.utc_datetime().timestamp())
            })
        elif event == 2:
            this_pass.update({
                "endAz": round(az.degrees, 2),
                "endAzCompass": az_compass(az.degrees),
                "endUTC": int(ti.utc_datetime().timestamp())
            })
            duration = (this_pass["endUTC"] - this_pass["startUTC"]) / 60.0
            if duration >= min_minutes:
                passes.append(this_pass)
    
    client_ip = request.client.host
    logging.info(f"API Access - Key: {api_key} - IP: {client_ip} - SATID: {satid}")

    return {
        "info": {
            "satid": satid,
            "satname": name,
            "transactionscount": len(passes),
            "passescount": len(passes)
        },
        "passes": passes
    }
