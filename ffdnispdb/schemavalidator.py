# -*- coding: utf-8 -*-

from jsonschema import Draft4Validator, RefResolver, draft4_format_checker
from jsonschema.exceptions import RefResolutionError, SchemaError, ValidationError
import json
import os.path
from urlparse import urlparse


class MyRefResolver(RefResolver):
    def resolve_remote(self, uri):
        # Prevent remote resolving
        raise RefResolutionError("LOL NOPE")


def load_schema(name):
    """
    Load a schema from ./schemas/``name``.json and return it.

    """
    schemadir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'schemas'
    )
    schemapath = os.path.join(schemadir, '%s.json' % (name,))
    with open(schemapath) as f:
        return json.load(f)


schemas={
    0.1: load_schema('isp-0.1')
}

resources={
    'http://json-schema.org/geo': load_schema('geo'),
    'http://json-schema.org/address': load_schema('address'),
    'http://json-schema.org/geojson/geojson.json#': load_schema('geojson/geojson'),
    'http://json-schema.org/geojson/geometry.json#': load_schema('geojson/geometry'),
    'http://json-schema.org/geojson/bbox.json#': load_schema('geojson/bbox'),
    'http://json-schema.org/geojson/crs.json#': load_schema('geojson/crs'),
}

def validate_diyisp(jdict):
    """
    Validate a json-object against the diyisp json-schema
    """
    if not 'version' in jdict:
        raise ValidationError(u'version is a required property')
    try:
        schema=schemas.get(jdict['version'])
    except (AttributeError, TypeError):
        raise ValidationError(u'version %r unsupported'%jdict['version'])

    v=Draft4Validator(
        schema,
        resolver=MyRefResolver.from_schema(schema, store=resources),
        format_checker=draft4_format_checker,
    )

    for err in v.iter_errors(jdict):
        yield err

    def is_valid_url(u):
        try:
            pu=urlparse(u)
        except:
            return False
        if pu.scheme not in ('', 'http', 'https'):
            return False
        if not pu.netloc:
            return False
        return True

    if 'website' in jdict and not is_valid_url(jdict['website']):
        yield ValidationError(u'%r must be an absolute HTTP URL'%u'website',
                              instance=jdict[u'website'], schema=schema[u'properties'][u'website'],
                              path=[u'website'], schema_path=[u'properties', u'website', u'description'],
                              validator=u'validate_url', validator_value=jdict['website'])

    if 'logoURL' in jdict and not is_valid_url(jdict['logoURL']):
        yield ValidationError(u'%r must be an absolute HTTP URL'%u'logoURL',
                              instance=jdict[u'logoURL'], schema=schema[u'properties'][u'logoURL'],
                              path=[u'logoURL'], schema_path=[u'properties', u'logoURL', u'description'],
                              validator=u'validate_url', validator_value=jdict['logoURL'])

    sch=schema[u'properties'][u'otherWebsites'][u'patternProperties'][u'^.+$']
    for name, url in jdict.get('otherWebsites', {}).iteritems():
        if is_valid_url(url):
            continue
        yield ValidationError(u'%r must be an absolute HTTP URL'%name,
                              instance=url, schema=sch, path=[u'otherWebsite', name],
                              schema_path=[u'properties', u'otherWebsites', u'patternProperties', u'^.+$', 'description'],
                              validator=u'validate_url', validator_value=url)


if __name__ == '__main__':
    import sys
    j=json.load(open(sys.argv[1]))
    for e in validate_diyisp(j):
        print e


