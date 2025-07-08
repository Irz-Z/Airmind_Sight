import requests
import time
import math
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

# AirVisual API Key (Community tier: 10,000 calls/year, expires Jul 8, 2026)
AIRVISUAL_API_KEY = "eeb3ba1c-2778-4b29-a766-30a21e6fa7c8"
API_CALL_COUNT = 0  # ตัวนับการใช้ API
MAX_API_CALLS = 10000  # ขีดจำกัดต่อปี

# Global cache for air quality data
AIR_QUALITY_CACHE = {}

def normalize_province_name(name):
    return ALIAS_TO_PROVINCE.get(name.strip().lower(), name.strip())

def normalize_place_name(name):
    """ปรับชื่อสถานที่ให้เป็นมาตรฐานสำหรับการเปรียบเทียบ"""
    if not name:
        return ""
    # ลบช่องว่างส่วนเกิน แปลงเป็นตัวพิมพ์เล็ก และตัดคำที่ไม่จำเป็น
    normalized = name.strip().lower()
    # ลบคำที่ซ้ำกันหรือไม่จำเป็น
    words_to_remove = ['the', 'a', 'an', 'hotel', 'resort', 'restaurant', 'temple', 'wat']
    words = normalized.split()
    filtered_words = [word for word in words if word not in words_to_remove]
    return ' '.join(filtered_words)

def remove_duplicates(places):
    """ลบสถานที่ที่มีชื่อซ้ำกัน"""
    if not places:
        return places
    
    seen_names = set()
    unique_places = []
    
    for place in places:
        place_name = place.get('name', '')
        normalized_name = normalize_place_name(place_name)
        
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            unique_places.append(place)
        elif not normalized_name:  # เก็บสถานที่ที่ไม่มีชื่อไว้
            unique_places.append(place)
    
    return unique_places

def calculate_distance(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่างพิกัดสองจุด (Haversine formula)"""
    R = 6371  # รัศมีโลกในหน่วยกิโลเมตร
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2)**2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def get_nearest_air_quality_data():
    """ดึงข้อมูลคุณภาพอากาศจากตำแหน่งที่ใกล้ที่สุด (ไม่ต้องระบุพิกัด)"""
    global API_CALL_COUNT
    
    if API_CALL_COUNT >= MAX_API_CALLS:
        print(f"⚠️  ถึงขีดจำกัดการใช้ API แล้ว ({MAX_API_CALLS} calls/year)")
        return None
    
    url = f"http://api.airvisual.com/v2/nearest_city?key={AIRVISUAL_API_KEY}"
    
    try:
        response = requests.get(url, timeout=15)
        API_CALL_COUNT += 1
        
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
        elif response.status_code == 429:
            print(f"⚠️  API Rate limit - รอสักครู่ (API calls: {API_CALL_COUNT}/{MAX_API_CALLS})")
            time.sleep(2)
            return None
        else:
            print(f"❌ HTTP {response.status_code} - API calls: {API_CALL_COUNT}/{MAX_API_CALLS}")
            return None
    except Exception as e:
        print(f"❌ ไม่สามารถดึงข้อมูลคุณภาพอากาศได้: {e}")
        return None

def get_air_quality_stations(province_name):
    """ดึงข้อมูลสถานีวัดคุณภาพอากาศจาก AirVisual API"""
    print(f"\n🌬️ กำลังค้นหาสถานีวัดคุณภาพอากาศใน {province_name}...")
    print(f"📊 API calls ที่ใช้ไป: {API_CALL_COUNT}/{MAX_API_CALLS}")
    
    # ใช้ nearest city API เพื่อหาข้อมูลคุณภาพอากาศ
    air_quality_data = get_nearest_air_quality_data()
    if air_quality_data:
        return [air_quality_data]
    return []

def get_air_quality_by_coordinates(lat, lon):
    """ดึงข้อมูลคุณภาพอากาศจากพิกัดที่กำหนด"""
    global API_CALL_COUNT, AIR_QUALITY_CACHE
    
    # สร้าง cache key (ปัดเศษพิกัดเพื่อจัดกลุ่มพื้นที่ใกล้เคียง)
    cache_key = (round(lat, 1), round(lon, 1))
    
    # ตรวจสอบ cache ก่อน
    if cache_key in AIR_QUALITY_CACHE:
        return AIR_QUALITY_CACHE[cache_key]
    
    if API_CALL_COUNT >= MAX_API_CALLS:
        print(f"⚠️  ถึงขีดจำกัดการใช้ API แล้ว ({MAX_API_CALLS} calls/year)")
        # ใช้ข้อมูลจาก nearest city แทน
        nearest_data = get_nearest_air_quality_data()
        AIR_QUALITY_CACHE[cache_key] = nearest_data
        return nearest_data
    
    url = f"http://api.airvisual.com/v2/nearest_city?lat={lat}&lon={lon}&key={AIRVISUAL_API_KEY}"
    
    try:
        response = requests.get(url, timeout=15)
        API_CALL_COUNT += 1
        
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
                AIR_QUALITY_CACHE[cache_key] = air_quality_data
                return air_quality_data
        elif response.status_code == 429:
            print(f"⚠️  API Rate limit - ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน")
            # ใช้ nearest city API แทน
            nearest_data = get_nearest_air_quality_data()
            AIR_QUALITY_CACHE[cache_key] = nearest_data
            return nearest_data
        else:
            print(f"❌ HTTP {response.status_code} - ใช้ข้อมูลจากสถานีใกล้ที่สุดแทน")
            # ใช้ nearest city API แทน
            nearest_data = get_nearest_air_quality_data()
            AIR_QUALITY_CACHE[cache_key] = nearest_data
            return nearest_data
    except Exception as e:
        print(f"❌ ไม่สามารถดึงข้อมูลคุณภาพอากาศได้: {e}")
        # ใช้ nearest city API แทน
        nearest_data = get_nearest_air_quality_data()
        AIR_QUALITY_CACHE[cache_key] = nearest_data
        return nearest_data

def get_aqi_level_description(aqi):
    """แปลงค่า AQI เป็นคำอธิบายภาษาไทย"""
    if aqi <= 50:
        return "ดีมาก 🟢", "อากาศสะอาด ปลอดภัยสำหรับกิจกรรมกลางแจ้ง"
    elif aqi <= 100:
        return "ปานกลาง 🟡", "อากาศพอใช้ได้ คนไวต่อมลพิษควรระวัง"
    elif aqi <= 150:
        return "ไม่ดีสำหรับกลุ่มเสี่ยง 🟠", "คนไวต่อมลพิษควรหลีกเลี่ยงกิจกรรมกลางแจ้ง"
    elif aqi <= 200:
        return "ไม่ดี 🔴", "ทุกคนควรจำกัดกิจกรรมกลางแจ้ง"
    elif aqi <= 300:
        return "แย่มาก 🟣", "ทุกคนควรหลีกเลี่ยงกิจกรรมกลางแจ้ง"
    else:
        return "อันตราย ⚫", "ทุกคนควรอยู่ในอาคาร"

def display_air_quality_info(air_quality_data):
    """แสดงข้อมูลคุณภาพอากาศ"""
    if not air_quality_data:
        return
    
    pollution = air_quality_data.get('pollution', {})
    weather = air_quality_data.get('weather', {})
    
    print(f"   🌬️  คุณภาพอากาศ: {air_quality_data.get('city', 'ไม่ระบุ')}")
    
    if pollution:
        aqi = pollution.get('aqius', 0)
        main_pollutant = pollution.get('mainus', 'ไม่ระบุ')
        level, description = get_aqi_level_description(aqi)
        
        print(f"   📊 AQI (US): {aqi} - {level}")
        print(f"   💨 สาเหตุหลัก: {main_pollutant}")
        print(f"   ℹ️  {description}")
    
    if weather:
        temp = weather.get('tp', 'ไม่ระบุ')
        humidity = weather.get('hu', 'ไม่ระบุ')
        pressure = weather.get('pr', 'ไม่ระบุ')
        
        print(f"   🌡️  อุณหภูมิ: {temp}°C | ความชื้น: {humidity}% | ความกดอากาศ: {pressure} hPa")

def get_nominatim_places(province_name, place_type="tourism", limit=5):
    query = f"{place_type} in {province_name}, Thailand"
    params = {
        'q': query,
        'format': 'json',
        'limit': limit * 2,  # ดึงมากกว่าเป้าหมายเพื่อรองรับการลบซ้ำ
        'addressdetails': 1,
        'extratags': 1
    }
    headers = {
        'User-Agent': 'Thailand Tourism App (educational purpose)'
    }
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            places = []
            for item in data:
                place_info = {
                    'name': item.get('display_name', '').split(',')[0],
                    'full_address': item.get('display_name', ''),
                    'lat': float(item.get('lat', 0)),
                    'lon': float(item.get('lon', 0)),
                    'type': item.get('type', 'ไม่ระบุประเภท'),
                    'importance': item.get('importance', 0)
                }
                places.append(place_info)
            
            # ลบข้อมูลซ้ำและจำกัดจำนวน
            unique_places = remove_duplicates(places)
            return unique_places[:limit]
        else:
            return []
    except Exception as e:
        return []

def group_places_by_air_quality(places):
    """จัดกลุ่มสถานที่ตามสถานีวัดคุณภาพอากาศที่ใกล้ที่สุด"""
    global API_CALL_COUNT
    
    if not places:
        return []
    
    grouped_places = defaultdict(list)
    
    print(f"🔄 กำลังดึงข้อมูลคุณภาพอากาศ... (API calls: {API_CALL_COUNT}/{MAX_API_CALLS})")
    
    for place in places:
        if place.get('lat') and place.get('lon'):
            lat, lon = place['lat'], place['lon']
            
            # ดึงข้อมูลคุณภาพอากาศ (มี cache และ fallback)
            air_quality_data = get_air_quality_by_coordinates(lat, lon)
            place['air_quality'] = air_quality_data
            
            # จัดกลุ่มตามพิกัดสถานีวัดคุณภาพอากาศ
            if air_quality_data:
                station_key = (air_quality_data.get('city', 'Unknown'), 
                              air_quality_data.get('state', 'Unknown'))
                grouped_places[station_key].append(place)
            else:
                grouped_places[('ไม่ทราบ', 'ไม่ทราบ')].append(place)
            
            # หน่วงเวลาเล็กน้อยเพื่อไม่ให้เรียก API บ่อยเกินไป
            time.sleep(0.5)
    
    return grouped_places

def display_places_with_air_quality(places, title):
    if not places:
        print(f"\n❌ ไม่พบข้อมูล {title}")
        return
    
    print(f"\n📍 {title}")
    print("-" * 50)
    
    # จัดกลุ่มสถานที่ตามคุณภาพอากาศ
    grouped_places = group_places_by_air_quality(places)
    
    for station_info, place_list in grouped_places.items():
        station_city, station_state = station_info
        print(f"\n🏢 บริเวณสถานีวัด: {station_city}, {station_state}")
        print("-" * 30)
        
        # แสดงข้อมูลคุณภาพอากาศครั้งเดียวต่อกลุ่ม
        if place_list and place_list[0].get('air_quality'):
            display_air_quality_info(place_list[0]['air_quality'])
            print()
        
        # แสดงรายการสถานที่ในกลุ่ม
        for i, place in enumerate(place_list, 1):
            print(f"   {i}. {place.get('name', 'ไม่มีชื่อ')}")
            if place.get('type'):
                print(f"      🏷️  ประเภท: {place['type']}")
            if place.get('full_address'):
                print(f"      🏠 ที่อยู่: {place['full_address'][:100]}...")
            if place.get('lat') and place.get('lon'):
                lat, lon = place['lat'], place['lon']
                print(f"      🗺️  พิกัด: {lat:.4f}, {lon:.4f}")
                print(f"      🌐 แผนที่: https://maps.google.com/?q={lat},{lon}")
            print()

def display_places(places, title):
    """แสดงข้อมูลสถานที่โดยไม่มีข้อมูลคุณภาพอากาศ"""
    if not places:
        print(f"\n❌ ไม่พบข้อมูล {title}")
        return
    
    print(f"\n📍 {title}")
    print("-" * 50)
    
    for i, place in enumerate(places, 1):
        print(f"{i}. {place.get('name', 'ไม่มีชื่อ')}")
        if place.get('type'):
            print(f"   🏷️  ประเภท: {place['type']}")
        if place.get('full_address'):
            print(f"   🏠 ที่อยู่: {place['full_address'][:100]}...")
        if place.get('lat') and place.get('lon'):
            lat, lon = place['lat'], place['lon']
            print(f"   🗺️  พิกัด: {lat:.4f}, {lon:.4f}")
            print(f"   🌐 แผนที่: https://maps.google.com/?q={lat},{lon}")
        print()

def show_api_menu():
    print("\n" + "="*60)
    print("🏛️ แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย + คุณภาพอากาศ")
    print("="*60)
    print(f"📊 API Usage: {API_CALL_COUNT}/{MAX_API_CALLS} calls used")
    print(f"🗂️  Cache: {len(AIR_QUALITY_CACHE)} พื้นที่ในหน่วยความจำ")
    print("-"*60)
    print("1. 📍 สถานที่ท่องเที่ยว (พร้อมข้อมูลอากาศ)")
    print("2. 🏨 โรงแรม (พร้อมข้อมูลอากาศ)")
    print("3. 🍽️  ร้านอาหาร (พร้อมข้อมูลอากาศ)")
    print("4. 🎯 ค้นหาสถานที่ทั้งหมด (พร้อมข้อมูลอากาศ)")
    print("5. 🌬️  ดูเฉพาะข้อมูลคุณภาพอากาศ")
    print("6. 📋 ค้นหาสถานที่ (ไม่มีข้อมูลอากาศ - ประหยัด API)")
    print("7. 🧹 ล้างข้อมูลใน Cache")
    print("0. ❌ ออกจากโปรแกรม")
    print("-"*60)

def get_combined_tourism(province_name):
    """รวมสถานที่ท่องเที่ยวจากหลายหมวด"""
    tourism_types = [
        ("tourism", "สถานที่ท่องเที่ยว"),
        ("attraction", "สถานที่น่าสนใจ"),
        ("viewpoint", "จุดชมวิว"),
        ("museum", "พิพิธภัณฑ์"),
        ("zoo", "สวนสัตว์")
    ]
    
    print(f"\n🔍 กำลังค้นหาสถานที่ท่องเที่ยวใน {province_name}")
    print("=" * 50)
    
    all_results = []
    total_found = 0
    
    for place_type, thai_name in tourism_types:
        places = get_nominatim_places(province_name, place_type, limit=3)
        found_count = len(places)
        total_found += found_count
        
        # แสดงผลการค้นหาแต่ละประเภท
        if found_count > 0:
            print(f"✅ {thai_name}: พบ {found_count} แห่ง")
        else:
            print(f"❌ {thai_name}: ไม่พบข้อมูล")
            
        all_results.extend(places)
        
        # หยุดเมื่อได้ครบ 5 สถานที่
        if len(all_results) >= 5:
            break
    
    # ลบข้อมูลซ้ำและจำกัดผลลัพธ์ที่ 5 สถานที่
    unique_results = remove_duplicates(all_results)
    final_results = unique_results[:5]
    
    print(f"\n📊 สรุปผลการค้นหา:")
    print(f"   🔢 รวมทั้งหมด: {total_found} สถานที่")
    print(f"   🔄 หลังลบซ้ำ: {len(unique_results)} สถานที่")
    print(f"   📍 แสดงผล: {len(final_results)} สถานที่")
    print("-" * 50)
    
    return final_results

def main():
    print("🇹🇭 แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย + คุณภาพอากาศ")
    print("ค้นหาสถานที่ท่องเที่ยว โรงแรม ร้านอาหาร พร้อมข้อมูลคุณภาพอากาศ")
    print("✨ ระบบใหม่: ใช้ข้อมูลจากสถานีใกล้ที่สุดเมื่อเกิน API limit")

    while True:
        show_api_menu()
        choice = input("เลือกตัวเลือก (0-7): ").strip()

        if choice == "0":
            print("👋 ขอบคุณที่ใช้บริการ!")
            print(f"📊 API calls ที่ใช้ไปทั้งหมด: {API_CALL_COUNT}/{MAX_API_CALLS}")
            break

        elif choice == "7":
            AIR_QUALITY_CACHE.clear()
            print("🧹 ล้างข้อมูลใน Cache เรียบร้อย!")
            continue

        if choice in ["1", "2", "3", "4", "5", "6"]:
            province_name = input("\nกรอกชื่อจังหวัด: ").strip()
            if not province_name:
                print("❌ กรุณากรอกชื่อจังหวัด")
                continue
            province_name = normalize_province_name(province_name)
            print(f"\n🔍 กำลังค้นหาข้อมูลสำหรับจังหวัด: {province_name}")

        if choice == "1":
            places = get_combined_tourism(province_name)
            display_places_with_air_quality(places, "สถานที่ท่องเที่ยว")

        elif choice == "2":
            print(f"\n🔍 กำลังค้นหาโรงแรมใน {province_name}")
            print("=" * 50)
            hotels = get_nominatim_places(province_name, "hotel", 8)
            found_count = len(hotels)
            print(f"✅ โรงแรม: พบ {found_count} แห่ง")
            print(f"📍 แสดงผล: {min(found_count, 8)} แห่ง")
            print("-" * 50)
            display_places_with_air_quality(hotels, "โรงแรม")

        elif choice == "3":
            print(f"\n🔍 กำลังค้นหาร้านอาหารใน {province_name}")
            print("=" * 50)
            restaurants = get_nominatim_places(province_name, "restaurant", 8)
            found_count = len(restaurants)
            print(f"✅ ร้านอาหาร: พบ {found_count} แห่ง")
            print(f"📍 แสดงผล: {min(found_count, 8)} แห่ง")
            print("-" * 50)
            display_places_with_air_quality(restaurants, "ร้านอาหาร")

        elif choice == "4":
            print(f"\n🚀 กำลังค้นหาสถานที่ทั้งหมดสำหรับ {province_name}")
            print("="*60)

            tourism_places = get_combined_tourism(province_name)
            display_places_with_air_quality(tourism_places, "สถานที่ท่องเที่ยว")

            print(f"\n🔍 กำลังค้นหาโรงแรมใน {province_name}")
            print("-" * 30)
            hotels = get_nominatim_places(province_name, "hotel", 4)
            found_count = len(hotels)
            print(f"✅ โรงแรม: พบ {found_count} แห่ง")
            display_places_with_air_quality(hotels, "โรงแรม")

            print(f"\n🔍 กำลังค้นหาร้านอาหารใน {province_name}")
            print("-" * 30)
            restaurants = get_nominatim_places(province_name, "restaurant", 4)
            found_count = len(restaurants)
            print(f"✅ ร้านอาหาร: พบ {found_count} แห่ง")
            display_places_with_air_quality(restaurants, "ร้านอาหาร")

            print(f"\n🔍 กำลังค้นหาศูนย์การค้าใน {province_name}")
            print("-" * 30)
            shopping = get_nominatim_places(province_name, "shopping center", 3)
            found_count = len(shopping)
            print(f"✅ ศูนย์การค้า: พบ {found_count} แห่ง")
            display_places_with_air_quality(shopping, "ศูนย์การค้า")

            print(f"\n🔍 กำลังค้นหาวัด/สถานที่ทางศาสนาใน {province_name}")
            print("-" * 30)
            temples = get_nominatim_places(province_name, "place of worship", 3)
            found_count = len(temples)
            print(f"✅ วัด/สถานที่ทางศาสนา: พบ {found_count} แห่ง")
            display_places_with_air_quality(temples, "วัด/สถานที่ทางศาสนา")

            print(f"\n✅ ค้นหาสถานที่เสร็จสมบูรณ์!")

        elif choice == "5":
            air_stations = get_air_quality_stations(province_name)
            if air_stations:
                print(f"\n🌬️ ข้อมูลคุณภาพอากาศใน {province_name}")
                print("-" * 50)
                for station in air_stations:
                    display_air_quality_info(station)
            else:
                print("❌ ไม่พบข้อมูลคุณภาพอากาศ")

        elif choice == "6":
            print(f"\n📋 ค้นหาสถานที่ทั้งหมด (ไม่มีข้อมูลอากาศ) - ประหยัด API")
            print("="*60)

            tourism_places = get_combined_tourism(province_name)
            display_places(tourism_places, "สถานที่ท่องเที่ยว")

            print(f"\n🔍 กำลังค้นหาโรงแรมใน {province_name}")
            print("-" * 30)
            hotels = get_nominatim_places(province_name, "hotel", 6)
            found_count = len(hotels)
            print(f"✅ โรงแรม: พบ {found_count} แห่ง")
            display_places(hotels, "โรงแรม")

            print(f"\n🔍 กำลังค้นหาร้านอาหารใน {province_name}")
            print("-" * 30)
            restaurants = get_nominatim_places(province_name, "restaurant", 6)
            found_count = len(restaurants)
            print(f"✅ ร้านอาหาร: พบ {found_count} แห่ง")
            display_places(restaurants, "ร้านอาหาร")

            print(f"\n🔍 กำลังค้นหาศูนย์การค้าใน {province_name}")
            print("-" * 30)
            shopping = get_nominatim_places(province_name, "shopping center", 4)
            found_count = len(shopping)
            print(f"✅ ศูนย์การค้า: พบ {found_count} แห่ง")
            display_places(shopping, "ศูนย์การค้า")

            print(f"\n🔍 กำลังค้นหาวัด/สถานที่ทางศาสนาใน {province_name}")
            print("-" * 30)
            temples = get_nominatim_places(province_name, "place of worship", 4)
            found_count = len(temples)
            print(f"✅ วัด/สถานที่ทางศาสนา: พบ {found_count} แห่ง")
            display_places(temples, "วัด/สถานที่ทางศาสนา")

            print(f"\n✅ ค้นหาสถานที่เสร็จสมบูรณ์! (ไม่ใช้ API คุณภาพอากาศ)")

        else:
            print("❌ กรุณาเลือกตัวเลือกที่ถูกต้อง (0-7)")

        time.sleep(1)
        print("\n" + "="*60)
        input("กด Enter เพื่อดำเนินการต่อ...")

if __name__ == "__main__":
    main()