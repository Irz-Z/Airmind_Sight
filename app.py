import requests

API_KEY = "dUO6Sbg1KV3GZEqtgwpsVisvOMTS0b8D"
HEADERS = {
    "accept": "application/json",
    "Accept-Language": "th",
    "x-api-key": API_KEY
}

# ชื่อเล่น → ชื่อจริง
ALIAS_TO_PROVINCE = {
    "โคราช": "นครราชสีมา",
    "กทม": "กรุงเทพมหานคร",
    "บางกอก": "กรุงเทพมหานคร",
    "พัทยา": "ชลบุรี",
    "อุบล": "อุบลราชธานี",
    "ขอนแก่น": "ขอนแก่น",
}

# หมวดหมู่สถานที่
PLACE_CATEGORIES = {
    2: "ที่พัก",
    5: "สถานที่ท่องเที่ยว", 
    16: "สถานที่อื่นๆ"
}

def normalize_province_name(name):
    return ALIAS_TO_PROVINCE.get(name.strip(), name.strip())

def get_places_by_category(category_id, province_name, limit=4):
    """ดึงสถานที่ตามหมวดหมู่และจังหวัด"""
    url = "https://tatdataapi.io/api/v2/places"
    params = {
        "place_category_id": category_id,
        "limit": 300  # เพิ่มเป็น 300 เพื่อให้ได้ข้อมูลมากขึ้น
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return []
        
        all_places = response.json().get("data", [])
        print(f"  [DEBUG] พบข้อมูลทั้งหมด: {len(all_places)} รายการ")
        
        # กรองตามจังหวัด
        filtered = [
            place for place in all_places
            if place.get("location", {}).get("province", {}).get("name") == province_name
        ]
        
        print(f"  [DEBUG] กรองแล้วเหลือ: {len(filtered)} รายการ")
        
        # ถ้าไม่เจอ ลองค้นหาแบบไม่เคร่งครัด
        if not filtered:
            print(f"  [DEBUG] ไม่พบจังหวัด '{province_name}' พอดี กำลังลองค้นหาแบบคลุมเครือ...")
            filtered = [
                place for place in all_places
                if province_name.lower() in place.get("location", {}).get("province", {}).get("name", "").lower()
            ]
            print(f"  [DEBUG] ค้นหาแบบคลุมเครือเจอ: {len(filtered)} รายการ")
        
        return filtered[:limit]
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def get_events_filtered(province_name):
    """ดึงข้อมูล Events (เดิม)"""
    url = "https://tatdataapi.io/api/v2/events"
    params = {"limit": 300}  # เพิ่มจำนวนเป็น 300
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            return []

        all_events = response.json().get("data", [])
        filtered = [
            event for event in all_events
            if event.get("location", {}).get("province", {}).get("name") == province_name
        ]
        
        # ถ้าไม่เจอ ลองค้นหาแบบไม่เคร่งครัด
        if not filtered:
            filtered = [
                event for event in all_events
                if province_name.lower() in event.get("location", {}).get("province", {}).get("name", "").lower()
            ]
        
        return filtered[:4]
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events: {e}")
        return []

def safe_get_title(item):
    """ดึงชื่อจาก title หรือ name"""
    return item.get("title") or item.get("name") or "ไม่มีชื่อ"

def display_places_info(places):
    """แสดงข้อมูลสถานที่พร้อมรายละเอียด"""
    if not places:
        print("ไม่พบข้อมูล")
        return
    
    for place in places:
        title = safe_get_title(place)
        description = place.get("description", "")
        location = place.get("location", {})
        district = location.get("district", {}).get("name", "")
        
        print(f"- {title}")
        if district:
            print(f"  📍 {district}")
        if description and len(description) > 0:
            # ตัดคำอธิบายให้สั้นๆ
            short_desc = description[:100] + "..." if len(description) > 100 else description
            print(f"  💬 {short_desc}")
        print()

def main():
    input_name = input("กรอกชื่อจังหวัด: ").strip()
    province_name = normalize_province_name(input_name)
    
    print(f"\n{'='*50}")
    print(f"ข้อมูลการท่องเที่ยวในจังหวัด {province_name}")
    print(f"{'='*50}")
    
    # ดึงข้อมูลสถานที่แต่ละหมวดหมู่
    for category_id, category_name in PLACE_CATEGORIES.items():
        print(f"\n🏛️ {category_name}")
        print("-" * 30)
        places = get_places_by_category(category_id, province_name)
        display_places_info(places)
    
    # ดึงข้อมูล Events (เดิม)
    print(f"\n🎭 กิจกรรมและเหตุการณ์")
    print("-" * 30)
    events = get_events_filtered(province_name)
    if events:
        for e in events:
            print(f"- {safe_get_title(e)}")
    else:
        print("ไม่พบข้อมูล Event")
    
    # แสดงข้อมูลจังหวัดทั้งหมดที่มีใน API (เพื่อ debug)
    print(f"\n🔍 ข้อมูลเพิ่มเติม")
    print("-" * 30)
    print("หากไม่พบข้อมูล อาจเป็นเพราะ API ไม่มีข้อมูลสำหรับจังหวัดนี้")
    print("ลองใช้ชื่อจังหวัดอื่นๆ เช่น: กรุงเทพมหานคร, เชียงใหม่, ภูเก็ต, ขอนแก่น")
    
    # เพิ่มตัวเลือกดู debug info
    show_debug = input("\nต้องการดูข้อมูล debug หรือไม่? (y/n): ").lower()
    if show_debug == 'y':
        show_available_provinces()

def show_available_provinces():
    """แสดงจังหวัดที่มีข้อมูลใน API"""
    print("\n🔍 กำลังตรวจสอบจังหวัดที่มีข้อมูลใน API...")
    
    try:
        # ดึงข้อมูลจาก places API
        url = "https://tatdataapi.io/api/v2/places"
        params = {"limit": 100}
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code == 200:
            places = response.json().get("data", [])
            provinces = set()
            for place in places:
                province = place.get("location", {}).get("province", {}).get("name")
                if province:
                    provinces.add(province)
            
            print(f"จังหวัดที่พบใน Places API ({len(provinces)} จังหวัด):")
            for prov in sorted(provinces):
                print(f"  - {prov}")
        
        # ดึงข้อมูลจาก events API
        url = "https://tatdataapi.io/api/v2/events"
        params = {"limit": 100}
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code == 200:
            events = response.json().get("data", [])
            event_provinces = set()
            for event in events:
                province = event.get("location", {}).get("province", {}).get("name")
                if province:
                    event_provinces.add(province)
            
            print(f"\nจังหวัดที่พบใน Events API ({len(event_provinces)} จังหวัด):")
            for prov in sorted(event_provinces):
                print(f"  - {prov}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()