// สร้างแผนที่
const map = L.map('map').setView([13.736717, 100.523186], 6);
const sidePopup = document.getElementById('side-popup');

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
        
        marker.bindPopup(
          `<div class="custom-popup"><strong>${province}</strong><br/>PM2.5: ${aqi} AQI</div>`
        );
        marker.on('mouseover', function(e) {
          this.openPopup();
        });
        marker.on('mouseout', function(e) {
          this.closePopup();
        });
        marker.on('click', function(e) {
          sidePopup.classList.remove('hidden');
          sidePopup.innerHTML = `
            <button style="position: absolute; top: 10px; right: 20px; background: #00e4ff; font-size: 20px; cursor: pointer;" onclick="document.getElementById('side-popup').classList.add('hidden')">x</button>
            <h2>${province}</h2>
            <p><strong>PM2.5:</strong> ${aqi} AQI</p>
            <p><strong>Latitude:</strong> ${lat.toFixed(4)}</p>
            <p><strong>Longitude:</strong> ${lng.toFixed(4)}</p>
            
            <fieldset style="margin-top: 16px;">
              <legend><strong>ตัวเลือกการแสดงข้อมูล:</strong></legend>
              
              <label><input type="checkbox" name="dataType" value="PM10" /> PM10</label>
              <label><input type="checkbox" name="dataType" value="PM2.5" checked /> PM2.5</label>
              
            </fieldset>

            <canvas id="forecast-chart" height="200" style="margin-top: 20px;"></canvas>

            <div id="widget-container" style="margin-top: 20px;"></div>
          `;
          fetch('/forecast')
            .then(res => res.json())
            .then(forecastData => {
              const forecast = forecastData.data[province];

              if (!forecast || forecast?.status === "error" || Object.keys(forecast).length === 0) {
                const warning = document.createElement('p');
                warning.textContent = 'ไม่มีข้อมูล';
                warning.style.color = 'red';
                warning.style.marginTop = '20px';

                // เพิ่มข้อความก่อน widget-container
                const widgetContainer = document.getElementById('widget-container');
                sidePopup.insertBefore(warning, widgetContainer);

                // ลบ canvas และ fieldset ถ้ามี
                const canvas = document.getElementById('forecast-chart');
                if (canvas) canvas.remove();
                const fieldset = document.querySelector('fieldset');
                if (fieldset) fieldset.remove();

                return;
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
