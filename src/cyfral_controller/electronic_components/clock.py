from micropython import const

from datetime import Datetime

DATETIME_REG = const(0)  # 0x00-0x06
CHIP_HALT = const(128)
CONTROL_REG = const(7)  # 0x07
RAM_REG = const(8)  # 0x08-0x3F


class DS1307:
    """Driver for the DS1307 RTC."""

    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        self.weekday_start = 1
        self._halt = False

    @staticmethod
    def _dec2bcd(value):
        """Convert decimal to binary coded decimal (BCD) format"""
        return (value // 10) << 4 | (value % 10)

    @staticmethod
    def _bcd2dec(value):
        """Convert binary coded decimal (BCD) format to decimal"""
        return ((value >> 4) * 10) + (value & 0x0F)

    def set_datetime(self, datetime: Datetime) -> None:
        """Set datetime"""
        buf = bytearray(7)
        buf[0] = self._dec2bcd(datetime.second) & 0x7F  # second, msb = CH, 1=halt, 0=go
        buf[1] = self._dec2bcd(datetime.minute)
        buf[2] = self._dec2bcd(datetime.hour)
        buf[4] = self._dec2bcd(datetime.day)
        buf[5] = self._dec2bcd(datetime.month)
        buf[6] = self._dec2bcd(datetime.year - 2000)
        if self._halt:
            buf[0] |= (1 << 7)
        self.i2c.writeto_mem(self.addr, DATETIME_REG, buf)

    def get_datetime(self) -> Datetime:
        """Get datetime"""
        buf = self.i2c.readfrom_mem(self.addr, DATETIME_REG, 7)
        return Datetime(
            year=self._bcd2dec(buf[6]) + 2000,
            month=self._bcd2dec(buf[5]),
            day=self._bcd2dec(buf[4]),
            hour=self._bcd2dec(buf[2]),
            minute=self._bcd2dec(buf[1]),
            second=self._bcd2dec(buf[0] & 0x7F),
            microsecond=0
        )

    def halt(self, val=None):
        """Power up, power down or check status"""
        if val is None:
            return self._halt
        reg = self.i2c.readfrom_mem(self.addr, DATETIME_REG, 1)[0]
        if val:
            reg |= CHIP_HALT
        else:
            reg &= ~CHIP_HALT
        self._halt = bool(val)
        self.i2c.writeto_mem(self.addr, DATETIME_REG, bytearray([reg]))

    def square_wave(self, sqw=0, out=0):
        """Output square wave on pin SQ at 1Hz, 4.096kHz, 8.192kHz or 32.768kHz,
        or disable the oscillator and output logic level high/low."""
        rs0 = 1 if sqw == 4 or sqw == 32 else 0
        rs1 = 1 if sqw == 8 or sqw == 32 else 0
        out = 1 if out > 0 else 0
        sqw = 1 if sqw > 0 else 0
        reg = rs0 | rs1 << 1 | sqw << 4 | out << 7
        self.i2c.writeto_mem(self.addr, CONTROL_REG, bytearray([reg]))
