#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, jsonify 
import sqlite3
from datetime import date, time, timedelta, datetime
import locale
locale.setlocale(locale.LC_ALL, '')
import string

from settings import *

app = Flask(__name__) 
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()
    #g.db.execute("PRAGMA foreign_keys = ON")

@app.teardown_request
def teardown_request(exception):
    g.db.close()

@app.route('/')
def home():
    return render_template('index.html', active_button="home")

def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
        for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/members')
def members():
    members = query_db('select * from fai where is_member = 1')
    return render_template('members.html', members=members)

@app.route('/projects')
def projects():
    projects = list()
    for project in query_db('select * from fai order by is_member desc,step desc,name'):
        project['stepname'] = STEPS[project['step']]
        projects.append(project)
    return render_template('projects.html', projects=projects)

@app.route('/fai/<projectid>')
def project(projectid):
    project = query_db('select * from fai where id = ?', [projectid], one=True) 
    if project is None:
        abort(404)
    project['stepname'] = STEPS[project['step']]
    return render_template('project.html', project=project)

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
                    return redirect(url_for(project, projectid=projectid))
                else:
                    flash(u'Le nom complet ou le nom court que vous avez choisi est déjà pris.', 'error')
            else:
                flash(u'Vous devez spécifier un nom court (éventuellement, le même que le nom complet).', 'error')
        else:
            flash(u'Vous devez spécifier un nom.', 'error')

    project['stepname'] = STEPS[project['step']]
    return render_template('edit_project.html', project=project)

@app.route('/create', methods=['GET', 'POST'])
def create_project():
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
                        return redirect(url_for(project))
                    else:
                        flash(u'Hum… il semble que le projet n\'a pas été créé… vous voulez-bien réessayer ?', 'error')
                else:
                    flash(u'Le nom complet ou le nom court que vous avez choisi est déjà pris.', 'error')
            else:
                flash(u'Vous devez spécifier un nom court (éventuellement, le même que le nom complet).', 'error')
        else:
            flash(u'Vous devez spécifier un nom.', 'error')
    return render_template('create_project.html')

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

#------
# Filters

@app.template_filter('step_to_label')
def step_to_label(step):
    return u"<a href='#' rel='tooltip' data-placement='right' title='" + STEPS[step] + "'><span class='badge badge-" + STEPS_LABELS[step] + "'>" + str(step) + "</span></a>"

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

#------
# Main

if __name__ == '__main__':
    app.run()

