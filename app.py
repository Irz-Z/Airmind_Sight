from flask import Flask, request, jsonify, render_template
import requests
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fetch_data import *

app = Flask(__name__)

# IQAIR
API_KEY = '0199d98b-12a7-4ea8-8ef8-674a08a79ce7' # pppurpg@gmail.com
# API_KEY = 'c926d92f-7623-4d75-81dd-7c5542c59e5e' # adisonbb2@gmail.com

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

@app.route('/')
def index():
    return render_template('index.html')

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
def get_forecast_data():
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

if __name__ == '__main__':
    app.run(debug=True)