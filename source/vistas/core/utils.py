import asyncio
import datetime
import json
import platform
import sys
from functools import wraps

import os

import wx


def get_platform():
    """ Utility function for determining the current operating system. """
    return 'macos' if platform.uname().system == 'Darwin' else 'windows'


def get_config_dir():
    if get_platform() == 'macos':
        return os.path.join(wx.StandardPaths.Get().UserLocalDataDir, 'VISTAS')
    else:
        return os.path.join(wx.StandardPaths.Get().UserConfigDir, 'VISTAS')


class DatetimeEncoder(json.JSONEncoder):
    """
    Converts a python object, where datetime and timedelta objects are converted
    into objects that can be decoded using the DatetimeDecoder.
    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {
              '__type__': 'datetime',
              'year': obj.year,
              'month': obj.month,
              'day': obj.day,
              'hour': obj.hour,
              'minute': obj.minute,
              'second': obj.second,
              'microsecond': obj.microsecond,
            }

        elif isinstance(obj, datetime.timedelta):
            return {
                '__type__': 'timedelta',
                'days': obj.days,
                'seconds': obj.seconds,
                'microseconds': obj.microseconds,
              }

        else:
            return json.JSONEncoder.default(self, obj)


class DatetimeDecoder(json.JSONDecoder):
    """
    Converts a json string, where datetime and timedelta objects were converted
    into objects using the DatetimeEncoder, back into a python object.
    """

    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d):
        if '__type__' not in d:
            return d

        type = d.pop('__type__')
        if type == 'datetime':
            return datetime.datetime(**d)
        elif type == 'timedelta':
            return datetime.timedelta(**d)
        else:
            # Oops... better put this back together.
            d['__type__'] = type
            return d


def asyncio_guard(func):
    """ Wraps a function to ensure an event loop has been set for the current thread """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            asyncio.get_event_loop()
        except:
            if sys.platform == 'win32':
                asyncio.set_event_loop(asyncio.ProactorEventLoop())
            else:
                asyncio.set_event_loop(asyncio.SelectorEventLoop())
        return func(*args, **kwargs)
    return wrapper
