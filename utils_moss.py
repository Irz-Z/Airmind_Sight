import requests
import time
import math
import os
import datetime
import json
from collections import defaultdict

# แผนที่ชื่อเล่น → ชื่อจังหวัดจริง
ALIAS_TO_PROVINCE = {
    "โคราช": "นครราชสีมา",
    "กทม": "กรุงเทพมหานคร",
    "บางกอก": "กรุงเทพมหานคร",
    "พัทยา": "ชลบุรี",
    "อุบล": "อุบลราชธานี",
    "ขอนแก่น": "ขอนแก่น",
    "เชียงใหม่": "เชียงใหม่",
    "ภูเก็ต": "ภูเก็ต",
    "กระบี่": "กระบี่",
    "สุราษฎร์ธานี": "สุราษฎร์ธานี"
}

# แผนที่อำเภอ → จังหวัดหลัก (สำหรับ forecast data)
DISTRICT_TO_PROVINCE = {
    "พิมาย": "Nakhon Ratchasima",
    "ปากช่อง": "Nakhon Ratchasima", 
    "โคราช": "Nakhon Ratchasima",
    "พัทยา": "Chonburi",
    "เกาะช้าง": "Trat",
    "เกาะสมุย": "Surat Thani",
    "หัวหิน": "Prachuap Khiri Khan",
    "อยุธยา": "Phra Nakhon Si Ayutthaya"
}

# แผนที่ชื่อจังหวัดไทย → อังกฤษ (สำหรับ forecast data)
THAI_TO_ENGLISH_PROVINCE = {
    "กรุงเทพมหานคร": "Bangkok",
    "นครราชสีมา": "Nakhon Ratchasima",
    "ชลบุรี": "Chonburi",
    "เชียงใหม่": "Chiang Mai",
    "ภูเก็ต": "Phuket",
    "กระบี่": "Krabi",
    "สุราษฎร์ธานี": "Surat Thani",
    "อุบลราชธานี": "Ubon Ratchathani",
    "ขอนแก่น": "Khon Kaen",
    "ตราด": "Trat",
    "ประจวบคีรีขันธ์": "Prachuap Khiri Khan",
    "พระนครศรีอยุธยา": "Phra Nakhon Si Ayutthaya"
}

# AirVisual API Key (Community tier: 10,000 calls/year, expires Jul 8, 2026)
AIRVISUAL_API_KEY = "eeb3ba1c-2778-4b29-a766-30a21e6fa7c8"
API_CALL_COUNT = 0  # ตัวนับการใช้ API
MAX_API_CALLS = 10000  # ขีดจำกัดต่อปี

# Global cache for air quality data
AIR_QUALITY_CACHE = {}

# Directory for daily JSON cache files
CACHE_DIR = "cache"

def normalize_province_name(name):
    """ปรับชื่อจังหวัดให้เป็นมาตรฐานจากชื่อเล่นหรือชื่อเต็ม"""
    return ALIAS_TO_PROVINCE.get(name.strip().lower(), name.strip())

def normalize_place_name(name):
    """ปรับชื่อสถานที่ให้เป็นมาตรฐานสำหรับการเปรียบเทียบเพื่อลบข้อมูลซ้ำ"""
    if not name:
        return "ไม่ระบุ"
    
    # แปลงเป็นตัวพิมพ์เล็กและลบช่องว่างส่วนเกิน
    normalized = name.strip().lower()
    
    # ลบคำนำหน้าที่ไม่จำเป็น
    prefixes_to_remove = ['วัด', 'wat ', 'temple ', 'the ']
    suffixes_to_remove = [' temple', ' center', ' shopping center']
    
    # ลบคำนำหน้า
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    
    # ลบคำส่วนท้าย
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    
    # แปลงชื่อภาษาอังกฤษของสถานที่มีชื่อเป็นภาษาไทยบางที่
    name_mappings = {
        'grand palace': 'พระบรมมหาราชวัง',
        'phra si rattana satsadaram': 'พระศรีรัตนศาสดาราม',
        'wat phra si rattana satsadaram': 'พระศรีรัตนศาสดาราม',
        'emerald buddha temple': 'พระศรีรัตนศาสดาราม',
    }
    
    # ใช้การแปลงชื่อถ้ามี
    if normalized in name_mappings:
        normalized = name_mappings[normalized]
    
    # ลบคำที่ซ้ำ เช่น กรุงเทพ กรุงเทพมหานคร
    if 'กรุงเทพ' in normalized:
        normalized = normalized.replace(' กรุงเทพมหานคร', '').replace(' กรุงเทพ', '')
    
    return normalized

def remove_duplicates(places):
    """ลบสถานที่ที่มีชื่อซ้ำกันโดยใช้ชื่อที่ปรับเป็นมาตรฐานแล้ว"""
    if not places:
        return places
    
    seen_names = set()
    unique_places = []
    
    for place in places:
        place_name = place.get('name', 'ไม่ระบุ')
        normalized_name = normalize_place_name(place_name)
        
        if normalized_name and normalized_name not in seen_names and normalized_name != "ไม่ระบุ":
            seen_names.add(normalized_name)
            unique_places.append(place)
        elif normalized_name == "ไม่ระบุ":  # Keep places with unknown names but don't filter by them
            unique_places.append(place)
    
    return unique_places

def calculate_distance(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่างพิกัดสองจุด (Haversine formula) ในหน่วยกิโลเมตร"""
    R = 6371  # Radius of Earth in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def get_nearest_air_quality_data():
    """ดึงข้อมูลคุณภาพอากาศจากตำแหน่งที่ใกล้ที่สุด (ไม่ต้องระบุพิกัด) โดยใช้ AirVisual API"""
    global API_CALL_COUNT
    
    if API_CALL_COUNT >= MAX_API_CALLS:
        print(f"  ถึงขีดจำกัดการใช้ API แล้ว ({MAX_API_CALLS} calls/year)")
        return None
    
    url = f"http://api.airvisual.com/v2/nearest_city?key={AIRVISUAL_API_KEY}"
    
    try:
        response = requests.get(url, timeout=15)
        API_CALL_COUNT += 1 # Increment API call count
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city_data = data['data']
                return {
                    'city': city_data.get('city', 'ไม่ระบุ'),
                    'state': city_data.get('state', 'ไม่ระบุ'),
                    'country': city_data.get('country', 'ไม่ระบุ'),
                    'coordinates': city_data.get('location', {}).get('coordinates', [0, 0]),
                    'pollution': city_data.get('current', {}).get('pollution', {}),
                    'weather': city_data.get('current', {}).get('weather', {})
                }
            else:
                print(f" AirVisual API Error: {data.get('data', {}).get('message', 'Unknown error')}")
                return None
        elif response.status_code == 429:
            print(f"  API Rate limit - รอสักครู่ (API calls: {API_CALL_COUNT}/{MAX_API_CALLS})")
            time.sleep(2) # Wait a bit if rate limited
            return None
        else:
            print(f" HTTP {response.status_code} - AirVisual API calls: {API_CALL_COUNT}/{MAX_API_CALLS}")
            return None
    except requests.exceptions.RequestException as e:
        print(f" ไม่สามารถดึงข้อมูลคุณภาพอากาศได้ (Request Error): {e}")
        return None
    except Exception as e:
        print(f" เกิดข้อผิดพลาดที่ไม่คาดคิดในการดึงข้อมูลคุณภาพอากาศ: {e}")
        return None

def get_air_quality_stations(province_name):
    """ดึงข้อมูลสถานีวัดคุณภาพอากาศจาก AirVisual API (ใช้ nearest city เป็นหลัก)"""
    print(f"\nกำลังค้นหาสถานีวัดคุณภาพอากาศใน {province_name}...")
    print(f" API calls used: {API_CALL_COUNT}/{MAX_API_CALLS}")
    
    # Use nearest city API to get air quality data
    air_quality_data = get_nearest_air_quality_data()
    if air_quality_data:
        return [air_quality_data] # Return as a list for consistency
    return []

def get_air_quality_by_coordinates(lat, lon):
    """ดึงข้อมูลคุณภาพอากาศจากพิกัดที่กำหนด โดยใช้ cache และ fallback ไปยัง nearest city API"""
    global API_CALL_COUNT, AIR_QUALITY_CACHE
    
    # Create cache key (round coordinates to group nearby areas)
    cache_key = (round(lat, 1), round(lon, 1))
    
    # Check cache first
    if cache_key in AIR_QUALITY_CACHE:
        return AIR_QUALITY_CACHE[cache_key]
    
    if API_CALL_COUNT >= MAX_API_CALLS:
        print(f"  ถึงขีดจำกัดการใช้ API แล้ว ({MAX_API_CALLS} calls/year). ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน.")
        # Use data from the nearest city if API limit is reached
        nearest_data = get_nearest_air_quality_data()
        AIR_QUALITY_CACHE[cache_key] = nearest_data # Cache this fallback data
        return nearest_data
    
    url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={AIRVISUAL_API_KEY}"
    
    try:
        response = requests.get(url, timeout=15)
        API_CALL_COUNT += 1 # Increment API call count
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city_data = data['data']
                air_quality_data = {
                    'city': city_data.get('city', 'ไม่ระบุ'),
                    'state': city_data.get('state', 'ไม่ระบุ'),
                    'country': city_data.get('country', 'ไม่ระบุ'),
                    'coordinates': city_data.get('location', {}).get('coordinates', [lon, lat]),
                    'pollution': city_data.get('current', {}).get('pollution', {}),
                    'weather': city_data.get('current', {}).get('weather', {})
                }
                AIR_QUALITY_CACHE[cache_key] = air_quality_data # Cache the fetched data
                return air_quality_data
            else:
                print(f" AirVisual API Error for coordinates ({lat},{lon}): {data.get('data', {}).get('message', 'Unknown error')}. ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน.")
                nearest_data = get_nearest_air_quality_data()
                AIR_QUALITY_CACHE[cache_key] = nearest_data
                return nearest_data
        elif response.status_code == 429:
            print(f"  API Rate limit - ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน")
            nearest_data = get_nearest_air_quality_data()
            AIR_QUALITY_CACHE[cache_key] = nearest_data
            return nearest_data
        else:
            print(f" HTTP {response.status_code} - ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน")
            nearest_data = get_nearest_air_quality_data()
            AIR_QUALITY_CACHE[cache_key] = nearest_data
            return nearest_data
    except requests.exceptions.RequestException as e:
        print(f" ไม่สามารถดึงข้อมูลคุณภาพอากาศได้ (Request Error) สำหรับ ({lat},{lon}): {e}. ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน.")
        nearest_data = get_nearest_air_quality_data()
        AIR_QUALITY_CACHE[cache_key] = nearest_data
        return nearest_data
    except Exception as e:
        print(f" เกิดข้อผิดพลาดที่ไม่คาดคิดในการดึงข้อมูลคุณภาพอากาศสำหรับ ({lat},{lon}): {e}. ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน.")
        nearest_data = get_nearest_air_quality_data()
        AIR_QUALITY_CACHE[cache_key] = nearest_data
        return nearest_data

def get_aqi_level_description(aqi):
    """แปลงค่า AQI เป็นคำอธิบายภาษาไทยและระดับสี"""
    if aqi <= 50:
        return "ดีมาก GREEN", "อากาศสะอาด ปลอดภัยสำหรับกิจกรรมกลางแจ้ง"
    elif aqi <= 100:
        return "ปานกลาง YELLOW", "อากาศพอใช้ได้ คนไวต่อมลพิษควรระวัง"
    elif aqi <= 150:
        return "ไม่ดีสำหรับกลุ่มเสี่ยง ORANGE", "คนไวต่อมลพิษควรหลีกเลี่ยงกิจกรรมกลางแจ้ง"
    elif aqi <= 200:
        return "ไม่ดี RED", "ทุกคนควรจำกัดกิจกรรมกลางแจ้ง"
    elif aqi <= 300:
        return "แย่มาก 🟣", "ทุกคนควรหลีกเลี่ยงกิจกรรมกลางแจ้ง"
    else:
        return "อันตราย BLACK", "ทุกคนควรอยู่ในอาคาร"

def display_air_quality_info(air_quality_data):
    """แสดงข้อมูลคุณภาพอากาศในคอนโซล"""
    if not air_quality_data:
        print("    ไม่พบข้อมูลคุณภาพอากาศ")
        return
    
    pollution = air_quality_data.get('pollution', {})
    weather = air_quality_data.get('weather', {})
    
    print(f"     คุณภาพอากาศ: {air_quality_data.get('city', 'ไม่ระบุ')}")
    
    if pollution:
        aqi = pollution.get('aqius', 0)
        main_pollutant = pollution.get('mainus', 'ไม่ระบุ')
        level, description = get_aqi_level_description(aqi)
        
        print(f"    AQI (US): {aqi} - {level}")
        print(f"   💨 สาเหตุหลัก: {main_pollutant}")
        print(f"   ℹ️  {description}")
    
    if weather:
        temp = weather.get('tp', 'ไม่ระบุ')
        humidity = weather.get('hu', 'ไม่ระบุ')
        pressure = weather.get('pr', 'ไม่ระบุ')
        
        print(f"   🌡️  อุณหภูมิ: {temp}°C | ความชื้น: {humidity}% | ความกดอากาศ: {pressure} hPa")

def get_nominatim_places(province_name, place_type="tourism", limit=5):
    """ดึงข้อมูลสถานที่จาก Nominatim (OpenStreetMap)"""
    query = f"{place_type} in {province_name}, Thailand"
    params = {
        'q': query,
        'format': 'json',
        'limit': limit * 2,  # Fetch more than target to allow for deduplication
        'addressdetails': 1,
        'extratags': 1
    }
    headers = {
        'User-Agent': 'Thailand Tourism App (educational purpose)' # Important for Nominatim
    }
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()
        places = []
        for item in data:
            place_info = {
                'name': item.get('display_name', 'ไม่ระบุ').split(',')[0] or 'ไม่ระบุ', # Take first part for name
                'full_address': item.get('display_name', 'ไม่ระบุ'),
                'lat': float(item.get('lat', 0)),
                'lon': float(item.get('lon', 0)),
                'type': item.get('type', 'ไม่ระบุ'),
                'importance': item.get('importance', 0)
            }
            places.append(place_info)
        
        # Deduplicate and limit the number of results
        unique_places = remove_duplicates(places)
        return unique_places[:limit]
    except requests.exceptions.RequestException as e:
        print(f" เกิดข้อผิดพลาดในการเชื่อมต่อ Nominatim API: {e}")
        return []
    except Exception as e:
        print(f" เกิดข้อผิดพลาดในการประมวลผลข้อมูล Nominatim: {e}")
        return []

def enrich_places_with_air_quality(places):
    """เพิ่มข้อมูลคุณภาพอากาศให้กับสถานที่แต่ละแห่ง"""
    enriched_places = []
    for place in places:
        if place.get('lat') and place.get('lon'):
            air_quality = get_air_quality_by_coordinates(place['lat'], place['lon'])
            if air_quality and air_quality.get('pollution'):
                pollution_data = air_quality['pollution']
                aqi = pollution_data.get('aqius', 0)
                pm25 = pollution_data.get('p2', None) # PM2.5
                pm10 = pollution_data.get('p1', None) # PM10
                
                # If PM2.5 and PM10 are not available, estimate from AQI
                if pm25 is None or pm25 == 0:
                    pm25 = estimate_pm25_from_aqi(aqi)
                if pm10 is None or pm10 == 0:
                    pm10 = estimate_pm10_from_aqi(aqi)
                
                # Debug print to check what we're getting
                print(f"Air quality data for {place.get('name', 'Unknown')}: AQI={aqi}, PM2.5={pm25}, PM10={pm10}")
                
                level, description = get_aqi_level_description(aqi)
                
                # Ensure PM values are properly extracted and handled - convert to int if valid
                place['air_quality'] = {
                    'aqi': int(aqi) if aqi is not None and aqi >= 0 else None,
                    'pm25': int(pm25) if pm25 is not None and pm25 >= 0 else None,
                    'pm10': int(pm10) if pm10 is not None and pm10 >= 0 else None,
                    'level': level,
                    'description': description,
                    'city': air_quality.get('city', 'ไม่ระบุ')
                }
            else:
                print(f"No air quality data available for {place.get('name', 'Unknown')}")
                place['air_quality'] = {
                    'aqi': None,
                    'pm25': None,
                    'pm10': None,
                    'level': 'ไม่ระบุ',
                    'description': 'ไม่ระบุ',
                    'city': 'ไม่ระบุ'
                } # Default values when no air quality data is found
        else:
            print(f"No coordinates available for {place.get('name', 'Unknown')}")
            place['air_quality'] = {
                'aqi': None,
                'pm25': None,
                'pm10': None,
                'level': 'ไม่ระบุ',
                'description': 'ไม่ระบุ',
                'city': 'ไม่ระบุ'
            }
        enriched_places.append(place)
    return enriched_places


def group_places_by_air_quality(places):
    """จัดกลุ่มสถานที่ตามสถานีวัดคุณภาพอากาศที่ใกล้ที่สุดและดึงข้อมูล AQI"""
    global API_CALL_COUNT
    
    if not places:
        return []
    
    grouped_places = defaultdict(list)
    
    print(f"🔄 กำลังดึงข้อมูลคุณภาพอากาศสำหรับสถานที่... (API calls: {API_CALL_COUNT}/{MAX_API_CALLS})")
    
    for place in places:
        if place.get('lat') and place.get('lon'):
            lat, lon = place['lat'], place['lon']
            
            # Fetch air quality data (with cache and fallback)
            air_quality_data = get_air_quality_by_coordinates(lat, lon)
            place['air_quality'] = air_quality_data
            
            # Group by air quality station's city/state for display purposes
            if air_quality_data:
                station_key = (air_quality_data.get('city', 'Unknown'), 
                              air_quality_data.get('state', 'Unknown'))
                grouped_places[station_key].append(place)
            else:
                grouped_places[('ไม่ทราบ', 'ไม่ทราบ')].append(place) # Group places without AQI
            
            # Add a small delay to avoid hitting API rate limits too quickly
            time.sleep(0.5)
    
    return grouped_places

def display_places_with_air_quality(places, title):
    """แสดงข้อมูลสถานที่พร้อมข้อมูลคุณภาพอากาศในคอนโซล"""
    if not places:
        print(f"\n ไม่พบข้อมูล {title}")
        return
    
    print(f"\n {title}")
    print("-" * 50)
    
    # Group places by air quality for better presentation
    grouped_places = group_places_by_air_quality(places)
    
    for station_info, place_list in grouped_places.items():
        station_city, station_state = station_info
        print(f"\n🏢 บริเวณสถานีวัด: {station_city}, {station_state}")
        print("-" * 30)
        
        # Display air quality info once per group
        if place_list and place_list[0].get('air_quality'):
            display_air_quality_info(place_list[0]['air_quality'])
            print()
        
        # Display list of places in the group
        for i, place in enumerate(place_list, 1):
            print(f"   {i}. {place.get('name', 'ไม่ระบุ')}")
            if place.get('type'):
                print(f"        ประเภท: {place.get('type', 'ไม่ระบุ')}")
            else:
                print(f"        ประเภท: ไม่ระบุ")
            if place.get('full_address'):
                print(f"      🏠 ที่อยู่: {place.get('full_address', 'ไม่ระบุ')[:100]}...")
            else:
                print(f"      🏠 ที่อยู่: ไม่ระบุ")
            if place.get('lat') and place.get('lon'):
                lat, lon = place['lat'], place['lon']
                print(f"        พิกัด: {lat:.4f}, {lon:.4f}")
                print(f"      🌐 แผนที่: https://maps.google.com/?q={lat},{lon}")
            else:
                print(f"        พิกัด: ไม่ระบุ")
            print()

def display_places(places, title):
    """แสดงข้อมูลสถานที่โดยไม่มีข้อมูลคุณภาพอากาศในคอนโซล"""
    if not places:
        print(f"\n ไม่พบข้อมูล {title}")
        return
    
    print(f"\n {title}")
    print("-" * 50)
    
    for i, place in enumerate(places, 1):
        print(f"{i}. {place.get('name', 'ไม่ระบุ')}")
        if place.get('type'):
            print(f"     ประเภท: {place.get('type', 'ไม่ระบุ')}")
        else:
            print(f"     ประเภท: ไม่ระบุ")
        if place.get('full_address'):
            print(f"   🏠 ที่อยู่: {place.get('full_address', 'ไม่ระบุ')[:100]}...")
        else:
            print(f"   🏠 ที่อยู่: ไม่ระบุ")
        if place.get('lat') and place.get('lon'):
            lat, lon = place['lat'], place['lon']
            print(f"     พิกัด: {lat:.4f}, {lon:.4f}")
            print(f"   🌐 แผนที่: https://maps.google.com/?q={lat},{lon}")
        else:
            print(f"     พิกัด: ไม่ระบุ")
        print()

def show_api_menu():
    """แสดงเมนูตัวเลือกสำหรับผู้ใช้ในคอนโซล"""
    print("\n" + "="*60)
    print(" แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย + คุณภาพอากาศ")
    print("="*60)
    print(f" API Usage: {API_CALL_COUNT}/{MAX_API_CALLS} calls used")
    print(f"🗂️  Cache: {len(AIR_QUALITY_CACHE)} พื้นที่ในหน่วยความจำ")
    print("-"*60)
    print("1.  สถานที่ท่องเที่ยว (พร้อมข้อมูลอากาศ)")
    print("2.  โรงแรม (พร้อมข้อมูลอากาศ)") 
    print("3.   ร้านอาหาร (พร้อมข้อมูลอากาศ)")
    print("4. 🎯 ค้นหาสถานที่ทั้งหมด (พร้อมข้อมูลอากาศ)")
    print("5. ดูเฉพาะข้อมูลคุณภาพอากาศ")
    print("6. 📋 ค้นหาสถานที่ (ไม่มีข้อมูลอากาศ - ประหยัด API)")
    print("7. 🧹 ล้างข้อมูลใน Cache")
    print("0.  ออกจากโปรแกรม")
    print("-"*60)

def get_combined_tourism(province_name, limit=5):
    """รวมสถานที่ท่องเที่ยวจากหลายหมวดหมู่ รวมถึงวัด/ศาสนสถาน"""
    tourism_types = [
        ("tourism", "สถานที่ท่องเที่ยว"),
        ("attraction", "สถานที่น่าสนใจ"),
        ("viewpoint", "จุดชมวิว"),
        ("museum", "พิพิธภัณฑ์"),
        ("zoo", "สวนสัตว์"),
        ("place of worship", "วัด/ศาสนสถาน") # Added this type
    ]
    
    print(f"\nกำลังค้นหาสถานที่ท่องเที่ยวใน {province_name}")
    print("=" * 50)
    
    all_results = []
    total_found = 0
    
    for place_type, thai_name in tourism_types:
        places = get_nominatim_places(province_name, place_type, limit=limit) # Use passed limit
        found_count = len(places)
        total_found += found_count
        
        # Display search results for each type
        if found_count > 0:
            print(f" {thai_name}: พบ {found_count} แห่ง")
        else:
            print(f" {thai_name}: ไม่พบข้อมูล")
            
        all_results.extend(places)
        
        # Stop once enough places are found (if limit is effective)
        if len(all_results) >= limit:
            break
    
    # Deduplicate and limit the final results
    unique_results = remove_duplicates(all_results)
    final_results = unique_results[:limit]
    
    print(f"\n สรุปผลการค้นหา:")
    print(f"   🔢 รวมทั้งหมด (ก่อนลบซ้ำ): {total_found} สถานที่")
    print(f"   🔄 หลังลบซ้ำ: {len(unique_results)} สถานที่")
    print(f"    แสดงผล: {len(final_results)} สถานที่")
    print("-" * 50)
    
    return final_results

# --- Cache Management Functions ---
def get_cache_file_path(province_name):
    """สร้างเส้นทางไฟล์ cache สำหรับจังหวัดและวันที่ปัจจุบัน"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    # Sanitize province_name for filename
    safe_province_name = "".join(c for c in province_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    filename = f"{safe_province_name}_{today}.json"
    return os.path.join(CACHE_DIR, filename)

def load_from_cache(province_name):
    """โหลดข้อมูลจาก cache ถ้ามีและยังไม่หมดอายุ (ตามวัน)"""
    file_path = get_cache_file_path(province_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f" โหลดข้อมูลจาก cache: {file_path}")
                return data
        except json.JSONDecodeError as e:
            print(f" Cache file เสียหายหรืออ่านไม่ได้ {file_path}: {e}")
            os.remove(file_path) # Remove corrupted file
            return None
        except Exception as e:
            print(f" เกิดข้อผิดพลาดในการโหลด cache จาก {file_path}: {e}")
            return None
    return None

def save_to_cache(province_name, data):
    """บันทึกข้อมูลลงใน cache file"""
    os.makedirs(CACHE_DIR, exist_ok=True) # Ensure cache directory exists
    file_path = get_cache_file_path(province_name)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4) # Use indent for readability
        print(f"💾 บันทึกข้อมูลลง cache: {file_path}")
    except Exception as e:
        print(f" เกิดข้อผิดพลาดในการบันทึก cache ลง {file_path}: {e}")

def rank_places_by_dust(places, dust_type='aqius'):
    """
    จัดเรียงสถานที่ตามค่าคุณภาพอากาศ (ฝุ่น) ที่ระบุ (น้อยไปมาก)
    Parameters:
    - places: รายการของสถานที่ แต่ละสถานที่ต้องมี 'air_quality' dict
    - dust_type: ชนิดของฝุ่นที่ต้องการเรียงลำดับ ('aqius', 'pm25', 'pm10')
    """
    if not places:
        return []

    # Map user-friendly dust_type to actual keys in air_quality dict
    if dust_type == 'pm25':
        actual_dust_key = 'pm25'
    elif dust_type == 'pm10':
        actual_dust_key = 'pm10'
    else:  # Default to AQI US
        actual_dust_key = 'aqi'

    places_with_dust_data = []
    places_without_dust_data = []

    for place in places:
        air_quality = place.get('air_quality')
        if air_quality and air_quality.get(actual_dust_key) is not None:
            places_with_dust_data.append(place)
        else:
            places_without_dust_data.append(place)

    # Sort places with dust data by the specified dust_type in ascending order (น้อยไปมาก)
    places_with_dust_data.sort(key=lambda x: x['air_quality'][actual_dust_key])

    # Combine sorted places with those without dust data (these will appear at the end)
    return places_with_dust_data + places_without_dust_data

def rank_places_by_category_and_dust(places, dust_type='aqi'):
    """
    จัดอันดับสถานที่แยกตามประเภท (attraction, hotel, restaurant) 
    และให้อันดับ 1, 2, 3 แยกในแต่ละประเภท
    Parameters:
    - places: รายการของสถานที่ แต่ละสถานที่ต้องมี 'air_quality' dict และ 'type'
    - dust_type: ชนิดของฝุ่นที่ต้องการเรียงลำดับ ('aqi', 'pm25', 'pm10')
    """
    if not places:
        return {}

    # Map dust_type to actual keys in air_quality dict
    if dust_type == 'pm25':
        actual_dust_key = 'pm25'
    elif dust_type == 'pm10':
        actual_dust_key = 'pm10'
    else:  # Default to AQI
        actual_dust_key = 'aqi'

    # จัดกลุ่มสถานที่ตามประเภท
    categorized_places = {
        'attraction': [],  # สถานที่ท่องเที่ยว/ศาสนสถาน
        'hotel': [],      # โรงแรม
        'restaurant': []  # ร้านอาหาร
    }

    # แยกสถานที่ตามประเภท
    for place in places:
        place_type = place.get('type', '').lower()
        place_copy = place.copy()  # สร้างสำเนาเพื่อไม่ให้กระทบต้นฉบับ
        
        if place_type in ['attraction', 'tourism', 'viewpoint', 'museum', 'zoo', 'place_of_worship']:
            categorized_places['attraction'].append(place_copy)
        elif place_type in ['hotel', 'accommodation', 'hostel', 'resort']:
            categorized_places['hotel'].append(place_copy)
        elif place_type in ['restaurant', 'cafe', 'food', 'bar']:
            categorized_places['restaurant'].append(place_copy)
        else:
            # หากไม่ระบุประเภทชัดเจน ให้ดูจากชื่อ
            place_name = place.get('name', '').lower()
            if any(word in place_name for word in ['โรงแรม', 'hotel', 'resort', 'hostel']):
                categorized_places['hotel'].append(place_copy)
            elif any(word in place_name for word in ['ร้าน', 'restaurant', 'cafe', 'food']):
                categorized_places['restaurant'].append(place_copy)
            else:
                categorized_places['attraction'].append(place_copy)

    # จัดอันดับในแต่ละประเภท
    ranked_categories = {}
    
    for category, places_list in categorized_places.items():
        if not places_list:
            ranked_categories[category] = []
            continue
            
        # แยกสถานที่ที่มีข้อมูลฝุ่นและไม่มี
        places_with_data = []
        places_without_data = []
        
        for place in places_list:
            air_quality = place.get('air_quality')
            if air_quality and air_quality.get(actual_dust_key) is not None:
                places_with_data.append(place)
            else:
                places_without_data.append(place)
        
        # จัดเรียงสถานที่ที่มีข้อมูลฝุ่นตามค่าฝุ่น (น้อยไปมาก = ดีที่สุด)
        places_with_data.sort(key=lambda x: x['air_quality'][actual_dust_key])
        
        # ให้อันดับแยกในแต่ละประเภท (ไม่ข้ามอันดับ)
        current_rank = 1
        previous_value = None
        
        for i, place in enumerate(places_with_data):
            current_value = place['air_quality'][actual_dust_key]
            
            # หากค่าต่างจากค่าก่อนหน้า ให้เพิ่มอันดับทีละ 1 (ไม่ข้าม)
            if previous_value is not None and current_value != previous_value:
                current_rank += 1  # เพิ่มทีละ 1 ไม่ข้ามอันดับ
            
            place['rank'] = current_rank
            place['category_rank'] = current_rank  # อันดับในประเภทนี้
            
            # ให้เหรียญรางวัลเฉพาะ 3 อันดับแรก
            if current_rank == 1:
                place['medal'] = '🥇'
                place['rank_text'] = '1'
            elif current_rank == 2:
                place['medal'] = '🥈'
                place['rank_text'] = '2'
            elif current_rank == 3:
                place['medal'] = '🥉'
                place['rank_text'] = '3'
            else:
                place['medal'] = ''
                place['rank_text'] = str(current_rank)
            
            previous_value = current_value
        
        # สถานที่ที่ไม่มีข้อมูลฝุ่นจะไม่มีอันดับ
        for place in places_without_data:
            place['rank'] = None
            place['category_rank'] = None
            place['medal'] = ''
            place['rank_text'] = '-'
        
        # รวมสถานที่ที่มีข้อมูลและไม่มีข้อมูล
        ranked_categories[category] = places_with_data + places_without_data

    return ranked_categories
# === Time Series Functions ===
def get_time_series_data(province_name, start_date, end_date, interval='daily'):
    """
    ดึงข้อมูล time series จริงโดยใช้ cache และ API
    หมายเหตุ: Function นี้ไม่ได้ใช้แล้ว เนื่องจากลบโหมดข้อมูลย้อนหลังออกแล้ว
    เก็บไว้เพื่อความเข้ากันได้ (backward compatibility)
    """
    import datetime
    from datetime import timedelta
    import json
    import os
    
    try:
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print(" รูปแบบวันที่ไม่ถูกต้อง ใช้รูปแบบ YYYY-MM-DD")
        return []
    
    if start > end:
        print(" วันที่เริ่มต้นต้องมาก่อนวันที่สิ้นสุด")
        return []
    
    print(f" กำลังดึงข้อมูล time series จาก {start_date} ถึง {end_date}")
    
    # ดึงข้อมูลสถานที่ในจังหวัด
    places = get_combined_tourism(province_name, limit=3)
    
    if not places:
        print(f" ไม่พบสถานที่ในจังหวัด {province_name}")
        return []
    
    time_series_data = []
    current_date = start.date()
    end_date_obj = end.date()
    
    # สร้างโฟลเดอร์ cache ถ้ายังไม่มี
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"กำลังประมวลผลข้อมูลจาก {len(places)} สถานที่")
    
    while current_date <= end_date_obj:
        date_str = current_date.strftime('%Y-%m-%d')
        
        for place in places:
            if not place.get('lat') or not place.get('lon'):
                continue
                
            place_name = place.get('name', 'ไม่ระบุ')
            
            # ลองหาข้อมูลใน cache ก่อน
            cached_data = get_cached_historical_data(place_name, date_str, cache_dir)
            
            if cached_data:
                # ใช้ข้อมูลจาก cache
                time_series_data.append({
                    'date': date_str,
                    'place_name': place_name,
                    'lat': place['lat'],
                    'lon': place['lon'],
                    'aqi': cached_data.get('aqi', 0),
                    'pm25': cached_data.get('pm25', 0),
                    'pm10': cached_data.get('pm10', 0),
                    'city': cached_data.get('city', 'ไม่ระบุ'),
                    'is_historical': True,
                    'source': 'cache'
                })
                print(f"  📁 {date_str}: {place_name} - ใช้ข้อมูลจาก cache")
            else:
                # หากไม่มีใน cache และเป็นวันในอดีต ให้สร้างข้อมูลจำลองที่สมจริง
                if current_date < datetime.date.today():
                    simulated_data = create_realistic_historical_data(
                        place, current_date, province_name
                    )
                    
                    time_series_data.append(simulated_data)
                    
                    # บันทึกลง cache
                    save_to_time_series_cache(place_name, date_str, simulated_data, cache_dir)
                    print(f"  🔄 {date_str}: {place_name} - สร้างข้อมูลจำลอง")
                elif current_date == datetime.date.today():
                    # วันปัจจุบัน - ดึงข้อมูลจริงจาก API
                    try:
                        current_air = get_air_quality_by_coordinates(place['lat'], place['lon'])
                        if current_air and current_air.get('pollution'):
                            real_data = {
                                'date': date_str,
                                'place_name': place_name,
                                'lat': place['lat'],
                                'lon': place['lon'],
                                'aqi': current_air['pollution'].get('aqius', 0),
                                'pm25': current_air['pollution'].get('p2', 0),
                                'pm10': current_air['pollution'].get('p1', 0),
                                'city': current_air.get('city', 'ไม่ระบุ'),
                                'is_historical': False,
                                'source': 'api_realtime'
                            }
                            time_series_data.append(real_data)
                            print(f"  🌐 {date_str}: {place_name} - ข้อมูลจริงจาก API")
                    except Exception as e:
                        print(f"   ไม่สามารถดึงข้อมูลปัจจุบันสำหรับ {place_name}: {e}")
        
        # เพิ่มช่วงเวลาตาม interval
        if interval == 'daily':
            current_date += timedelta(days=1)
        elif interval == 'weekly':
            current_date += timedelta(weeks=1)
        elif interval == 'monthly':
            # หาวันที่เดียวกันของเดือนถัดไป
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    print(f" ดึงข้อมูล time series เสร็จสิ้น: {len(time_series_data)} รายการ")
    return time_series_data

def get_cached_historical_data(place_name, date_str, cache_dir):
    """
    ดึงข้อมูลจาก cache ถ้ามี
    """
    try:
        # ทำความสะอาดชื่อไฟล์เพื่อป้องกันปัญหา
        safe_place_name = "".join(c for c in place_name if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        cache_file = os.path.join(cache_dir, f"{safe_place_name}_{date_str}.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f" ข้อผิดพลาดในการอ่าน cache: {e}")
    return None

def save_to_time_series_cache(place_name, date_str, data, cache_dir):
    """
    บันทึกข้อมูลลง time series cache
    """
    try:
        # ทำความสะอาดชื่อไฟล์เพื่อป้องกันปัญหา
        safe_place_name = "".join(c for c in place_name if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        cache_file = os.path.join(cache_dir, f"{safe_place_name}_{date_str}.json")
        
        cache_data = {
            'aqi': data.get('aqi', 0),
            'pm25': data.get('pm25', 0),
            'pm10': data.get('pm10', 0),
            'city': data.get('city', 'ไม่ระบุ'),
            'cached_at': datetime.datetime.now().isoformat()
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f" ข้อผิดพลาดในการบันทึก cache: {e}")

def create_realistic_historical_data(place, date, province_name):
    """
    สร้างข้อมูลประวัติศาสตร์ที่สมจริงโดยใช้ pattern ตามฤดูกาลและลักษณะพื้นที่
    """
    import random
    import math
    import datetime
    
    place_name = place.get('name', 'ไม่ระบุ')
    
    # กำหนดค่าพื้นฐานตามลักษณะของพื้นที่
    base_aqi = 45
    base_pm25 = 22
    base_pm10 = 35
    
    # ปรับค่าตามประเภทพื้นที่
    area_type = classify_area_type(place_name, province_name)
    
    if area_type == 'urban':  # เมืองใหญ่
        base_aqi += 20
        base_pm25 += 12
        base_pm10 += 15
    elif area_type == 'industrial':  # พื้นที่อุตสาหกรรม
        base_aqi += 35
        base_pm25 += 18
        base_pm10 += 25
    elif area_type == 'rural':  # ชนบท
        base_aqi -= 10
        base_pm25 -= 8
        base_pm10 -= 10
    elif area_type == 'coastal':  # ชายทะเล
        base_aqi -= 5
        base_pm25 -= 5
        base_pm10 -= 8
    
    # ปัจจัยตามฤดูกาล
    month = date.month
    seasonal_multiplier = 1.0
    
    if month in [12, 1, 2]:  # ฤดูหนาว
        seasonal_multiplier = 1.15
    elif month in [3, 4]:  # ฤดูร้อนต้น - หมอกควัน
        seasonal_multiplier = 1.45
    elif month in [5]:  # ฤดูร้อนปลาย
        seasonal_multiplier = 1.25
    elif month in [6, 7, 8, 9, 10]:  # ฤดูฝน
        seasonal_multiplier = 0.65
    elif month in [11]:  # หลังฤดูฝน
        seasonal_multiplier = 0.8
    
    # ปัจจัยตามวันในสัปดาห์
    weekday_factor = 1.1 if date.weekday() < 5 else 0.9  # วันธรรมดา vs วันหยุด
    
    # การเปลี่ยนแปลงแบบ sine wave เพื่อจำลองรูปแบบตามธรรมชาติ
    day_of_year = date.timetuple().tm_yday
    natural_variation = 1.0 + (0.1 * math.sin(2 * math.pi * day_of_year / 365))
    
    # ปัจจัยสุ่มรายวัน
    daily_random = random.uniform(0.8, 1.2)
    
    # คำนวณค่าสุดท้าย
    total_factor = seasonal_multiplier * weekday_factor * natural_variation * daily_random
    
    final_aqi = int(base_aqi * total_factor)
    final_pm25 = int(base_pm25 * total_factor)
    final_pm10 = int(base_pm10 * total_factor)
    
    # จำกัดค่าให้อยู่ในช่วงที่สมเหตุสมผล
    final_aqi = max(15, min(200, final_aqi))
    final_pm25 = max(8, min(120, final_pm25))
    final_pm10 = max(15, min(150, final_pm10))
    
    return {
        'date': date.strftime('%Y-%m-%d'),
        'place_name': place_name,
        'lat': place['lat'],
        'lon': place['lon'],
        'aqi': final_aqi,
        'pm25': final_pm25,
        'pm10': final_pm10,
        'city': place.get('province', 'ไม่ระบุ'),
        'is_historical': True,
        'source': 'generated_realistic'
    }

def classify_area_type(place_name, province_name):
    """
    จำแนกประเภทพื้นที่เพื่อกำหนดระดับมลพิษ
    """
    urban_keywords = ['เซ็นทรัล', 'ห้าง', 'สถานี', 'ตลาด', 'โรงพยาบาล', 'มหาวิทยาลัย']
    industrial_keywords = ['โรงงาน', 'นิคม', 'ท่าเรือ', 'สนามบิน']
    coastal_keywords = ['หาด', 'ทะเล', 'เกาะ', 'อ่าว']
    rural_keywords = ['วัด', 'ป่า', 'ภูเขา', 'น้ำตก', 'อุทยาน']
    
    place_lower = place_name.lower()
    
    if any(keyword in place_lower for keyword in industrial_keywords):
        return 'industrial'
    elif any(keyword in place_lower for keyword in urban_keywords):
        return 'urban'
    elif any(keyword in place_lower for keyword in coastal_keywords):
        return 'coastal'
    elif any(keyword in place_lower for keyword in rural_keywords):
        return 'rural'
    
    # ตัดสินใจตามจังหวัด
    if province_name.lower() in ['กรุงเทพมหานคร', 'สมุทรปราการ', 'นนทบุรี', 'ปทุมธานี']:
        return 'urban'
    elif province_name.lower() in ['ระยอง', 'ชลบุรี', 'สระบุรี']:
        return 'industrial'
    elif province_name.lower() in ['ภูเก็ต', 'กระบี่', 'สุราษฎร์ธานี', 'สงขลา']:
        return 'coastal'
    else:
        return 'rural'

def analyze_time_series_ranking(time_series_data, sort_by='aqi'):
    """
    วิเคราะห์และจัดอันดับข้อมูล time series
    """
    if not time_series_data:
        return {}
    
    # จัดกลุ่มข้อมูลตามสถานที่
    place_stats = {}
    
    for data in time_series_data:
        place_name = data['place_name']
        if place_name not in place_stats:
            place_stats[place_name] = {
                'name': place_name,
                'values': [],
                'dates': [],
                'lat': data['lat'],
                'lon': data['lon'],
                'city': data['city']
            }
        
        place_stats[place_name]['values'].append(data[sort_by])
        place_stats[place_name]['dates'].append(data['date'])
    
    # คำนวณสถิติสำหรับแต่ละสถานที่
    ranking_data = []
    for place_name, stats in place_stats.items():
        values = stats['values']
        
        if values:
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)
            
            ranking_data.append({
                'name': place_name,
                'lat': stats['lat'],
                'lon': stats['lon'],
                'city': stats['city'],
                'average': round(avg_value, 2),
                'minimum': min_value,
                'maximum': max_value,
                'data_points': len(values),
                'values': values,
                'dates': stats['dates']
            })
    
    # จัดเรียงตามค่าเฉลี่ย (น้อยไปมาก = ดีที่สุด)
    ranking_data.sort(key=lambda x: x['average'])
    
    # เพิ่มอันดับ
    for i, place in enumerate(ranking_data, 1):
        place['rank'] = i
        
        # เพิ่มเหรียญรางวัล
        if i == 1:
            place['medal'] = '1'
        elif i == 2:
            place['medal'] = '2'
        elif i == 3:
            place['medal'] = '3'
        else:
            place['medal'] = ''
    
    return {
        'rankings': ranking_data,
        'total_places': len(ranking_data),
        'sort_by': sort_by,
        'best_place': ranking_data[0] if ranking_data else None,
        'worst_place': ranking_data[-1] if ranking_data else None
    }

def display_time_series_ranking(analysis_result):
    """
    แสดงผลการจัดอันดับ time series
    """
    if not analysis_result or not analysis_result.get('rankings'):
        print(" ไม่มีข้อมูลสำหรับการจัดอันดับ")
        return
    
    rankings = analysis_result['rankings']
    sort_by = analysis_result['sort_by'].upper()
    
    print(f"\n การจัดอันดับคุณภาพอากาศ (ตาม {sort_by})")
    print("=" * 60)
    
    for place in rankings:
        print(f"{place['medal']} {place['rank']}. {place['name']}")
        print(f"    ค่าเฉลี่ย {sort_by}: {place['average']}")
        print(f"    ช่วงค่า: {place['minimum']} - {place['maximum']}")
        print(f"   📅 จำนวนข้อมูล: {place['data_points']} จุด")
        print(f"    ตำแหน่ง: {place['city']}")
        print()
    
    if analysis_result.get('best_place'):
        best = analysis_result['best_place']
        print(f" สถานที่ที่มีอากาศดีที่สุด: {best['name']} (เฉลี่ย {sort_by}: {best['average']})")
    
    if analysis_result.get('worst_place'):
        worst = analysis_result['worst_place']
        print(f"  สถานที่ที่มีอากาศแย่ที่สุด: {worst['name']} (เฉลี่ย {sort_by}: {worst['average']})")

def get_forecast_data(province_name, forecast_days=5, interval='daily'):
    """
    ดึงข้อมูลพยากรณ์คุณภาพอากาศจริงจากไฟล์ forecast_results.json 
    เหมือนกับที่ใช้ในหน้า map
    """
    import datetime
    from datetime import timedelta
    import os
    import json
    
    print(f"🔮 กำลังดึงข้อมูลพยากรณ์จริงสำหรับ {province_name} ({forecast_days} วัน)")
    
    try:
        # อ่านข้อมูลจากไฟล์ forecast_results.json (เหมือนกับหน้า map)
        forecast_file_path = os.path.join(os.path.dirname(__file__), 'forecast_results.json')
        if not os.path.exists(forecast_file_path):
            print(f" ไม่พบไฟล์ forecast_results.json ที่ {forecast_file_path}")
            return generate_fallback_forecast_data(province_name, forecast_days)
        
        with open(forecast_file_path, 'r', encoding='utf-8') as f:
            forecast_data = json.load(f)
        
        # ลองหาข้อมูลหลายวิธี
        province_forecast = None
        search_names = []
        
        # 1. ใช้ชื่อตรงๆ ที่ส่งมา
        search_names.append(province_name)
        
        # 2. ตรวจสอบว่าเป็นอำเภอหรือไม่ ถ้าใช่ให้แปลงเป็นจังหวัด
        if province_name in DISTRICT_TO_PROVINCE:
            search_names.append(DISTRICT_TO_PROVINCE[province_name])
            print(f" 🔄 แปลงอำเภอ '{province_name}' เป็นจังหวัด '{DISTRICT_TO_PROVINCE[province_name]}'")
        
        # 3. ลองแปลงจากไทยเป็นอังกฤษ
        if province_name in THAI_TO_ENGLISH_PROVINCE:
            search_names.append(THAI_TO_ENGLISH_PROVINCE[province_name])
            print(f" 🔄 แปลงชื่อไทย '{province_name}' เป็นอังกฤษ '{THAI_TO_ENGLISH_PROVINCE[province_name]}'")
        
        # 4. ลองใช้ alias mapping
        if province_name in ALIAS_TO_PROVINCE:
            thai_name = ALIAS_TO_PROVINCE[province_name]
            search_names.append(thai_name)
            if thai_name in THAI_TO_ENGLISH_PROVINCE:
                search_names.append(THAI_TO_ENGLISH_PROVINCE[thai_name])
                print(f" 🔄 แปลงจากชื่อเล่น '{province_name}' → '{thai_name}' → '{THAI_TO_ENGLISH_PROVINCE[thai_name]}'")
        
        # ค้นหาในไฟล์ forecast
        for search_name in search_names:
            if search_name in forecast_data:
                province_forecast = forecast_data[search_name]
                print(f" ✅ พบข้อมูลพยากรณ์สำหรับ '{search_name}'")
                break
        
        if not province_forecast:
            print(f" ❌ ไม่พบข้อมูลพยากรณ์สำหรับ {province_name} (ลองค้นหา: {search_names})")
            print(f" 🔄 สร้างข้อมูลจำลองแทน...")
            return generate_fallback_forecast_data(province_name, forecast_days)
        
        # ตรวจสอบว่าข้อมูลมีสถานะ error หรือไม่
        if province_forecast.get('status') == 'error':
            print(f" ⚠️ ข้อมูลพยากรณ์สำหรับ {province_name} มีสถานะ error")
            print(f" 🔄 สร้างข้อมูลจำลองแทน...")
            return generate_fallback_forecast_data(province_name, forecast_days)
        
        # ดึงข้อมูล PM2.5 และ PM10
        pm25_data = province_forecast.get('pm25', [])
        pm10_data = province_forecast.get('pm10', [])
        
        if not pm25_data and not pm10_data:
            print(f" ❌ ไม่มีข้อมูล PM2.5 และ PM10 สำหรับ {province_name}")
            print(f" 🔄 สร้างข้อมูลจำลองแทน...")
            return generate_fallback_forecast_data(province_name, forecast_days)
        
        # แปลงข้อมูลให้เป็นรูปแบบที่ Time Series ใช้
        time_series_data = []
        
        # ใช้ข้อมูล PM2.5 เป็นหลัก หากไม่มีจึงใช้ PM10
        primary_data = pm25_data if pm25_data else pm10_data
        secondary_data = pm10_data if pm25_data else pm25_data
        
        # จำกัดจำนวนวันตาม forecast_days
        limited_data = primary_data[:forecast_days] if len(primary_data) >= forecast_days else primary_data
        
        for i, pm_entry in enumerate(limited_data):
            date_str = pm_entry.get('day', '')
            if not date_str:
                continue
            
            # หาข้อมูล PM10 ที่ตรงกับวันเดียวกัน
            pm10_entry = None
            if secondary_data and i < len(secondary_data):
                pm10_entry = secondary_data[i]
            
            # คำนวณ AQI จาก PM2.5 (ใช้มาตรฐาน US EPA)
            pm25_value = pm_entry.get('avg', 0)
            pm10_value = pm10_entry.get('avg', 0) if pm10_entry else 0
            aqi_value = calculate_aqi_from_pm25(pm25_value)
            
            time_series_data.append({
                'date': date_str,
                'place_name': f"จังหวัด{province_name}",  # ใช้ชื่อจังหวัดแทนสถานที่ท่องเที่ยว
                'lat': 0,  # ไม่มีพิกัดเฉพาะเจาะจง
                'lon': 0,
                'aqi': aqi_value,
                'pm25': pm25_value,
                'pm10': pm10_value,
                'city': province_name,
                'is_forecast': True,
                'confidence': calculate_forecast_confidence(i),
                'source': 'forecast_api_real_data',
                'min_pm25': pm_entry.get('min', pm25_value),
                'max_pm25': pm_entry.get('max', pm25_value),
                'min_pm10': pm10_entry.get('min', pm10_value) if pm10_entry else pm10_value,
                'max_pm10': pm10_entry.get('max', pm10_value) if pm10_entry else pm10_value
            })
            
            print(f"  📅 {date_str}: PM2.5={pm25_value}, PM10={pm10_value}, AQI={aqi_value}")
        
        print(f" ✅ ดึงข้อมูลพยากรณ์จริงเสร็จสิ้น: {len(time_series_data)} รายการ")
        return time_series_data
        
    except json.JSONDecodeError as e:
        print(f" ❌ ข้อผิดพลาดในการอ่าน JSON: {e}")
        return generate_fallback_forecast_data(province_name, forecast_days)
    except Exception as e:
        print(f" ❌ ข้อผิดพลาดในการดึงข้อมูลพยากรณ์: {e}")
        return generate_fallback_forecast_data(province_name, forecast_days)
    
def generate_fallback_forecast_data(province_name, forecast_days=7):
    """
    สร้างข้อมูลพยากรณ์จำลองเมื่อไม่พบข้อมูลจริง
    """
    import datetime
    from datetime import timedelta
    import random
    
    print(f"� สร้างข้อมูลพยากรณ์จำลองสำหรับ {province_name}")
    
    time_series_data = []
    base_date = datetime.date.today()
    
    # กำหนดค่าพื้นฐานตามประเภทพื้นที่
    if province_name in ['กรุงเทพมหานคร', 'Bangkok']:
        base_pm25, base_pm10 = 35, 45
    elif province_name in ['เชียงใหม่', 'Chiang Mai']:
        base_pm25, base_pm10 = 40, 55  # หมอกควันภาคเหนือ
    elif 'ชายทะเล' in province_name or province_name in ['ภูเก็ต', 'กระบี่', 'Phuket', 'Krabi']:
        base_pm25, base_pm10 = 25, 35  # อากาศดีกว่า
    else:
        base_pm25, base_pm10 = 30, 40  # ค่าปกติ
    
    for i in range(forecast_days):
        forecast_date = base_date + timedelta(days=i)
        
        # เพิ่มความผันผวนแบบสมจริง
        daily_variation = random.uniform(0.8, 1.2)
        confidence_factor = random.uniform(0.9, 1.1)
        
        pm25_value = int(base_pm25 * daily_variation * confidence_factor)
        pm10_value = int(base_pm10 * daily_variation * confidence_factor)
        aqi_value = calculate_aqi_from_pm25(pm25_value)
        
        # จำกัดค่าให้อยู่ในช่วงที่สมเหตุสมผล
        pm25_value = max(10, min(100, pm25_value))
        pm10_value = max(15, min(120, pm10_value))
        aqi_value = max(15, min(150, aqi_value))
        
        time_series_data.append({
            'date': forecast_date.strftime('%Y-%m-%d'),
            'place_name': f"จังหวัด{province_name}",
            'lat': 0,
            'lon': 0,
            'aqi': aqi_value,
            'pm25': pm25_value,
            'pm10': pm10_value,
            'city': province_name,
            'is_forecast': True,
            'confidence': calculate_forecast_confidence(i),
            'source': 'generated_fallback',
            'min_pm25': int(pm25_value * 0.9),
            'max_pm25': int(pm25_value * 1.1),
            'min_pm10': int(pm10_value * 0.9),
            'max_pm10': int(pm10_value * 1.1)
        })
        
        print(f"  📅 {forecast_date.strftime('%Y-%m-%d')}: PM2.5={pm25_value}, PM10={pm10_value}, AQI={aqi_value} (จำลอง)")
    
    print(f" ✅ สร้างข้อมูลจำลองเสร็จสิ้น: {len(time_series_data)} รายการ")
    return time_series_data

def calculate_aqi_from_pm25(pm25):
    """
    คำนวณ AQI จากค่า PM2.5 ตามมาตรฐาน US EPA
    """
    if pm25 is None or pm25 < 0:
        return 0
    
    # US EPA AQI breakpoints for PM2.5
    if pm25 <= 12.0:
        # Good (0-50)
        return int((50 - 0) / (12.0 - 0.0) * pm25 + 0)
    elif pm25 <= 35.4:
        # Moderate (51-100)
        return int((100 - 51) / (35.4 - 12.1) * (pm25 - 12.1) + 51)
    elif pm25 <= 55.4:
        # Unhealthy for Sensitive Groups (101-150)
        return int((150 - 101) / (55.4 - 35.5) * (pm25 - 35.5) + 101)
    elif pm25 <= 150.4:
        # Unhealthy (151-200)
        return int((200 - 151) / (150.4 - 55.5) * (pm25 - 55.5) + 151)
    elif pm25 <= 250.4:
        # Very Unhealthy (201-300)
        return int((300 - 201) / (250.4 - 150.5) * (pm25 - 150.5) + 201)
    else:
        # Hazardous (301-500)
        return int((500 - 301) / (500.4 - 250.5) * (pm25 - 250.5) + 301)

def calculate_forecast_confidence(day_offset):
    """
    คำนวณความมั่นใจในการพยากรณ์ (ยิ่งไกลยิ่งไม่แน่นอน)
    """
    base_confidence = 0.95
    decline_rate = 0.05
    confidence = base_confidence - (day_offset * decline_rate)
    return max(0.6, confidence)  # ความมั่นใจขั้นต่ำ 60%

# === PM Estimation Functions ===
def estimate_pm25_from_aqi(aqi):
    """Estimate PM2.5 value from AQI (US standard)"""
    if aqi is None or aqi <= 0:
        return None
    
    # AQI to PM2.5 conversion based on US EPA breakpoints
    if aqi <= 50:
        # Good: 0-12 µg/m³
        return int(aqi * 12 / 50)
    elif aqi <= 100:
        # Moderate: 12.1-35.4 µg/m³
        return int(12 + (aqi - 50) * (35.4 - 12) / 50)
    elif aqi <= 150:
        # Unhealthy for Sensitive Groups: 35.5-55.4 µg/m³
        return int(35.4 + (aqi - 100) * (55.4 - 35.4) / 50)
    elif aqi <= 200:
        # Unhealthy: 55.5-150.4 µg/m³
        return int(55.4 + (aqi - 150) * (150.4 - 55.4) / 50)
    elif aqi <= 300:
        # Very Unhealthy: 150.5-250.4 µg/m³
        return int(150.4 + (aqi - 200) * (250.4 - 150.4) / 100)
    else:
        # Hazardous: 250.5+ µg/m³
        return int(250.4 + (aqi - 300) * 100 / 100)

def estimate_pm10_from_aqi(aqi):
    """Estimate PM10 value from AQI (US standard)"""
    if aqi is None or aqi <= 0:
        return None
    
    # AQI to PM10 conversion based on US EPA breakpoints
    if aqi <= 50:
        # Good: 0-54 µg/m³
        return int(aqi * 54 / 50)
    elif aqi <= 100:
        # Moderate: 55-154 µg/m³
        return int(55 + (aqi - 50) * (154 - 55) / 50)
    elif aqi <= 150:
        # Unhealthy for Sensitive Groups: 155-254 µg/m³
        return int(155 + (aqi - 100) * (254 - 155) / 50)
    elif aqi <= 200:
        # Unhealthy: 255-354 µg/m³
        return int(255 + (aqi - 150) * (354 - 255) / 50)
    elif aqi <= 300:
        # Very Unhealthy: 355-424 µg/m³
        return int(355 + (aqi - 200) * (424 - 355) / 100)
    else:
        # Hazardous: 425+ µg/m³
        return int(425 + (aqi - 300) * 75 / 100)

if __name__ == "__main__":
    print("This module is designed to be imported by Flask app, not run directly.")