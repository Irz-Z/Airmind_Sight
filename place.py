import requests

API_KEY = "dUO6Sbg1KV3GZEqtgwpsVisvOMTS0b8D"
BASE_URL = "https://tatdataapi.io/api/v2/places/"

headers = {
    "accept": "application/json",
    "Accept-Language": "th",
    "x-api-key": API_KEY
}

for i in range(100000):  # ไล่จาก 0 ถึง 999
    url = f"{BASE_URL}{i}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "category" in data:
                print(f"[places/{i}] => categoryId: {data['category'].get('categoryId')} | name: {data['category'].get('name')}")
            else:
                print(f"[places/{i}] => ไม่มี category")
        else:
            print(f"[places/{i}] => HTTP {response.status_code}")
    except Exception as e:
        print(f"[places/{i}] => ERROR: {e}")
