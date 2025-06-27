// Global variables
const searchCache = new Map();
const requestTimestamps = [];
const MAX_REQUESTS_PER_MINUTE = 10;
let suggestionBox = null;

// AQICN API Key - Replace with your actual API key
//2ef3a30d49f442f000c799d495a0f050e0109602
const AQICN_API_KEY = '2ef3a30d49f442f000c799d495a0f050e0109602'; // Get your key from https://aqicn.org/api/

// DOM Elements utility function
function getElements() {
    return {
        placeTitle: document.getElementById('place-title'),
        weatherTemp: document.getElementById('weather-temp'),
        weatherDetail: document.getElementById('weather-detail'),
        weatherFeels: document.getElementById('weather-feels'),
        weatherRain: document.getElementById('weather-rain'),
        weatherHumidity: document.getElementById('weather-humidity'),
        weatherWind: document.getElementById('weather-wind'),
        forecastGraph: document.getElementById('forecast-graph'),
        dateText: document.getElementById('date-text'),
        timeText: document.getElementById('time-text')
    };
}

// Direct weather data fetch using AQICN
async function fetchWeatherData(place) {
    try {
        // Try searching by city name first
        const cityUrl = `https://api.waqi.info/feed/${encodeURIComponent(place)}/?token=${AQICN_API_KEY}`;
        const response = await fetch(cityUrl);
        const data = await response.json();
        
        if (data.status === 'ok' && data.data) {
            return data;
        }

        // If city search fails, do not fallback to Bangkok, just return null
        return null;
    } catch (error) {
        console.error('Weather fetch failed:', error);
        return null;
    }
}

// Weather data handling
async function loadWeatherAndLocation() {
    const elements = getElements();
    
    if (!elements.placeTitle || !elements.weatherTemp) {
        console.warn('Required DOM elements not found');
        return;
    }

    const place = new URLSearchParams(window.location.search).get('place');
    if (!place) {
        updateUIWithError(elements, 'ไม่พบข้อมูลสถานที่');
        return;
    }

    updateUIWithLoading(elements, place);

    try {
        const weatherData = await fetchWeatherData(place);
        if (!weatherData || !weatherData.data) {
            updateUIWithError(elements, 'ไม่พบข้อมูล');
            return;
        }
        updateUIWithWeatherData(elements, weatherData.data);
    } catch (error) {
        console.error('Error loading weather data:', error);
        updateUIWithError(elements, 'ไม่สามารถโหลดข้อมูลได้');
    }
}

function updateUIWithWeatherData(elements, data) {
    if (!data) return;

    // Use only province or city name for display, not the full station name
    let displayName = '';
    if (data.city && data.city.name) {
        // Try to extract province or district from the city name
        // Example: "Municipal Waste Water Pumping Station, Nakhon Ratchasima, Thailand"
        // We want only "Nakhon Ratchasima" (province/city)
        const parts = data.city.name.split(',').map(s => s.trim());
        if (parts.length >= 2) {
            // Use the second part (province/city)
            displayName = parts[parts.length - 2];
        } else {
            displayName = data.city.name;
        }
    }
    if (elements.placeTitle) elements.placeTitle.textContent = displayName || data.city.name;
    if (elements.weatherTemp) {
        const temp = data.iaqi.t ? Math.round(data.iaqi.t.v) : '--';
        elements.weatherTemp.textContent = `${temp}°C`;
    }
    if (elements.weatherDetail) elements.weatherDetail.textContent = getAQIDescription(data.aqi);
    if (elements.weatherFeels) {
        const feelsLike = data.iaqi.t ? Math.round(data.iaqi.t.v) : '--';
        elements.weatherFeels.textContent = `Feels like ${feelsLike}°C`;
    }
    if (elements.weatherHumidity) {
        const humidity = data.iaqi.h ? Math.round(data.iaqi.h.v) : '--';
        elements.weatherHumidity.textContent = `Humidity: ${humidity}%`;
    }
    if (elements.weatherWind) {
        const wind = data.iaqi.w ? Math.round(data.iaqi.w.v) : '--';
        elements.weatherWind.textContent = `Wind: ${wind} km/hr`;
    }
    if (elements.forecastGraph) {
        updateForecastGraph(elements.forecastGraph, data);
    }
}

function getAQIDescription(aqi) {
    if (!aqi) return 'ไม่มีข้อมูล AQI';
    
    if (aqi <= 50) return 'คุณภาพอากาศดี';
    if (aqi <= 100) return 'คุณภาพอากาศปานกลาง';
    if (aqi <= 150) return 'คุณภาพอากาศไม่ดีต่อกลุ่มเสี่ยง';
    if (aqi <= 200) return 'คุณภาพอากาศไม่ดี';
    if (aqi <= 300) return 'คุณภาพอากาศไม่ดีมาก';
    return 'คุณภาพอากาศอันตราย';
}

function updateForecastGraph(graphElement, data) {
    // Simple text representation for now
    graphElement.textContent = `AQI: ${data.aqi} - ${getAQIDescription(data.aqi)}`;
}

function updateUIWithLoading(elements, place) {
    if (elements.placeTitle) elements.placeTitle.textContent = place;
    if (elements.weatherDetail) elements.weatherDetail.textContent = 'กำลังโหลดข้อมูล...';
    
    ['weatherTemp', 'weatherFeels', 'weatherRain', 'weatherHumidity', 'weatherWind'].forEach(id => {
        if (elements[id]) elements[id].textContent = '--';
    });
}

function updateUIWithError(elements, message) {
    if (elements.placeTitle) elements.placeTitle.textContent = message;
    if (elements.weatherDetail) elements.weatherDetail.textContent = message;
    
    ['weatherTemp', 'weatherFeels', 'weatherRain', 'weatherHumidity', 'weatherWind'].forEach(id => {
        if (elements[id]) elements[id].textContent = '--';
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Update date/time
    updateDateTime();
    setInterval(updateDateTime, 1000);
    
    // Load weather data
    loadWeatherAndLocation();
    
    // Initialize search box
    const searchBox = document.getElementById('search-box');
    if (searchBox) {
        const place = new URLSearchParams(window.location.search).get('place');
        if (place) searchBox.value = place;
    }
});

// Time and date handling
function updateDateTime() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    const elements = getElements();
    const dayElement = document.querySelector('.hero-title + div');
    
    if (dayElement) dayElement.textContent = days[now.getDay()];
    if (elements.dateText) {
        elements.dateText.textContent = `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
    }
    if (elements.timeText) {
        elements.timeText.textContent = now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
}