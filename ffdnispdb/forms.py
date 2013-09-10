from functools import partial
import itertools
from flask.ext.wtf import Form
from wtforms import Form as InsecureForm
from wtforms import (TextField, DateField, DecimalField, IntegerField, SelectField,
                     SelectMultipleField, FieldList, FormField)
from wtforms.widgets import TextInput, ListWidget, html_params, HTMLString, CheckboxInput, Select
from wtforms.validators import DataRequired, Optional, URL, Email, Length, NumberRange, ValidationError
from flask.ext.babel import Babel, gettext as _
from .constants import STEPS
from .models import ISP


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

class Unique(object):
    """ validator that checks field uniqueness """
    def __init__(self, model, field, message=None, allow_edit=False):
        self.model = model
        self.field = field
        if not message:
            message = _(u'this element already exists')
        self.message = message

    def __call__(self, form, field):
        default=field.default() if callable(field.default) else field.default
        if field.object_data != default and field.object_data == field.data:
            return
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)


TECHNOLOGIES_CHOICES=(
    ('ftth', _('FTTH')),
    ('dsl', _('DSL')),
    ('wifi', _('Wi-Fi')),
)
class CoveredArea(InsecureForm):
    name         = TextField(_(u'name'), widget=partial(TextInput(), class_='input-medium', placeholder=_(u'Area')))
    technologies = SelectMultipleField(_(u'technologies'), choices=TECHNOLOGIES_CHOICES,
                                       widget=partial(Select(True), **{'class': 'selectpicker', 'data-title': _(u'Technologies deployed')}))
#    area          =

    def validate(self, *args, **kwargs):
        r=super(CoveredArea, self).validate(*args, **kwargs)
        if bool(self.name.data) != bool(self.technologies.data):
            self._fields['name'].errors += [_(u'You must fill both fields')]
            r=False
        return r


class OtherWebsites(InsecureForm):
    name = TextField(_(u'name'), widget=partial(TextInput(), class_='input-small', placeholder=_(u'Name')))
    url  = TextField(_(u'url'), widget=partial(TextInput(), class_='input-medium', placeholder=_(u'URL')),
                     validators=[Optional(), URL(require_tld=True)])


class ProjectForm(Form):
    name          = TextField(_(u'full name'), description=[_(u'E.g. French Data Network')],
                              validators=[DataRequired(), Length(min=2), Unique(ISP, ISP.name)])
    shortname     = TextField(_(u'short name'), description=[_(u'E.g. FDN')],
                              validators=[Optional(), Length(min=2, max=15), Unique(ISP, ISP.shortname)])
    description   = TextField(_(u'description'), description=[None, _(u'Short text describing the project')])
    logo_url      = TextField(_(u'logo url'), validators=[Optional(), URL(require_tld=True)])
    website       = TextField(_(u'website'), validators=[Optional(), URL(require_tld=True)])
    other_websites= FieldList(MyFormField(OtherWebsites, widget=partial(InputListWidget(), class_='formfield')),
                                          min_entries=1, widget=InputListWidget(),
                                          description=[None, _(u'Additional websites that you host (e.g. wiki, etherpad...)')])
    contact_email = TextField(_(u'contact email'), validators=[Optional(), Email()],
                              description=[None, _(u'General contact email address')])
    main_ml       = TextField(_(u'main mailing list'), validators=[Optional(), Email()],
                              description=[None, u'Address of your main mailing list'])
    creation_date = DateField(_(u'creation date'), validators=[Optional()],
                              description=[None, u'Date at which the legal structure for your project was created'])
    chatrooms     = FieldList(TextField(_(u'chatrooms')), min_entries=1, widget=InputListWidget(),
                              description=[None, _(u'In URI form, e.g. <code>irc://irc.isp.net/#isp</code> or '+
                                                    '<code>xmpp:isp@chat.isp.net?join</code>')])
    covered_areas = FieldList(MyFormField(CoveredArea, widget=partial(InputListWidget(), class_='formfield')),
                                          min_entries=1, widget=InputListWidget(),
                                          description=[None, _(u'Descriptive name of the covered areas and technologies deployed')])
    latitude      = DecimalField(_(u'latitude'), validators=[Optional(), NumberRange(min=-90, max=90)],
                             description=[None, _(u'Geographical coordinates of your registered office or usual meeting location.')])
    longitude     = DecimalField(_(u'longitude'), validators=[Optional(), NumberRange(min=-180, max=180)])
    step          = SelectField(_(u'progress step'), choices=[(k, u'%u - %s' % (k, STEPS[k])) for k in STEPS], coerce=int)
    member_count     = IntegerField(_(u'members'), validators=[Optional(), NumberRange(min=0)],
                                    description=[None, _('Number of members')])
    subscriber_count = IntegerField(_(u'subscribers'), validators=[Optional(), NumberRange(min=0)],
                                    description=[None, _('Number of subscribers to an internet access')])

    def validate(self, *args, **kwargs):
        r=super(ProjectForm, self).validate(*args, **kwargs)
        if (self.latitude.data is None) != (self.longitude.data is None):
            self._fields['longitude'].errors += [_(u'You must fill both fields')]
            r=False
        return r

    def validate_covered_areas(self, field):
        if len(filter(lambda e: e['name'], field.data)) == 0:
            # not printed, whatever..
            raise ValidationError(_(u'You must specify at least one area'))

    def to_json(self, json=None):
        if json is None:
            json={}

        json['name'] = self.name.data

        def optstr(k, v):
            if k in json or v:
                json[k]=v

        def optlist(k, v):
            if k in json or len(v):
                json[k]=v

        optstr('shortname', self.shortname.data)
        optstr('description', self.description.data)
        optstr('logoURL', self.logo_url.data)
        optstr('website', self.website.data)
        optstr('otherWebsites', dict(((w['name'], w['url']) for w in self.other_websites.data)))
        optstr('email', self.contact_email.data)
        optstr('mainMailingList', self.main_ml.data)
        optstr('creationDate', self.creation_date.data)
        optstr('progressStatus', self.step.data)
        optstr('memberCount', self.member_count.data)
        optstr('subscriberCount', self.subscriber_count.data)
        optlist('chatrooms', filter(bool, self.chatrooms.data)) # remove empty strings
        optstr('coordinates', {'latitude': self.latitude.data, 'longitude': self.longitude.data}
                                if self.latitude.data else {})
        optlist('coveredAreas', filter(lambda e: e['name'], self.covered_areas.data))
        return json

    @classmethod
    def edit_json(cls, json):
        obj=type('abject', (object,), {})()
        def set_attr(attr, itemk=None, d=json):
            if itemk is None:
                itemk=attr
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
        return cls(obj=obj)


class ProjectJSONForm(Form):
    url = TextField(_(u'link url'), validators=[Optional(), URL(require_tld=True)])

