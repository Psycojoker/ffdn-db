# -*- coding: utf-8 -*-

from flask import current_app
from flask.globals import _request_ctx_stack
from collections import OrderedDict
from datetime import datetime
from urlparse import urlunsplit
import pytz
import json
import sys
from . import db



def dict_to_geojson(d_in):
    """
    Encode a dict representing a GeoJSON object into a JSON string.
    This is needed because spatialite's GeoJSON parser is not really
    JSON-compliant and it fails when keys are not in the right order.
    """
    d=OrderedDict()
    d['type']=d_in['type']

    if 'crs' in d_in:
        d['crs']=d_in['crs']
    # our spatialite geo column is defined with EPSG SRID 4326 (WGS 84)
    d['crs'] = {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:EPSG:4326'}}

    if 'bbox' in d_in:
        d['bbox']=d_in['bbox']

    d['coordinates']=d_in['coordinates']

    return json.dumps(d)


def check_geojson_spatialite(_gjson):
    """
    Checks if a GeoJSON dict is understood by spatialite

    >>> check_geojson_spatialite({'type': 'NOPE', 'coordinates': []})
    False
    >>> check_geojson_spatialite({'type': 'Polygon', 'coordinates': [
    ...    [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]
    ... ]})
    True
    """
    gjson=dict_to_geojson(_gjson)
    return bool(db.session.query(db.func.GeomFromGeoJSON(gjson) != None).first()[0])


def utcnow():
    """
    Return the current UTC date and time as a datetime object with proper tzinfo.
    """
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def tosystemtz(d):
    """
    Convert the UTC datetime ``d`` to the system time zone defined in the settings
    """
    return d.astimezone(pytz.timezone(current_app.config['SYSTEM_TIME_ZONE']))


def filesize_fmt(num):
    fmt = lambda num, unit: "%s %s" % (format(num, '.2f').rstrip('0').rstrip('.'), unit)
    for x in ['bytes', 'KiB', 'MiB', 'GiB']:
        if num < 1024.0:
            return fmt(num, x)
        num /= 1024.0
    return fmt(num, 'TiB')


def stream_with_ctx_and_exc(generator_or_function):
    """
    taken from flask's code, added exception logging
    """
    try:
        gen = iter(generator_or_function)
    except TypeError:
        def decorator(*args, **kwargs):
            gen = generator_or_function()
            return stream_with_context(gen)
        return update_wrapper(decorator, generator_or_function)

    def generator():
        ctx = _request_ctx_stack.top
        if ctx is None:
            raise RuntimeError('Attempted to stream with context but '
                'there was no context in the first place to keep around.')
        with ctx:
            # Dummy sentinel.  Has to be inside the context block or we're
            # not actually keeping the context around.
            yield None

            # The try/finally is here so that if someone passes a WSGI level
            # iterator in we're still running the cleanup logic.  Generators
            # don't need that because they are closed on their destruction
            # automatically.
            try:
                for item in gen:
                    yield item
            except Exception as e:
                exc_type, exc_value, tb = sys.exc_info()
                current_app.log_exception((exc_type, exc_value, tb))
            finally:
                if hasattr(gen, 'close'):
                    gen.close()

    # The trick is to start the generator.  Then the code execution runs until
    # the first dummy None is yielded at which point the context was already
    # pushed.  This item is discarded.  Then when the iteration continues the
    # real generator is executed.
    wrapped_g = generator()
    next(wrapped_g)
    return wrapped_g


def make_ispjson_url(split_url):
    """
    Take a tuple as returned by urlsplit and return the
    isp.json url for that domain

    >>> from urlparse import urlsplit
    >>> make_ispjson_url(urlsplit('http://isp.com'))
    'http://isp.com/isp.json'
    """
    u = list(split_url)
    u[2] = '/isp.json'  # new path
    return urlunsplit(u)
