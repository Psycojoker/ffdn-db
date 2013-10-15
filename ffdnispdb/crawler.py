

from flask import escape, json
import requests
import io

from ispformat.validator import validate_isp
from .models import ISP


class Crawler(object):

    MAX_JSON_SIZE=1*1024*1024

    format_validation_errors=unicode
    escape=lambda x:x

    def m(self, msg, evt=None):
        return u'%sdata: %s\n\n'%(u'event: %s\n'%evt if evt else '', msg)

    def err(self, msg, *args):
        return self.m(u'! %s'%msg, *args)

    def warn(self, msg):
        return self.m(u'@ %s'%msg)

    def info(self, msg):
        return self.m(u'\u2013 %s'%msg)

    def abort(self, msg):
        return (self.m('<br />== <span style="color: crimson">%s</span>'%msg)+
                self.m(json.dumps({'closed': 1}), 'control'))

    def done_cb(self):
        pass

    def __call__(self, url):
        esc=self.escape
        yield self.m('Starting the validation process...')
        r=None
        try:
            yield self.m('* Attempting to retreive <strong>%s</strong>'%url)
            r=requests.get(url, verify='/etc/ssl/certs/ca-certificates.crt',
                           headers={'User-Agent': 'FFDN DB validator'},
                           stream=True, timeout=10)
        except requests.exceptions.SSLError as e:
            yield self.err('Unable to connect, SSL Error: <code style="color: #dd1144;">%s</code>'%esc(e))
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

        yield self.info('Response code: <strong>%s %s</strong>'%(esc(r.status_code), esc(r.reason)))
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            yield self.err('Response code indicates an error')
            yield self.abort('Invalid response code')
            return

        yield self.info('Content type: <strong>%s</strong>'%(esc(r.headers.get('content-type', 'not defined'))))
        if not r.headers.get('content-type'):
            yield self.error('Content-type <strong>MUST</strong> be defined')
            yield self.abort('The file must have a proper content-type to continue')
        elif r.headers.get('content-type').lower() != 'application/json':
            yield self.warn('Content-type <em>SHOULD</em> be application/json')

        if not r.encoding:
            yield self.warn('Encoding not set. Assuming it\'s unicode, as per RFC4627 section 3')

        yield self.info('Content length: <strong>%s</strong>'%(esc(r.headers.get('content-length', 'not set'))))

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
            yield self.info('Successfully decoded file as %s'%esc(r.encoding or charset))
        except LookupError as e:
            yield self.err('Invalid/unknown charset: %s'%esc(e))
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
            yield self.err('Error while parsing JSON: %s'%esc(e))
        except Exception as e:
            yield self.err('Unexpected error while parsing JSON: %s'%esc(e))

        if not jdict:
            yield self.abort('Could not parse JSON')
            return

        yield self.info('JSON parsed successfully')

        yield self.m('<br />* Validating the JSON against the schema')

        v=list(validate_isp(jdict))
        if v:
            yield self.err('Validation errors:<br />%s'%esc(self.format_validation_errors(v)))
            yield self.abort('Your JSON file does not follow the schema, please fix it')
            return
        else:
            yield self.info('Done. No errors encountered \o')

        # check name uniqueness
        where = (ISP.name == jdict['name'])
        if 'shortname' in jdict and jdict['shortname']:
            where |= (ISP.shortname == jdict.get('shortname'))
        if ISP.query.filter(where).count() > 0:
            yield self.err('An ISP named "%s" already exist'%esc(
                jdict['name']+(' ('+jdict['shortname']+')' if jdict.get('shortname') else '')
            ))
            yield self.abort('The name of your ISP must be unique')
            return

        yield (self.m('<br />== <span style="color: forestgreen">All good ! You can click on Confirm now</span>')+
               self.m(json.dumps({'passed': 1}), 'control'))

        self.jdict=jdict
        self.done_cb()



class PrettyValidator(Crawler):

    def __init__(self, session=None, *args, **kwargs):
        super(PrettyValidator, self).__init__(*args, **kwargs)
        self.session=session
        self.escape=escape

    def err(self, msg, *args):
        return self.m(u'<strong style="color: crimson">!</strong> %s'%msg, *args)

    def warn(self, msg):
        return self.m(u'<strong style="color: dodgerblue">@</strong> %s'%msg)

    def info(self, msg):
        return self.m(u'&ndash; %s'%msg)

    def abort(self, msg):
        return (self.m(u'<br />== <span style="color: crimson">%s</span>'%msg)+
                self.m(json.dumps({'closed': 1}), 'control'))

    def format_validation_errors(self, errs):
        r=[]
        for e in errs:
            r.append(u'    %s: %s'%('.'.join(list(e.schema_path)[1:]), str(e)))

        return '\n'.join(r)

    def done_cb(self):
        self.session['form_json']['validated']=True
        self.session['form_json']['jdict']=self.jdict
        self.session.save()
