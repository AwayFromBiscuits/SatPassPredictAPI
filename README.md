# SatPassPredictAPI
Python program for satellite transit prediction based on Skyfield and FastAPI.


## PROGRAM FOR TESTING PURPOSE ONLY!


### Usage

#### Auto installation
`bash init.sh`

#### Manual installation

- install dependencies.

`pip install fastapi uvicorn skyfield numpy httpx apscheduler`

- modified necessary parameters(SPACE_TRACK_USER, SPACE_TRACK_PASS, SAT_ID).

- start the program.

`uvicorn satpredict:app --host 0.0.0.0 --port 8000`

### API format

- INPUT format
```
http://
  {ip/url}:{port}/
  {sat_id}/
  {latitude}/
  {longitude}/
  {altitude}/
  {predict_for_next_x_days}/
  {max_elevation_angle}
```
example: `http://1.14.5.14:1919/12345/123.45/54.3210/0/3/10`

- OUT format
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
example: `{"info":{"satid":25544,"satname":"SAT-test","transactionscount":22,"passescount":22},"passes":[{"startAz":197.77,"startAzCompass":"SSW","startUTC":1751467016,"maxAz":129.28,"maxAzCompass":"SE","maxEl":21.95,"maxUTC":1751467316,"endAz":61.13,"endAzCompass":"ENE","endUTC":1751467618}]}`
