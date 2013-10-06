# -*- coding: utf-8 -*-

from flask import request, g, redirect, url_for, abort, \
    render_template, flash, json, session, Response, escape
from flask.ext.babel import gettext as _
import requests
from datetime import date, time, timedelta, datetime
from urlparse import urlunsplit
import locale
locale.setlocale(locale.LC_ALL, '')
import string
import io
from time import time

from . import forms
from .constants import *
from . import app, db
from .models import ISP
from .schemavalidator import validate_isp


@app.route('/')
def home():
    return render_template('index.html', active_button="home")


@app.route('/projects')
def project_list():
    return render_template('project_list.html', projects=ISP.query.filter_by(is_disabled=False))


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

    validator=ValidateJSONURL(session=session._get_current_object())
    return Response(validator(session['form_json']['url']),
                    mimetype="text/event-stream")


class ValidateJSONURL(object):

    MAX_JSON_SIZE=1*1024*1024

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def m(self, msg, evt=None):
        return '%sdata: %s\n\n'%('event: %s\n'%evt if evt else '', msg)

    def err(self, msg, *args):
        return self.m('<strong style="color: crimson">!</strong> %s'%msg, *args)

    def warn(self, msg):
        return self.m('<strong style="color: dodgerblue">@</strong> %s'%msg)

    def info(self, msg):
        return self.m('&ndash; %s'%msg)

    def abort(self, msg):
        return (self.m('<br />== <span style="color: crimson">%s</span>'%msg)+
                self.m(json.dumps({'closed': 1}), 'control'))

    def done_cb(self):
        self.session['form_json']['validated']=True
        self.session['form_json']['jdict']=self.jdict
        self.session.save()

    def __call__(self, url):
        yield self.m('Starting the validation process...')
        r=None
        try:
            yield self.m('* Attempting to retreive <strong>%s</strong>'%url)
            r=requests.get(url, verify='/etc/ssl/certs/ca-certificates.crt',
                           headers={'User-Agent': 'FFDN DB validator'},
                           stream=True, timeout=10)
        except requests.exceptions.SSLError as e:
            yield self.err('Unable to connect, SSL Error: <code style="color: #dd1144;">%s</code>'%escape(e))
        except requests.exceptions.ConnectionError as e:
            yield self.err('Unable to connect: <code style="color: #dd1144;">%s</code>'%e)
        except requests.exceptions.Timeout as e:
            yield self.err('Connection timeout')
        except requests.exceptions.TooManyRedirects as e:
            yield self.err('Too many redirects')
        except requests.exceptions.RequestException as e:
            yield self.err('Internal request exception')
        except Exception as e:
            yield self.err('Unexpected request exception')

        if r is None:
            yield self.abort('Connection could not be established, aborting')
            return

        yield self.info('Connection established')

        yield self.info('Response code: <strong>%s %s</strong>'%(escape(r.status_code), escape(r.reason)))
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            yield cls.err('Response code indicates an error')
            yield cls.abort('Invalid response code')
            return

        yield self.info('Content type: <strong>%s</strong>'%(escape(r.headers.get('content-type', 'not defined'))))
        if not r.headers.get('content-type'):
            yield self.error('Content-type <strong>MUST</strong> be defined')
            yield self.abort('The file must have a proper content-type to continue')
        elif r.headers.get('content-type').lower() != 'application/json':
            yield self.warn('Content-type <em>SHOULD</em> be application/json')

        if not r.encoding:
            yield self.warn('Encoding not set. Assuming it\'s unicode, as per RFC4627 section 3')

        yield self.info('Content length: <strong>%s</strong>'%(escape(r.headers.get('content-length', 'not set'))))

        cl=r.headers.get('content-length')
        if not cl:
            yield self.warn('No content-length. Note that we will not process a file whose size exceed 1MiB')
        elif int(cl) > self.MAX_JSON_SIZE:
            yield self.abort('File too big ! File size must be less then 1MiB')

        yield self.info('Reading response into memory...')
        b=io.BytesIO()
        for d in r.iter_content(requests.models.CONTENT_CHUNK_SIZE):
            b.write(d)
            if b.tell() > self.MAX_JSON_SIZE:
                yield self.abort('File too big ! File size must be less then 1MiB')
                return
        r._content=b.getvalue()
        del b
        yield self.info('Successfully read %d bytes'%len(r.content))

        yield self.m('<br>* Parsing the JSON file')
        if not r.encoding:
            charset=requests.utils.guess_json_utf(r.content)
            if not charset:
                yield self.err('Unable to guess unicode charset')
                yield self.abort('The file MUST be unicode-encoded when no explicit charset is in the content-type')
                return

            yield self.info('Guessed charset: <strong>%s</strong>'%charset)

        try:
            txt=r.content.decode(r.encoding or charset)
            yield self.info('Successfully decoded file as %s'%escape(r.encoding or charset))
        except LookupError as e:
            yield self.err('Invalid/unknown charset: %s'%escape(e))
            yield self.abort('Charset error, Cannot continue')
            return
        except UnicodeDecodeError as e:
            yield self.err('Unicode decode error: %s'%e)
            yield self.abort('Charset error, cannot continue')
            return
        except Exception:
            yield self.abort('Unexpected charset error')
            return

        jdict=None
        try:
            jdict=json.loads(txt)
        except ValueError as e:
            yield self.err('Error while parsing JSON: %s'%escape(e))
        except Exception as e:
            yield self.err('Unexpected error while parsing JSON: %s'%escape(e))

        if not jdict:
            yield self.abort('Could not parse JSON')
            return

        yield self.info('JSON parsed successfully')

        yield self.m('<br />* Validating the JSON against the schema')

        v=list(validate_isp(jdict))
        if v:
            yield self.err('Errors: %s'%escape(str(v)))
            yield self.abort('Your JSON file does not follow the schema, please fix it')
        else:
            yield self.info('Done. No errors encountered \o')

        # check name uniqueness
        where = (ISP.name == jdict['name'])
        if 'shortname' in jdict and jdict['shortname']:
            where |= (ISP.shortname == jdict.get('shortname'))
        if ISP.query.filter(where).count() > 1:
            yield self.info('An ISP named %s already exist'%escape(
                jdict['name']+(' ('+jdict['shortname']+')' if jdict.get('shortname') else '')
            ))

        yield (self.m('<br />== <span style="color: forestgreen">All good ! You can click on Confirm now</span>')+
               self.m(json.dumps({'passed': 1}), 'control'))

        self.jdict=jdict
        self.done_cb()


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
        isp.shotname=jdict['shortname']
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


