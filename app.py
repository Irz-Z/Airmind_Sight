from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from utils_pom import (
    normalize_province_name,
    get_thailand_open_data,
    get_overpass_data,
    get_nominatim_places,
    get_weather_data,
    get_datetime
)
from utils_moss import (
    normalize_province_name,
    get_nominatim_places,
    get_air_quality_by_coordinates,
    get_aqi_level_description,
    remove_duplicates,
    get_combined_tourism,
    enrich_places_with_air_quality,
    load_from_cache,
    save_to_cache,
    rank_places_by_dust,
    rank_places_by_category_and_dust,
    get_time_series_data,
    analyze_time_series_ranking,
    get_forecast_data
)
from fetch_data import *

app = Flask(__name__)

# IQAIR
# API_KEY = '0199d98b-12a7-4ea8-8ef8-674a08a79ce7' # pppurpg@gmail.com
API_KEY = 'c926d92f-7623-4d75-81dd-7c5542c59e5e' # adisonbb2@gmail.com

# aqicn
key = '2eb93a22c78a1235a2f52546750a691ba41cd200'

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

def get_aqi_description(aqi):
    if aqi is None:
        return 'ไม่มีข้อมูล AQI', '#cccccc'
    elif aqi <= 25:
        return 'Very Good', '#4DC4EC'
    elif aqi <= 50:
        return 'Good', '#8AC541'
    elif aqi <= 100:
        return 'Moderate', '#FFEC00'
    elif aqi <= 200:
        return 'Not good for your health', '#F7941D'
    elif aqi > 200:
        return 'Very Unhealthy', '#ED1C24'
    
def add_ranking_to_places(places):
    """Add proper ranking to places based on air quality (AQI) - No rank skipping"""
    if not places:
        return places
    
    # Filter places with air quality data
    places_with_data = []
    places_without_data = []
    
    for place in places:
        air_quality = place.get('air_quality')
        if air_quality and air_quality.get('aqi') is not None:
            places_with_data.append(place)
        else:
            places_without_data.append(place)
    
    # Sort by AQI (lower = better)
    places_with_data.sort(key=lambda x: x['air_quality']['aqi'])
    
    # Assign ranks without skipping (Standard Competition Ranking)
    current_rank = 1
    previous_aqi = None
    
    for i, place in enumerate(places_with_data):
        current_aqi = place['air_quality']['aqi']
        
        # If AQI is different from previous, increment rank by 1 only
        if previous_aqi is not None and current_aqi != previous_aqi:
            current_rank += 1  # Only increment by 1, no skipping
        
        place['rank'] = current_rank
        
        # Add medal and rank text
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
        
        previous_aqi = current_aqi
    
    # Places without data don't get ranks
    for place in places_without_data:
        place['rank'] = None
        place['medal'] = ''
        place['rank_text'] = '-'
    
    return places_with_data + places_without_data

@app.route("/", methods=["GET", "POST"])
@app.route("/<province>", methods=["GET", "POST"])
def index(province=None):
    # Handle province selection
    if request.method == "POST":
        # Get province from form data
        province = normalize_province_name(request.form.get("province", ""))
        if province:
            # Redirect to clean URL
            return redirect(url_for('index', province=province.replace(" ", "-")))
    
    # Use default province if none provided
    if not province:
        province = "Khon Kaen"
    # init
    with open("results.json", "r", encoding="utf-8") as file:
        weather = json.load(file)
    results = {}
    datetime = get_datetime()  # Get current date and time

    # if province is get by URL
    # request data from API in utils.py output as dict
   
    return render_template("index_pom.html", province=province.replace("-", " "), results=results, datetime=datetime, weather=weather)

@app.route('/map')
def map_view():
    return render_template('index_ady.html')

@app.route('/data')
# IQAIR 
def get_all_data():
    try:
        with open('results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/forecast')
# aqicn
def get_forecast_api():
    try:
        with open('forecast_results.json', 'r', encoding='utf-8') as f:
            forecast_results = json.load(f)
        
        return jsonify({"status": "success", "data": forecast_results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/province/<province_name>')
def get_province_data(province_name):
    try:
        # ดึงข้อมูลจังหวัดเดียว
        data = get_data(API_KEY, province_name)
        data_json = json.loads(data)
        
        if data_json.get('status') == 'success':
            aqi = data_json['data']['current']['pollution']['aqius']
            description, color = get_aqi_description(aqi)
            
            return jsonify({
                "status": "success",
                "province": province_name,
                "aqi": aqi,
                "description": description,
                "color": color,
                "data": data_json
            })
        else:
            return jsonify({"status": "error", "message": "ไม่สามารถดึงข้อมูลได้"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/area_rec", methods=["GET", "POST"])
def area_rec():
    """
    หน้าหลักของแอปพลิเคชัน จัดการการค้นหาสถานที่และแสดงผล
    รองรับการค้นหาด้วย POST และแสดงผลลัพธ์
    มีการใช้งานระบบ Cache และการจัดเรียงตามคุณภาพอากาศ
    รองรับ Time Series Analysis
    """
    province = ""
    results = {}
    error_message = ""
    
    # Time series parameters
    enable_time_series = False
    forecast_days = "5"

    # Read parameters from form on POST, from args on GET
    if request.method == "POST":
        sort_by_dust = request.form.get("sort_by_dust", "aqius")
        enable_time_series = request.form.get("enable_time_series") == "true"
        forecast_days = request.form.get("forecast_days", "5")
    else:
        sort_by_dust = request.args.get("sort_by_dust", "aqius")
        enable_time_series = request.args.get("enable_time_series") == "true"
        forecast_days = request.args.get("forecast_days", "5")

    if request.method == "POST":
        province_input = request.form.get("province", "").strip()
        
        if not province_input:
            error_message = "กรุณากรอกชื่อจังหวัด"
        else:
            province = normalize_province_name(province_input)
            
            # 1. ลองโหลดข้อมูลจาก Cache ก่อน
            cached_data = load_from_cache(province)
            if cached_data:
                results = cached_data
                # หากโหลดจาก Cache ได้ ให้ทำการ enrich และ rank ใหม่แบบแยกประเภท
                all_places = []
                combined_tourism = []
                
                # รวม tourism และ shopping เข้าด้วยกัน
                if results.get("tourism"):
                    results["tourism"] = enrich_places_with_air_quality(results["tourism"])
                    combined_tourism.extend(results["tourism"])
                    all_places.extend(results["tourism"])
                    
                # รวม shopping เข้าใน tourism หากมี (จาก cache เก่า)
                if results.get("shopping"):
                    shopping_from_cache = enrich_places_with_air_quality(results["shopping"])
                    # เปลี่ยน type เป็น attraction เพื่อให้รวมกับสถานที่ท่องเที่ยว
                    for place in shopping_from_cache:
                        place['type'] = 'attraction'
                    combined_tourism.extend(shopping_from_cache)
                    all_places.extend(shopping_from_cache)
                
                # ลบสถานที่ซ้ำจาก combined_tourism
                combined_tourism = remove_duplicates(combined_tourism)
                
                if results.get("hotels"):
                    results["hotels"] = enrich_places_with_air_quality(results["hotels"])
                    # ลบสถานที่ซ้ำจาก hotels
                    results["hotels"] = remove_duplicates(results["hotels"])
                    all_places.extend(results["hotels"])
                if results.get("restaurants"):
                    results["restaurants"] = enrich_places_with_air_quality(results["restaurants"])
                    # ลบสถานที่ซ้ำจาก restaurants
                    results["restaurants"] = remove_duplicates(results["restaurants"])
                    all_places.extend(results["restaurants"])
                
                # จัดอันดับแยกตามประเภท
                if all_places:
                    ranked_categories = rank_places_by_category_and_dust(all_places, sort_by_dust)
                    results["tourism"] = ranked_categories.get("attraction", [])
                    results["hotels"] = ranked_categories.get("hotel", [])
                    results["restaurants"] = ranked_categories.get("restaurant", [])
                    results["shopping"] = []  # เคลียร์ shopping เพราะรวมเข้า tourism แล้ว
                
                print(f"ใช้ข้อมูลจาก Cache สำหรับ {province}")
            else:
                try:
                    # 2. หากไม่มีใน Cache หรือ Cache หมดอายุ ให้ดึงข้อมูลจาก API
                    tourism_places = get_combined_tourism(province, 6)
                    hotels = get_nominatim_places(province, "hotel", 6)
                    restaurants = get_nominatim_places(province, "restaurant", 6)
                    shopping = get_nominatim_places(province, "shopping center", 4)
                    
                    # 3. เพิ่มข้อมูลคุณภาพอากาศและรวม shopping เข้าใน tourism
                    all_places = []
                    
                    # รวม tourism และ shopping เข้าด้วยกัน
                    combined_tourism = []
                    if tourism_places:
                        tourism_places = enrich_places_with_air_quality(tourism_places)
                        combined_tourism.extend(tourism_places)
                        all_places.extend(tourism_places)
                    if shopping:
                        shopping = enrich_places_with_air_quality(shopping)
                        # เปลี่ยน type เป็น attraction เพื่อให้รวมกับสถานที่ท่องเที่ยว
                        for place in shopping:
                            place['type'] = 'attraction'
                        combined_tourism.extend(shopping)
                        all_places.extend(shopping)
                    
                    # ลบสถานที่ซ้ำจาก combined_tourism
                    combined_tourism = remove_duplicates(combined_tourism)
                    
                    if hotels:
                        hotels = enrich_places_with_air_quality(hotels)
                        # ลบสถานที่ซ้ำจาก hotels
                        hotels = remove_duplicates(hotels)
                        all_places.extend(hotels)
                    if restaurants:
                        restaurants = enrich_places_with_air_quality(restaurants)
                        # ลบสถานที่ซ้ำจาก restaurants  
                        restaurants = remove_duplicates(restaurants)
                        all_places.extend(restaurants)
                    
                    # จัดอันดับแยกตามประเภท
                    if all_places:
                        ranked_categories = rank_places_by_category_and_dust(all_places, sort_by_dust)
                        combined_tourism = ranked_categories.get("attraction", [])
                        hotels = ranked_categories.get("hotel", [])
                        restaurants = ranked_categories.get("restaurant", [])

                    results = {
                        "tourism": combined_tourism,
                        "hotels": hotels,
                        "restaurants": restaurants,
                        "shopping": [],  # เก็บไว้เป็น empty list เพื่อ backward compatibility
                    }
                    
                    total_results = sum(len(places) for key, places in results.items() if key != "total_count")
                    results["total_count"] = total_results

                    save_to_cache(province, results)
                    
                    if enable_time_series:
                        try:
                            print(f"เริ่มวิเคราะห์ Time Series สำหรับ {province}")
                            
                            # ใช้เฉพาะโหมด forecast
                            time_series_data = get_forecast_data(province, int(forecast_days), "daily")
                            
                            if time_series_data:
                                real_data_count = sum(1 for item in time_series_data if item.get('source') == 'api_realtime')
                                cached_data_count = sum(1 for item in time_series_data if item.get('source') == 'cache')
                                simulated_data_count = sum(1 for item in time_series_data if item.get('source') in ['generated_realistic', 'calculated_forecast'])
                                
                                metric = 'aqi' if sort_by_dust == 'aqius' else sort_by_dust
                                time_series_analysis = analyze_time_series_ranking(time_series_data, metric)
                                
                                results['time_series'] = {
                                    'enabled': True,
                                    'mode': 'forecast',
                                    'forecast_days': forecast_days,
                                    'interval': 'daily',
                                    'analysis': time_series_analysis,
                                    'raw_data': time_series_data,
                                    'data_statistics': {
                                        'total_records': len(time_series_data),
                                        'real_data_count': real_data_count,
                                        'cached_data_count': cached_data_count,
                                        'simulated_data_count': simulated_data_count
                                    },
                                    'real_data_count': real_data_count
                                }
                                
                                print(f"วิเคราะห์ Time Series เสร็จสิ้น")
                                print(f"  ข้อมูลทั้งหมด: {len(time_series_data)} รายการ")
                                print(f"  ข้อมูลจริง: {real_data_count} รายการ")
                                print(f"  ข้อมูล cache: {cached_data_count} รายการ")
                                print(f"  ข้อมูลจำลอง: {simulated_data_count} รายการ")
                            else:
                                results['time_series'] = {
                                    'enabled': True,
                                    'error': 'ไม่สามารถดึงข้อมูล Time Series ได้'
                                }
                        except Exception as ts_error:
                            print(f"เกิดข้อผิดพลาดใน Time Series: {ts_error}")
                            results['time_series'] = {
                                'enabled': True,
                                'error': f'เกิดข้อผิดพลาด: {str(ts_error)}'
                            }
                    else:
                        results['time_series'] = {'enabled': False}
                    
                except Exception as e:
                    error_message = f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"
                    results = {}

    return render_template("index_moss.html", 
                           province=province, 
                           results=results, 
                           error_message=error_message,
                           sort_by_dust=sort_by_dust,
                           enable_time_series=enable_time_series,
                           forecast_days=forecast_days)
    
@app.route("/api/air-quality/<float:lat>/<float:lon>")
def get_air_quality_api(lat, lon):
    """API endpoint สำหรับดึงข้อมูลคุณภาพอากาศตามพิกัด"""
    try:
        air_quality = get_air_quality_by_coordinates(lat, lon)
        
        if air_quality and air_quality.get('pollution'):
            aqi = air_quality['pollution'].get('aqius', 0)
            pm25 = air_quality['pollution'].get('p2', 0)
            pm10 = air_quality['pollution'].get('p1', 0)
            level, description = get_aqi_level_description(aqi)
            
            return jsonify({
                'success': True,
                'data': {
                    'aqi': aqi,
                    'pm25': pm25,
                    'pm10': pm10,
                    'level': level,
                    'description': description,
                    'city': air_quality.get('city', 'ไม่ระบุ'),
                    'weather': air_quality.get('weather', {})
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'ไม่สามารถดึงข้อมูลคุณภาพอากาศได้'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
        
@app.route("/api/search")
def search_places():
    """API endpoint สำหรับค้นหาสถานที่ (ไม่ได้ใช้ในหน้าหลักโดยตรง แต่มีไว้สำหรับ API call)"""
    province = request.args.get('province', '').strip()
    place_type = request.args.get('type', 'tourism')
    limit = int(request.args.get('limit', 5))
    
    if not province:
        return jsonify({
            'success': False,
            'error': 'กรุณาระบุชื่อจังหวัด'
        })
    
    try:
        province = normalize_province_name(province)
        
        if place_type == 'tourism':
            places = get_combined_tourism(province, limit)
        else:
            places = get_nominatim_places(province, place_type, limit)
        
        places = enrich_places_with_air_quality(places)

        return jsonify({
            'success': True,
            'data': places,
            'count': len(places)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route("/about")
def about():
    return render_template('about.html', datetime=get_datetime())

@app.errorhandler(404)
def not_found(error):
    """จัดการข้อผิดพลาด 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """จัดการข้อผิดพลาด 500"""
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(debug=True)