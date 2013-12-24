ffdnispdb
=========

``ffdnispdb`` is a website designed to display all the ISPs implementing the
``ispschema`` specification.

## How to install & develop
Third-party dependencies:
 * ``sqlite``
 * ``libspatialite``

Preferably in a virtualenv, run:

    pip install -r requirements.txt
    python manage.py db create

To start the development server, run:

    python manage.py runserver

## Production deployment
To deploy this application, we recommend the use of gunicorn/gevent.
We strongly discourage you to use a synchronous WSGI server, since the app uses
``Server-sent events``.

First, copy the example settings file:

    cp settings_prod.py.dist settings_prod.py

Then, edit the newly created ``settings_prod.py``:
generate a random ``SECRET_KEY``, add yourself to the ``ADMINS`` array.
To see the full list of available settings, see the ``ffdnispdb/default_settings.py`` file
and [Flask's documentation](http://flask.pocoo.org/docs/config/#builtin-configuration-values).

Now, you can run gunicorn using the ``app_prod.py`` file, which logs warnings
to an application.log file and send you errors by email.

    gunicorn -k gevent -b 127.0.0.1:8080 --log-level warning app_prod:app

You can also edit ``app_prod.py`` to customize logging behavior.

## How to translate
First, generate the template:

    pybabel extract -F babel.cfg -o messages.pot ffdnispdb

Then initialize the catalog for the language you want:

    pybabel init -i messages.pot -d ffdnispdb/translations -l XX

(where XX is the language code)

Once you're done translating, run:

    pybabel compile -d ffdnispdb/translations

Now, you can add your language to the ``LANGUAGES`` dict in ``ffdnispdb/default_settings.py``.

To update the catalog with the latest strings:

    pybabel extract -F babel.cfg -o messages.pot ffdnispdb
    pybabel update -i messages.pot -d ffdnispdb/translations

Once you've tested your work and you're satisfied with the result, you can
send us a patch (or the po file directly).
