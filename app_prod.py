
import os; os.environ.setdefault('FFDNISPDB_SETTINGS', '../settings_prod.py')
from ffdnispdb import create_app


app=create_app()
if not app.debug:
    import logging
    from logging.handlers import SMTPHandler
    from logging import FileHandler
    mail_handler = SMTPHandler('127.0.0.1',
                               'server-error@db.ffdn.org',
                               app.config['ADMINS'], 'FFDN DB Error')
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter('''
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s

Message:

%(message)s
    '''))
    app.logger.addHandler(mail_handler)

    file_handler = FileHandler('application.log')
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(file_handler)
