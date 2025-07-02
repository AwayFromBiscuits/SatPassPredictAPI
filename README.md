# SatPassPredictAPI
Python program for satellite transit prediction based on Skyfield and FastAPI.


## PROGRAM FOR TESTING PURPOSE ONLY!


### Usage

install dependencies.

`pip install fastapi uvicorn skyfield numpy httpx apscheduler`

modified necessary parameters(SPACE_TRACK_USER, SPACE_TRACK_PASS, SAT_ID).

start the program.

`uvicorn satpredict:app --host 0.0.0.0 --port 8000`
