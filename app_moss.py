from flask import Flask, render_template, request, jsonify
import json
import os
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

app = Flask(__name__)

def add_ranking_to_places(places):
    """Add a 'rank' field to each place based on its order in the list (1-based)."""
    for idx, place in enumerate(places):
        place['rank'] = idx + 1
    return places

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
                # หากโหลดจาก Cache ได้ ให้ทำการ enrich และ rank ใหม่แบบแยกประเภท
                all_places = []
                if results.get("tourism"):
                    results["tourism"] = enrich_places_with_air_quality(results["tourism"])
                    all_places.extend(results["tourism"])
                if results.get("hotels"):
                    results["hotels"] = enrich_places_with_air_quality(results["hotels"])
                    all_places.extend(results["hotels"])
                if results.get("restaurants"):
                    results["restaurants"] = enrich_places_with_air_quality(results["restaurants"])
                    all_places.extend(results["restaurants"])
                if results.get("shopping"):
                    results["shopping"] = enrich_places_with_air_quality(results["shopping"])
                    all_places.extend(results["shopping"])
                
                # จัดอันดับแยกตามประเภท
                if all_places:
                    ranked_categories = rank_places_by_category_and_dust(all_places, sort_by_dust)
                    results["tourism"] = ranked_categories.get("attraction", [])
                    results["hotels"] = ranked_categories.get("hotel", [])
                    results["restaurants"] = ranked_categories.get("restaurant", [])
                
                print(f"ใช้ข้อมูลจาก Cache สำหรับ {province}")
            else:
                try:
                    # 2. หากไม่มีใน Cache หรือ Cache หมดอายุ ให้ดึงข้อมูลจาก API
                    tourism_places = get_combined_tourism(province, 6)
                    hotels = get_nominatim_places(province, "hotel", 6)
                    restaurants = get_nominatim_places(province, "restaurant", 6)
                    shopping = get_nominatim_places(province, "shopping center", 4)
                    
                    # 3. เพิ่มข้อมูลคุณภาพอากาศและจัดเรียงสถานที่แยกตามประเภท
                    all_places = []
                    if tourism_places:
                        tourism_places = enrich_places_with_air_quality(tourism_places)
                        tourism_places = remove_duplicates(tourism_places)  # ลบข้อมูลซ้ำ
                        all_places.extend(tourism_places)
                    if hotels:
                        hotels = enrich_places_with_air_quality(hotels)
                        hotels = remove_duplicates(hotels)  # ลบข้อมูลซ้ำ
                        all_places.extend(hotels)
                    if restaurants:
                        restaurants = enrich_places_with_air_quality(restaurants)
                        restaurants = remove_duplicates(restaurants)  # ลบข้อมูลซ้ำ
                        all_places.extend(restaurants)
                    if shopping:
                        shopping = enrich_places_with_air_quality(shopping)
                        shopping = remove_duplicates(shopping)  # ลบข้อมูลซ้ำ
                        all_places.extend(shopping)
                    
                    # จัดอันดับแยกตามประเภท
                    if all_places:
                        ranked_categories = rank_places_by_category_and_dust(all_places, sort_by_dust)
                        tourism_places = ranked_categories.get("attraction", [])
                        hotels = ranked_categories.get("hotel", [])
                        restaurants = ranked_categories.get("restaurant", [])
                        shopping = ranked_categories.get("attraction", [])  # shopping มักจะเป็น attraction
                    
                    results = {
                        "tourism": tourism_places,
                        "hotels": hotels,
                        "restaurants": restaurants,
                        "shopping": shopping,
                    }
                    
                    total_results = sum(len(places) for key, places in results.items() if key != "total_count")
                    results["total_count"] = total_results

                    save_to_cache(province, results)
                    
                    if enable_time_series:
                        try:
                            print(f"เริ่มวิเคราะห์ Time Series สำหรับ {province}")
                            
                            if time_mode == "forecast":
                                time_series_data = get_forecast_data(province, int(forecast_days), time_interval)
                            else:
                                if not start_date or not end_date:
                                    import datetime
                                    end_date = datetime.date.today().strftime('%Y-%m-%d')
                                    start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                                
                                time_series_data = get_time_series_data(province, start_date, end_date, time_interval)
                            
                            if time_series_data:
                                real_data_count = sum(1 for item in time_series_data if item.get('source') == 'api_realtime')
                                cached_data_count = sum(1 for item in time_series_data if item.get('source') == 'cache')
                                simulated_data_count = sum(1 for item in time_series_data if item.get('source') in ['generated_realistic', 'calculated_forecast'])
                                
                                metric = 'aqi' if sort_by_dust == 'aqius' else sort_by_dust
                                time_series_analysis = analyze_time_series_ranking(time_series_data, metric)
                                
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
                                    'real_data_count': real_data_count
                                }
                                
                                # Replace tourism results with time series rankings when time series is enabled
                                if time_series_analysis and time_series_analysis.get('rankings'):
                                    time_series_places = []
                                    
                                    # Create detailed forecast data for each place from time_series_data
                                    forecast_by_place = {}
                                    for ts_data in time_series_data:
                                        place_name = ts_data['place_name']
                                        if place_name not in forecast_by_place:
                                            forecast_by_place[place_name] = []
                                        forecast_by_place[place_name].append(ts_data)
                                    
                                    for rank_data in time_series_analysis['rankings']:
                                        place_forecast_data = forecast_by_place.get(rank_data['name'], [])
                                        place = {
                                            'name': rank_data['name'],
                                            'lat': rank_data['lat'],
                                            'lon': rank_data['lon'],
                                            'full_address': f"{rank_data['name']}, {rank_data['city']}",
                                            'rank': rank_data['rank'],
                                            'air_quality': {
                                                'aqi': int(rank_data['average']) if metric == 'aqi' else None,
                                                'pm25': int(rank_data['average']) if metric == 'pm25' else None,
                                                'pm10': int(rank_data['average']) if metric == 'pm10' else None,
                                                'level': 'Time Series Average',
                                                'description': f"เฉลี่ย: {rank_data['average']}, ต่ำสุด: {rank_data['minimum']}, สูงสุด: {rank_data['maximum']}",
                                                'city': rank_data['city']
                                            },
                                            'time_series_stats': {
                                                'average': rank_data['average'],
                                                'minimum': rank_data['minimum'],
                                                'maximum': rank_data['maximum'],
                                                'data_points': rank_data['data_points'],
                                                'medal': rank_data.get('medal', '')
                                            },
                                            'forecast_data': place_forecast_data
                                        }
                                        time_series_places.append(place)
                                    # แยก Top 3 และที่เหลือ
                                    results['top_3_places'] = time_series_places[:3]
                                    results['other_places'] = time_series_places[3:]
                                    
                                    # Replace tourism with time series results
                                    results["tourism"] = time_series_places
                                    results["hotels"] = []
                                    results["restaurants"] = []
                                    results["shopping"] = []
                                    results["total_count"] = len(time_series_places)
                                
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
                           time_mode=time_mode,
                           start_date=start_date,
                           end_date=end_date,
                           forecast_days=forecast_days,
                           time_interval=time_interval)

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
        places = remove_duplicates(places)  # ลบข้อมูลซ้ำ

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
    os.makedirs('cache', exist_ok=True)
    app.run(debug=True)