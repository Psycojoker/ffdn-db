# -*- coding: utf-8 -*-

from flask import current_app
from collections import OrderedDict
from datetime import datetime
import pytz
import json
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
