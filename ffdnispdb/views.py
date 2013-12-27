# -*- coding: utf-8 -*-

from flask import request, redirect, url_for, abort, \
    render_template, flash, json, session, Response, Markup, \
    current_app, Blueprint
from flask.ext.babel import gettext as _, get_locale
from flask.ext.mail import Message
import itsdangerous
import docutils.core
import ispformat.specs

from datetime import datetime
from urlparse import urlunsplit
import locale
locale.setlocale(locale.LC_ALL, '')
from time import time
import os.path

from . import forms, utils
from .constants import STEPS, STEPS_LABELS, LOCALES_FLAGS
from . import db, cache, mail
from .models import ISP, ISPWhoosh, CoveredArea, RegisteredOffice
from .crawler import WebValidator, PrettyValidator


ispdb = Blueprint('ispdb', __name__)


@ispdb.route('/')
def home():
    return render_template('index.html', active_button="home")


@ispdb.route('/isp/')
def project_list():
    return render_template('project_list.html', projects=ISP.query.filter_by(is_disabled=False))


@ispdb.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@ispdb.app_errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# this needs to be cached
@ispdb.route('/isp/map_data.json', methods=['GET'])
def isp_map_data():
    isps = ISP.query.filter_by(is_disabled=False)
    data = []
    for isp in isps:
        d = dict(isp.json)
        for k in d.keys():
            if k not in ('name', 'shortname', 'coordinates'):
                del d[k]

        d['id'] = isp.id
        d['ffdn_member'] = isp.is_ffdn_member
        d['popup'] = render_template('map_popup.html', isp=isp)
        data.append(d)

    return Response(json.dumps(data), mimetype='application/json')


@ispdb.route('/isp/find_near.json', methods=['GET'])
def isp_find_near():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        abort(400)

    q = CoveredArea.containing((lat, lon))\
                   .options(db.joinedload('isp'))
    res = [[{
        'isp_id': ca.isp_id,
        'area': {
            'id': ca.id,
            'name': ca.name,
        }
    } for ca in q]]

    dst = RegisteredOffice.point.distance(db.func.MakePoint(lon, lat), 1).label('distance')
    q = db.session.query(RegisteredOffice, dst)\
                  .options(db.joinedload('isp'))\
                  .order_by('distance ASC')\
                  .limit(2)

    res.append([{
        'distance': d,
        'isp_id': r.isp.id,
    } for r, d in q])

    return Response(json.dumps(res))


@ispdb.route('/isp/<projectid>/covered_areas.json', methods=['GET'])
def isp_covered_areas(projectid):
    p = ISP.query.filter_by(id=projectid, is_disabled=False)\
                 .options(db.joinedload('covered_areas'),
                          db.defer('covered_areas.area'),
                          db.undefer('covered_areas.area_geojson'))\
                 .scalar()
    if not p:
        abort(404)
    cas = []
    for ca in p.covered_areas:
        cas.append({
            'id': ca.id,
            'name': ca.name,
            'area': json.loads(ca.area_geojson) if ca.area_geojson else None
        })
    return Response(json.dumps(cas), mimetype='application/json')


@ispdb.route('/isp/<projectid>/')
def project(projectid):
    p = ISP.query.filter_by(id=projectid, is_disabled=False).first()
    if not p:
        abort(404)
    return render_template('project_detail.html', project_row=p, project=p.json)


@ispdb.route('/isp/<projectid>/edit', methods=['GET', 'POST'])
def edit_project(projectid):
    MAX_TOKEN_AGE = 3600
    isp = ISP.query.filter_by(id=projectid, is_disabled=False).first_or_404()
    sess_token = session.get('edit_tokens', {}).get(isp.id)

    if 'token' in request.args:
        s = itsdangerous.URLSafeTimedSerializer(current_app.secret_key, salt='edit')
        try:
            r = s.loads(request.args['token'], max_age=MAX_TOKEN_AGE,
                        return_timestamp=True)
        except:
            abort(403)

        if r[0] != isp.id:
            abort(403)

        tokens = session.setdefault('edit_tokens', {})
        session.modified = True  # ITS A TARP
        tokens[r[0]] = r[1]
        # refresh page, without the token in the url
        return redirect(url_for('.edit_project', projectid=r[0]))
    elif (sess_token is None or (datetime.utcnow()-sess_token).total_seconds() > MAX_TOKEN_AGE):
        return redirect(url_for('.gen_edit_token', projectid=isp.id))

    if isp.is_local:
        form = forms.ProjectForm.edit_json(isp)
        if form.validate_on_submit():
            isp.name = form.name.data
            isp.shortname = form.shortname.data or None
            isp.json = form.to_json(isp.json)
            isp.tech_email = form.tech_email.data

            db.session.add(isp)
            db.session.commit()
            flash(_(u'Project modified'), 'info')
            return redirect(url_for('.project', projectid=isp.id))
        return render_template('edit_project_form.html', form=form)
    else:
        form = forms.ProjectJSONForm(obj=isp)
        if form.validate_on_submit():
            isp.tech_email = form.tech_email.data
            u = list(form.json_url.data)
            u[2] = '/isp.json'  # new path
            url = urlunsplit(u)
            isp.json_url = url

            db.session.add(isp)
            db.session.commit()
            flash(_(u'Project modified'), 'info')
            return redirect(url_for('.project', projectid=isp.id))
        return render_template('edit_project_json_form.html', form=form)


@ispdb.route('/isp/<projectid>/gen_edit_token', methods=['GET', 'POST'])
def gen_edit_token(projectid):
    isp = ISP.query.filter_by(id=projectid, is_disabled=False).first_or_404()
    form = forms.RequestEditToken()
    if form.validate_on_submit():  # validated
        if form.tech_email.data == isp.tech_email:
            s = itsdangerous.URLSafeTimedSerializer(current_app.secret_key, salt='edit')
            token = s.dumps(isp.id)
            msg = Message("Edit request of your ISP", sender=current_app.config['EMAIL_SENDER'])
            msg.body = """
Hello,
You are receiving this message because your are listed as technical contact for "%s" on the FFDN ISP database.

Someone asked to edit your ISP's data in our database. If it's not you, please ignore this message.

To proceed to the editing form, please click on the following link:
%s?token=%s

Note: the link is only valid for one hour from the moment we send you this email.

Thanks,
The FFDN ISP Database team
https://db.ffdn.org
            """.strip() % (isp.complete_name,
                           url_for('.edit_project', projectid=isp.id, _external=True),
                           token)
            msg.add_recipient(isp.tech_email)
            mail.send(msg)

        # if the email provided is not the correct one, we still redirect
        flash(_(u'If you provided the correct email adress, '
                'you must will receive a message shortly (check your spam folder)'), 'info')
        return redirect(url_for('.project', projectid=isp.id))

    return render_template('gen_edit_token.html', form=form)


@ispdb.route('/add-a-project', methods=['GET'])
def add_project():
    return render_template('add_project.html')


@ispdb.route('/isp/create/form', methods=['GET', 'POST'])
def create_project_form():
    form = forms.ProjectForm()
    if form.validate_on_submit():
        isp = ISP()
        isp.name = form.name.data
        isp.shortname = form.shortname.data or None
        isp.tech_email = form.tech_email.data
        isp.json = form.to_json(isp.json)

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('.project', projectid=isp.id))
    return render_template('add_project_form.html', form=form)


@ispdb.route('/isp/create/validator', methods=['GET'])
def json_url_validator():
    if 'form_json' not in session or \
       session['form_json'].get('validated', False):
        abort(403)

    v = session['form_json'].get('validator')

    if v is not None:
        if v > time()-5:
            abort(429)
    else:
        session['form_json']['validator'] = time()

    validator = WebValidator(session._get_current_object(), 'form_json')
    return Response(utils.stream_with_ctx_and_exc(
        validator(session['form_json']['url'])
    ), mimetype="text/event-stream")


@ispdb.route('/isp/create', methods=['GET', 'POST'])
def create_project_json():
    form = forms.ProjectJSONForm()
    if form.validate_on_submit():
        u = list(form.json_url.data)
        u[2] = '/isp.json'  # new path
        url = urlunsplit(u)
        session['form_json'] = {'url': url, 'tech_email': form.tech_email.data}
        return render_template('project_json_validator.html')
    return render_template('add_project_json_form.html', form=form)


@ispdb.route('/isp/create/confirm', methods=['POST'])
def create_project_json_confirm():
    if 'form_json' in session and session['form_json'].get('validated', False):
        if not forms.is_url_unique(session['form_json']['url']):
            abort(409)
        jdict = session['form_json']['jdict']
        isp = ISP()
        isp.name = jdict['name']
        if 'shortname' in jdict:
            isp.shortname = jdict['shortname']
        isp.json_url = session['form_json']['url']
        isp.json = jdict
        isp.tech_email = session['form_json']['tech_email']
        isp.last_update_attempt = session['form_json']['last_update']
        isp.last_update_success = session['form_json']['last_update']
        isp.next_update = session['form_json']['next_update']
        isp.cache_info = session['form_json']['cache_info']
        del session['form_json']

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('.project', projectid=isp.id))
    else:
        return redirect(url_for('.create_project_json'))


@ispdb.route('/isp/reactivate-validator', methods=['GET'])
def reactivate_validator():
    if 'form_reactivate' not in session or \
       session['form_reactivate'].get('validated', False):
        abort(403)

    p = ISP.query.get(session['form_reactivate']['isp_id'])
    if not p:
        abort(403)

    v = session['form_reactivate'].get('validator')

    if v is not None:
        if v > time()-5:
            abort(429)
    else:
        session['form_reactivate']['validator'] = time()

    validator = PrettyValidator(session._get_current_object(), 'form_reactivate')
    return Response(utils.stream_with_ctx_and_exc(
        validator(p.json_url, p.cache_info or {})
    ), mimetype="text/event-stream")


@ispdb.route('/isp/<projectid>/reactivate',  methods=['GET', 'POST'])
def reactivate_isp(projectid):
    """
    Allow to reactivate an ISP after it has been disabled
    because of problems with the JSON file.
    """
    p = ISP.query.filter(ISP.id == projectid, ISP.is_disabled == False,
                         ISP.update_error_strike >= 3).first_or_404()
    if request.method == 'GET':
        key = request.args.get('key')
        try:
            s = itsdangerous.URLSafeSerializer(current_app.secret_key,
                                               salt='reactivate')
            d = s.loads(key)
        except Exception:
            abort(403)

        if (len(d) != 2 or d[0] != p.id or d[1] != str(p.last_update_attempt)):
            abort(403)

        session['form_reactivate'] = {'isp_id': p.id}
        return render_template('reactivate_validator.html', isp=p)
    else:
        if 'form_reactivate' not in session or \
           not session['form_reactivate'].get('validated', False):
            abort(409)

        p = ISP.query.get(session['form_reactivate']['isp_id'])
        p.json = session['form_reactivate']['jdict']
        p.cache_info = session['form_reactivate']['cache_info']
        p.last_update_attempt = session['form_form_reactivate']['last_update']
        p.last_update_success = p.last_update_attempt

        db.session.add(p)
        db.session.commit()

        flash(_(u'Automatic updates activated'), 'info')
        return redirect(url_for('.project', projectid=p.id))


@ispdb.route('/search', methods=['GET', 'POST'])
def search():
    terms = request.args.get('q')
    if not terms:
        return redirect(url_for('.home'))

    res = ISPWhoosh.search(terms)
    return render_template('search_results.html', results=res, search_terms=terms)


@ispdb.route('/format', methods=['GET'])
def format():
    parts = cache.get('format-spec')
    if parts is None:
        spec = open(ispformat.specs.versions[0.1]).read()
        overrides = {
            'initial_header_level': 3,
        }
        parts = docutils.core.publish_parts(
            spec,
            source_path=os.path.dirname(ispformat.specs.versions[0.1]),
            destination_path=None, writer_name='html',
            settings_overrides=overrides
        )
        cache.set('format-spec', parts, timeout=60*60*24)
    return render_template('format_spec.html', spec=Markup(parts['html_body']))


@ispdb.route('/api/v1/', methods=['GET'])
def api():
    return render_template('api.html')


@ispdb.route('/humans.txt', methods=['GET'])
def humans():
    import os.path
    authors_file = os.path.join(os.path.dirname(__file__), '../AUTHORS')
    return Response(open(authors_file), mimetype='text/plain; charset=utf-8')


@ispdb.route('/site.js', methods=['GET'])
def site_js():
    l = get_locale()
    js_i18n = cache.get('site_js_%s' % (l,))
    if not js_i18n:
        js_i18n = render_template('site.js')
        cache.set('site_js_%s' % (l,), js_i18n, timeout=60*60)
    r = Response(js_i18n, headers={
        'Content-type': 'application/javascript',
        'Cache-control': 'private, max-age=3600'
    })
    r.add_etag()
    r.make_conditional(request)
    return r


@ispdb.route('/locale_selector', methods=['GET', 'POST'])
def locale_selector():
    l = current_app.config['LANGUAGES']

    if request.method == 'POST' and request.form.get('locale') in l:
        resp = redirect(url_for('.home'))
        resp.set_cookie('locale', request.form['locale'])
        return resp

    return render_template('locale_selector.html', locales=(
        (code, LOCALES_FLAGS[code], name) for code, name in l.iteritems()
    ))


#------
# Filters

@ispdb.app_template_filter('step_to_label')
def step_to_label(step):
    if step:
        return u"<a href='#' data-toggle='tooltip' data-placement='right' title='" + STEPS[step] + "'><span class='badge badge-" + STEPS_LABELS[step] + "'>" + str(step) + "</span></a>"
    else:
        return u'-'


@ispdb.app_template_filter('stepname')
def stepname(step):
    return STEPS[step]


@ispdb.app_template_filter('js_str')
def json_filter(v):
    return Markup(json.dumps(unicode(v)))


@ispdb.app_template_filter('locale_flag')
def locale_flag(l):
    return LOCALES_FLAGS.get(str(l), '_unknown')


@ispdb.app_template_global('current_locale')
def current_locale():
    return get_locale()

