from functools import partial
import itertools
import urlparse
import json
import collections
from flask import current_app
from flask.ext.wtf import Form
from wtforms import Form as InsecureForm
from wtforms import (TextField, DateField, DecimalField, IntegerField, SelectField,
                     SelectMultipleField, FieldList, FormField)
from wtforms.widgets import TextInput, ListWidget, html_params, HTMLString, CheckboxInput, Select, TextArea
from wtforms.validators import (DataRequired, Optional, URL, Email, Length,
                                NumberRange, ValidationError, StopValidation)
from flask.ext.babel import lazy_gettext as _, gettext
from babel.support import LazyProxy
from ispformat.validator import validate_geojson
from .constants import STEPS
from .models import ISP
from .utils import check_geojson_spatialite, filesize_fmt


class InputListWidget(ListWidget):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = ['<%s %s>' % (self.html_tag, html_params(**kwargs))]
        for subfield in field:
            html.append('<li>%s</li>' % (subfield()))
        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class MyFormField(FormField):

    @property
    def flattened_errors(self):
        return list(itertools.chain.from_iterable(self.errors.values()))


class GeoJSONField(TextField):
    widget = TextArea()

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            max_size = current_app.config['ISP_FORM_GEOJSON_MAX_SIZE']
            if len(valuelist[0]) > max_size:
                raise ValueError(_(u'JSON value too big, must be less than %(max_size)s',
                                   max_size=filesize_fmt(max_size)))
            try:
                self.data = json.loads(valuelist[0], object_pairs_hook=collections.OrderedDict)
            except Exception as e:
                raise ValueError(_(u'Not a valid JSON value'))
        elif valuelist and valuelist[0].strip() == '':
            self.data = None  # if an empty string was passed, set data as None

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return json.dumps(self.data)
        else:
            return ''

    def pre_validate(self, form):
        if self.data is not None:
            if not validate_geojson(self.data):
                raise StopValidation(_(u'Invalid GeoJSON, please check it'))
            if not check_geojson_spatialite(self.data):
                current_app.logger.error('Spatialite could not decode the following GeoJSON: %s', self.data)
                raise StopValidation(_(u'Unable to store GeoJSON in database'))


class Unique(object):
    """ validator that checks field uniqueness """
    def __init__(self, model, field, message=None, allow_edit=False):
        self.model = model
        self.field = field
        if not message:
            message = _(u'this element already exists')
        self.message = message

    def __call__(self, form, field):
        default = field.default() if callable(field.default) else field.default
        if field.object_data != default and field.object_data == field.data:
            return
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)


TECHNOLOGIES_CHOICES = (
    ('ftth', _('FTTH')),
    ('dsl', _('DSL')),
    ('wifi', _('Wi-Fi')),
)


class CoveredArea(InsecureForm):
    name = TextField(_(u'name'), widget=partial(TextInput(), class_='input-medium', placeholder=_(u'Area')))
    technologies = SelectMultipleField(_(u'technologies'), choices=TECHNOLOGIES_CHOICES,
                                       widget=partial(Select(True), **{'class': 'selectpicker', 'data-title': _(u'Technologies deployed')}))
    area = GeoJSONField(_('area'), widget=partial(TextArea(), class_='geoinput'))

    def validate(self, *args, **kwargs):
        r = super(CoveredArea, self).validate(*args, **kwargs)
        if bool(self.name.data) != bool(self.technologies.data):
            self._fields['name'].errors += [_(u'You must fill both fields')]
            r = False
        return r


class OtherWebsites(InsecureForm):
    name = TextField(_(u'name'), widget=partial(TextInput(), class_='input-small', placeholder=_(u'Name')))
    url = TextField(_(u'url'), widget=partial(TextInput(), class_='input-medium', placeholder=_(u'URL')),
                   validators=[Optional(), URL(require_tld=True)])


STEP_CHOICES = [(k, LazyProxy(lambda k, s: u'%u - %s' % (k, s), k, STEPS[k], enable_cache=False)) for k in STEPS]


class ProjectForm(Form):
    name = TextField(_(u'full name'), description=[_(u'E.g. French Data Network')],
                    validators=[DataRequired(), Length(min=2), Unique(ISP, ISP.name)])
    shortname = TextField(_(u'short name'), description=[_(u'E.g. FDN')],
                         validators=[Optional(), Length(min=2, max=15), Unique(ISP, ISP.shortname)])
    description = TextField(_(u'description'), description=[None, _(u'Short text describing the project')])
    logo_url = TextField(_(u'logo url'), validators=[Optional(), URL(require_tld=True)])
    website = TextField(_(u'website'), validators=[Optional(), URL(require_tld=True)])
    other_websites = FieldList(MyFormField(OtherWebsites, widget=partial(InputListWidget(), class_='formfield')),
                              min_entries=1, widget=InputListWidget(),
                              description=[None, _(u'Additional websites that you host (e.g. wiki, etherpad...)')])
    contact_email = TextField(_(u'contact email'), validators=[Optional(), Email()],
                              description=[None, _(u'General contact email address')])
    main_ml = TextField(_(u'main mailing list'), validators=[Optional(), Email()],
                       description=[None, _(u'Address of your main mailing list')])
    creation_date = DateField(_(u'creation date'), validators=[Optional()], widget=partial(TextInput(), placeholder=_(u'YYYY-mm-dd')),
                              description=[None, _(u'Date at which the legal structure for your project was created')])
    chatrooms = FieldList(TextField(_(u'chatrooms')), min_entries=1, widget=InputListWidget(),
                         description=[None, _(u'In URI form, e.g. <code>irc://irc.isp.net/#isp</code> or ' +
                         '<code>xmpp:isp@chat.isp.net?join</code>')])
    covered_areas = FieldList(MyFormField(CoveredArea, _('Covered Areas'), widget=partial(InputListWidget(), class_='formfield')),
                             min_entries=1, widget=InputListWidget(),
                             description=[None, _(u'Descriptive name of the covered areas and technologies deployed')])
    latitude = DecimalField(_(u'latitude'), validators=[Optional(), NumberRange(min=-90, max=90)],
                           description=[None, _(u'Coordinates of your registered office or usual meeting location. '
                           '<strong>Required in order to appear on the map.</strong>')])
    longitude = DecimalField(_(u'longitude'), validators=[Optional(), NumberRange(min=-180, max=180)])
    step = SelectField(_(u'progress step'), choices=STEP_CHOICES, coerce=int)
    member_count = IntegerField(_(u'members'), validators=[Optional(), NumberRange(min=0)],
                               description=[None, _('Number of members')])
    subscriber_count = IntegerField(_(u'subscribers'), validators=[Optional(), NumberRange(min=0)],
                                    description=[None, _('Number of subscribers to an internet access')])

    tech_email = TextField(_('Email'), validators=[Email(), DataRequired()], description=[None,
                            _('Technical contact, in case of problems with your submission')])

    def validate(self, *args, **kwargs):
        r = super(ProjectForm, self).validate(*args, **kwargs)
        if (self.latitude.data is None) != (self.longitude.data is None):
            self._fields['longitude'].errors += [_(u'You must fill both fields')]
            r = False
        return r

    def validate_covered_areas(self, field):
        if len(filter(lambda e: e['name'], field.data)) == 0:
            # not printed, whatever..
            raise ValidationError(_(u'You must specify at least one area'))

        geojson_size = sum([len(ca.area.raw_data[0]) for ca in self.covered_areas if ca.area.raw_data])
        max_size = current_app.config['ISP_FORM_GEOJSON_MAX_SIZE_TOTAL']
        if geojson_size > max_size:
            # TODO: XXX This is not printed !
            raise ValidationError(gettext(u'The size of all GeoJSON data combined must not exceed %(max_size)s',
                                          max_size=filesize_fmt(max_size)))

    def to_json(self, json=None):
        if json is None:
            json = {}

        json['name'] = self.name.data

        def optstr(k, v):
            if k in json or v:
                json[k] = v

        def optlist(k, v):
            if k in json or len(v):
                json[k] = v

        def transform_covered_areas(cas):
            for ca in cas:
                if not ca['name']:
                    continue
                if 'area' in ca and ca['area'] is None:
                    del ca['area']
                yield ca

        optstr('shortname', self.shortname.data)
        optstr('description', self.description.data)
        optstr('logoURL', self.logo_url.data)
        optstr('website', self.website.data)
        optstr('otherWebsites', dict(((w['name'], w['url']) for w in self.other_websites.data if w['name'])))
        optstr('email', self.contact_email.data)
        optstr('mainMailingList', self.main_ml.data)
        optstr('creationDate', self.creation_date.data.isoformat() if self.creation_date.data else None)
        optstr('progressStatus', self.step.data)
        optstr('memberCount', self.member_count.data)
        optstr('subscriberCount', self.subscriber_count.data)
        optlist('chatrooms', filter(bool, self.chatrooms.data))  # remove empty strings
        optstr('coordinates', {'latitude': self.latitude.data, 'longitude': self.longitude.data}
              if self.latitude.data else {})
        optlist('coveredAreas', list(transform_covered_areas(self.covered_areas.data)))
        return json

    @classmethod
    def edit_json(cls, isp):
        json = isp.json
        obj = type('abject', (object,), {})()

        def set_attr(attr, itemk=None, d=json):
            if itemk is None:
                itemk = attr
            if itemk in d:
                setattr(obj, attr, d[itemk])
        set_attr('name')
        set_attr('shortname')
        set_attr('description')
        set_attr('logo_url', 'logoURL')
        set_attr('website')
        set_attr('contact_email', 'email')
        set_attr('main_ml', 'mainMailingList')
        set_attr('creation_date', 'creationDate')
        if hasattr(obj, 'creation_date'):
            obj.creation_date = ISP.str2date(obj.creation_date)
        set_attr('step', 'progressStatus')
        set_attr('member_count', 'memberCount')
        set_attr('subscriber_count', 'subscriberCount')
        set_attr('chatrooms', 'chatrooms')
        if 'coordinates' in json:
            set_attr('latitude', d=json['coordinates'])
            set_attr('longitude', d=json['coordinates'])
        if 'otherWebsites' in json:
            setattr(obj, 'other_websites', [{'name': n, 'url': w} for n, w in json['otherWebsites'].iteritems()])
        set_attr('covered_areas', 'coveredAreas')
        obj.tech_email = isp.tech_email
        return cls(obj=obj)


class URLField(TextField):
    def _value(self):
        if isinstance(self.data, basestring):
            return self.data
        elif self.data is None:
            return ''
        else:
            return urlparse.urlunsplit(self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = urlparse.urlsplit(valuelist[0])
            except:
                self.data = None
                raise ValidationError(_(u'Invalid URL'))


def is_url_unique(url):
    if isinstance(url, basestring):
        url = urlparse.urlsplit(url)
    t = list(url)
    t[2] = ''
    u1 = urlparse.urlunsplit(t)
    t[0] = 'http' if t[0] == 'https' else 'https'
    u2 = urlparse.urlunsplit(t)
    if ISP.query.filter(ISP.json_url.startswith(u1) | ISP.json_url.startswith(u2)).count() > 0:
        return False
    return True


class ProjectJSONForm(Form):
    json_url = URLField(_(u'base url'), description=[_(u'E.g. https://isp.com/'),
                            _(u'A ressource implementing our JSON-Schema specification ' +
                       'must exist at path /isp.json')])
    tech_email = TextField(_(u'Email'), validators=[Email()], description=[None,
                           _(u'Technical contact, in case of problems')])

    def validate_json_url(self, field):
        if not field.data.netloc:
            raise ValidationError(_(u'Invalid URL'))

        if field.data.scheme not in ('http', 'https'):
            raise ValidationError(_(u'Invalid URL (must be HTTP(S))'))

        if not field.object_data and not is_url_unique(field.data):
            raise ValidationError(_(u'This URL is already in our database'))


class RequestEditToken(Form):
    tech_email = TextField(_(u'Tech Email'), validators=[Email()], description=[None,
                           _(u'The Technical contact you provided while registering')])
