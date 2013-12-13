# -*- coding: utf-8 -*-

from decimal import Decimal
import json
import os
import itertools
from datetime import datetime
import pytz
from . import db
from .utils import dict_to_geojson, utcnow
from flask import current_app
import flask_sqlalchemy
from sqlalchemy.types import TypeDecorator, VARCHAR, DateTime
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import event
import geoalchemy as geo
import whoosh
from whoosh import fields, index, qparser


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


class UTCDateTime(TypeDecorator):

    impl = DateTime

    def process_bind_param(self, value, engine):
        if value is not None:
            return value.astimezone(pytz.utc)

    def process_result_value(self, value, engine):
        if value is not None:
            return datetime(value.year, value.month, value.day,
                            value.hour, value.minute, value.second,
                            value.microsecond, tzinfo=pytz.utc)


class ISP(db.Model):
    __tablename__ = 'isp'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True, unique=True)
    shortname = db.Column(db.String(12), index=True, unique=True)
    is_ffdn_member = db.Column(db.Boolean, default=False)
    is_disabled = db.Column(db.Boolean, default=False) # True = ISP will not appear
    json_url = db.Column(db.String)
    last_update_success = db.Column(UTCDateTime)
    last_update_attempt = db.Column(UTCDateTime)
    update_error_strike = db.Column(db.Integer, default=0) # if >= 3; then updates are disabled
    next_update = db.Column(UTCDateTime, default=utcnow)
    tech_email = db.Column(db.String)
    cache_info = db.Column(MutableDict.as_mutable(JSONEncodedDict))
    json = db.Column(MutableDict.as_mutable(JSONEncodedDict))
    covered_areas = db.relationship('CoveredArea', backref='isp')
#    covered_areas_query = db.relationship('CoveredArea', lazy='dynamic')
    registered_office = db.relationship('RegisteredOffice', uselist=False, backref='isp')

    def __init__(self, *args, **kwargs):
        super(ISP, self).__init__(*args, **kwargs)
        self.json={}

    def pre_save(self, *args):
        if 'name' in self.json:
            assert self.name == self.json['name']

        if 'shortname' in self.json:
            assert self.shortname == self.json['shortname']

        if db.inspect(self).attrs.json.history.has_changes():
            self._sync_covered_areas()

    def _sync_covered_areas(self):
        """
        Called to synchronise between json['coveredAreas'] and the
        covered_areas table, when json was modified.
        """
        # delete current covered areas & registered office
        CoveredArea.query.filter_by(isp_id=self.id).delete()
        RegisteredOffice.query.filter_by(isp_id=self.id).delete()

        for ca_js in self.json.get('coveredAreas', []):
            ca=CoveredArea()
            ca.name=ca_js['name']
            area=ca_js.get('area')
            ca.area=db.func.CastToMultiPolygon(
                db.func.GeomFromGeoJSON(dict_to_geojson(area))
            ) if area else None
            self.covered_areas.append(ca)

        coords=self.json.get('coordinates')
        if coords:
            self.registered_office=RegisteredOffice(
                point=db.func.MakePoint(coords['longitude'], coords['latitude'], 4326)
            )


    def covered_areas_names(self):
        return [c['name'] for c in self.json.get('coveredAreas', [])]

    @property
    def is_local(self):
        return self.json_url is None

    @property
    def complete_name(self):
        if 'shortname' in self.json:
            return u'%s (%s)'%(self.json['shortname'], self.json['name'])
        else:
            return u'%s'%self.json['name']

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
        return u'<ISP %r>' % (self.shortname if self.shortname else self.name,)


class CoveredArea(db.Model):
    __tablename__ = 'covered_areas'
    id = db.Column(db.Integer, primary_key=True)
    isp_id = db.Column(db.Integer, db.ForeignKey('isp.id'))
    name = db.Column(db.String)
    area = geo.GeometryColumn(geo.MultiPolygon(2))
    area_geojson = db.column_property(db.func.AsGeoJSON(db.literal_column('area')), deferred=True)

    @classmethod
    def containing(cls, coords):
        """
        Return CoveredAreas containing point (lat,lon)
        """
        return cls.query.filter(
            cls.area != None,
            cls.area.gcontains(db.func.MakePoint(coords[1], coords[0])) == 1
        )

    def __repr__(self):
        return u'<CoveredArea %r>' % (self.name,)

geo.GeometryDDL(CoveredArea.__table__)


class RegisteredOffice(db.Model):
    __tablename__ = 'registered_offices'
    id = db.Column(db.Integer, primary_key=True)
    isp_id = db.Column(db.Integer, db.ForeignKey('isp.id'))
    point = geo.GeometryColumn(geo.Point(0))

geo.GeometryDDL(RegisteredOffice.__table__)

@event.listens_for(db.metadata, 'before_create')
def init_spatialite_metadata(target, conn, **kwargs):
    conn.execute('SELECT InitSpatialMetaData(1)')


def pre_save_hook(sess):
    for v in itertools.chain(sess.new, sess.dirty):
        if hasattr(v, 'pre_save') and hasattr(v.pre_save, '__call__'):
            v.pre_save(sess)


class ISPWhoosh(object):
    """
    Helper class to index the ISP model with Whoosh to allow full-text search
    """
    schema = fields.Schema(
        id=fields.ID(unique=True, stored=True),
        is_ffdn_member=fields.BOOLEAN(),
        is_disabled=fields.BOOLEAN(),
        name=fields.TEXT(),
        shortname=fields.TEXT(),
        description=fields.TEXT(),
        covered_areas=fields.KEYWORD(scorable=True, commas=True, lowercase=True),
        step=fields.NUMERIC(signed=False),
    )

    primary_key=schema._fields['id']

    @staticmethod
    def get_index_dir():
        return current_app.config.get('WHOOSH_INDEX_DIR', 'whoosh')

    @classmethod
    def get_index(cls):
        idxdir=cls.get_index_dir()
        if index.exists_in(idxdir):
            idx = index.open_dir(idxdir)
        else:
            if not os.path.exists(idxdir):
                os.makedirs(idxdir)
            idx = index.create_in(idxdir, cls.schema)
        return idx

    @classmethod
    def _search(cls, s, terms):
        return s.search(qparser.MultifieldParser([
            'name', 'shortname', 'description', 'covered_areas'
        ], schema=cls.schema).parse(terms),
           mask=whoosh.query.Term('is_disabled', True))

    @classmethod
    def search(cls, terms):
        with ISPWhoosh.get_index().searcher() as s:
            sres=cls._search(s, terms)
            ranks={}
            for rank, r in enumerate(sres):
                ranks[r['id']]=rank

            if not len(ranks):
                return []

            _res=ISP.query.filter(ISP.id.in_(ranks.keys()))

        return sorted(_res, key=lambda r: ranks[r.id])

    @classmethod
    def update_document(cls, writer, model):
        kw={
            'id': unicode(model.id),
            '_stored_id': model.id,
            'is_ffdn_member': model.is_ffdn_member,
            'is_disabled': model.is_disabled,
            'name': model.name,
            'shortname': model.shortname,
            'description': model.json.get('description'),
            'covered_areas': model.covered_areas_names(),
            'step': model.json.get('progressStatus')
        }
        writer.update_document(**kw)

    @classmethod
    def _after_flush(cls, app, changes):
        isp_changes = []
        for change in changes:
            if change[0].__class__ == ISP:
                update = change[1] in ('update', 'insert')
                isp_changes.append((update, change[0]))

        if not len(changes):
            return

        idx=cls.get_index()
        with idx.writer() as writer:
            for update, model in isp_changes:
                if update:
                    cls.update_document(writer, model)
                else:
                    writer.delete_by_term(cls.primary_key, model.id)


flask_sqlalchemy.models_committed.connect(ISPWhoosh._after_flush)
event.listen(flask_sqlalchemy.Session, 'before_commit', pre_save_hook)

