#!/usr/bin/env python3
from datetime import datetime
import time
import requests 
import json
import configparser

# SAP HANA connection information
headers = {'content-type': 'application/json;charset=utf-8'}
config = {}

def sendData(weather):
    try:
        timestamp = getTimestamp()
        payload = {'TIMESTAMP':timestamp, **weather}
        # send request to HANA
        #print(json.dumps(payload))
        auth = config["HANA"]["username"], config["HANA"]["password"]
        url = config["HANA"]["url"]
        r = requests.post(url, data=json.dumps(payload), headers=headers, auth=auth)
        print(auth)
        print(json.dumps(payload))
        print(r.text)
    except:
        print("Fehler beim upload!")
    #print(r.text)

def getTimestamp():
    return '/Date(' + format(round(time.time())) + '000)/'

def get_weatherdata(location):
    key = config["OPENWEATHERMAP"]["appid"]
    url = "https://api.openweathermap.org/data/2.5/weather?q=" + location + "&APPID=" + key
    request = requests.get(url)
    return request.json()

def main():
    global config 
    config = configparser.ConfigParser()
    config.read("config.ini")
    w = get_weatherdata(config["OPENWEATHERMAP"]["location"])
    weather = {
        "MAIN": w["weather"][0]["main"],
        "DESCRIPTION": w["weather"][0]["description"],
        "ICON": w["weather"][0]["icon"],
        "WINDSPEED": "{:05.2f}".format(w["wind"]["speed"]),
        "TEMPERATURE": "{:05.2f}".format(w["main"]["temp"]),
        # "rain": w["rain"]["3h"],
        "HUMIDITY": w["main"]["humidity"],
        "PRESSURE": w["main"]["pressure"]
    }
    sendData(weather)

if __name__ == '__main__':
    main()