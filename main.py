from flask import Flask, render_template, request, abort, redirect, send_file
from datetime import datetime
import requests
import pycountry
import boto3
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('API_KEY')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/forecast', methods=['POST'])
def forecast():
    global info
    country = request.form.get('country')
    info = handle_info(country)
    return render_template('weather.html', info=info, err=None)

@app.route('/upload', methods=['GET'])
def uploadInfo():
    saveInfoToDB(info)
    return redirect('/')

@app.route("/download")
def downloadFile():
    s3 = boto3.client('s3')
    file = s3.download_file('mybucket011', 'img.png', 'image.png')
    return send_file('image.png', as_attachment=True)

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html')


def handle_info(country):
    country_info = handle_geo_loc(country)
    weather_info = handle_weather_info(country_info['lat'], country_info['lon'])
    handled_info = {'location': country_info['location'], 'country': country_info['country'], 'daily': []}
    for day in weather_info[1:]:
        handled_info['daily'].append({
                            'date': datetime.fromtimestamp(day['dt']).strftime('%b %d, %a'),
                            'day_temp': day['temp']['day'],
                            'night_temp': day['temp']['day'],
                            'humidity': day['humidity'],
                            'main': day['weather'][0]['main'],
                            'description': day['weather'][0]['description'],
                            'icon': f"../static/{day['weather'][0]['icon']}.png"})
    return handled_info


def handle_geo_loc(country):
    query = {'appid': api_key, 'limit': 1, 'q': country}
    try:
        response = requests.get('http://api.openweathermap.org/geo/1.0/direct', params=query).json()[0]
        return {'lat': response['lat'], 'lon': response['lon'], 'location': response['name'],
            'country': pycountry.countries.lookup(response['country']).name}
    except IndexError:
        abort(500)


def handle_weather_info(latitude, longitude):
    query = {'appid': api_key, 'exclude': 'hourly, minutely, current',
             'units': 'metric', 'lon': longitude, 'lat': latitude}
    try:
        response = requests.get('https://api.openweathermap.org/data/2.5/onecall', params=query).json()
        return response['daily']
    except Exception:
        abort(500)


def saveInfoToDB(info):
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
    table = dynamodb.Table('locations')
    info['id'] = str(datetime.now())
    table.put_item(Item=info)


if __name__ == '__main__':
    app.run(debug=True)
