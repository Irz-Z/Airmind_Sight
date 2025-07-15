import requests
import json
import time

from fetch_data import *

# IQAIR
data = fetch_all_data('0199d98b-12a7-4ea8-8ef8-674a08a79ce7', provinces, 'w')
print(json.dumps(data, indent=2, ensure_ascii=False))

# aqicn
forecast_data = get_forecast('2eb93a22c78a1235a2f52546750a691ba41cd200', provinces, 'w')
print(json.dumps(forecast_data, indent=2, ensure_ascii=False))