<h1 align="center">
    Cyfral Controller
</h1>
<p align="center">
    <em>контроллер управления абонентской трубкой домофона Цифрал КЛ-2 на базе WI-FI модуля ESP8266 (ESP-12F)</em>
    <a href="https://ibb.co/K07HBCf"><img src="https://i.ibb.co/TvR5Jz7/logo.png" alt="logo" border="0"></a>
</p>

---
## Конфигурация
Создать **settings.py** файл в директории с исходным кодом прошивки, содержащий:

    WLAN_SSID = 'ssid'
    WLAN_PASSWORD = 'password'
    WLAN_DHCP = False
    WLAN_IP = '192.168.1.100'
    WLAN_MASK = '255.255.255.0'
    WLAN_GATE = '192.168.1.1'
    WLAN_DNS = '8.8.8.8'
    SOUND_MODE_RELAY_PIN = 14
    HANDSET_RELAY_PIN = 12
    INCOMING_CALL_OPTOCOUPLER_PIN = 16
    DOOR_OPENING_OPTOCOUPLER_PIN = 13
    MQTT_CLIENT_ID = 'Cyfral_Controller'
    MQTT_HOST = 'localhost'
    MQTT_PORT = 1883
    MQTT_USER = 'user'
    MQTT_PASSWORD = 'password'
    MQTT_KEEPALIVE = 60
    MQTT_INCOMING_CALL_STATE_TOPIC = 'call/state'
    MQTT_SOUND_MODE_STATE_TOPIC = 'sound_mode/state'
    MQTT_AUTO_OPEN_MODE_TOPIC = 'auto_open/state'
    MQTT_CONTROL_TOPIC = 'control'


## Подключение к плате абонентской трубке
<h2 align="center">
    <a href="https://ibb.co/NCJqXdw"><img src="https://i.ibb.co/wgPqTFD/connection-diagram.png" alt="connection-diagram" border="0"></a>
</h2>
