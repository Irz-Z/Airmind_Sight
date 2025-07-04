from flask import Flask, render_template, request

app = Flask(__name__)

# City data for individual pages
cities = [
    "Bangkok", "Amnat Charoen", "Ang Thong", "Bueng Kan", "Buri Ram", "Chachoengsao",
    "Chai Nat", "Chaiyaphum", "Chanthaburi", "Chiang Mai", "Chiang Rai", "Chonburi",
    "Chumphon", "Kalasin", "Kamphaeng Phet", "Kanchanaburi", "Khon Kaen", "Krabi",
    "Lampang", "Lamphun", "Loei", "Lopburi", "Mae Hong Son", "Maha Sarakham",
    "Mukdahan", "Nakhon Nayok", "Nakhon Pathom", "Nakhon Phanom", "Nakhon Ratchasima",
    "Nakhon Sawan", "Nakhon Si Thammarat", "Nan", "Narathiwat", "Nong Bua Lam Phu",
    "Nong Khai", "Nonthaburi", "Pathum Thani", "Pattani", "Phang Nga", "Phatthalung",
    "Phayao", "Phetchabun", "Phetchaburi", "Phichit", "Phitsanulok", "Phra Nakhon Si Ayutthaya",
    "Phrae", "Phuket", "Prachinburi", "Prachuap Khiri Khan", "Ranong", "Ratchaburi",
    "Rayong", "Roi Et", "Sa Kaeo", "Sakon Nakhon", "Samut Prakan", "Samut Sakhon",
    "Samut Songkhram", "Saraburi", "Satun", "Sing Buri", "Sisaket", "Songkhla",
    "Sukhothai", "Suphan Buri", "Surat Thani", "Surin", "Tak", "Trang", "Trat",
    "Ubon Ratchathani", "Udon Thani", "Uthai Thani", "Uttaradit", "Yala", "Yasothon"
]

# index
@app.route('/', methods=['GET'])
def index():
    query = request.args.get('query', '')
    # Initialize results as an empty list
    results = []
    if query:
        # Filter cities based on the query
        results = [city for city in cities if query.lower() in city.lower()] if query else []
    return render_template('index.html', results=results, query=query)

# individual pages
@app.route('/individual')
def individual():
    return render_template('individual-weather.html')

if __name__ == '__main__':
    app.run(debug=True)
