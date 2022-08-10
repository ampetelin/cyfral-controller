import time
import machine
from datetime import Time
from umqtt.simple import MQTTClient

from cyfral_controller.electronic_components.clock import DS1307
from cyfral_controller.electronic_components.relays import (
    Relay,
    ControlOptocoupler,
    ControlledOptocoupler
)
from cyfral_controller.exceptions import (
    CyfralControllerException,
    SwitchSoundModeError,
    PickUpHandsetError,
    HangUpHandsetError,
    PressOpenDoorButtonError
)
from cyfral_controller.utils import blinks


class SoundMode:
    """Режим звука"""
    SILENT = 1
    AUDIBLE = 2


class AutoOpenMode:
    """Режим автоматического открытия двери"""
    DISABLED = 0
    ENABLED = 1


class IntercomState:
    """Состояние домофона"""
    WAITING_CALL = 1
    INCOMING_CALL = 2
    HANDSET_IS_PICK_UP = 3
    HANDSET_IS_HANG_UP = 4


class CyfralController:
    """Контроллер домофона Cyfral"""

    def __init__(self,
                 sound_mode_relay_pin: int,
                 handset_relay_pin: int,
                 incoming_call_optocoupler_pin: int,
                 door_opening_optocoupler_pin: int,
                 mqtt_client: MQTTClient,
                 mqtt_incoming_call_state_topic: str,
                 mqtt_sound_mode_state_topic: str,
                 mqtt_auto_open_mode_topic: str,
                 mqtt_control_topic: str,
                 real_time_clock: DS1307):
        """Инициализирует атрибуты объекта CyfralController"""
        self._sound_mode_relay = Relay(sound_mode_relay_pin)
        self._handset_relay = Relay(handset_relay_pin)
        self._incoming_call_optocoupler = ControlledOptocoupler(incoming_call_optocoupler_pin)
        self._door_opening_optocoupler = ControlOptocoupler(door_opening_optocoupler_pin)
        self._rtc = real_time_clock

        self._intercom_state = IntercomState.WAITING_CALL
        self._incoming_call_time = None

        self._sound_mode = None
        self._sound_mode_switch_timer = machine.Timer(-1)
        self._unmute_time = Time(hour=3)
        self._mute_time = Time(hour=18)

        self._auto_open_mode = AutoOpenMode.DISABLED
        self._auto_open_mode_timer = machine.Timer(-1)

        self._mqtt_client = mqtt_client
        self._mqtt_connected = False
        self._mqtt_keepalive_timer = machine.Timer(-1)
        self._mqtt_control_topic = mqtt_control_topic
        self._mqtt_incoming_call_state_topic = mqtt_incoming_call_state_topic
        self._mqtt_sound_mode_state_topic = mqtt_sound_mode_state_topic
        self._mqtt_auto_open_mode_topic = mqtt_auto_open_mode_topic

    def run(self):
        """Основной цикл контроллера"""
        self._sound_mode_initialization()
        self._enable_auto_sound_mode()

        while True:
            if not self._mqtt_connected:
                try:
                    self._connect_to_mqtt_server()
                except OSError:
                    blinks.error_blink()
                else:
                    self._mqtt_keepalive_timer.init(
                        period=self._mqtt_client.keepalive * 1000,
                        callback=self._mqtt_keepalive_ping_callback
                    )
                    self._subscribe_to_topic(self._mqtt_control_topic)
                    self._mqtt_components_state_initialization()
            else:
                incoming_call = self._incoming_call

                if self._intercom_state == IntercomState.WAITING_CALL and incoming_call:
                    self._intercom_state = IntercomState.INCOMING_CALL
                    self._publish_mqtt_message(self._mqtt_incoming_call_state_topic, 'ON')

                if not self._intercom_state == IntercomState.WAITING_CALL:
                    if incoming_call:
                        self._incoming_call_time = time.ticks_ms()
                        if self._auto_open_mode:
                            self.open_door()
                    else:
                        incoming_call_time_diff = time.ticks_diff(time.ticks_ms(), self._incoming_call_time) // 1000
                        if incoming_call_time_diff >= 5:
                            self._intercom_state = IntercomState.WAITING_CALL
                            self._publish_mqtt_message(self._mqtt_incoming_call_state_topic, 'OFF')

                self._check_mqtt_message()

    def mute(self, mqtt_payload: bool = True, check_auto_mode: bool = True):
        """Переводит домофон в режим "Без звука" """
        if self._sound_mode == SoundMode.SILENT:
            raise SwitchSoundModeError('Домофон уже находится в беззвучном режиме')

        self._sound_mode_relay.enable()
        self._sound_mode = SoundMode.SILENT

        if mqtt_payload:
            self._publish_mqtt_message(self._mqtt_sound_mode_state_topic, 'OFF')

        if check_auto_mode:
            if self._determine_sound_mode() == SoundMode.AUDIBLE:
                self._disable_auto_sound_mode()
            else:
                self._enable_auto_sound_mode()

        time.sleep_ms(500)

    def unmute(self, mqtt_payload: bool = True, check_auto_mode: bool = True):
        """Переводит домофон в режим "Со звуком" """
        if self._sound_mode == SoundMode.AUDIBLE:
            raise SwitchSoundModeError('Домофон уже находится в звуковом режиме')

        self._sound_mode_relay.disable()
        self._sound_mode = SoundMode.AUDIBLE

        if mqtt_payload:
            self._publish_mqtt_message(self._mqtt_sound_mode_state_topic, 'ON')

        if check_auto_mode:
            if self._determine_sound_mode() == SoundMode.SILENT:
                self._disable_auto_sound_mode()
            else:
                self._enable_auto_sound_mode()

        time.sleep_ms(500)

    def open_door(self):
        """Открывает дверь домофона"""
        if self._sound_mode == SoundMode.AUDIBLE:
            self._pick_up_handset()
            self._press_open_door_button()
            self._hang_up_handset()
        else:
            self._pick_up_handset()
            self.unmute(mqtt_payload=False, check_auto_mode=False)
            self._press_open_door_button()
            self._hang_up_handset()
            self.mute(mqtt_payload=False, check_auto_mode=False)

    def reject_call(self):
        """Сбрасывает входящий вызов"""
        if self._sound_mode == SoundMode.AUDIBLE:
            self._pick_up_handset()
            self._hang_up_handset()
        else:
            self._pick_up_handset()
            self.unmute(mqtt_payload=False, check_auto_mode=False)
            self._hang_up_handset()
            self.mute(mqtt_payload=False, check_auto_mode=False)

    def _pick_up_handset(self):
        """Поднимает трубку домофона и переводит контроллер в режим "Трубка поднята"""
        if not self._intercom_state == IntercomState.INCOMING_CALL:
            raise PickUpHandsetError('Невозможно снять трубку домофона без входящего звонка')

        self._handset_relay.enable()
        self._intercom_state = IntercomState.HANDSET_IS_PICK_UP
        time.sleep_ms(500)

    def _press_open_door_button(self):
        """Нажимает кнопку открытия двери"""
        if not self._intercom_state == IntercomState.HANDSET_IS_PICK_UP:
            raise PressOpenDoorButtonError('Невозможно открыть дверь без снятия трубки домофона')

        self._door_opening_optocoupler.enable()
        time.sleep_ms(500)
        self._door_opening_optocoupler.disable()

    def _hang_up_handset(self):
        """Вешает трубку домофона и переводит контроллер в режим "Трубка повешена"""
        if not self._intercom_state == IntercomState.HANDSET_IS_PICK_UP:
            raise HangUpHandsetError('Трубка домофона уже повешена')

        self._handset_relay.disable()
        self._intercom_state = IntercomState.HANDSET_IS_HANG_UP
        time.sleep_ms(500)

    @property
    def _incoming_call(self) -> bool:
        """Свойство входящего вызова"""
        if not self._incoming_call_optocoupler.state:
            return False
        return True

    def _sound_mode_initialization(self):
        """Инициализирует звуковой режим"""
        if self._determine_sound_mode() == SoundMode.AUDIBLE:
            self._sound_mode = SoundMode.AUDIBLE
        else:
            self.mute(mqtt_payload=False, check_auto_mode=False)

    def _determine_sound_mode(self) -> int:
        """Определяет режим звука относительно текущего времени"""
        if self._unmute_time < self._rtc.get_datetime().time() < self._mute_time:
            return SoundMode.AUDIBLE
        return SoundMode.SILENT

    def _auto_sound_mode_setting_callback(self, timer):
        """Коллбэк автоматической настройки звукового режима относительно текущего времени"""
        determined_sound_mode = self._determine_sound_mode()
        if determined_sound_mode == self._sound_mode:
            return

        if determined_sound_mode == SoundMode.AUDIBLE:
            self.unmute(check_auto_mode=False)
        else:
            self.mute(check_auto_mode=False)

    def _enable_auto_sound_mode(self):
        """Включает автоматическое определение звукового режима"""
        self._sound_mode_switch_timer.init(period=5 * 60000, callback=self._auto_sound_mode_setting_callback)

    def _disable_auto_sound_mode(self):
        """Отключает автоматическое определение звукового режима"""
        self._sound_mode_switch_timer.deinit()

    def _auto_open_mode_callback(self, timer):
        """Коллбэк отключения режима автоматического открытия двери"""
        self._disable_auto_open_mode()

    def _enable_auto_open_mode(self):
        """Включает автоматическое открытие двери"""
        self._auto_open_mode = AutoOpenMode.ENABLED
        self._auto_open_mode_timer.init(period=30 * 60000, callback=self._auto_open_mode_callback)
        self._publish_mqtt_message(self._mqtt_auto_open_mode_topic, 'ON')

    def _disable_auto_open_mode(self):
        """Отключает автоматическое открытие двери"""
        self._auto_open_mode = AutoOpenMode.DISABLED
        self._auto_open_mode_timer.deinit()
        self._publish_mqtt_message(self._mqtt_auto_open_mode_topic, 'OFF')

    def _mqtt_callback(self, _, message):
        """Обратный вызов MQTT подписки"""
        command_method_mapper = {
            'OPEN_DOOR': self.open_door,
            'REJECT_CALL': self.reject_call,
            'MUTE_SOUND': self.mute,
            'UNMUTE_SOUND': self.unmute,
            'ENABLE_AUTO_OPEN': self._enable_auto_open_mode,
            'DISABLE_AUTO_OPEN': self._disable_auto_open_mode,
        }

        message = message.decode()
        try:
            command_method_mapper[message]()
        except KeyError:
            print(f'Method for "{message}" command not found')
        except CyfralControllerException as ex:
            print(f'Cyfral controller error: {ex}')
            blinks.error_blink()

    def _connect_to_mqtt_server(self):
        """Подключается в MQTT серверу"""
        try:
            self._mqtt_client.connect()
            self._mqtt_connected = True
        except OSError as ex:
            print(f'Server connection error: {ex}')
            raise

    def _mqtt_components_state_initialization(self):
        """Инициализация первоначальных состояний MQTT компонентов"""
        self._publish_mqtt_message(self._mqtt_incoming_call_state_topic, 'OFF')

        if self._sound_mode == SoundMode.AUDIBLE:
            self._publish_mqtt_message(self._mqtt_sound_mode_state_topic, 'ON')
        else:
            self._publish_mqtt_message(self._mqtt_sound_mode_state_topic, 'OFF')

        self._publish_mqtt_message(self._mqtt_auto_open_mode_topic, 'OFF')

    def _subscribe_to_topic(self, topic_name):
        """Подписывается на MQTT топик"""
        if not self._mqtt_client.cb:
            self._mqtt_client.set_callback(self._mqtt_callback)

        try:
            self._mqtt_client.subscribe(topic_name)
        except OSError as ex:
            print(f'Topic subscription error: {ex}')
            self._mqtt_connection_error()

    def _mqtt_keepalive_ping_callback(self, timer):
        """Поддерживает соединение с MQTT сервером"""
        try:
            self._mqtt_client.ping()
        except OSError as ex:
            print(f'Keepalive ping error: {ex}')
            self._mqtt_connection_error()

    def _check_mqtt_message(self):
        """Проверяет наличие сообщения в MQTT топике"""
        try:
            self._mqtt_client.check_msg()
        except OSError as ex:
            print(f'Check message error: {ex}')
            self._mqtt_connection_error()

    def _publish_mqtt_message(self, topic: str, message: str):
        """Публикует сообщение в MQTT топик"""
        try:
            self._mqtt_client.publish(topic, message)
        except OSError as ex:
            print(f'Publishing message error: {ex} (topic: {topic}, message: {message})')
            self._mqtt_connection_error()

    def _mqtt_connection_error(self):
        """Помечает соединение с MQTT сервером как неактивное и отключает keepalive-таймер"""
        self._mqtt_connected = False
        self._mqtt_keepalive_timer.deinit()
