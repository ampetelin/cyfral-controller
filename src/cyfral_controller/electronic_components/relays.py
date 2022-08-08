from machine import Pin


class RelayState:
    """Состояние реле"""
    DISABLED = 0
    ENABLED = 1


class Relay:
    """Реле"""

    def __init__(self, control_pin: int):
        self.state = RelayState.DISABLED
        self._machine_control_pin = Pin(control_pin, Pin.OUT, value=0)

    def enable(self):
        """Включить реле"""
        self.state = RelayState.ENABLED
        self._machine_control_pin.on()

    def disable(self):
        """Выключить реле"""
        self.state = RelayState.DISABLED
        self._machine_control_pin.off()

    def switch(self):
        """Переключить состояние реле"""
        if self.state == RelayState.DISABLED:
            self.enable()
        else:
            self.disable()


class ControlOptocoupler(Relay):
    """Управляющая оптопара"""


class ControlledOptocoupler:
    """Управляемая оптопара"""

    def __init__(self, state_pin: int):
        self._machine_state_pin = Pin(state_pin, Pin.IN)

    @property
    def state(self) -> int:
        return self._machine_state_pin.value()
