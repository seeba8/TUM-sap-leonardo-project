# coding=utf-8
#--------------------------------------------------#
# Count number of customers
# - 2 ultrasonic sensors (HC-SR04/KY-050)
# - 2 voltage translator / level shifter (KY-051)
#
#--------------------------------------------------#

#Bibliotheken einbinden
# import RPi.GPIO as GPIO
from datetime import datetime
import time
import requests 
import json
import configparser
import sys

config = configparser.ConfigParser()
config.read("config.ini")


# SAP HANA connection information
url = config["HANA"]["url"]
headers = {'content-type': 'application/json;charset=utf-8'}
auth = config["HANA"]["username"], config["HANA"]["password"]

#----- Configuration
# Modus (Test / Echt)
testMode = True # False
# Wartezeit zwischen Messungen (z.B. 0,025s = 25ms)
waitingTime = 0.015 #0.025

#GPIO Modus (BOARD / BCM) = logische pin nummerierung
GPIO.setmode(GPIO.BCM)
 
#GPIO Pins zuweisen
GPIO_TRIGGER = 23
GPIO_ECHO = 24

#Richtung der GPIO-Pins festlegen (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(GPIO_TRIGGER, False)

#  wär noch frei am RPi
# Belegung zweiter Sensor
# RPi: 3,3V = Pin 17; GPIO18 (Pin 12) = trigger, GPIO24 (Pin 18) = echo, Masse = Pin34
# 

GPIO_TRIGGER2 = 17
GPIO_ECHO2 = 27
GPIO.setup(GPIO_TRIGGER2, GPIO.OUT)
GPIO.setup(GPIO_ECHO2, GPIO.IN)
GPIO.setup(GPIO_TRIGGER2, False)

# Waiting time for sensor to settle
time.sleep(2)

def sendData(numberCustomers):
    try:
        timestamp = getTimestamp()
        idGen = round(time.time())
        payload = {'ID':idGen, 'CUSTOMER_CHANGE':numberCustomers, 'TIMESTAMP':timestamp}
        #payload = {'CUSTOMER_CHANGE':numberCustomers, 'TIMESTAMP':timestamp}
        # send request to HANA
        #print(json.dumps(payload))
        if testMode == False:
            r = requests.post(url, data=json.dumps(payload), headers=headers, auth=auth)
        print("Aktuelle Anzahl: %s" % numberCustomers)
    except:
        print("Fehler beim upload!")
    #print(r.text)

def getTimestamp():
    return '/Date(' + format(round(time.time())) + '000)/'

#--------------------
# Minimum Abstand unterschritten?
#--------------------
def customerDetected(distance):
    if distance < 150: # and distance > 50: #150: #150 cm (bis zum Ende der Türe)
        return True
    else:
        return False

#--------------------
# Measure Distance
#--------------------	
def getDistance(gpio_trigger, gpio_echo):
    # setze Trigger auf HIGH
    GPIO.output(gpio_trigger, True)
 
    # setze Trigger nach 0.01ms auf LOW (1ms = 0.001s)
    time.sleep(0.00001)
    GPIO.output(gpio_trigger, False)
 
    startTime = time.time()
    endTime = time.time()
 
    # speichere Startzeit
    while GPIO.input(gpio_echo) == 0:
        # Es wird solange die aktuelle Zeit gespeichert, bis das Signal aktiviert wird
        startTime = time.time()
 
    # speichere Ankunftszeit
    while GPIO.input(gpio_echo) == 1:
        # Es wird die letzte Zeit aufgenommen, wo noch das Signal aktiv war
        endTime = time.time()
 
    # Zeit Differenz zwischen Start und Ankunft
    timeElapsed = endTime - startTime
    # mit der Schallgeschwindigkeit (34300 cm/s) multiplizieren
    # und durch 2 teilen, da hin und zurueck
    distance = (timeElapsed * 34300) / 2
 
    return distance
 
if __name__ == '__main__':
    customers = 0
    oldDistance = 0
    oldDistance2 = 0
    newCustomer = True
    
    try:
        while True:
            # Sensor 1 (Beim Verlassen <---)
            distance = getDistance(GPIO_TRIGGER, GPIO_ECHO)
            if testMode == True:
                print("Sensor AUSGANG Entfernung = %.1f cm" % distance)

            # Sicherheitsabstand
            time.sleep(waitingTime)
            
            # Sensor 2 (Beim Eintreten --->)
            distance2 = getDistance(GPIO_TRIGGER2, GPIO_ECHO2)
            if testMode == True:
                print("Sensor EINGANG Entfernung = %.1f cm" % distance2)

            # Neuer Eingang? (Signal am Eingang aber noch nicht am Ausgang)
            if customerDetected(distance2) and not customerDetected(distance) and newCustomer:
                # so lange Warten bis am Ausgangssensor aehnliche Distanz vorliegt
                # halbe Sekunde warten
                print("??? ---> Angeblicher Eingang")
                startTime = time.time()
                while time.time() - startTime < 0.5:
                    distanceIn = distance2
                    time.sleep(waitingTime)
                    distanceOut = getDistance(GPIO_TRIGGER, GPIO_ECHO)
                    if (distanceOut + 15) > distanceIn and (distanceOut - 15) < distanceIn:
                        print("---> Kunde betritt den Laden")
                        print("Abstand Eingang: %.1f cm" % distanceIn)
                        print("Abstand Ausagang: %.1f cm" % distanceOut)
                        customers = customers + 1
                        sendData(customers)
                        newCustomer = False
                        time.sleep(2)
                        break
 
            # Neuer Ausagang? (Signal am Ausgang aber noch nicht am Eingang)
            if customerDetected(distance) and not customerDetected(distance2) and newCustomer:
                print("??? <--- Angeblicher Ausgang")
                startTime = time.time()
                while time.time() - startTime < 0.5:
                    distanceOut = distance
                    time.sleep(waitingTime)
                    distanceIn = getDistance(GPIO_TRIGGER2, GPIO_ECHO2)
                    if (distanceIn + 15) > distanceOut and (distanceIn - 15) < distanceOut:
                        if customers > 0:
                            print("<--- Kunde verlässt den Laden")
                            print("Abstand Eingang: %.1f cm" % distanceIn)
                            print("Abstand Ausagang: %.1f cm" % distanceOut)
                            customers = customers - 1
                            sendData(customers)
                            newCustomer = False
                            time.sleep(2)
                            break
                #raise KeyboardInterrupt

	    # Wenn kein Kunde in der Tür steht, warte 2 Sekunden und gib die Erkennung frei
            if not customerDetected(distance) and not customerDetected(distance2) and not newCustomer:
                newCustomer = True
                

            # Sicherheitsabstand
            time.sleep(waitingTime)
            

            #TODO: evtl. Prüfung auf Ladenöffnungszeiten
            #now = datetime.now()
            #if not time(7,30) <= now.time() <= time(18,30):
            #    print("innerhalb Ladenöffnungszeit")
 
        # Beim Abbruch durch STRG+C resetten
    except KeyboardInterrupt:
        print("Messung vom User gestoppt")
        print("Anzahl Kunden: %s" % customers)
 
        GPIO.cleanup()
