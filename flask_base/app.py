from flask import Flask, render_template, request, jsonify
import json
from utils import (
    normalize_province_name,
    get_nominatim_places,
    get_air_quality_by_coordinates,
    get_aqi_level_description,
    remove_duplicates
)

app = Flask(__name__)

def get_combined_tourism(province_name, limit=5):
    """รวมสถานที่ท่องเที่ยวจากหลายหมวด"""
    tourism_types = [
        ("tourism", "สถานที่ท่องเที่ยว"),
        ("attraction", "สถานที่น่าสนใจ"),
        ("viewpoint", "จุดชมวิว"),
        ("museum", "พิพิธภัณฑ์"),
        ("zoo", "สวนสัตว์")
    ]
    
    all_results = []
    
    for place_type, thai_name in tourism_types:
        places = get_nominatim_places(province_name, place_type, limit=3)
        all_results.extend(places)
        
        # หยุดเมื่อได้ครบตามที่กำหนด
        if len(all_results) >= limit:
            break
    
    # ลบข้อมูลซ้ำและจำกัดผลลัพธ์
    unique_results = remove_duplicates(all_results)
    return unique_results[:limit]

def enrich_places_with_air_quality(places):
    """เพิ่มข้อมูลคุณภาพอากาศให้กับสถานที่"""
    enriched_places = []
    
    for place in places:
        if place.get('lat') and place.get('lon'):
            # ดึงข้อมูลคุณภาพอากาศ
            air_quality = get_air_quality_by_coordinates(place['lat'], place['lon'])
            
            if air_quality and air_quality.get('pollution'):
                aqi = air_quality['pollution'].get('aqius', 0)
                level, description = get_aqi_level_description(aqi)
                
                place['air_quality'] = {
                    'aqi': aqi,
                    'level': level,
                    'description': description,
                    'city': air_quality.get('city', 'ไม่ระบุ')
                }
            else:
                place['air_quality'] = None
        
        enriched_places.append(place)
    
    return enriched_places

@app.route("/", methods=["GET", "POST"])
def index():
    province = ""
    results = {}
    error_message = ""
    
    if request.method == "POST":
        province_input = request.form.get("province", "").strip()
        
        if not province_input:
            error_message = "กรุณากรอกชื่อจังหวัด"
        else:
            province = normalize_province_name(province_input)
            
            try:
                # ค้นหาสถานที่ต่างๆ
                results["tourism"] = get_combined_tourism(province, 6)
                results["hotels"] = get_nominatim_places(province, "hotel", 6)
                results["restaurants"] = get_nominatim_places(province, "restaurant", 6)
                results["temples"] = get_nominatim_places(province, "place of worship", 4)
                results["shopping"] = get_nominatim_places(province, "shopping center", 4)
                
                # เพิ่มข้อมูลคุณภาพอากาศ (เฉพาะสถานที่ท่องเที่ยว)
                if results["tourism"]:
                    results["tourism"] = enrich_places_with_air_quality(results["tourism"])
                
                # นับจำนวนผลลัพธ์ทั้งหมด
                total_results = sum(len(places) for places in results.values())
                results["total_count"] = total_results
                
            except Exception as e:
                error_message = f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"
                results = {}

    return render_template("index.html", 
                         province=province, 
                         results=results, 
                         error_message=error_message)

@app.route("/api/air-quality/<float:lat>/<float:lon>")
def get_air_quality_api(lat, lon):
    """API endpoint สำหรับดึงข้อมูลคุณภาพอากาศ"""
    try:
        air_quality = get_air_quality_by_coordinates(lat, lon)
        
        if air_quality and air_quality.get('pollution'):
            aqi = air_quality['pollution'].get('aqius', 0)
            level, description = get_aqi_level_description(aqi)
            
            return jsonify({
                'success': True,
                'data': {
                    'aqi': aqi,
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
    """API endpoint สำหรับค้นหาสถานที่"""
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
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)