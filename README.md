ffdnispdb
=========

``ffdnispdb`` is a website designed to display all the ISPs implementing the
``ispschema`` specification.

## How to deploy & use
Preferably in a virtualenv, run:

    pip install -r requirements.txt
    python shell.py
    >> db.create_all()
    python run.py


## How to translate
First, generate the template:

    pybabel extract -F babel.cfg -o messages.pot ffdnispdb

Then initialize the catalog for the language you want:

    pybabel init -i messages.pot -d ffdnispdb/translations -l XX

(where XX is the language code)

Once you're done translating, run:

    pybabel compile -d ffdnispdb/translations

To update the catalog with the latest strings:

    pybabel extract -F babel.cfg -o messages.pot ffdnispdb
    pybabel update -i messages.pot -d ffdnispdb/translations

