from flask import Flask, send_from_directory, render_template
import os

app = Flask(__name__, static_folder='.', template_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=True)
