# -*- coding: utf-8 -*-

from flask import request, g, redirect, url_for, abort, \
    render_template, flash, json, session, Response, Markup
from flask.ext.babel import gettext as _
import itsdangerous
import docutils.core
import ispformat.specs

from datetime import date, time, timedelta, datetime
from urlparse import urlunsplit
import locale
locale.setlocale(locale.LC_ALL, '')
from time import time
import os.path

from . import forms
from .constants import *
from . import app, db, cache
from .models import ISP, ISPWhoosh
from .crawler import WebValidator, PrettyValidator


@app.route('/')
def home():
    return render_template('index.html', active_button="home")


@app.route('/isp/')
def project_list():
    return render_template('project_list.html', projects=ISP.query.filter_by(is_disabled=False))

# this needs to be cached
@app.route('/isp/map_data.json', methods=['GET'])
def isp_map_data():
    isps=ISP.query.filter_by(is_disabled=False)
    data=[]
    for isp in isps:
        d=dict(isp.json)
        for k in d.keys():
            if k not in ('name', 'shortname', 'coordinates'):
                del d[k]

        d['id']=isp.id
        d['ffdn_member']=isp.is_ffdn_member
        d['popup']=render_template('map_popup.html', isp=isp)
        data.append(d)

    return Response(json.dumps(data), mimetype='application/json')


@app.route('/isp/<projectid>/covered_areas.json', methods=['GET'])
def isp_covered_areas(projectid):
    p=ISP.query.filter_by(id=projectid, is_disabled=False).first()
    if not p:
        abort(404)
    return Response(json.dumps(p.json['coveredAreas']), mimetype='application/json')


@app.route('/isp/<projectid>/')
def project(projectid):
    p=ISP.query.filter_by(id=projectid, is_disabled=False).first()
    if not p:
        abort(404)
    return render_template('project_detail.html', project_row=p, project=p.json)


@app.route('/isp/<projectid>/edit', methods=['GET', 'POST'])
def edit_project(projectid):
    isp=ISP.query.filter_by(id=projectid, is_disabled=False).first()
    if not isp:
        abort(404)
    form = forms.ProjectForm.edit_json(isp.json)
    if form.validate_on_submit():
        isp.name = form.name.data
        isp.shortname = form.shortname.data or None
        isp.json=form.to_json(isp.json)

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project modified'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    return render_template('project_form.html', form=form, project=isp)


@app.route('/add-a-project', methods=['GET'])
def add_project():
    return render_template('add_project.html')


@app.route('/isp/create/form', methods=['GET', 'POST'])
def create_project_form():
    form = forms.ProjectForm()
    if form.validate_on_submit():
        isp=ISP()
        isp.name = form.name.data
        isp.shortname = form.shortname.data or None
        isp.tech_email = form.tech_email.data
        isp.json=form.to_json(isp.json)

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    return render_template('project_form.html', form=form)


@app.route('/isp/create/validator', methods=['GET'])
def json_url_validator():
    if 'form_json' not in session or \
       session['form_json'].get('validated', False):
        abort(403)

    v=session['form_json'].get('validator')

    if v is not None:
        if v > time()-5:
            abort(429)
    else:
        session['form_json']['validator']=time()

    validator=WebValidator(session._get_current_object(), 'form_json')
    return Response(validator(session['form_json']['url']),
                    mimetype="text/event-stream")


@app.route('/isp/create', methods=['GET', 'POST'])
def create_project_json():
    form = forms.ProjectJSONForm()
    if form.validate_on_submit():
        u=list(form.url.data)
        u[2]='/isp.json' # new path
        url=urlunsplit(u)
        session['form_json'] = {'url': url, 'tech_email': form.tech_email.data}
        return render_template('project_json_validator.html')
    return render_template('project_json_form.html', form=form)


@app.route('/isp/create/confirm', methods=['POST'])
def create_project_json_confirm():
    if 'form_json' in session and session['form_json'].get('validated', False):
        if not forms.is_url_unique(session['form_json']['url']):
            abort(409)
        jdict=session['form_json']['jdict']
        isp=ISP()
        isp.name=jdict['name']
        if 'shortname' in jdict:
            isp.shortname=jdict['shortname']
        isp.json_url=session['form_json']['url']
        isp.json=jdict
        isp.tech_email=session['form_json']['tech_email']
        del session['form_json']

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    else:
        return redirect(url_for('create_project_json'))


@app.route('/isp/reactivate-validator', methods=['GET'])
def reactivate_validator():
    if 'form_reactivate' not in session or \
       session['form_reactivate'].get('validated', False):
        abort(403)

    p=ISP.query.get(session['form_reactivate']['isp_id'])
    if not p:
        abort(403)

    v=session['form_reactivate'].get('validator')

    if v is not None:
        if v > time()-5:
            abort(429)
    else:
        session['form_reactivate']['validator']=time()

    validator=PrettyValidator(session._get_current_object(), 'form_reactivate')
    return Response(validator(p.json_url, p.cache_info or {}),
                    mimetype="text/event-stream")


@app.route('/isp/<projectid>/reactivate',  methods=['GET', 'POST'])
def reactivate_isp(projectid):
    """
    Allow to reactivate an ISP after it has been disabled
    because of problems with the JSON file.
    """
    p=ISP.query.filter(ISP.id==projectid, ISP.is_disabled==False,
                       ISP.update_error_strike>=3).first_or_404()
    if request.method == 'GET':
        key = request.args.get('key')
        try:
            s=itsdangerous.URLSafeSerializer(app.secret_key,
                                             salt='reactivate')
            d=s.loads(key)
        except Exception as e:
            abort(403)

        if (len(d) != 2 or d[0] != p.id or
            d[1] != str(p.last_update_attempt)):
            abort(403)

        session['form_reactivate'] = {'isp_id': p.id}
        return render_template('reactivate_validator.html', isp=p)
    else:
        if 'form_reactivate' not in session or \
           not session['form_reactivate'].get('validated', False):
            abort(409)

        p=ISP.query.get(session['form_reactivate']['isp_id'])
        p.json=session['form_reactivate']['jdict']
        p.cache_info=session['form_reactivate']['cache_info']
        p.last_update_attempt=datetime.now()
        p.last_update_success=p.last_update_attempt

        db.session.add(p)
        db.session.commit()

        flash(_(u'Automatic updates activated'), 'info')
        return redirect(url_for('project', projectid=p.id))


@app.route('/search', methods=['GET', 'POST'])
def search():
    terms=request.args.get('q')
    if not terms:
        return redirect(url_for('home'))

    res=ISPWhoosh.search(terms)
    return render_template('search_results.html', results=res, search_terms=terms)


@app.route('/format', methods=['GET'])
def format():
    parts = cache.get('format-spec')
    if parts is None:
        spec=open(ispformat.specs.versions[0.1]).read()
        overrides = {
            'initial_header_level' : 3,
        }
        parts = docutils.core.publish_parts(spec,
                    source_path=os.path.dirname(ispformat.specs.versions[0.1]),
                    destination_path=None, writer_name='html',
                    settings_overrides=overrides)
        cache.set('format-spec', parts, timeout=60*60*24)
    return render_template('format_spec.html', spec=Markup(parts['html_body']))


#------
# Filters

@app.template_filter('step_to_label')
def step_to_label(step):
    if step:
        return u"<a href='#' rel='tooltip' data-placement='right' title='" + STEPS[step] + "'><span class='badge badge-" + STEPS_LABELS[step] + "'>" + str(step) + "</span></a>"
    else:
        return u'-'

@app.template_filter('stepname')
def stepname(step):
    return STEPS[step]

