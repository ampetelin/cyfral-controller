class CyfralControllerException(Exception):
    """Базовое исключение контроллера домофона Cyfral"""


class SwitchSoundModeError(CyfralControllerException):
    """Ошибка переключения режима звука"""


class HandsetException(CyfralControllerException):
    """Исключения трубки домофона"""


class PickUpHandsetError(HandsetException):
    """Ошибка снятия трубки домофона"""


class HangUpHandsetError(HandsetException):
    """Ошибка повешения трубки домофона"""


class PressOpenDoorButtonError(CyfralControllerException):
    """Ошибка нажатия кнопки открытия двери"""
