import requests
import json
from urllib.parse import quote
import time

# ชื่อเล่น → ชื่อจริง
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

def normalize_province_name(name):
    return ALIAS_TO_PROVINCE.get(name.strip(), name.strip())

# ================================
# 1. Thailand Open Data Portal API
# ================================
def get_thailand_open_data(province_name):
    """ดึงข้อมูลจาก Thailand Open Data Portal"""
    print("\n🔍 กำลังค้นหาข้อมูลจาก Thailand Open Data Portal...")
    
    base_url = "https://data.go.th/api/datasets"
    
    try:
        search_url = f"{base_url}?q=tourism+{province_name}"
        response = requests.get(search_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ พบข้อมูลจาก Open Data Portal: {len(data.get('results', []))} รายการ")
            return data.get('results', [])[:5]
        else:
            print(f"❌ Open Data Portal: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Open Data Portal Error: {e}")
        return []

# ================================
# 2. OpenStreetMap Overpass API
# ================================
def get_overpass_data(province_name, amenity_type="tourism", limit=5):
    """ดึงข้อมูลจาก OpenStreetMap Overpass API"""
    print(f"\n🔍 กำลังค้นหา{amenity_type}จาก OpenStreetMap Overpass API...")
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["{amenity_type}"]["addr:province"~"{province_name}",i];
      way["{amenity_type}"]["addr:province"~"{province_name}",i];
      relation["{amenity_type}"]["addr:province"~"{province_name}",i];
    );
    out center meta;
    """
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    try:
        response = requests.post(
            overpass_url,
            data=overpass_query,
            headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            print(f"✅ Overpass API พบ: {len(elements)} รายการ")
            
            places = []
            for element in elements[:limit]:
                place_info = {
                    'name': element.get('tags', {}).get('name', 'ไม่มีชื่อ'),
                    'type': element.get('tags', {}).get(amenity_type, 'ไม่ระบุประเภท'),
                    'address': element.get('tags', {}).get('addr:full', ''),
                    'lat': element.get('lat', 0),
                    'lon': element.get('lon', 0)
                }
                places.append(place_info)
            
            return places
        else:
            print(f"❌ Overpass API: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Overpass API Error: {e}")
        return []

# ================================
# 3. Nominatim API (OpenStreetMap)
# ================================
def get_nominatim_places(province_name, place_type="tourism", limit=5):
    """ดึงข้อมูลจาก Nominatim API"""
    print(f"\n🔍 กำลังค้นหา {place_type} จาก Nominatim API...")
    
    query = f"{place_type} in {province_name}, Thailand"
    
    params = {
        'q': query,
        'format': 'json',
        'limit': limit,
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
            print(f"✅ Nominatim API พบ: {len(data)} รายการ")
            
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
            
            return places
        else:
            print(f"❌ Nominatim API: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Nominatim API Error: {e}")
        return []

# ================================
# 4. REST Countries API
# ================================
def get_thailand_country_info():
    """ดึงข้อมูลประเทศไทยจาก REST Countries API"""
    print("\n🔍 กำลังดึงข้อมูลประเทศไทย...")
    
    url = "https://restcountries.com/v3.1/name/thailand"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                country = data[0]
                info = {
                    'name': country.get('name', {}).get('common', 'Thailand'),
                    'capital': country.get('capital', ['N/A'])[0],
                    'population': country.get('population', 0),
                    'area': country.get('area', 0),
                    'region': country.get('region', ''),
                    'currency': list(country.get('currencies', {}).keys())[0] if country.get('currencies') else 'N/A',
                    'languages': list(country.get('languages', {}).values()),
                    'timezone': country.get('timezones', ['N/A'])[0]
                }
                print("✅ ได้ข้อมูลประเทศไทยแล้ว")
                return info
        
        print(f"❌ REST Countries API: HTTP {response.status_code}")
        return None
        
    except Exception as e:
        print(f"❌ REST Countries API Error: {e}")
        return None

# ================================
# Display Functions
# ================================
def display_places(places, title):
    """แสดงข้อมูลสถานที่"""
    if not places:
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
            print(f"   🗺️  พิกัด: {place['lat']:.4f}, {place['lon']:.4f}")
        print()

def display_country_info(country_info):
    """แสดงข้อมูลประเทศ"""
    if not country_info:
        return
    
    print(f"\n🇹🇭 ข้อมูลประเทศไทย")
    print("-" * 50)
    print(f"🏛️  เมืองหลวง: {country_info['capital']}")
    print(f"👥 ประชากร: {country_info['population']:,} คน")
    print(f"📐 พื้นที่: {country_info['area']:,} ตร.กม.")
    print(f"🌏 ภูมิภาค: {country_info['region']}")
    print(f"💰 สกุลเงิน: {country_info['currency']}")
    print(f"🗣️  ภาษา: {', '.join(country_info['languages'])}")
    print(f"🕐 เขตเวลา: {country_info['timezone']}")

def show_api_menu():
    """แสดงเมนูเลือก API"""
    print("\n" + "="*60)
    print("🏛️ แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย")
    print("="*60)
    print("1. 🏛️  Thailand Open Data Portal")
    print("2. 🗺️  OpenStreetMap Overpass API")
    print("3. 🇹🇭 ข้อมูลประเทศไทย")
    print("4. 📍 สถานที่ท่องเที่ยว (Nominatim)")
    print("5. 🏨 โรงแรม (Nominatim)")
    print("6. 🍽️  ร้านอาหาร (Nominatim)")
    print("7. 🎯 ค้นหาสถานที่ทั้งหมด")
    print("0. ❌ ออกจากโปรแกรม")
    print("-"*60)

def main():
    print("🇹🇭 แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย")
    print("ค้นหาสถานที่ท่องเที่ยว โรงแรม ร้านอาหาร และข้อมูลทั่วไป")
    
    while True:
        show_api_menu()
        choice = input("เลือกตัวเลือก (0-7): ").strip()
        
        if choice == "0":
            print("👋 ขอบคุณที่ใช้บริการ!")
            break
        
        if choice in ["1", "2", "4", "5", "6", "7"]:
            province_name = input("\nกรอกชื่อจังหวัด: ").strip()
            if not province_name:
                print("❌ กรุณากรอกชื่อจังหวัด")
                continue
            
            province_name = normalize_province_name(province_name)
            print(f"\n🔍 กำลังค้นหาข้อมูลสำหรับจังหวัด: {province_name}")
        
        # ดำเนินการตามตัวเลือก
        if choice == "1":
            # Thailand Open Data Portal
            data = get_thailand_open_data(province_name)
            if data:
                print(f"\n📊 ข้อมูลจาก Thailand Open Data Portal")
                print("-" * 50)
                for i, item in enumerate(data, 1):
                    print(f"{i}. {item.get('title', 'ไม่มีชื่อ')}")
                    if item.get('description'):
                        print(f"   📝 {item['description'][:100]}...")
                    print()
            else:
                print("❌ ไม่พบข้อมูลจาก Thailand Open Data Portal")
        
        elif choice == "2":
            # OpenStreetMap Overpass API
            tourism_places = get_overpass_data(province_name, "tourism")
            display_places(tourism_places, "สถานที่ท่องเที่ยว (Overpass API)")
        
        elif choice == "3":
            # REST Countries API
            country_info = get_thailand_country_info()
            display_country_info(country_info)
        
        elif choice == "4":
            # สถานที่ท่องเที่ยว
            places = get_nominatim_places(province_name, "tourism attraction", 8)
            display_places(places, "สถานที่ท่องเที่ยว")
        
        elif choice == "5":
            # โรงแรม
            hotels = get_nominatim_places(province_name, "hotel", 8)
            display_places(hotels, "โรงแรม")
        
        elif choice == "6":
            # ร้านอาหาร
            restaurants = get_nominatim_places(province_name, "restaurant", 8)
            display_places(restaurants, "ร้านอาหาร")
        
        elif choice == "7":
            # ค้นหาสถานที่ทั้งหมด
            print(f"\n🚀 กำลังค้นหาสถานที่ทั้งหมดสำหรับ {province_name}")
            print("="*60)
            
            # 1. ข้อมูลประเทศ
            country_info = get_thailand_country_info()
            display_country_info(country_info)
            
            # 2. สถานที่ท่องเที่ยว (Nominatim)
            tourism_places = get_nominatim_places(province_name, "tourism attraction", 6)
            display_places(tourism_places, "สถานที่ท่องเที่ยว")
            
            # 3. โรงแรม
            hotels = get_nominatim_places(province_name, "hotel", 6)
            display_places(hotels, "โรงแรม")
            
            # 4. ร้านอาหาร
            restaurants = get_nominatim_places(province_name, "restaurant", 6)
            display_places(restaurants, "ร้านอาหาร")
            
            # 5. ศูนย์การค้า
            shopping = get_nominatim_places(province_name, "shopping center", 4)
            display_places(shopping, "ศูนย์การค้า")
            
            # 6. วัด/สถานที่ทางศาสนา
            temples = get_nominatim_places(province_name, "temple", 4)
            display_places(temples, "วัด/สถานที่ทางศาสนา")
            
            # 7. Open Data Portal
            open_data = get_thailand_open_data(province_name)
            if open_data:
                print(f"\n📊 ข้อมูลเพิ่มเติม (Open Data Portal)")
                print("-" * 50)
                for i, item in enumerate(open_data[:3], 1):
                    print(f"{i}. {item.get('title', 'ไม่มีชื่อ')}")
                    print()
            
            print(f"\n✅ ค้นหาสถานที่เสร็จสมบูรณ์!")
        
        else:
            print("❌ กรุณาเลือกตัวเลือกที่ถูกต้อง")
        
        # หยุดชั่วคราวเพื่อไม่ให้ API rate limit
        time.sleep(1)
        
        print("\n" + "="*60)
        input("กด Enter เพื่อดำเนินการต่อ...")

if __name__ == "__main__":
    main()