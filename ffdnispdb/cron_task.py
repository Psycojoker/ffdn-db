#!/usr/bin/env python2


import signal
import traceback
from sys import stderr
from datetime import datetime, timedelta
from flask.ext.mail import Message
from flask import url_for
import itsdangerous

from ffdnispdb.crawler import TextValidator
from ffdnispdb.models import ISP
from ffdnispdb import create_app, db, mail, utils


app=create_app({
    'SERVER_NAME': 'db.ffdn.org',
})

MAX_RUNTIME=15*60

class Timeout(Exception):
    pass

class ScriptTimeout(Exception):
    """
    Script exceeded its allowed run time
    """


strike=1
last_isp=-1
script_begin=datetime.now()
def timeout_handler(signum, frame):
    global last_isp, strike
    if script_begin < datetime.now()-timedelta(seconds=MAX_RUNTIME):
        raise ScriptTimeout

    if last_isp == isp.id:
        strike += 1
        if strike > 2:
            signal.alarm(6)
            raise Timeout
    else:
        last_isp = isp.id
        strike = 1

    signal.alarm(6)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(6)


def gen_reactivate_key(isp):
    s=itsdangerous.URLSafeSerializer(app.secret_key,
                                     salt='reactivate')
    return s.dumps([
        isp.id,
        str(isp.last_update_attempt)
    ])


def send_warning_email(isp, debug_msg):
    msg=Message(u"Problem while updating your ISP's data", sender=app.config['EMAIL_SENDER'])
    msg.body = """
Hello,

You are receiving this message because your are listed as technical contact for "%s" on the FFDN ISP database.

Our automatic update script could not access or process your ISP's data located at %s.

Automatic updates of your ISP were disabled until you fix the problem.

Here is some debug output to help you locate the issue:

%s

---
When the issue is resolved, please click on the link below to reactivate automatic updates on your ISP:
%s?key=%s

Thanks,
The FFDN ISP Database team
https://db.ffdn.org
    """.strip()%(isp.complete_name, isp.json_url, debug_msg.strip(),
                 url_for('ispdb.reactivate_isp', projectid=isp.id), gen_reactivate_key(isp))
    msg.add_recipient(isp.tech_email)
    print u'    Sending notification email to %s'%(isp.tech_email)
    mail.send(msg)


app.app_context().push()

try:
    for isp in ISP.query.filter(ISP.is_disabled == False,
                                ISP.json_url != None,
                                ISP.next_update < utils.utcnow(),
                                ISP.update_error_strike < 3)\
                        .order_by(ISP.last_update_success):
        try:
            print u'%s: Attempting to update %s'%(datetime.now(), isp)
            print u'    last successful update=%s'%(utils.tosystemtz(isp.last_update_success))
            print u'    last update attempt=%s'%(utils.tosystemtz(isp.last_update_attempt))
            print u'    next update was scheduled %s ago'%(utils.utcnow()-isp.next_update)
            print u'    strike=%d'%(isp.update_error_strike)

            isp.last_update_attempt=utils.utcnow()
            db.session.add(isp)
            db.session.commit()

            validator=TextValidator()
            log = ''
            exc, exc_trace = None, None
            try:
                for l in validator(isp.json_url, isp.cache_info or {}):
                    log += l
            except Exception as e:
                exc = e
                exc_trace = traceback.format_exc()

            if not validator.success: # handle error
                isp.update_error_strike += 1
                # reset cache info (to force refetch next time)
                isp.cache_info = {}
                isp.next_update = utils.utcnow()+timedelta(seconds=validator.jdict_max_age)
                db.session.add(isp)
                db.session.commit()
                print u'%s: Error while updating:'%(datetime.now())
                if isp.update_error_strike >= 3:
                    print u'    three strikes, you\'re out'
                    send_warning_email(isp, log)

                print log.rstrip().encode('utf-8')+'\n'
                if exc:
                    print u'Unexpected exception in the validator: %r' % exc
                    print exc_log

                continue

            if validator.modified:
                isp.json = validator.jdict
            isp.cache_info = validator.cache_info
            isp.last_update_success = isp.last_update_attempt
            isp.update_error_strike = 0
            isp.next_update = utils.utcnow()+timedelta(seconds=validator.jdict_max_age)
            db.session.add(isp)
            db.session.commit()

            print u'%s: Update successful !'%(datetime.now())
            print u'    next update is scheduled for %s\n'%(isp.next_update)
        except Timeout:
            print u'%s: Timeout while updating:'%(datetime.now())
            isp=ISP.query.get(isp.id)
            isp.update_error_strike += 1
            db.session.add(isp)
            db.session.commit()
            if isp.update_error_strike >= 3:
                send_warning_email(isp, 'Your ISP took more then 18 seconds to process. '
                                        'Having problems with your webserver ?')
                print u'    three strikes, you\'re out'
            print traceback.format_exc()

except ScriptTimeout:
    pass
except Timeout:
    pass
