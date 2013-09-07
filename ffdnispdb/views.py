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

@app.route('/fai/<projectid>')
def project(projectid):
    p=ISP.query.get(projectid)
    if not p:
        abort(404)
    return render_template('project_detail.html', project_row=p, project=p.json)

@app.route('/edit/<projectid>', methods=['GET', 'POST'])
def edit_project(projectid):
    project = query_db('select * from fai where id = ?', [projectid], one=True)
    if project is None:
        abort(404)
    if request.method == 'POST':
        if request.form['name']:
            if request.form['shortname']:
                if query_db('select * from fai where id!=? and (name=? or shortname=?)', [projectid, request.form['name'], request.form['shortname']], one=True) is None:
                    is_member = 0
                    if 'is_member' in request.form.keys():
                        is_member = 1
                    g.db.execute('update fai set name = ?, shortname = ?, description = ?, website = ?, email = ?, irc_channel = ?, irc_server = ?, zone = ?, gps = ?, step = ?, is_member = ? where id = ?', 
                            [request.form['name'], request.form['shortname'], request.form['description'], request.form['website'], request.form['email'], request.form['irc_channel'], request.form['irc_server'], request.form['zone'], request.form['gps1'] + ':' + request.form['gps2'], request.form['step'][:1], is_member, projectid]) 
                    g.db.commit()
                    flash(u"Le projet a bien été mis à jour. Merci pour votre contribution !", "success")
                    project = query_db('select * from fai where id = ?', [projectid], one=True)
                    return redirect(url_for('project', projectid=projectid))
                else:
                    flash(u'Le nom complet ou le nom court que vous avez choisi est déjà pris.', 'error')
            else:
                flash(u'Vous devez spécifier un nom court (éventuellement, le même que le nom complet).', 'error')
        else:
            flash(u'Vous devez spécifier un nom.', 'error')

    project['stepname'] = STEPS[project['step']]
    return render_template('edit_project.html', project=project)

@app.route('/create_old', methods=['GET', 'POST'])
def create_project_old():
    if request.method == 'POST':
        if request.form['name']:
            if request.form['shortname']:
                if query_db('select * from fai where name=? or shortname=?', [request.form['name'], request.form['shortname']], one=True) is None:
                    g.db.execute('INSERT INTO fai (name, shortname, description, website, email, irc_channel, irc_server, zone, gps, step) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                            [request.form['name'], request.form['shortname'], request.form['description'], request.form['website'], request.form['email'], request.form['irc_channel'], request.form['irc_server'], request.form['zone'], request.form['gps1'] + ':' + request.form['gps2'], request.form['step'][:1]]) 
                    g.db.commit()
                    flash(u"Le projet a bien été créé. Merci pour votre contribution !", "success")
                    project = query_db('select * from fai where name = ?', [request.form['name']], one=True)
                    if project is not None:
                        return redirect(url_for('project', projectid=project['id']))
                    else:
                        flash(u'Hum… il semble que le projet n\'a pas été créé… vous voulez-bien réessayer ?', 'error')
                else:
                    flash(u'Le nom complet ou le nom court que vous avez choisi est déjà pris.', 'error')
            else:
                flash(u'Vous devez spécifier un nom court (éventuellement, le même que le nom complet).', 'error')
        else:
            flash(u'Vous devez spécifier un nom.', 'error')
    return render_template('create_project.html')

@app.route('/add-a-project', methods=['GET'])
def add_project():
    return render_template('add_project.html')


@app.route('/create/form', methods=['GET', 'POST'])
def create_project():
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

