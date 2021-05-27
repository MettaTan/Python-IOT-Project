# === Importing ===
import RPi.GPIO as GPIO #import RPi.GPIO module
import spidev #import SPI library
import dht11
import datetime
from time import sleep
from firebase import firebase

global p
p = 0

# get port number from firebase
'''
buzzer_port = firebase.get("/Buzzer", "port")
doorlock_port = firebase.get("/Doorlock", "port")
humidity_port = firebase.get("/Humidity", "port")
ir_port = firebase.get("/IR", "port")
ldr_port = firebase.get("/LDR", "port")
led_port = firebase.get("/LED_STATUS", "port")
temp_port = firebase.get("/Temperature", "port")
'''

# === GPIO initialization ===
GPIO.setmode(GPIO.BCM) #choose BCM mode
GPIO.setwarnings(False)
GPIO.setup(17,GPIO.IN) # PIR sensor using GPIO 17 as input
GPIO.setup(18,GPIO.IN) # LDR sensor using GPIO 18 as input
GPIO.setup(24,GPIO.OUT) # LED using GPIO 24 as output
GPIO.setup(18,GPIO.OUT) # Buzzer using GPIO 18 as output
instance = dht11.DHT11(pin=21) #read data using pin 21
GPIO.setup(23,GPIO.OUT) #set GPIO 23 as output for doorlock

# === Main program ===
firebase = firebase.FirebaseApplication('https://mad-miniproject.firebaseio.com/', None)

# === ADC ===
spi=spidev.SpiDev() #create SPI object
spi.open(0,0) #open SPI port 0, device (CS) 0

def readadc(adcnum):
    #read SPI data from the MCP3008, 8 channels in total
    if adcnum>7 or adcnum<0:
        return -1
    spi.max_speed_hz = 1350000
    r = spi.xfer2([1,8+adcnum<<4,0])
        #construct list of 3 items, before sending to ADC:
        #1(start), (single-ended+channel#) shifted left 4 bits, 0(stop)
        #see MCP3008 datasheet for details
    data = ((r[1]&3)<<8)+r[2]
        #ADD first byte with 3 or 0b00000011 - masking operation
        #shift result left by 8 bits
        #OR result with second byte, to get 10-bit ADC result
    return data

# === Automated Lighting Control ===
sleep(5) #to allow sensor time to stabilize
PIR_state=0 #use this, so that only a change in state is reported

while (True):
    LDR_value = readadc(0) #read ADC channel 0 i.e. LDR
    print("LDR = ", LDR_value) #print result
    result = firebase.put("/LDR", "Value", LDR_value)

    manual_light_control = firebase.get("/LED_STATUS", "Value")
    automatic_light_switch = firebase.get("/LED_STATUS", "Automatic")
    if automatic_light_switch == 1:
        if GPIO.input(17): 
            if LDR_value > 700:            
                if PIR_state==0:
                    print('No motion detected and/or light level of surroundings more than 700')
                
                    PIR_state=1

                    GPIO.output(24,0) # turn off LED
                    sleep(0.1)
        else:             
            if PIR_state==1:
                print('Motion detected and light level of surroundings less than 700')
                PIR_state=0

                GPIO.output(24,1) # turn on LED
                sleep(0.1)
    else:
         
         if manual_light_control == 1:
            GPIO.output(24,1)
         elif manual_light_control == 0:
            GPIO.output(24,0)
            
# === Temp & Humi ===
    dht11result = instance.read()
    if dht11result.is_valid(): #print datetime & sensor values
        print("Last valid input: " + str(datetime.datetime.now()))
        
        print("Temperature: %-3.1f C" % dht11result.temperature)
        temp = firebase.put("/Temperature", "Value", dht11result.temperature)
        
        print("Humidity: %-3.1f %%" % dht11result.humidity)
        humi = firebase.put("/Humidity", "Value", dht11result.humidity)
                          
        sleep(1.5)
    

# === Intruder Alert ===
    outside = firebase.get("/Doorlock", "Value")
    if outside == 1:
        if p == 0:
            GPIO.output(23,1) #output logic high/'1'
            sleep(1) #delay 1 second
            GPIO.output(23,0) #output logic low/'0'
            p = 1
        for x in range(500): 
            if GPIO.input(17): 
                     
                    if PIR_state==0:
                        print('No motion detected')
                        
                        PIR_state=1
                        PIR_tofirebase = firebase.put("/IR", "Value", PIR_state)

                        intruder_alert = firebase.put("/Doorlock", "intruder", 0)

                        #GPIO.output(24,0) # turn off LED
                        #sleep(0.1)
            else:             
                if PIR_state==1:
                    print('Motion detected')
                    PIR_state=0
                    PIR_tofirebase = firebase.put("/IR", "Value", PIR_state)

                    intruder_alert = firebase.put("/Doorlock", "intruder", 1)

                    #GPIO.output(24,1) # turn on LED
                    #sleep(0.1)

                    for i in range(10):
                        GPIO.output(18,1) #output logic high/'1'
                        sleep(1) #delay 1 second
                    
                    GPIO.output(18,0) #output logic low/'0'
                    sleep(1) #delay 1 second
         
                sleep(1)
    elif outside == 0:
        if p == 1:
            GPIO.output(23,1) #output logic high/'1'
            sleep(1) #delay 1 second
            GPIO.output(23,0) #output logic low/'0'
            p=0
        
        


#buzzer
    buzzer = firebase.get("/Buzzer", "Value")
    if buzzer == 1:
        GPIO.output(18,1)
    elif buzzer == 0:
        GPIO.output(18,0)


 


    


               
