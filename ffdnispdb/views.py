# -*- coding: utf-8 -*-

from flask import request, g, redirect, url_for, abort, \
    render_template, flash, json, session, Response, Markup
from flask.ext.babel import gettext as _
import docutils.core
import ispformat.specs

from datetime import date, time, timedelta, datetime
from urlparse import urlunsplit
import locale
locale.setlocale(locale.LC_ALL, '')
import string
from time import time

from . import forms
from .constants import *
from . import app, db, cache
from .models import ISP
from .crawler import PrettyValidator


@app.route('/')
def home():
    return render_template('index.html', active_button="home")


@app.route('/projects')
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


@app.route('/create/form', methods=['GET', 'POST'])
def create_project_form():
    form = forms.ProjectForm()
    if form.validate_on_submit():
        isp=ISP()
        isp.name = form.name.data
        isp.shortname = form.shortname.data or None
        isp.json=form.to_json(isp.json)

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    return render_template('project_form.html', form=form)


@app.route('/create/json-url/validator', methods=['GET'])
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

    validator=PrettyValidator(session=session._get_current_object())
    return Response(validator(session['form_json']['url']),
                    mimetype="text/event-stream")


@app.route('/create/json-url', methods=['GET', 'POST'])
def create_project_json():
    form = forms.ProjectJSONForm()
    if form.validate_on_submit():
        u=list(form.url.data)
        u[2]='/isp.json' # new path
        url=urlunsplit(u)
        session['form_json'] = {'url': url}
        return render_template('project_json_validator.html')
    return render_template('project_json_form.html', form=form)


@app.route('/create/json-url/confirm', methods=['POST'])
def create_project_json_confirm():
    if 'form_json' in session and session['form_json'].get('validated', False):
        if not forms.is_url_unique(session['form_json']['url']):
            abort(409)
        jdict=session['form_json']['jdict']
        isp=ISP()
        isp.name=jdict['name']
        isp.shortname=jdict['shortname']
        isp.url=session['form_json']['url']
        isp.json=jdict
        del session['form_json']

        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    else:
        return redirect(url_for('create_project_json'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        pass
    return render_template('search.html')


@app.route('/format', methods=['GET'])
def format():
    parts = cache.get('format-spec')
    if parts is None:
        spec=open(ispformat.specs.versions[0.1]).read()
        overrides = {
            'initial_header_level' : 3,
        }
        parts = docutils.core.publish_parts(spec,
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

@app.template_filter('member_to_label')
def member_to_label(is_member):
    if is_member:
        return u'<a href="#" rel="tooltip" data-placement="right" title="Membre de la Fédération FDN"><span class="label label-success">FFDN</span></a>'
    return ''

@app.template_filter('stepname')
def stepname(step):
    return STEPS[step]

@app.template_filter('gpspart')
def gpspart(gps, part):
    parts = gps.split(':');
    if part == 1:
        return parts[0]
    elif part == 2:
        return parts[1]
    return "";


