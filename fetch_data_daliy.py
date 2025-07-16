import requests
import json
import time

from fetch_data import *

# IQAIR
# API_KEY = '0199d98b-12a7-4ea8-8ef8-674a08a79ce7' # pppurpg@gmail.com
API_KEY = 'c926d92f-7623-4d75-81dd-7c5542c59e5e' # adisonbb2@gmail.com

# aqicn
key = '2eb93a22c78a1235a2f52546750a691ba41cd200'

# IQAIR
data = fetch_all_data(API_KEY, provinces, 'w')
print(json.dumps(data, indent=2, ensure_ascii=False))

# aqicn
forecast_data = get_forecast(key, provinces, 'w')
print(json.dumps(forecast_data, indent=2, ensure_ascii=False))