// สร้างแผนที่
const map = L.map('map').setView([13.736717, 100.523186], 6);
const sidePopup = document.getElementById('side-popup');
const provinceTH = {
  "Amnat Charoen": "อำนาจเจริญ",
  "Ang Thong": "อ่างทอง",
  "Bangkok": "กรุงเทพมหานคร",
  "Buriram": "บุรีรัมย์",
  "Chachoengsao": "ฉะเชิงเทรา",
  "Chai Nat": "ชัยนาท",
  "Chaiyaphum": "ชัยภูมิ",
  "Changwat Bueng Kan": "บึงกาฬ",
  "Changwat Ubon Ratchathani": "อุบลราชธานี",
  "Chanthaburi": "จันทบุรี",
  "Chiang Mai": "เชียงใหม่",
  "Chiang Rai": "เชียงราย",
  "Chon Buri": "ชลบุรี",
  "Chumphon": "ชุมพร",
  "Kalasin": "กาฬสินธุ์",
  "Kamphaeng Phet": "กำแพงเพชร",
  "Kanchanaburi": "กาญจนบุรี",
  "Khon Kaen": "ขอนแก่น",
  "Krabi": "กระบี่",
  "Lampang": "ลำปาง",
  "Lamphun": "ลำพูน",
  "Loei": "เลย",
  "Lopburi": "ลพบุรี",
  "Mae Hong Son": "แม่ฮ่องสอน",
  "Maha Sarakham": "มหาสารคาม",
  "Mukdahan": "มุกดาหาร",
  "Nakhon Nayok": "นครนายก",
  "Nakhon Pathom": "นครปฐม",
  "Nakhon Phanom": "นครพนม",
  "Nakhon Ratchasima": "นครราชสีมา",
  "Nakhon Sawan": "นครสวรรค์",
  "Nakhon Si Thammarat": "นครศรีธรรมราช",
  "Nan": "น่าน",
  "Narathiwat": "นราธิวาส",
  "Nong Bua Lamphu": "หนองบัวลำภู",
  "Nong Khai": "หนองคาย",
  "Nonthaburi": "นนทบุรี",
  "Pathum Thani": "ปทุมธานี",
  "Pattani": "ปัตตานี",
  "Phangnga": "พังงา",
  "Phatthalung": "พัทลุง",
  "Phayao": "พะเยา",
  "Phetchabun": "เพชรบูรณ์",
  "Phetchaburi": "เพชรบุรี",
  "Phichit": "พิจิตร",
  "Phitsanulok": "พิษณุโลก",
  "Phra Nakhon Si Ayutthaya": "พระนครศรีอยุธยา",
  "Phrae": "แพร่",
  "Phuket": "ภูเก็ต",
  "Prachin Buri": "ปราจีนบุรี",
  "Prachuap Khiri Khan": "ประจวบคีรีขันธ์",
  "Ranong": "ระนอง",
  "Ratchaburi": "ราชบุรี",
  "Rayong": "ระยอง",
  "Roi Et": "ร้อยเอ็ด",
  "Sa Kaeo": "สระแก้ว",
  "Sakon Nakhon": "สกลนคร",
  "Samut Prakan": "สมุทรปราการ",
  "Samut Sakhon": "สมุทรสาคร",
  "Samut Songkhram": "สมุทรสงคราม",
  "Sara Buri": "สระบุรี",
  "Satun": "สตูล",
  "Sing Buri": "สิงห์บุรี",
  "Sisaket": "ศรีสะเกษ",
  "Songkhla": "สงขลา",
  "Sukhothai": "สุโขทัย",
  "Suphan Buri": "สุพรรณบุรี",
  "Surat Thani": "สุราษฎร์ธานี",
  "Surin": "สุรินทร์",
  "Tak": "ตาก",
  "Trang": "ตรัง",
  "Trat": "ตราด",
  "Udon Thani": "อุดรธานี",
  "Uthai Thani": "อุทัยธานี",
  "Uttaradit": "อุตรดิตถ์",
  "Yala": "ยะลา",
  "Yasothon": "ยโสธร"
}
// ใช้ Tile จาก OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

function getAQIColor(aqi) {
  if (aqi == null) return '#cccccc';
  if (aqi <= 25) return '#4DC4EC';           // Very Good
  if (aqi <= 50) return '#8AC541';           // Good
  if (aqi <= 100) return '#FFEC00';          // Moderate
  if (aqi <= 200) return '#F7941D';          // Not good for your health
  return '#ED1C24';                          // Very Unhealthy
}

// Estimate PM2.5 from AQI (US standard)
function estimatePM25FromAQI(aqi) {
  if (!aqi || aqi <= 0) return 0;
  
  if (aqi <= 50) {
    return Math.round(aqi * 12 / 50);
  } else if (aqi <= 100) {
    return Math.round(12 + (aqi - 50) * (35.4 - 12) / 50);
  } else if (aqi <= 150) {
    return Math.round(35.4 + (aqi - 100) * (55.4 - 35.4) / 50);
  } else if (aqi <= 200) {
    return Math.round(55.4 + (aqi - 150) * (150.4 - 55.4) / 50);
  } else if (aqi <= 300) {
    return Math.round(150.4 + (aqi - 200) * (250.4 - 150.4) / 100);
  } else {
    return Math.round(250.4 + (aqi - 300) * 100 / 100);
  }
}

// Estimate PM10 from AQI (US standard)
function estimatePM10FromAQI(aqi) {
  if (!aqi || aqi <= 0) return 0;
  
  if (aqi <= 50) {
    return Math.round(aqi * 54 / 50);
  } else if (aqi <= 100) {
    return Math.round(55 + (aqi - 50) * (154 - 55) / 50);
  } else if (aqi <= 150) {
    return Math.round(155 + (aqi - 100) * (254 - 155) / 50);
  } else if (aqi <= 200) {
    return Math.round(255 + (aqi - 150) * (354 - 255) / 50);
  } else if (aqi <= 300) {
    return Math.round(355 + (aqi - 200) * (424 - 355) / 100);
  } else {
    return Math.round(425 + (aqi - 300) * 75 / 100);
  }
}

fetch('/data')
  .then(response => response.json())
  .then(data => {
    if (data.status !== "success") return;
    Object.entries(data.data).forEach(([province, info]) => {
      if (
        info.data &&
        info.data.location &&
        info.data.location.coordinates &&
        info.data.current &&
        info.data.current.pollution
      ) {
        const [lng, lat] = info.data.location.coordinates;
        const aqi = info.data.current.pollution.aqius;

        // สร้าง DivIcon ที่มีค่า AQI อยู่บน marker
        const aqiIcon = L.divIcon({
          className: 'aqi-marker',
          html: `<div style="
            background:${getAQIColor(aqi)};
            border:2px solid #000000;
            border-radius:50%;
            width:36px;
            height:36px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:bold;
            color: #000000;
            font-size:14px;
            box-shadow:0 2px 6px rgba(0,0,0,0.2);
          ">${aqi}</div>`,
          iconSize: [36, 36],
          iconAnchor: [18, 36],
          popupAnchor: [0, -36]
        });
        
        // แก้ไข: เพิ่ม { icon: aqiIcon } เพื่อใช้ custom icon
        const marker = L.marker([lat, lng], { icon: aqiIcon }).addTo(map);
        const provinceNameTH = provinceTH[province] || province;
        marker.bindPopup(
          `<div class="custom-popup"><strong>${provinceNameTH}</strong><br/>AQI : ${aqi}</div>`
        );
        marker.on('mouseover', function(e) {
          this.openPopup();
        });
        marker.on('mouseout', function(e) {
          this.closePopup();
        });
        marker.on('click', function(e) {
          // Calculate estimated PM values from AQI
          const estimatedPM25 = estimatePM25FromAQI(aqi);
          const estimatedPM10 = estimatePM10FromAQI(aqi);

          sidePopup.classList.remove('hidden');
          sidePopup.innerHTML = `
            <button style="position: absolute; top: 6rem; right: 20px; border: 1px solid #0ea5e9; background: #f0f9ff;color: #000; font-size: 20px; cursor: pointer;" onclick="document.getElementById('side-popup').classList.add('hidden')">x</button>
            
            <br><h1 style="font-size:2rem;"><strong>${provinceNameTH}</strong></h1>

            <div style="background-color: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 12px; margin: 16px 0;">
              <h3 style="margin: 0 0 8px 0; color: #0ea5e9;">ข้อมูลเบื้องต้น</h3>
              <p style="margin: 4px 0;"><strong>Air Quality Index :</strong> ${aqi}</p>
              <p><strong>Latitude :</strong> ${lat.toFixed(4)}</p>
              <p><strong>Longitude :</strong> ${lng.toFixed(4)}</p>
            </div>

            <br><a href="https://www.iqair.com/th/?srsltid=AfmBOoqC9g9l7-OySMJWqAtXm0ovJP8cl29FuiIb1NoohXxAUwbe49sA" target="_blank">
                <img src="https://upload.wikimedia.org/wikipedia/en/thumb/5/5f/IQAir_logo.svg/2560px-IQAir_logo.svg.png" alt="IQAir Logo" style="height:40px; margin-bottom:10px;">
                </a>
            <div id="widget-container" style="margin-top: 20px;"></div>

            <br><a href="https://aqicn.org/city/bangkok/th/" target="_blank">
                <img src="https://avatars.githubusercontent.com/u/5398635?s=280&v=4" alt="aqicn Logo" style="height:40px; margin-bottom:10px;">
                </a>

            <fieldset style="margin-top: 16px;">
              <legend><strong>ตัวเลือกการแสดงข้อมูล:</strong></legend>
              <label><input type="checkbox" name="dataType" value="PM10" /> PM10 AQI</label>
              <label><input type="checkbox" name="dataType" value="PM2.5" checked /> PM2.5 AQI</label>
            </fieldset>

            <canvas id="forecast-chart" height="200" style="margin-top: 20px;"></canvas>
          `;
          fetch('/forecast')
            .then(res => res.json())
            .then(forecastData => {
              const forecast = forecastData.data[province];

              if (!forecast || forecast?.status === "error" || Object.keys(forecast).length === 0) {
                const warning = document.createElement('p');
                warning.textContent = 'ไม่มีข้อมูลการพยากรณ์';
                warning.style.color = 'red';
                warning.style.marginTop = '20px';

                // เพิ่มข้อความก่อน widget-container
                const widgetContainer = document.getElementById('widget-container');
                const aqicnLink = widgetContainer.parentNode.querySelector('a[href="https://aqicn.org/city/bangkok/th/"]');
                if (aqicnLink) {
                    widgetContainer.parentNode.insertBefore(warning, aqicnLink.nextSibling);
                } else {
                    widgetContainer.parentNode.insertBefore(warning, widgetContainer.nextSibling);
                }

                // ลบ canvas และ fieldset ถ้ามี
                const canvas = document.getElementById('forecast-chart');
                if (canvas) canvas.remove();
                const fieldset = document.querySelector('fieldset');
                if (fieldset) fieldset.remove();

                return;
              }
              
              // Update current air quality section with today's PM values
              const currentAirDiv = document.querySelector('div[style*="background: #f0f9ff"]');
              if (currentAirDiv && forecast.pm25 && forecast.pm25.length > 0 && forecast.pm10 && forecast.pm10.length > 0) {
                const todayPM25 = forecast.pm25[0]?.avg || 'N/A';
                const todayPM10 = forecast.pm10[0]?.avg || 'N/A';
                currentAirDiv.innerHTML = `
                  <h3 style="margin: 0 0 8px 0; color: #0ea5e9;">Current Air Quality</h3>
                  <p style="margin: 4px 0;"><strong>AQI:</strong> ${aqi}</p>
                  <p style="margin: 4px 0;"><strong>PM2.5:</strong> ${todayPM25} μg/m³</p>
                  <p style="margin: 4px 0;"><strong>PM10:</strong> ${todayPM10} μg/m³</p>
                `;
              }

              setTimeout(() => {
                const canvas = document.getElementById('forecast-chart');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                if (!ctx) return;

                createChart(forecast);
                document.querySelectorAll('input[name="dataType"]').forEach(input => {
                    input.addEventListener('change', () => createChart(forecast));
                });
              }, 10);
            });
            
          fetch('/static/province_widget.json') // ดึงข้อมูลจาก province_widget.json
            .then(response => response.json())
            .then(widgetKeyMap => {
              const widgetKey = widgetKeyMap[province]; // ใช้ข้อมูลจาก JSON
              if (widgetKey) {
                const widgetContainer = document.getElementById('widget-container');
                const widgetScript = document.createElement('script');
                widgetScript.type = 'text/javascript';
                widgetScript.src = `https://widget.iqair.com/script/widget_v3.0.js`;
                widgetContainer.innerHTML = `<div name="airvisual_widget" key="${widgetKey}"></div>`;
                widgetContainer.appendChild(widgetScript);
              }
            })
            .catch(error => {
              console.error('Error loading province_widget.json:', error);
            });
        });
        map.on('click', function(e) {
          // ซ่อน side-popup เมื่อคลิกบนแผนที่ที่ไม่ใช่ marker
          if (!sidePopup.classList.contains('hidden')) {
            sidePopup.classList.add('hidden');
          }
        });
      }
    });
  });





let chartInstance = null;

function createChart(forecast) {
  const selectedTypes = Array.from(document.querySelectorAll('input[name="dataType"]:checked'))
    .map(input => input.value.toLowerCase().replace('.', ''));

  const labels = forecast.pm25.map(entry => entry.day);

  const datasets = selectedTypes.map(type => {
    if (!forecast[type]) return null;
    return {
      label: type.toUpperCase(),
      data: forecast[type].map(entry => entry.avg),
      borderColor: randomColor(),
      fill: false
    };
  }).filter(Boolean);

  const ctx = document.getElementById('forecast-chart').getContext('2d');

  if (chartInstance) {
    chartInstance.destroy(); // ล้างกราฟเดิม
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom'
        },
        title: {
          display: true,
          text: 'Forecast Air Quality'
        }
      }
    }
  });
}

// สุ่มสีสำหรับแต่ละเส้น
function randomColor() {
  return `hsl(${Math.floor(Math.random() * 360)}, 70%, 50%)`;
}
