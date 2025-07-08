import requests

API_KEY = "dUO6Sbg1KV3GZEqtgwpsVisvOMTS0b8D"
BASE_URL = "https://tatdataapi.io/api/v2/places/"

headers = {
    "accept": "application/json",
    "Accept-Language": "th",
    "x-api-key": API_KEY
}

seen_categories = set()

for i in range(10000):  # ไล่จาก 0 ถึง 999
    url = f"{BASE_URL}{i}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            category = data.get("category")
            if category:
                cat_id = category.get("categoryId")
                cat_name = category.get("name")
                if cat_id not in seen_categories:
                    seen_categories.add(cat_id)
                    print(f"[places/{i}] => categoryId: {cat_id} | name: {cat_name}")
        else:
            print(f"[places/{i}] => HTTP {response.status_code}")
    except Exception as e:
        print(f"[places/{i}] => ERROR: {e}")
