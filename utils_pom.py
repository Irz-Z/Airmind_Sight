import requests
import json
from datetime import datetime
from datetime import date
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

# get current date and time
def get_datetime():
  print('Getting Date Data')
  """Converts a datetime object to a dictionary."""
  # get date data
  d = date.today()
  d = d.strftime("%A %d %B %Y")
  d = d.split(' ')
  date_dict = {
      'day': d[0],
      'date': d[1],
      'month': d[2],
      'year': d[3]
  }
  # fetch time data
  time_obj = datetime.now()
  CURRENT_TIME = f'{time_obj.hour}:{time_obj.minute}'
  time_dict = {
      'current_time': CURRENT_TIME
      }
  datetime_dict_output = date_dict | time_dict
  print(datetime_dict_output)
  return datetime_dict_output

# convert nickname to full province name
def normalize_province_name(name):
    return ALIAS_TO_PROVINCE.get(name.strip(), name.strip())

# fetch data from Thailand Open Data Portal
def get_thailand_open_data(province_name):
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

# fetch places from OpenStreetMap Overpass API
def get_overpass_data(province_name, amenity_type="tourism", limit=5):
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

# fetch places from Nominatim API
def get_nominatim_places(province_name, place_type="tourism", limit=5):
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

# display places in a formatted way
def display_places(places, title):
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
            print(f"   🗺️  พิกัด: {place['lat']:.4f}, {place['lon']:.4f}")
        print()

# show api menu
def show_api_menu():
    print("\n" + "="*60)
    print("🏛️ แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย")
    print("="*60)
    print("1. 🏛️  Thailand Open Data Portal")
    print("2. 🗺️  OpenStreetMap Overpass API")
    print("3. 📍 สถานที่ท่องเที่ยว (Nominatim)")
    print("4. 🏨 โรงแรม (Nominatim)")
    print("5. 🍽️  ร้านอาหาร (Nominatim)")
    print("6. 🎯 ค้นหาสถานที่ทั้งหมด")
    print("0. ❌ ออกจากโปรแกรม")
    print("-"*60)

# fetch weather data from IQAIR
def get_weather_data(province_name):
    print('Getting Weather Data...')
    city = province_name
    state = province_name
    key = 'c276b727-085b-4e13-8a72-181ce160c0a6'
    response = requests.get(f'http://api.airvisual.com/v2/city?city={city}&state={state}&country=Thailand&key={key}')
    weather_data = response.json()
    print(f'Status: {weather_data['status']}')
    return weather_data

# main function to run the application
def main():
    print("🇹🇭 แอปพลิเคชันข้อมูลสถานที่ท่องเที่ยวไทย")
    print("ค้นหาสถานที่ท่องเที่ยว โรงแรม ร้านอาหาร")

    while True:
        show_api_menu()
        choice = input("เลือกตัวเลือก (0-6): ").strip()

        if choice == "0":
            print("👋 ขอบคุณที่ใช้บริการ!")
            break

        if choice in ["1", "2", "3", "4", "5", "6"]:
            province_name = input("\nกรอกชื่อจังหวัด: ").strip()
            if not province_name:
                print("❌ กรุณากรอกชื่อจังหวัด")
                continue
            province_name = normalize_province_name(province_name)
            print(f"\n🔍 กำลังค้นหาข้อมูลสำหรับจังหวัด: {province_name}")

        if choice == "1":
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
            tourism_places = get_overpass_data(province_name, "tourism")
            display_places(tourism_places, "สถานที่ท่องเที่ยว (Overpass API)")

        elif choice == "3":
            places = get_nominatim_places(province_name, "tourism", 8)
            display_places(places, "สถานที่ท่องเที่ยว")

        elif choice == "4":
            hotels = get_nominatim_places(province_name, "hotel", 8)
            display_places(hotels, "โรงแรม")

        elif choice == "5":
            restaurants = get_nominatim_places(province_name, "restaurant", 8)
            display_places(restaurants, "ร้านอาหาร")

        elif choice == "6":
            print(f"\n🚀 กำลังค้นหาสถานที่ทั้งหมดสำหรับ {province_name}")
            print("="*60)

            tourism_places = get_nominatim_places(province_name, "tourism", 6)
            display_places(tourism_places, "สถานที่ท่องเที่ยว")

            hotels = get_nominatim_places(province_name, "hotel", 6)
            display_places(hotels, "โรงแรม")

            restaurants = get_nominatim_places(province_name, "restaurant", 6)
            display_places(restaurants, "ร้านอาหาร")

            shopping = get_nominatim_places(province_name, "shopping center", 4)
            display_places(shopping, "ศูนย์การค้า")

            temples = get_nominatim_places(province_name, "place of worship", 4)
            display_places(temples, "วัด/สถานที่ทางศาสนา")

            open_data = get_thailand_open_data(province_name)
            if open_data:
                print(f"\n📊 ข้อมูลเพิ่มเติม (Open Data Portal)")
                print("-" * 50)
                for i, item in enumerate(open_data[:3], 1):
                    print(f"{i}. {item.get('title', 'ไม่มีชื่อ')}")
                    print()

            print(f"\n✅ ค้นหาสถานที่เสร็จสมบูรณ์!")

        time.sleep(1)
        print("\n" + "="*60)
        input("กด Enter เพื่อดำเนินการต่อ...")

if __name__ == "__main__":
    main()
