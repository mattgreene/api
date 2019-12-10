#  Copyright 2019 Copper Labs, Inc.
#
#  weather-client.py
#
# prerequisites:
#    pip install -r requirements.txt
#    export DARK_SKY_API_KEY


import argparse
import csv
from datetime import datetime, timedelta, time
from dateutil import parser
import json
import os
from pprint import pprint
import requests
from urllib import urlencode


TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
DARK_SKY_API = 'https://api.darksky.net/forecast'


def get_postal_codes(premises_file):
    postal_codes = []
    return postal_codes
    with open(premises_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Postal Code'] not in postal_codes:
                postal_codes.append(row['Postal Code'])
    return postal_codes


def get_postal_geopoints(postal_codes, postal_geo_file):
    postal_geopoints = {}
    with open(postal_geo_file, 'r') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if row['Zip'] in postal_codes:
                postal_geopoints[row['Zip']] = row
    return postal_geopoints


def get_weather_data(postal_geopoints, start, end):
    weather_data = {}
    sdate = parser.parse(start)
    edate = parser.parse(end)
    delta = edate - sdate
    ctime = time()
    qstr = urlencode({'exclude': 'currently,daily,flags'})
    for postal_code, geopoint in postal_geopoints.items():
        print('Fetching weather for ' + geopoint['Zip'])
        weather_data[postal_code] = {}
        for i in range(delta.days + 1):
            day = sdate + timedelta(days=i)
            # convert to datetime
            t = datetime.combine(day, ctime).isoformat()
            daily_temps = []
            print('Fetching weather for ' + t)
            url = '{url}/{key}/{lat},{long},{time}?{qstr}'.format(
                url=DARK_SKY_API,
                key=os.environ['DARK_SKY_API_KEY'],
                lat=geopoint['Latitude'],
                long=geopoint['Longitude'],
                time=t,
                qstr=qstr
            )
            r = requests.get(url)
            weather = r.json()
            for entry in weather['hourly']['data']:
                daily_temps.append({
                    'timestamp': str(datetime.fromtimestamp(entry['time'])),
                    'temperature': entry['temperature']
                })
            weather_data[postal_code][t] = daily_temps
    return weather_data


def build_weather_data(args):
    # load premises to obtain postal code list, seeded with DIA
    postal_codes = get_postal_codes(args.csv_premises)
    if args.debug:
        pprint(postal_codes)

    # load post code geo lookup data
    postal_geopoints = get_postal_geopoints(postal_codes, args.csv_postal_geo)
    if args.debug:
        pprint(postal_geopoints)

    postal_weather_data = get_weather_data(
        postal_geopoints, args.start, args.end)
    if args.debug:
        pprint(postal_weather_data)

    with open(args.json_output_file, 'wb') as f:
        json.dump(postal_weather_data, f)


def convert_weather_data(args):
    data = ''
    rows = []
    with open(args.json_input_file, 'r') as f:
        data = json.load(f)
        for postal_code in data.keys():
            for day_data in data[postal_code].values():
                rows += day_data
    rows.sort(key=lambda x: x['time'], reverse=False)
    pprint(rows)
    keys = ['timestamp', 'temperature']
    with open(args.csv_output_file, 'wb') as f:
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        add_help=True,
        description='Command-line utilities to interact with Copper Cloud.')
    parser.add_argument(
        '--quiet', dest='quiet', action='store_true', default=False,
        help='Suppress printing results to the console.')
    parser.add_argument(
        '--debug', dest='debug', action='store_true', default=False,
        help='Enable debug output')

    subparser = parser.add_subparsers()

    parser_a = subparser.add_parser("fetch")
    parser_a.set_defaults(func=build_weather_data)
    parser_a.add_argument(
        'csv_postal_geo',
        help='CSV with postal code to lat/long mapping.')
    parser_a.add_argument(
        'csv_premises',
        help='CSV with premises to look up historical weather.')
    time_fmt = '%%Y-%%m-%%dT%%H:%%M:%%SZ'
    parser_a.add_argument(
        'start',
        help='Query start time, formatted as: ' + time_fmt)
    parser_a.add_argument(
        'end',
        help='Query end time, formatted as: ' + time_fmt)
    parser_a.add_argument(
        'json_output_file',
        help='Write temperature data to JSON file.')

    parser_b = subparser.add_parser("convert")
    parser_b.set_defaults(func=convert_weather_data)
    parser_b.add_argument(
        'json_input_file',
        help='JSON input file with temperature data.')
    parser_b.add_argument(
        'csv_output_file',
        help='Write temperature data to CSV file.')

    args = parser.parse_args()
    args.func(args)

    print('complete!')


if (__name__ == "__main__"):
    main()
