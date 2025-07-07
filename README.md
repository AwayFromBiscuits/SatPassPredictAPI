# SatPassPredictAPI
Python program for satellite overpass prediction based on Skyfield and FastAPI.


## Features
- Local satellite overpass operation and output result via API.
- Hot loading temporary NORAD ID via API.

### Usage

#### Auto installation
- install dependencies and background persistence.

`bash init.sh`

- modify `config.env`.

- start the program.

`satpredict start`

- auto startup if you want.

`satpredict enable`

#### Manual installation

- install dependencies.

`pip install fastapi uvicorn skyfield numpy httpx apscheduler`

- modify modify `config.env`.

- start the program.

`uvicorn satpredict:app --host 0.0.0.0 --port 8000`

### API format

- Request input format
```
http://
  {ip/url}:{port}/
  {sat_id}/
  {latitude}/
  {longitude}/
  {altitude}/
  {predict_for_next_x_days}/
  {max_elevation_angle}
  {&/?}apikey={xxx} (optional)
```
example: `http://1.14.5.14:1919/12345/123.45/54.3210/0/3/10&apikey=123321`

example: `http://1.14.5.14:1919/12345/123.45/54.3210/0/3/10` (if apikey varification disabled)

- Output format
```
{
  "info":{
    "satid":25544,
    "satname":"SAT-test",
    "transactionscount":22,
    "passescount":22},
    "passes":[{
      "startAz":197.77,
      "startAzCompass":"SSW",
      "startUTC":1751467016,
      "maxAz":129.28,
      "maxAzCompass":"SE",
      "maxEl":21.95,
      "maxUTC":1751467316,
      "endAz":61.13,
      "endAzCompass":"ENE",
      "endUTC":1751467618
    },
    {
      ...
    },
  ]
}
```

- Update temporary id input format
```
http://
  {ip/url}:{port}/
  update_tle?
  extra_ids=12345,12346
  &apikey={xxx} (optional)
```

example: `http://1.14.5.14:1919/update_tle?extra_ids=12345,12346&apikey=ass-we-can`
- Output format
```
{"status":"ok","fetched_ids":[11111,22222,33333,44444],"added_ids":[12345,12346]}
```