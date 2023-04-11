#define BLYNK_TEMPLATE_ID "TMPLorUOYJb0"
#define BLYNK_DEVICE_NAME "Artiom"
#define RelayPin1 D5 //D5 towel
#define RelayPin2 D6 //D6 floor
#define VPIN_BUTTON_1    V4
#define VPIN_BUTTON_2    V5
#define DHTPIN D1
#define ONE_WIRE_BUS D4
#include <DHT.h>
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
#include <OneWire.h>
#include <DallasTemperature.h> 
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
#define BLYNK_FIRMWARE_VERSION        "0.1.7"
#define BLYNK_PRINT Serial
#include "BlynkEdgent.h" 
BlynkTimer timer;
bool toggleState_1 = HIGH; //Define integer to remember the toggle state for relay 1
bool toggleState_2 = HIGH;
float h, t;
BLYNK_CONNECTED() {
  // Request the latest state from the server
  Blynk.syncVirtual(VPIN_BUTTON_1);
  Blynk.syncVirtual(VPIN_BUTTON_2);
}
BLYNK_WRITE(VPIN_BUTTON_1) {
  toggleState_1 = param.asInt();
  if(toggleState_1 == 1){
    digitalWrite(RelayPin1, HIGH);
  }
  else { 
    digitalWrite(RelayPin1, LOW);
  }
}

BLYNK_WRITE(VPIN_BUTTON_2) {
  toggleState_2 = param.asInt();
  if(toggleState_2 == 1){
    digitalWrite(RelayPin2, HIGH);
  }
  else { 
    digitalWrite(RelayPin2, LOW);
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(RelayPin1, OUTPUT);  //towel
  pinMode(RelayPin2, OUTPUT);  // flour
  dht.begin();
  sensors.begin();                        // Starts the DS18B20 sensor(s).
  sensors.setResolution(10);
  BlynkEdgent.begin();
  timer.setInterval(6000L, send);
}
  void loop(){
  BlynkEdgent.run();
  timer.run();  
}

void send(){
  sensors.requestTemperatures(); // Polls the sensors
  Blynk.virtualWrite(0, sensors.getTempCByIndex(1));
  Blynk.virtualWrite(1, sensors.getTempCByIndex(0));
  Blynk.virtualWrite(2, dht.readTemperature());  
  Blynk.virtualWrite(3, dht.readHumidity()); 

}