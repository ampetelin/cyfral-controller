import machine
import micropython
import network
import ntptime
from datetime import Datetime
from umqtt.simple import MQTTClient

import settings
from cyfral_controller.controller import CyfralController
from cyfral_controller.electronic_components.clock import DS1307

micropython.alloc_emergency_exception_buf(100)

cyfral_controller = CyfralController(
    sound_mode_relay_pin=settings.SOUND_MODE_RELAY_PIN,
    handset_relay_pin=settings.HANDSET_RELAY_PIN,
    incoming_call_optocoupler_pin=settings.INCOMING_CALL_OPTOCOUPLER_PIN,
    door_opening_optocoupler_pin=settings.DOOR_OPENING_OPTOCOUPLER_PIN,
    mqtt_client=MQTTClient(
        client_id=settings.MQTT_CLIENT_ID,
        server=settings.MQTT_HOST,
        port=settings.MQTT_PORT,
        user=settings.MQTT_USER,
        password=settings.MQTT_PASSWORD,
        keepalive=settings.MQTT_KEEPALIVE
    ),
    mqtt_incoming_call_state_topic=settings.MQTT_INCOMING_CALL_STATE_TOPIC,
    mqtt_sound_mode_state_topic=settings.MQTT_SOUND_MODE_STATE_TOPIC,
    mqtt_auto_open_mode_topic=settings.MQTT_AUTO_OPEN_MODE_TOPIC,
    mqtt_control_topic=settings.MQTT_CONTROL_TOPIC,
    real_time_clock=DS1307(machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4)))
)


def connection_to_wlan_network():
    ap_if = network.WLAN(network.AP_IF)
    print('Deactivate AP interface')
    ap_if.active(False)

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Activate STA interface...')
        sta_if.active(True)

        if not settings.WLAN_DHCP:
            sta_if.ifconfig((settings.WLAN_IP, settings.WLAN_MASK, settings.WLAN_GATE, settings.WLAN_DNS))

        print('Connecting to wlan network...')
        sta_if.connect(settings.WLAN_SSID, settings.WLAN_PASSWORD)

        while not sta_if.isconnected():
            machine.idle()

        print(f'Connection successful {sta_if.ifconfig()}')
        return

    print(f'Connection already established {sta_if.ifconfig()}')


def datetime_synchronization():
    print('Synchronization of datetime')
    try:
        print('Set datetime to internal RTC from NTP pool')
        ntptime.settime()

        print('Get internal RTC datetime')
        internal_rtc = machine.RTC()
        datetime = internal_rtc.datetime()

        print('Set datetime to controller RTC')
        datetime = Datetime.from_internal_rtc_format(datetime)
        cyfral_controller._rtc.set_datetime(datetime)
    except OSError as ex:
        print(f'Failed to synchronization datetime ({ex})')
    else:
        print('Synchronization successful')


if __name__ == '__main__':
    micropython.mem_info()
    connection_to_wlan_network()
    datetime_synchronization()

    print('Starting cyfral controller')
    cyfral_controller.run()
