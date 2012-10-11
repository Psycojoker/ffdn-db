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
    for project in query_db('select * from fai order by is_member,step,name'):
        project['stepname'] = STEPS[project['step']]
        projects.append(project)
    return render_template('projects.html', projects=projects)

@app.route('/fai/<projectid>')
def project(projectid):
    project = query_db('select * from fai where id = ?', (projectid), one=True) 
    if project is None:
        abort(404)
    project['stepname'] = STEPS[project['step']]
    return render_template('project.html', project=project)

@app.route('/edit/<projectid>', methods=['GET', 'POST'])
def edit_project(projectid):
    project = query_db('select * from fai where id = ?', (projectid), one=True)
    if project is None:
        abort(404)
    if request.method == 'POST':
        g.db.execute('update fai set name = ?, description = ? where id = ?', [request.form['name'], request.form['description'], projectid]) 
        g.db.commit()
        flash(u"Le projet a bien été mis à jour. Merci pour votre contribution !", "success")
    project = query_db('select * from fai where id = ?', (projectid), one=True)
    project['stepname'] = STEPS[project['step']]
    return render_template('edit_project.html', project=project)

@app.route('/create/<projectid>')
def create_project(projectid):
    abort(404) # TODO

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
# Main

if __name__ == '__main__':
    app.run()

