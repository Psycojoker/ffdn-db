# -*- coding: utf-8 -*-

from decimal import Decimal
import json
from . import db
from datetime import datetime
from sqlalchemy.types import TypeDecorator, VARCHAR
from sqlalchemy.ext.mutable import MutableDict


class fakefloat(float):
    def __init__(self, value):
        self._value = value
    def __repr__(self):
        return str(self._value)

def defaultencode(o):
    if isinstance(o, Decimal):
        # Subclass float with custom repr?
        return fakefloat(o)
    raise TypeError(repr(o) + " is not JSON serializable")


class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value, default=defaultencode)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class ISP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True, unique=True)
    shortname = db.Column(db.String(12), index=True, unique=True)
    is_ffdn_member = db.Column(db.Boolean, default=False)
    is_disabled = db.Column(db.Boolean, default=False) # True = ISP will not appear
    url = db.Column(db.String)
    last_update_success = db.Column(db.DateTime)
    last_update_attempt = db.Column(db.DateTime)
    is_updatable = db.Column(db.Boolean, default=True) # set to False to disable JSON-URL updates
    tech_email = db.Column(db.String)
    cache_info = db.Column(db.Text)
    json = db.Column(MutableDict.as_mutable(JSONEncodedDict))

    def __init__(self, *args, **kwargs):
        super(ISP, self).__init__(*args, **kwargs)
        self.json={}

    def covered_areas_names(self):
        return [c['name'] for c in self.json.get('coveredAreas', [])]

    @staticmethod
    def str2date(_str):
        d=None
        try:
            d=datetime.strptime(_str, '%Y-%m-%d')
        except ValueError:
            pass

        if d is None:
            try:
                d=datetime.strptime(_str, '%Y-%m')
            except ValueError:
                pass
        return d

    def __repr__(self):
        return '<ISP %r>' % (self.shortname if self.shortname else self.name,)


