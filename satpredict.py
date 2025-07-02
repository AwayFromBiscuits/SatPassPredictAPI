from fastapi import FastAPI
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone
import numpy as np
import httpx
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
tle_lines = {}
TLE_FILE = "tle_cache.txt"

# account data
SPACE_TRACK_USER = "xxx" # spacetrack account
SPACE_TRACK_PASS = "xxx" # spacetrack account password

#sat data
SAT_ID = [111, 222, 333]
ids_str = ",".join(map(str, SAT_ID)) # satellite id

def az_compass(deg):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = int((deg + 11.25) // 22.5) % 16
    return dirs[ix]

def load_tle_from_file():
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
                    name = f"SAT-test"
                    tle_lines[satnum] = (name, l1, l2)
                except Exception as e:
                    print(f"Skipping bad TLE lines: {l1} {l2} due to {e}")
                    continue

# fetching tle data from spacetrack
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
                load_tle_from_file()
            else:
                print("Failed to fetch TLE data.")
        except Exception as e:
            print(f"Error fetching TLE: {e}")

# tle data initialization
@app.on_event("startup")
async def startup_event():
    if not os.path.exists(TLE_FILE):
        await fetch_tle_from_space_track()
    load_tle_from_file()

    # scheduled tle data fetching task
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(fetch_tle_from_space_track()), 'interval', hours=2)
    scheduler.start()

# api request parsing
import asyncio
@app.get("/{satid}/{lat}/{lon}/{alt}/{days}/{min_minutes}")
def predict_passes(satid: int, lat: float, lon: float, alt: float, days: int, min_minutes: int):
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

    return {
        "info": {
            "satid": satid,
            "satname": name,
            "transactionscount": len(passes),
            "passescount": len(passes)
        },
        "passes": passes
    }