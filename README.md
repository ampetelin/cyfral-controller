<h1 align="center">Cyfral Controller</h1>
<p align="center">
    <em>контроллер управления абонентской трубкой домофона Цифрал КЛ-2 на базе WI-FI модуля ESP8266 (ESP-12F)</em>
</p>
<p align="center">
    <img src="https://res.cloudinary.com/ampetelin/image/upload/v1668243575/cyfral-controller/logo_ndbt1l.png" alt="logo">
</p>


---
## Конфигурация
Создать **settings.py** файл в директории с исходным кодом прошивки, содержащий:

```Python
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
```

## Cборка
1) Загрузить исходники <a href="https://github.com/micropython/micropython">MicroPython<a/>
2) Проверить доступность подмодулей
```bash
$ make -C ports/esp8266 submodules
```
3) Скопировать содержимое каталога проекта ```src``` в ```ports/esp8266/modules```
4) Скомпилировать кросс-компилятор MicroPython
```bash
$ docker run --rm -v $HOME:$HOME -u $UID -w $PWD larsks/esp-open-sdk make -C mpy-cross
```
5) Перейти в каталог ```ports/esp8266```
6) Скомпилировать прошивку
```bash
$ docker run --rm -v $HOME:$HOME -u $UID -w $PWD larsks/esp-open-sdk make -j BOARD=GENERIC
```

см. <a href="https://github.com/micropython/micropython/blob/master/ports/esp8266/README.md">Официальная документация по сборке</a>

## Прошивка
1) Загрузить <a href="https://github.com/espressif/esptool/">esptool</a> или установить с помощью pip:
```bash
$ pip install esptool
```
2) Очистить флэш-память
```bash
$ esptool.py --port /dev/ttyUSB0 erase_flash
```
3) Загрузить прошивку
```bash
$ esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 <your_firmware_name>.bin
```

## Подключение к плате абонентской трубке
<h2 align="center">
    <img src="https://res.cloudinary.com/ampetelin/image/upload/v1668414822/cyfral-controller/connection-diagram_swmrme.png" alt="connection-diagram">
</h2>
