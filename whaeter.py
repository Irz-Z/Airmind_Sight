import requests

# ✅ Mapping จังหวัดไทย → ชื่อภาษาอังกฤษ (เฉพาะบางจังหวัด)
province_map = {
    "กรุงเทพ": "Bangkok",
    "เชียงใหม่": "Chiang Mai",
    "ขอนแก่น": "Khon Kaen",
    "ภูเก็ต": "Phuket",
    "นครราชสีมา": "Nakhon Ratchasima",
    "ชลบุรี": "Chonburi",
    "อุดรธานี": "Udon Thani",
    "นครศรีธรรมราช": "Nakhon Si Thammarat",
    "สงขลา": "Songkhla",
    "เชียงราย": "Chiang Rai"
}

API_KEY = "83e13ab7a98442d7a77122659250607"  # 🔑 ใส่ API Key ที่ได้จาก WeatherAPI

# 📥 รับชื่อจังหวัดจากผู้ใช้
province_th = input("กรอกชื่อจังหวัด (ภาษาไทย): ").strip()

if province_th not in province_map:
    print("❌ จังหวัดนี้ยังไม่รองรับ กรุณาเลือกจาก: ", ", ".join(province_map.keys()))
    exit()

province_en = province_map[province_th]

# 🔗 สร้าง URL
url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={province_en}&days=7&aqi=yes"

# 📡 เรียกข้อมูล API
response = requests.get(url)
data = response.json()

# ✅ แสดงผล
print(f"\n📍 จังหวัด: {province_th} ({province_en})")
print(f"สภาพอากาศล่วงหน้า 7 วัน:\n")

for day in data['forecast']['forecastday']:
    date = day['date']
    condition = day['day']['condition']['text']
    temp = day['day']['avgtemp_c']
    print(f"- {date}: {condition}, อุณหภูมิเฉลี่ย: {temp}°C")

# 🌫 แสดงคุณภาพอากาศ
aqi = data['current']['air_quality']
print("\n🌫 คุณภาพอากาศตอนนี้:")
print(f"PM2.5: {aqi['pm2_5']:.2f}, PM10: {aqi['pm10']:.2f}")
print(f"CO: {aqi['co']:.2f}, NO2: {aqi['no2']:.2f}, O3: {aqi['o3']:.2f}")
