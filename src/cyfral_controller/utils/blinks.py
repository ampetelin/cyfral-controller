import time

import machine

onboard_led = machine.Pin(2, machine.Pin.OUT, value=1)


def error_blink() -> None:
    for i in range(2):
        onboard_led.off()
        time.sleep_ms(200)
        onboard_led.on()
        time.sleep_ms(200)
