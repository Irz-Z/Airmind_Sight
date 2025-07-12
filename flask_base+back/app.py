from flask import Flask, render_template, request, redirect, url_for
from utils import (
    normalize_province_name,
    get_thailand_open_data,
    get_overpass_data,
    get_nominatim_places,
    get_weather_data,
    get_datetime
)

app = Flask(__name__)

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
    weather = get_weather_data(province)
    results = {}
    datetime = get_datetime()  # Get current date and time

    # if province is get by URL
    # request data from API in utils.py output as dict
    if request.method == "GET" and province:
        # For GET requests with province in URL, fetch data as well
        results["tourism"] = get_nominatim_places(province, "attraction", 5)
        results["hotels"] = get_nominatim_places(province, "hotel", 5)
        results["restaurants"] = get_nominatim_places(province, "restaurant", 5)
        results["temples"] = get_nominatim_places(province, "place of worship", 3)
        results["opendata"] = get_thailand_open_data(province)

    return render_template("index.html", province=province, results=results, datetime=datetime, weather=weather)

if __name__ == "__main__":
    app.run(debug=True)
