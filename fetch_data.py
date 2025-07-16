import requests
import json
import time

# def get_provinces_list(API_KEY):
#     country = "Thailand"
#     url = f"http://api.airvisual.com/v2/states?country={country}&key={API_KEY}"
    
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
        
#         provinces = []
#         response_json = response.json()
        
#         if response_json.get("status") == "success" and isinstance(response_json["data"], list):
#             for item in response_json["data"]:
#                 provinces.append(item["state"])
                
#         return provinces
#     except Exception as e:
#         print(f"Error fetching provinces: {e}")
#         return []

# IQAIR
def get_data(API_KEY, province):
    url = f'http://api.airvisual.com/v2/city?city={province}&state={province}&country=Thailand&key={API_KEY}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # ส่งคืนข้อมูลเป็น JSON string
        return json.dumps(response.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error fetching data for {province}: {e}")
        return json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False)

def fetch_all_data(API_KEY, provinces, condition):
    results = {}
    
    for i, province in enumerate(provinces):
        print(f"Fetching data for {province} ({i+1}/{len(provinces)})")
        
        try:
            data_str = get_data(API_KEY, province)
            data = json.loads(data_str)
            results[province] = data
            
            # หน่วงเวลา เพื่อไม่ให้ API rate limit
            time.sleep(13)
            
        except Exception as e:
            print(f"Error processing {province}: {e}")
            results[province] = {"status": "error", "message": str(e)}
    
    if condition == 'w':
        try:
            with open('forecast_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing forecast file: {e}")
    return results

# aqicn
def get_forecast(key, provinces, condition):
    result = {}
    
    for province in provinces:
        print(f"Fetching forecast for {province}")
        
        try:
            url = f'https://api.waqi.info/feed/{province}/?token={key}'
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()

            if data['status'] == 'ok' and 'forecast' in data['data'] and 'daily' in data['data']['forecast']:
                daily_data = data['data']['forecast']['daily']
                
                # ลบ o3 และ uvi ถ้ามี
                daily_data.pop('o3', None)
                daily_data.pop('uvi', None)
                
                result[province] = daily_data
            else:
                result[province] = {"status": data.get("status", "fail")}
                
            # หน่วงเวลา 1 วินาที
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching forecast for {province}: {e}")
            result[province] = {"status": "error", "message": str(e)}

    if condition == 'w':
        try:
            with open('forecast_results.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing forecast file: {e}")
    return result

provinces = ['Amnat Charoen', 'Ang Thong', 'Bangkok', 'Buriram', 'Chachoengsao', 
             'Chai Nat', 'Chaiyaphum', 'Changwat Bueng Kan', 'Changwat Ubon Ratchathani', 
             'Chanthaburi', 'Chiang Mai', 'Chiang Rai', 'Chon Buri', 'Chumphon', 'Kalasin', 
             'Kamphaeng Phet', 'Kanchanaburi', 'Khon Kaen', 'Krabi', 'Lampang', 'Lamphun', 
             'Loei', 'Lopburi', 'Mae Hong Son', 'Maha Sarakham', 'Mukdahan', 'Nakhon Nayok', 
             'Nakhon Pathom', 'Nakhon Phanom', 'Nakhon Ratchasima', 'Nakhon Sawan', 
             'Nakhon Si Thammarat', 'Nan', 'Narathiwat', 'Nong Bua Lamphu', 'Nong Khai', 
             'Nonthaburi', 'Pathum Thani', 'Pattani', 'Phangnga', 'Phatthalung', 'Phayao', 
             'Phetchabun', 'Phetchaburi', 'Phichit', 'Phitsanulok', 'Phra Nakhon Si Ayutthaya', 
             'Phrae', 'Phuket', 'Prachin Buri', 'Prachuap Khiri Khan', 'Ranong', 'Ratchaburi', 
             'Rayong', 'Roi Et', 'Sa Kaeo', 'Sakon Nakhon', 'Samut Prakan', 'Samut Sakhon', 
             'Samut Songkhram', 'Sara Buri', 'Satun', 'Sing Buri', 'Sisaket', 'Songkhla', 
             'Sukhothai', 'Suphan Buri', 'Surat Thani', 'Surin', 'Tak', 'Trang', 'Trat', 
             'Udon Thani', 'Uthai Thani', 'Uttaradit', 'Yala', 'Yasothon']

# IQAIR
# data = fetch_all_data('0199d98b-12a7-4ea8-8ef8-674a08a79ce7', provinces, 'w')
# print(json.dumps(data, indent=2, ensure_ascii=False))

# aqicn
# forecast_data = get_forecast('2eb93a22c78a1235a2f52546750a691ba41cd200', provinces, 'w')
# print(json.dumps(forecast_data, indent=2, ensure_ascii=False))