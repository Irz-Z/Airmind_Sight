// Global variables for caching and rate limiting
const searchCache = new Map();
const requestTimestamps = [];
const MAX_REQUESTS_PER_MINUTE = 10;
let suggestionBox = null;

// Time and date handling
function updateDateTime() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    const dayElement = document.querySelector('.hero-title + div');
    const dateElement = document.getElementById('date-text');
    const timeElement = document.getElementById('time-text');
    
    if (dayElement) dayElement.textContent = days[now.getDay()];
    if (dateElement) {
        dateElement.textContent = `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
    }
    if (timeElement) {
        timeElement.textContent = now.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
}

// Start time updates
function initializeTimeUpdates() {
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

// Search functionality
function handleSearch(query) {
    const loadingAnimation = document.querySelector('.loading-animation');
    createSuggestionBox();
    
    if (query.length > 2) {
        if (!isRateLimited()) {
            loadingAnimation.style.display = 'block';
            
            if (searchCache.has(query)) {
                showSuggestions(searchCache.get(query), query);
                loadingAnimation.style.display = 'none';
                return;
            }
            
            const timeoutPromise = new Promise((resolve) => {
                setTimeout(() => resolve([]), 5000);
            });
            
            Promise.race([
                fetchSuggestions(query),
                timeoutPromise
            ]).then(suggestions => {
                searchCache.set(query, suggestions);
                showSuggestions(suggestions, query);
                loadingAnimation.style.display = 'none';
            }).catch(() => {
                loadingAnimation.style.display = 'none';
                showSuggestions(getFallbackSuggestions(), query);
            });
        } else {
            showRateLimitMessage();
        }
    } else {
        loadingAnimation.style.display = 'none';
        showSuggestions([], query);
    }
}

function createSuggestionBox() {
    if (!suggestionBox) {
        suggestionBox = document.createElement('div');
        suggestionBox.className = 'autocomplete-suggestions';
        suggestionBox.style.cssText = `
            position: absolute;
            left: 0;
            right: 0;
            top: 110%;
            background: #fff;
            border-radius: 0 0 18px 18px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.10);
            z-index: 1001;
            max-height: 220px;
            overflow-y: auto;
            display: none;
            font-size: 15px;
            padding: 0;
        `;
        const container = document.querySelector('.search-container');
        container.appendChild(suggestionBox);
    }
}

async function fetchSuggestions(query) {
    requestTimestamps.push(Date.now());
    
    const proxies = [
        "https://api.allorigins.win/raw?url=",
        "https://proxy.cors.sh/",
        "https://cors-anywhere.herokuapp.com/"
    ];
    
    const apiUrl = `https://nominatim.openstreetmap.org/search?country=Thailand&q=${encodeURIComponent(query)}&format=json&accept-language=th&addressdetails=1&limit=10`;
    
    for (const proxy of proxies) {
        try {
            const url = proxy + encodeURIComponent(apiUrl);
            const res = await fetch(url, {
                headers: {
                    'Origin': window.location.origin,
                    'x-requested-with': 'XMLHttpRequest'
                }
            });
            
            if (!res.ok) continue;
            
            const data = await res.json();
            return data.map(item => ({
                station: {
                    name: item.display_name,
                    city: item.address.county || item.address.city || item.address.town || '',
                    country: item.address.country || '',
                    province: item.address.state || '',
                    district: item.address.county || '',
                },
                aqi: ''
            }));
        } catch (e) {
            console.warn(`Proxy ${proxy} failed:`, e);
            continue;
        }
    }
    
    throw new Error('All proxies failed');
}

function getFallbackSuggestions() {
    return [
        {
            station: {
                name: 'กรุงเทพมหานคร, ประเทศไทย',
                city: 'กรุงเทพมหานคร',
                country: 'ประเทศไทย',
                province: 'กรุงเทพมหานคร',
                district: ''
            },
            aqi: ''
        },
        {
            station: {
                name: 'เชียงใหม่, ประเทศไทย',
                city: 'เชียงใหม่',
                country: 'ประเทศไทย',
                province: 'เชียงใหม่',
                district: ''
            },
            aqi: ''
        }
    ];
}

function isRateLimited() {
    const now = Date.now();
    while (requestTimestamps.length > 0 && requestTimestamps[0] < now - 60000) {
        requestTimestamps.shift();
    }
    return requestTimestamps.length >= MAX_REQUESTS_PER_MINUTE;
}

function showRateLimitMessage() {
    createSuggestionBox();
    suggestionBox.innerHTML = '<div class="suggestion-error">Too many searches. Please wait a moment before trying again.</div>';
    suggestionBox.style.display = 'block';
}

function showSuggestions(suggestions, query) {
    createSuggestionBox();
    suggestionBox.innerHTML = '';
    
    const filtered = (suggestions || []).filter(item => {
        const country = (item.station.country || '').toLowerCase();
        return country.includes('thailand') || country.includes('ประเทศไทย');
    });
    
    if (!filtered || filtered.length === 0) {
        suggestionBox.style.display = 'none';
        return;
    }
    
    filtered.forEach(item => {
        const line = document.createElement('div');
        line.className = 'suggestion-item';
        line.style.cssText = `
            padding: 10px 18px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        `;
        
        const name = item.station.name;
        const city = item.station.city || '';
        const country = item.station.country || '';
        let display = name;
        
        if (city && !name.includes(city)) display += `, ${city}`;
        if (country && !name.includes(country)) display += `, ${country}`;
        
        line.textContent = display;
        line.title = name;
        
        line.addEventListener('mousedown', function(e) {
            e.preventDefault();
            document.getElementById('search-box').value = name;
            suggestionBox.style.display = 'none';
        });
        
        suggestionBox.appendChild(line);
    });
    
    suggestionBox.style.display = 'block';
}

// Demo features
function showDemo() {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #74b9ff, #0984e3);
        color: white;
        padding: 15px 25px;
        border-radius: 25px;
        font-size: 14px;
        z-index: 1000;
        animation: slideInDown 0.5s ease-out;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    `;
    notification.textContent = 'Demo feature - Full functionality available in production version';
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideInDown 0.5s ease-out reverse';
        setTimeout(() => notification.remove(), 500);
    }, 2500);
}

function demonstrateFeature(type) {
    const messages = {
        ai: 'AI-Powered analysis activated! Machine learning algorithms are processing weather patterns...',
        forecast: '7-Day forecast loading! Detailed hourly predictions being generated...',
        location: 'Area recommendations ready! Intelligent location-based weather insights available...'
    };
    
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 20px 30px;
        border-radius: 15px;
        font-size: 16px;
        z-index: 1000;
        animation: fadeInUp 0.5s ease-out;
        text-align: center;
        max-width: 400px;
    `;
    notification.textContent = messages[type];
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initializeTimeUpdates();
    
    const searchBox = document.getElementById('search-box');
    if (searchBox) {
        const place = new URLSearchParams(window.location.search).get('place');
        if (place) searchBox.value = place;
    }
});

document.addEventListener('click', function(e) {
    if (suggestionBox && !suggestionBox.contains(e.target) && e.target.id !== 'search-box') {
        suggestionBox.style.display = 'none';
    }
});

// Cloud animation
document.addEventListener('mousemove', (e) => {
    const clouds = document.querySelectorAll('.cloud');
    const mouseX = e.clientX / window.innerWidth;
    const mouseY = e.clientY / window.innerHeight;
    clouds.forEach((cloud, index) => {
        const speed = (index + 1) * 0.5;
        const xOffset = mouseX * speed;
        const yOffset = mouseY * speed;
        cloud.style.transform = `translate(${xOffset}px, ${yOffset}px)`;
    });
});