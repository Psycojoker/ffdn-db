# -*- coding: utf-8 -*-

from flask import current_app
from collections import OrderedDict
from datetime import datetime
import pytz
import json



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


def utcnow():
    """
    Return the current UTC date and time as a datetime object with proper tzinfo.
    """
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def tosystemtz(d):
    """
    Convert the UTC datetime ``d`` to the system time zone as defined in the config
    """
    return d.astimezone(pytz.timezone(current_app.config['SYSTEM_TIME_ZONE']))
