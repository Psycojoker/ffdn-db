# -*- coding: utf-8 -*-

from flask import Blueprint, make_response, request, Response, current_app
from flask.views import MethodView
from collections import OrderedDict
import sys
import json
import datetime

from . import utils, db
from .models import ISP, CoveredArea


ispdbapi = Blueprint('ispdbapi', __name__)


def output_json(data, code, headers=None):
    """Makes a Flask response with a JSON encoded body"""
    def encode(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        if hasattr(obj, '__json__'):
            return obj.__json__()

    indent = 4 if not request.is_xhr else None
    dumped = json.dumps(data, indent=indent, default=encode)
    dumped += '\n'

    resp = make_response(dumped, code)
    resp.headers.extend(headers or {})
    return resp


class REST(object):
    DEFAULT_MIMETYPE = 'application/json'

    OUTPUT_MIMETYPES = {
        'application/json': output_json
    }

    @classmethod
    def accepted_mimetypes(cls, default_mime=DEFAULT_MIMETYPE):
        am=[m for m, q in request.accept_mimetypes]
        if default_mime:
            am+=[default_mime]
        return am

    @classmethod
    def match_mimetype(cls):
        for accepted_mime in cls.accepted_mimetypes():
            if accepted_mime in cls.OUTPUT_MIMETYPES:
                return accepted_mime, cls.OUTPUT_MIMETYPES[accepted_mime]

    @classmethod
    def negociated_resp(cls, data, code, headers={}):
        output_mime, output_func = cls.match_mimetype()
        resp = output_func(data, code, headers)
        resp.headers['Content-Type'] = output_mime
        return resp

    @classmethod
    def marsh_error(cls, error):
        return cls.negociated_resp({
            'error': dict(error)
        }, error.status_code)


class RESTException(Exception):
    def __init__(self, status_code, msg, error_type=None):
        super(RESTException, self).__init__()
        self.status_code = status_code
        self.message = msg
        self.error_type = error_type

    def __iter__(self):
        return {
            'error_type': self.error_type,
            'message': self.message
        }.iteritems()

    def __json__(self):
        return {
            'error': dict(self)
        }


class RESTSimpleError(RESTException):
    def __init__(self):
        pass


class ObjectNotFound(RESTSimpleError):
    status_code = 404
    message = 'Object not found'
    error_type = 'ispdb.api.ObjectNotFound'


class InternalError(RESTSimpleError):
    status_code = 500
    message = 'There was an error while processing your request'
    error_type = 'ispdb.api.InternalError'


class Resource(MethodView, REST):

    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        resp = meth(*args, **kwargs)
        if isinstance(resp, Response):
            return resp

        data, code, headers = (None,)*3
        if isinstance(resp, tuple):
            data, code, headers = resp + (None,) * (3 - len(resp))
        data = resp if data is None else data
        code = 200 if code is None else code
        headers = {} if headers is None else headers
        resp = self.negociated_resp(data, code, headers)
        return resp

    def get_range(self):
        range_ = request.args.get('range')
        if not range_:
            return None
        try:
            range_ = map(int, filter(None, range_.split(',', 1)))
            return range_
        except ValueError:
            return None

    def apply_range(self, query, range_):
        return query.slice(*range_) if len(range_) > 1 else query.offset(range_[0])

    def handle_list(self, query, cb, paginate=10, out_var=None):
        res = OrderedDict()
        res['total_items'] = query.count()

        range_ = self.get_range()
        if range_:
            query = self.apply_range(query, range_)
            items = [cb(o) for o in query]
            res['range'] = ','.join(map(str, range_))
        elif paginate:
            page = request.args.get('page', 1)
            per_page = request.args.get('per_page', paginate)
            try:
                page = int(page)
            except ValueError:
                page = 1
            try:
                per_page = int(per_page)
            except ValueError:
                per_page = paginate
            pgn = query.paginate(page, per_page=per_page, error_out=False)
            items = [cb(o) for o in pgn.items]
            res['page'] = pgn.page
            res['num_pages'] = pgn.pages
            res['per_page'] = pgn.per_page

        if out_var is None:
            out_var = query.column_descriptions[0]['name'].lower()+'s'
        res[out_var] = items
        return res


class ISPResource(Resource):
    """
    /isp/
        GET - list all ISPs

    /isp/<int:isp_id>/
        GET - return ISP with the given id
    """
    def isp_to_dict(self, isp):
        r=OrderedDict()
        r['id'] = isp.id
        r['is_ffdn_member'] = isp.is_ffdn_member
        r['json_url'] = isp.json_url
        r['date_added'] = utils.tosystemtz(isp.date_added)
        if isp.last_update_success:
            r['last_update'] = utils.tosystemtz(isp.last_update_success)
        else:
            r['last_update'] = None
        r['ispformat'] = isp.json
        return r

    def get(self, isp_id=None):
        if isp_id is not None:
            s = ISP.query.filter_by(id=isp_id, is_disabled=False).scalar()
            if not s:
                raise ObjectNotFound
            return self.isp_to_dict(s)
        else:
            s = ISP.query.filter_by(is_disabled=False)
            return self.handle_list(s, self.isp_to_dict)


class CoveredAreaResource(Resource):
    """
    /covered_area/
        GET - list all covered areas

    /covered_area/<int:area_id>/
        GET - return covered area with the given id

    /isp/<int:isp_id>/covered_area/
        GET - return covered areas for the given ISP
    """
    def ca_to_dict(self, ca):
        r=OrderedDict()
        r['id'] = ca.id
        if not self.isp_id:
            r['isp'] = OrderedDict()
            r['isp']['id'] = ca.isp_id
            r['isp']['name'] = ca.isp.name
            r['isp']['shortname'] = ca.isp.shortname
        r['name'] = ca.name
        r['geojson'] = json.loads(ca.area_geojson) if ca.area_geojson else None
        return r

    def get(self, area_id=None, isp_id=None):
        self.area_id = area_id
        self.isp_id = isp_id
        if area_id is not None:
            raise ObjectNotFound
            s = CoveredArea.query.get_or_404(area_id)
            return self.ca_to_dict(s)
        else:
            s = CoveredArea.query.filter(ISP.is_disabled==False)\
                                 .options(db.joinedload('isp'),
                                          db.defer('isp.json'),
                                          db.defer('area'),
                                          db.undefer('area_geojson'))
            if isp_id:
                if not ISP.query.filter_by(id=isp_id, is_disabled=False).scalar():
                    raise ObjectNotFound
                s = s.filter(CoveredArea.isp_id==isp_id)
            return self.handle_list(s, self.ca_to_dict, out_var='covered_areas')


@ispdbapi.route('/<path:notfound>')
def path_not_found(notfound):
    "catch all"
    return REST.marsh_error(RESTException(404, 'path not found', 'ispdb.api.PathNotFound'))


@ispdbapi.errorhandler(404)
def resource_not_found(e):
    return REST.marsh_error(RESTException(404, 'not found'))


@ispdbapi.errorhandler(RESTException)
def handle_rest_error(e):
    return REST.marsh_error(e)


@ispdbapi.errorhandler(Exception)
def handle_generic_exception(e):
    "Return a REST-formated error response instead of the standard 500 html template"
    current_app.log_exception(sys.exc_info())
    return REST.marsh_error(InternalError())


isp_view = ISPResource.as_view('isp_api')
ispdbapi.add_url_rule('/v1/isp/', defaults={'isp_id': None},
                      view_func=isp_view, methods=['GET',])
ispdbapi.add_url_rule('/v1/isp/<int:isp_id>/', view_func=isp_view,
                      methods=['GET'])

@ispdbapi.route('/v1/isp/export_urls/')
@ispdbapi.route('/v1/isp/all_your_urls_are_belong_to_us/')
def all_urls():
    """
    This resource allows to simply export all ISP-format URLs in our DB
    without pulling all ISP data.
    """
    isps = db.session.query(ISP.id, ISP.json_url).filter(ISP.json_url != None)
    return REST.negociated_resp({
        'isps': [{'id': isp.id, 'json_url': isp.json_url} for isp in isps]
    }, 200)


ca_view = CoveredAreaResource.as_view('covered_area_api')
ispdbapi.add_url_rule('/v1/covered_area/', defaults={'area_id': None},
                      view_func=ca_view, methods=['GET',])
ispdbapi.add_url_rule('/v1/covered_area/<int:area_id>/', view_func=ca_view,
                      methods=['GET'])
ispdbapi.add_url_rule('/v1/isp/<int:isp_id>/covered_areas/', view_func=ca_view,
                      methods=['GET'])
