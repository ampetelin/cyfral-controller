MINYEAR = 1
MAXYEAR = 9999
_MAXORDINAL = 3652059
_DAYS_IN_MONTH = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DAYS_BEFORE_MONTH = [-1]
dbm = 0
for dim in _DAYS_IN_MONTH[1:]:
    _DAYS_BEFORE_MONTH.append(dbm)
    dbm += dim
del dbm, dim


def _compare(x, y) -> int:
    return 0 if x == y else 1 if x > y else -1


def _check_int_field(*args):
    for item in args:
        if not isinstance(item, int):
            raise TypeError(f'an integer is required (got type {type(item).__name__})')


def _is_leap(year) -> bool:
    """year -> 1 if leap year, else 0"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_before_year(year):
    """year -> number of days before January 1st of year."""
    y = year - 1
    return y * 365 + y // 4 - y // 100 + y // 400


def _days_before_month(year, month):
    """year, month -> number of days in year preceding first day of month."""
    assert 1 <= month <= 12, 'month must be in 1..12'
    return _DAYS_BEFORE_MONTH[month] + (month > 2 and _is_leap(year))


def _days_in_month(year, month) -> int:
    """year, month -> number of days in that month in that year"""
    assert 1 <= month <= 12, month
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month]


def _ymd2ord(year, month, day):
    """year, month, day -> ordinal, considering 01-Jan-0001 as day 1."""
    assert 1 <= month <= 12, 'month must be in 1..12'
    dim = _days_in_month(year, month)
    assert 1 <= day <= dim, ('day must be in 1..%d' % dim)
    return (_days_before_year(year) +
            _days_before_month(year, month) +
            day)


_DI400Y = _days_before_year(401)
_DI100Y = _days_before_year(101)
_DI4Y = _days_before_year(5)


def _ord2ymd(n):
    """ordinal -> (year, month, day), considering 01-Jan-0001 as day 1."""
    n -= 1
    n400, n = divmod(n, _DI400Y)
    year = n400 * 400 + 1
    n100, n = divmod(n, _DI100Y)
    n4, n = divmod(n, _DI4Y)
    n1, n = divmod(n, 365)

    year += n100 * 100 + n4 * 4 + n1
    if n1 == 4 or n100 == 4:
        assert n == 0
        return year - 1, 12, 31

    leapyear = n1 == 3 and (n4 != 24 or n100 == 3)
    assert leapyear == _is_leap(year)
    month = (n + 50) >> 5
    preceding = _DAYS_BEFORE_MONTH[month] + (month > 2 and leapyear)
    if preceding > n:
        month -= 1
        preceding -= _DAYS_IN_MONTH[month] + (month == 2 and leapyear)
    n -= preceding
    assert 0 <= n < _days_in_month(year, month)

    return year, month, n + 1


def _check_date_fields(year, month, day):
    _check_int_field(year, month, day)
    if not MINYEAR <= year <= MAXYEAR:
        raise ValueError(f'year must be in {MINYEAR}..{MAXYEAR}', year)
    if not 1 <= month <= 12:
        raise ValueError('month must be in 1..12', month)
    dim = _days_in_month(year, month)
    if not 1 <= day <= dim:
        raise ValueError(f'day must be in 1..{dim}', day)


def _check_time_fields(hour, minute, second, microsecond):
    _check_int_field(hour, minute, second, microsecond)
    if not 0 <= hour <= 23:
        raise ValueError('hour must be in 0..23', hour)
    if not 0 <= minute <= 59:
        raise ValueError('minute must be in 0..59', minute)
    if not 0 <= second <= 59:
        raise ValueError('second must be in 0..59', second)
    if not 0 <= microsecond <= 999999:
        raise ValueError('microsecond must be in 0..999999', microsecond)


class Timedelta:
    __slots__ = '_days', '_seconds', '_microseconds'

    def __new__(cls, days: int = 0, seconds: int = 0, microseconds: int = 0, milliseconds: int = 0, minutes: int = 0,
                hours: int = 0, weeks: int = 0):
        _check_int_field(days, seconds, microseconds, milliseconds, minutes, hours, weeks)

        days += weeks * 7
        seconds += minutes * 60 + hours * 3600
        microseconds += milliseconds * 1000

        d = days
        s = 0

        days, seconds = divmod(seconds, 24 * 3600)
        d += days
        s += seconds

        seconds, microseconds = divmod(microseconds, 1000000)
        days, seconds = divmod(seconds, 24 * 3600)
        d += days
        s += seconds

        seconds, us = divmod(microseconds, 1000000)
        s += seconds
        days, s = divmod(s, 24 * 3600)
        d += days

        assert isinstance(d, int)
        if abs(d) > 999999999:
            raise OverflowError("timedelta # of days is too large: %d" % d)
        assert isinstance(s, int) and 0 <= s < 24 * 3600
        assert isinstance(us, int) and 0 <= us < 1000000

        self = object.__new__(cls)
        self._days = d
        self._seconds = s
        self._microseconds = us

        return self

    def total_seconds(self):
        return ((self._days * 86400 + self._seconds) * 10 ** 6 + self._microseconds) / 10 ** 6

    @property
    def days(self):
        return self._days

    @property
    def seconds(self):
        return self._seconds

    @property
    def microseconds(self):
        return self._microseconds

    def __add__(self, other):
        if isinstance(other, Timedelta):
            return Timedelta(self._days + other._days,
                             self._seconds + other._seconds,
                             self._microseconds + other._microseconds)
        return NotImplemented

    __radd__ = __add__

    def __neg__(self):
        return Timedelta(-self._days, -self._seconds, -self._microseconds)

    def __str__(self):
        mm, ss = divmod(self._seconds, 60)
        hh, mm = divmod(mm, 60)
        s = "%d:%02d:%02d" % (hh, mm, ss)
        if self._days:
            def plural(n):
                return n, abs(n) != 1 and "s" or ""

            s = ("%d day%s, " % plural(self._days)) + s
        if self._microseconds:
            s = s + ".%06d" % self._microseconds
        return s


class Time:
    __slots__ = '_hour', '_minute', '_second', '_microsecond'

    def __new__(cls, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0):
        _check_time_fields(hour, minute, second, microsecond)
        self = object.__new__(cls)
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond

        return self

    def isoformat(self) -> str:
        return "{hour:02d}:{minute:02d}:{second:02d}.{microsecond:06d}".format(
            hour=self._hour,
            minute=self._minute,
            second=self._second,
            microsecond=self._microsecond,
        )

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    @property
    def second(self) -> int:
        return self._second

    @property
    def microsecond(self) -> int:
        return self._microsecond

    def _compare(self, other):
        if not isinstance(other, Time):
            raise TypeError(f"can't compare '{type(self).__name__}' to '{type(other).__name__}'")

        return _compare((self._hour, self._minute, self._second, self._microsecond),
                        (other._hour, other._minute, other._second, other._microsecond))

    def __lt__(self, other):
        """x<y"""
        return self._compare(other) < 0

    def __le__(self, other):
        """x<=y"""
        return self._compare(other) <= 0

    def __eq__(self, other):
        """x==y"""
        return self._compare(other) == 0

    def __gt__(self, other):
        """x>y"""
        return self._compare(other) > 0

    def __ge__(self, other):
        """x>=y"""
        return self._compare(other) >= 0

    def __str__(self):
        return self.isoformat()


class Date:
    __slots__ = '_year', '_month', '_day'

    def __new__(cls, year: int, month: int, day: int):
        _check_date_fields(year, month, day)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._day = day

        return self

    @classmethod
    def fromordinal(cls, n):
        y, m, d = _ord2ymd(n)
        return cls(y, m, d)

    def isoformat(self) -> str:
        return "{year:04d}-{month:02d}-{day:02d}".format(year=self._year, month=self._month, day=self._day)

    def toordinal(self):
        return _ymd2ord(self._year, self._month, self._day)

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def day(self) -> int:
        return self._day

    def _compare(self, other):
        if not isinstance(other, Date):
            raise TypeError(f"can't compare '{type(self).__name__}' to '{type(other).__name__}'")

        return _compare((self._year, self._month, self._day), (other._year, other._month, other._day))

    def __lt__(self, other):
        """x<y"""
        return self._compare(other) < 0

    def __le__(self, other):
        """x<=y"""
        return self._compare(other) <= 0

    def __eq__(self, other):
        """x==y"""
        return self._compare(other) == 0

    def __gt__(self, other):
        """x>y"""
        return self._compare(other) > 0

    def __ge__(self, other):
        """x>=y"""
        return self._compare(other) >= 0

    def __str__(self):
        return self.isoformat()

    def __add__(self, other):
        """Add a date to a timedelta."""
        if not isinstance(other, Timedelta):
            return NotImplemented
        o = self.toordinal() + other.days
        if 0 < o <= _MAXORDINAL:
            return type(self).fromordinal(o)
        raise OverflowError("result out of range")

    __radd__ = __add__

    def __sub__(self, other):
        """Subtract two dates, or a date and a timedelta."""
        if isinstance(other, Timedelta):
            return self + Timedelta(-other.days)
        if isinstance(other, Date):
            days1 = self.toordinal()
            days2 = other.toordinal()
            return Timedelta(days1 - days2)
        return NotImplemented


class Datetime(Date):
    __slots__ = Date.__slots__ + Time.__slots__

    def __new__(cls, year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0,
                microsecond: int = 0):
        _check_date_fields(year, month, day)
        _check_time_fields(hour, minute, second, microsecond)
        self = object.__new__(cls)
        self._year = year
        self._month = month
        self._day = day
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond

        return self

    def isoformat(self, sep='T') -> str:
        return "{year:04d}-{month:02d}-{day:02d}{sep}{hour:02d}:{minute:02d}:{second:02d}.{microsecond:06d}".format(
            year=self._year,
            month=self._month,
            day=self._day,
            sep=sep,
            hour=self._hour,
            minute=self._minute,
            second=self._second,
            microsecond=self._microsecond
        )

    @classmethod
    def from_internal_rtc_format(cls, datetime: tuple):
        return cls(datetime[0], datetime[1], datetime[2], datetime[4], datetime[5], datetime[6])

    @classmethod
    def combine(cls, date, time):
        if not isinstance(date, Date):
            raise TypeError("date argument must be a date instance")
        if not isinstance(time, Time):
            raise TypeError("time argument must be a time instance")
        return cls(date.year, date.month, date.day, time.hour, time.minute, time.second, time.microsecond)

    def date(self) -> Date:
        return Date(self._year, self._month, self._day)

    def time(self) -> Time:
        return Time(self._hour, self._minute, self._second, self._microsecond)

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    @property
    def second(self) -> int:
        return self._second

    @property
    def microsecond(self) -> int:
        return self._microsecond

    def _compare(self, other):
        if not isinstance(other, Datetime):
            raise TypeError(f"can't compare '{type(self).__name__}' to '{type(other).__name__}'")

        return _compare((self._year, self._month, self._day,
                         self._hour, self._minute, self._second,
                         self._microsecond),
                        (other._year, other._month, other._day,
                         other._hour, other._minute, other._second,
                         other._microsecond))

    def __str__(self):
        return self.isoformat(sep=' ')

    def __add__(self, other):
        """Add a datetime and a timedelta."""
        if not isinstance(other, Timedelta):
            return NotImplemented
        delta = Timedelta(self.toordinal(),
                          hours=self._hour,
                          minutes=self._minute,
                          seconds=self._second,
                          microseconds=self._microsecond)
        delta += other
        hour, rem = divmod(delta.seconds, 3600)
        minute, second = divmod(rem, 60)
        if 0 < delta.days <= _MAXORDINAL:
            return type(self).combine(Date.fromordinal(delta.days), Time(hour, minute, second, delta.microseconds))
        raise OverflowError("result out of range")

    __radd__ = __add__

    def __sub__(self, other):
        """Subtract two datetimes, or a datetime and a timedelta."""
        if not isinstance(other, Datetime):
            if isinstance(other, Timedelta):
                return self + -other
            return NotImplemented

        days1 = self.toordinal()
        days2 = other.toordinal()
        secs1 = self._second + self._minute * 60 + self._hour * 3600
        secs2 = other._second + other._minute * 60 + other._hour * 3600

        return Timedelta(days1 - days2, secs1 - secs2, self._microsecond - other._microsecond)
