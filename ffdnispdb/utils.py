# -*- coding: utf-8 -*-

from collections import OrderedDict
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

