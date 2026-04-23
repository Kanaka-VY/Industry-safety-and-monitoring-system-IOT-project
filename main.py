#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <PubSubClient.h>


// *WiFi Credentials*
const char* ssid = "Samsung";  
const char* password = "iot@2025"; 


// *MQTT Broker Details (Raspberry Pi)*
const char* mqtt_server = "192.168.152.138"; // Replace with Raspberry Pi's IP
const int mqtt_port = 1883;
const char* mqtt_topic_Fire = "industry/fire";
const char* mqtt_topic_Smoke = "industry/smoke";
const char* mqtt_topic_Gas = "industry/gas";
const char* mqtt_topic_Temperature = "industry/temperature";
const char* mqtt_topic_Humidity = "industry/humidity";
const char* mqtt_topic_ConveyorStatus = "industry/conveyor"; // Single topic for conveyor status


// *ThingSpeak API Key & URL*
const char* server = "http://api.thingspeak.com/update";
String apiKey = "N4LREVYAB0YYR2C0"; 


// *Sensor Pin Definitions*
#define FIRE_SENSOR_PIN 18  
#define SMOKE_SENSOR_PIN 33  
#define GAS_SENSOR_PIN 32  
#define DHTPIN 4   
#define IR_SENSOR_PIN 23 // *IR Sensor for Conveyor Belt*
#define DHTTYPE DHT11  
DHT dht(DHTPIN, DHTTYPE);


// *LED Pin Definitions*
#define RED_LED_PIN 27
#define GREEN_LED_PIN 26
#define BLUE_LED_PIN 25


// *Threshold Values*
#define SMOKE_THRESHOLD 400  
#define GAS_THRESHOLD 300  


WiFiClient espClient;
PubSubClient client(espClient);


// *Conveyor Belt Status Variables*
String conveyorStatus = "Stopped"; // "Running" or "Stopped"


void setup() {
    Serial.begin(115200);
    delay(1000); 
    Serial.println("🚀 ESP32 Booting...");


    dht.begin();


    pinMode(FIRE_SENSOR_PIN, INPUT);
    pinMode(SMOKE_SENSOR_PIN, INPUT);
    pinMode(GAS_SENSOR_PIN, INPUT);
    pinMode(IR_SENSOR_PIN, INPUT); 


    pinMode(RED_LED_PIN, OUTPUT);
    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(BLUE_LED_PIN, OUTPUT);


    connectWiFi();
    client.setServer(mqtt_server, mqtt_port);
    reconnectMQTT();
}


// *Function to Connect to WiFi*
void connectWiFi() {
    Serial.print("📡 Connecting to WiFi...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ Connected to WiFi!");
}


// *Reconnect MQTT if Disconnected*
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("🔗 Connecting to MQTT...");
        if (client.connect("ESP32_Client")) {
            Serial.println("✅ Connected!");
        } else {
            Serial.print("❌ Failed, rc=");
            Serial.print(client.state());
            Serial.println(" Retrying in 5s...");
            delay(5000);
        }
    }
}


// *Function to Set RGB LED Color*
void setRGB(bool r, bool g, bool b) {
    digitalWrite(RED_LED_PIN, !r);
    digitalWrite(GREEN_LED_PIN, !g);
    digitalWrite(BLUE_LED_PIN, !b);
}


void loop() {
    if (!client.connected()) reconnectMQTT();
    client.loop();


    // *Read Sensor Data*
    int fireStatus = digitalRead(FIRE_SENSOR_PIN);
    int smokeValue = analogRead(SMOKE_SENSOR_PIN);
    int gasValue = analogRead(GAS_SENSOR_PIN);
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    
    // *Read Conveyor Belt Status*
    delay(400); // Small delay to stabilize reading
    int irValue = digitalRead(IR_SENSOR_PIN);


    // *Determine Conveyor Belt Status*
    if (irValue == LOW) { // Object detected = Conveyor is Running
        conveyorStatus = "Running";
    } else { // No object detected = Conveyor is Stopped
        conveyorStatus = "Stopped";
    }


    // *Debugging: Check IR Sensor Readings*
    Serial.println("------ Sensor Readings ------");
    Serial.printf("🔥 Fire: %d (LOW = Fire Detected)\n", fireStatus);
    Serial.printf("💨 Smoke: %d (Threshold: %d)\n", smokeValue, SMOKE_THRESHOLD);
    Serial.printf("☠ Gas: %d (Threshold: %d)\n", gasValue, GAS_THRESHOLD);
    Serial.printf("🌡 Temp: %.2f°C (High Temp > 35°C)\n", temperature);
    Serial.printf("💧 Humidity: %.2f%%\n", humidity);
    Serial.printf("🔄 IR Sensor Value: %d\n", irValue);
    Serial.printf("🚀 Conveyor Status: %s\n", conveyorStatus.c_str());
    Serial.println("----------------------------");
    // LED Alerts
if (fireStatus == LOW || smokeValue >= SMOKE_THRESHOLD || gasValue >= GAS_THRESHOLD || temperature > 35) {
    setRGB(HIGH, LOW, LOW); // 🔴 Red LED (Danger - Fire, Smoke, Gas, or High Temp)
    Serial.println("🚨 DANGER! Critical Alert Triggered!");
} else if (temperature >= 25 && temperature <= 35) {
    setRGB(HIGH, HIGH, LOW); // 🟠 Orange LED (Moderate temperature)
    Serial.println("⚠ Moderate Temperature.");
} else {
    setRGB(LOW, HIGH, LOW); // 🟢 Green LED (Safe environment)
    Serial.println("✅ Environment Normal.");
}


    // *Send Data to ThingSpeak*
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(server) + "?api_key=" + apiKey + 
                     "&field1=" + String(fireStatus) + 
                     "&field2=" + String(smokeValue) + 
                     "&field3=" + String(gasValue) + 
                     "&field4=" + String(temperature) + 
                     "&field5=" + String(humidity) + 
                     "&field6=" + (conveyorStatus == "Running" ? "1" : "0");


        http.begin(url);
        int httpResponseCode = http.GET();


        if (httpResponseCode > 0) {
            Serial.printf("✅ ThingSpeak Response: %d\n", httpResponseCode);
        } else {
            Serial.printf("❌ Error Sending Data: %d\n", httpResponseCode);
        }
        http.end();
    } else {
        Serial.println("⚠ WiFi Disconnected. Reconnecting...");
        connectWiFi();
    }


    // *Publish Data to MQTT Topics*
    client.publish(mqtt_topic_Fire, String(fireStatus).c_str());
    client.publish(mqtt_topic_Smoke, String(smokeValue).c_str());
    client.publish(mqtt_topic_Gas, String(gasValue).c_str());
    client.publish(mqtt_topic_Temperature, String(temperature).c_str());
    client.publish(mqtt_topic_Humidity, String(humidity).c_str());
    client.publish(mqtt_topic_ConveyorStatus, conveyorStatus.c_str());


    Serial.println("📤 Sensor Data Published to MQTT!");
    delay(5000);  
}
