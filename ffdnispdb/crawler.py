

from flask import escape, json
import requests
import io
import cgi

from ispformat.validator import validate_isp
from .models import ISP


def get_encoding(content_type):
    content_type, params = cgi.parse_header(content_type)

    if 'charset' in params:
        return params['charset'].strip("'\"")


class Crawler(object):

    MAX_JSON_SIZE=1*1024*1024

    escape=staticmethod(lambda x:x)

    def m(self, msg, evt=None):
        if not evt:
            return u'%s\n'%msg
        else:
            return u''

    def err(self, msg, *args):
        return self.m(u'! %s'%msg, *args)

    def warn(self, msg):
        return self.m(u'@ %s'%msg)

    def info(self, msg):
        return self.m(u'\u2013 %s'%msg)

    def abort(self, msg):
        raise NotImplemented

    def color(self, color, msg):
        return msg

    def bold(self, msg):
        return msg

    def italics(self, msg):
        return msg

    def nl(self):
        return self.m('')

    def format_validation_errors(self, errs):
        r=[]
        for e in errs:
            r.append(u'    %s: %s'%('.'.join(list(e.schema_path)[1:]), e.message))

        return u'\n'.join(r)

    def done_cb(self):
        pass

    def __call__(self, url):
        esc=self.escape
        yield self.m('Starting the validation process...')
        r=None
        try:
            yield self.m('* Attempting to retreive %s'%self.bold(url))
            r=requests.get(url, verify='/etc/ssl/certs/ca-certificates.crt',
                           headers={'User-Agent': 'FFDN DB validator'},
                           stream=True, timeout=10)
        except requests.exceptions.SSLError as e:
            yield self.err('Unable to connect, SSL Error: '+self.color('#dd1144', esc(e)))
        except requests.exceptions.ConnectionError as e:
            yield self.err('Unable to connect: '+self.color('#dd1144', esc(e)))
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

        yield self.info('Response code: '+self.bold(str(r.status_code)+' '+esc(r.reason)))
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            yield self.err('Response code indicates an error')
            yield self.abort('Invalid response code')
            return

        yield self.info('Content type: '+self.bold(esc(r.headers.get('content-type', 'not defined'))))
        if not r.headers.get('content-type'):
            yield self.error('Content-type '+self.bold('MUST')+' be defined')
            yield self.abort('The file must have a proper content-type to continue')
        elif r.headers.get('content-type').lower() != 'application/json':
            yield self.warn('Content-type '+self.italics('SHOULD')+' be application/json')

        encoding=get_encoding(r.headers.get('content-type'))
        if not encoding:
            yield self.warn('Encoding not set. Assuming it\'s unicode, as per RFC4627 section 3')

        yield self.info('Content length: %s'%(self.bold(esc(r.headers.get('content-length', 'not set')))))

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

        yield self.nl()+self.m('* Parsing the JSON file')
        if not encoding:
            charset=requests.utils.guess_json_utf(r.content)
            if not charset:
                yield self.err('Unable to guess unicode charset')
                yield self.abort('The file MUST be unicode-encoded when no explicit charset is in the content-type')
                return

            yield self.info('Guessed charset: '+self.bold(charset))

        try:
            txt=r.content.decode(encoding or charset)
            yield self.info('Successfully decoded file as %s'%esc(encoding or charset))
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

        yield self.nl()+self.m('* Validating the JSON against the schema')

        v=list(validate_isp(jdict))
        if v:
            yield self.err('Validation errors:')+self.format_validation_errors(v)
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

        yield (self.nl()+self.m('== '+self.color('forestgreen', 'All good ! You can click on Confirm now'))+
               self.m(json.dumps({'passed': 1}), 'control'))

        self.jdict=jdict
        self.done_cb()



class PrettyValidator(Crawler):

    def __init__(self, session=None, *args, **kwargs):
        super(PrettyValidator, self).__init__(*args, **kwargs)
        self.session=session
        self.escape=escape

    def m(self, msg, evt=None):
        return u'%sdata: %s\n\n'%(u'event: %s\n'%evt if evt else '', msg)

    def err(self, msg, *args):
        return self.m(u'<strong style="color: crimson">!</strong> %s'%msg, *args)

    def warn(self, msg):
        return self.m(u'<strong style="color: dodgerblue">@</strong> %s'%msg)

    def info(self, msg):
        return self.m(u'&ndash; %s'%msg)

    def abort(self, msg):
        return (self.m(u'<br />== <span style="color: crimson">%s</span>'%msg)+
                self.m(json.dumps({'closed': 1}), 'control'))

    def bold(self, msg):
        return u'<strong>%s</strong>'%msg

    def italics(self, msg):
        return u'<em>%s</em>'%msg

    def color(self, color, msg):
        return u'<span style="color: %s">%s</span>'%(color, msg)

    def format_validation_errors(self, errs):
        lns=super(PrettyValidator, self).format_validation_errors(errs)
        buf=u''
        for l in lns.split('\n'):
            buf+=self.m(self.escape(l))
        return buf

    def done_cb(self):
        self.session['form_json']['validated']=True
        self.session['form_json']['jdict']=self.jdict
        self.session.save()


class TextValidator(Crawler):
    def abort(self, msg):
        res=u'ABORTED: %s\n'%msg
        pad=u'='*(len(res)-1)+'\n'
        return self.m(pad+res+pad)

