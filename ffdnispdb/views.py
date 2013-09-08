# -*- coding: utf-8 -*-

from flask import request, g, redirect, url_for, abort, \
    render_template, flash, jsonify 
from flask.ext.babel import gettext as _
from datetime import date, time, timedelta, datetime
import locale
locale.setlocale(locale.LC_ALL, '')
import string

from . import forms
from .constants import *
from . import app, query_db, db
from .models import ISP


@app.route('/')
def home():
    return render_template('index.html', active_button="home")

@app.route('/members')
def members():
    members = query_db('select * from fai where is_member = 1')
    return render_template('members.html', members=members)

@app.route('/projects')
def project_list():
    return render_template('project_list.html', projects=ISP.query.filter_by(is_disabled=False))

@app.route('/isp/<projectid>/')
def project(projectid):
    p=ISP.query.get(projectid)
    if not p:
        abort(404)
    return render_template('project_detail.html', project_row=p, project=p.json)


@app.route('/isp/<projectid>/edit', methods=['GET', 'POST'])
def edit_project(projectid):
    isp=ISP.query.get(projectid)
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


@app.route('/create/json-url', methods=['GET', 'POST'])
def create_project_json():
    form = forms.ProjectJSONForm()
    if form.validate_on_submit():
        isp=ISP()
        db.session.add(isp)
        db.session.commit()
        flash(_(u'Project created'), 'info')
        return redirect(url_for('project', projectid=isp.id))
    return render_template('project_json_form.html', form=form)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        pass
    return render_template('search.html')


@app.route('/api/<projects>.json')
def projects_json(projects):
    if projects == 'projects':
        query = 'select * from fai'
    elif projects == 'members':
        query = 'select * from fai where is_member = 1'
    else:
        abort(404)
    fais = dict()
    for fai in query_db(query):
        fais[fai['name']] = fai
    return jsonify(fais)

@app.route('/api/members_drupal')
def members_drupal():
    members = query_db('select * from fai where is_member = 1 order by shortname') 
    return render_template('members_drupal.html', members=members)

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

