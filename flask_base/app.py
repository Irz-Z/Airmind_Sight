from flask import Flask, render_template, request, jsonify
import json
import os
from utils import (
    normalize_province_name,
    get_nominatim_places,
    get_air_quality_by_coordinates,
    get_aqi_level_description,
    remove_duplicates,
    get_combined_tourism,
    enrich_places_with_air_quality, # Imported from utils.py
    load_from_cache,
    save_to_cache,
    rank_places_by_dust, # Imported from utils.py
    get_time_series_data,
    analyze_time_series_ranking,
    get_forecast_data
)

app = Flask(__name__)

def add_ranking_to_places(places):
    """Add a 'rank' field to each place based on its order in the list (1-based)."""
    for idx, place in enumerate(places):
        place['rank'] = idx + 1
    return places

@app.route("/", methods=["GET", "POST"])
def index():
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
    time_mode = "historical"
    start_date = ""
    end_date = ""
    forecast_days = "5"
    time_interval = "daily"

    # Read parameters from form on POST, from args on GET
    if request.method == "POST":
        sort_by_dust = request.form.get("sort_by_dust", "aqius")
        enable_time_series = request.form.get("enable_time_series") == "true"
        time_mode = request.form.get("time_mode", "historical")
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")
        forecast_days = request.form.get("forecast_days", "5")
        time_interval = request.form.get("time_interval", "daily")
    else:
        sort_by_dust = request.args.get("sort_by_dust", "aqius")
        enable_time_series = request.args.get("enable_time_series") == "true"
        time_mode = request.args.get("time_mode", "historical")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        forecast_days = request.args.get("forecast_days", "5")
        time_interval = request.args.get("time_interval", "daily")

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
                # หากโหลดจาก Cache ได้ ให้ทำการ enrich และ rank ใหม่
                if results.get("tourism"):
                    results["tourism"] = enrich_places_with_air_quality(results["tourism"])
                    results["tourism"] = rank_places_by_dust(results["tourism"], sort_by_dust)
                    results["tourism"] = add_ranking_to_places(results["tourism"])
                if results.get("hotels"):
                    results["hotels"] = enrich_places_with_air_quality(results["hotels"])
                    results["hotels"] = rank_places_by_dust(results["hotels"], sort_by_dust)
                    results["hotels"] = add_ranking_to_places(results["hotels"])
                if results.get("restaurants"):
                    results["restaurants"] = enrich_places_with_air_quality(results["restaurants"])
                    results["restaurants"] = rank_places_by_dust(results["restaurants"], sort_by_dust)
                    results["restaurants"] = add_ranking_to_places(results["restaurants"])
                if results.get("shopping"):
                    results["shopping"] = enrich_places_with_air_quality(results["shopping"])
                    results["shopping"] = rank_places_by_dust(results["shopping"], sort_by_dust)
                    results["shopping"] = add_ranking_to_places(results["shopping"])
                print(f"✅ ใช้ข้อมูลจาก Cache สำหรับ {province}")
            else:
                try:
                    # 2. หากไม่มีใน Cache หรือ Cache หมดอายุ ให้ดึงข้อมูลจาก API
                    # get_combined_tourism ได้รวมสถานที่ท่องเที่ยวและวัดเข้าด้วยกันแล้ว
                    tourism_places = get_combined_tourism(province, 6)
                    hotels = get_nominatim_places(province, "hotel", 6)
                    restaurants = get_nominatim_places(province, "restaurant", 6)
                    shopping = get_nominatim_places(province, "shopping center", 4)
                    
                    # 3. เพิ่มข้อมูลคุณภาพอากาศและจัดเรียงสถานที่ท่องเที่ยวตามค่าฝุ่น
                    if tourism_places:
                        tourism_places = enrich_places_with_air_quality(tourism_places)
                        tourism_places = rank_places_by_dust(tourism_places, sort_by_dust)
                        tourism_places = add_ranking_to_places(tourism_places)
                    if hotels:
                        hotels = enrich_places_with_air_quality(hotels)
                        hotels = rank_places_by_dust(hotels, sort_by_dust)
                        hotels = add_ranking_to_places(hotels)
                    if restaurants:
                        restaurants = enrich_places_with_air_quality(restaurants)
                        restaurants = rank_places_by_dust(restaurants, sort_by_dust)
                        restaurants = add_ranking_to_places(restaurants)
                    if shopping:
                        shopping = enrich_places_with_air_quality(shopping)
                        shopping = rank_places_by_dust(shopping, sort_by_dust)
                        shopping = add_ranking_to_places(shopping)

                    results = {
                        "tourism": tourism_places,
                        "hotels": hotels,
                        "restaurants": restaurants,
                        "shopping": shopping,
                        # ไม่ต้องมี "temples" แยกต่างหากแล้ว เพราะรวมอยู่ใน "tourism"
                    }
                    
                    # นับจำนวนผลลัพธ์ทั้งหมด
                    total_results = sum(len(places) for key, places in results.items() if key != "total_count")
                    results["total_count"] = total_results

                    # 4. บันทึกข้อมูลลง Cache สำหรับการค้นหาครั้งถัดไป
                    save_to_cache(province, results)
                    
                    # 5. หากเปิดใช้งาน Time Series ให้ดำเนินการวิเคราะห์
                    if enable_time_series:
                        try:
                            print(f"📊 เริ่มวิเคราะห์ Time Series สำหรับ {province}")
                            
                            if time_mode == "forecast":
                                # การพยากรณ์อากาศ
                                time_series_data = get_forecast_data(province, int(forecast_days), time_interval)
                            else:
                                # ข้อมูลย้อนหลังหรือกำหนดเอง
                                if not start_date or not end_date:
                                    # กำหนดค่าเริ่มต้นหากไม่ได้ระบุ
                                    import datetime
                                    end_date = datetime.date.today().strftime('%Y-%m-%d')
                                    start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                                
                                time_series_data = get_time_series_data(province, start_date, end_date, time_interval)
                            
                            if time_series_data:
                                # นับจำนวนข้อมูลจริงและข้อมูลจำลอง
                                real_data_count = sum(1 for item in time_series_data if item.get('source') == 'api_realtime')
                                cached_data_count = sum(1 for item in time_series_data if item.get('source') == 'cache')
                                simulated_data_count = sum(1 for item in time_series_data if item.get('source') in ['generated_realistic', 'calculated_forecast'])
                                
                                # วิเคราะห์การจัดอันดับ
                                metric = 'aqi' if sort_by_dust == 'aqius' else sort_by_dust
                                time_series_analysis = analyze_time_series_ranking(time_series_data, metric)
                                
                                # เพิ่มผลการวิเคราะห์ time series ลงใน results
                                results['time_series'] = {
                                    'enabled': True,
                                    'mode': time_mode,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'forecast_days': forecast_days,
                                    'interval': time_interval,
                                    'analysis': time_series_analysis,
                                    'raw_data': time_series_data,
                                    'data_statistics': {
                                        'total_records': len(time_series_data),
                                        'real_data_count': real_data_count,
                                        'cached_data_count': cached_data_count,
                                        'simulated_data_count': simulated_data_count
                                    },
                                    'real_data_count': real_data_count  # เพื่อแสดงใน template
                                }
                                
                                print(f"✅ วิเคราะห์ Time Series เสร็จสิ้น")
                                print(f"  📊 ข้อมูลทั้งหมด: {len(time_series_data)} รายการ")
                                print(f"  🌐 ข้อมูลจริง: {real_data_count} รายการ")
                                print(f"  📁 ข้อมูล cache: {cached_data_count} รายการ")
                                print(f"  🔄 ข้อมูลจำลอง: {simulated_data_count} รายการ")
                            else:
                                results['time_series'] = {
                                    'enabled': True,
                                    'error': 'ไม่สามารถดึงข้อมูล Time Series ได้'
                                }
                        except Exception as ts_error:
                            print(f"❌ เกิดข้อผิดพลาดใน Time Series: {ts_error}")
                            results['time_series'] = {
                                'enabled': True,
                                'error': f'เกิดข้อผิดพลาด: {str(ts_error)}'
                            }
                    else:
                        results['time_series'] = {'enabled': False}
                    
                except Exception as e:
                    error_message = f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"
                    results = {}

    return render_template("index.html", 
                           province=province, 
                           results=results, 
                           error_message=error_message,
                           sort_by_dust=sort_by_dust,
                           enable_time_series=enable_time_series,
                           time_mode=time_mode,
                           start_date=start_date,
                           end_date=end_date,
                           forecast_days=forecast_days,
                           time_interval=time_interval) # ส่งค่า parameters ไปยัง template

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
            # ใช้ get_combined_tourism ที่รวมวัดแล้ว
            places = get_combined_tourism(province, limit)
        else:
            places = get_nominatim_places(province, place_type, limit)
        
        # เพิ่มข้อมูลคุณภาพอากาศให้กับผลลัพธ์ API ด้วย
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

@app.errorhandler(404)
def not_found(error):
    """จัดการข้อผิดพลาด 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """จัดการข้อผิดพลาด 500"""
    return render_template('500.html'), 500

if __name__ == "__main__":
    # ตรวจสอบให้แน่ใจว่ามีโฟลเดอร์ cache ก่อนรันแอป
    os.makedirs('cache', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
