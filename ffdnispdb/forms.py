from functools import partial
import itertools
from flask.ext.wtf import Form
from wtforms import Form as InsecureForm
from wtforms import TextField, DateField, DecimalField, SelectField, SelectMultipleField, FieldList, FormField
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
    area_name    = TextField(_(u'name'), widget=partial(TextInput(), class_='input-medium', placeholder=_(u'Area')))
    technologies = SelectMultipleField(_(u'technologies'), choices=TECHNOLOGIES_CHOICES,
                                       widget=partial(Select(True), **{'class': 'selectpicker', 'data-title': _(u'Technologies deployed')}))
#    area          =


class ProjectForm(Form):
    name          = TextField(_(u'full name'), description=[_(u'E.g. French Data Network')],
                              validators=[DataRequired(), Length(min=2), Unique(ISP, ISP.name)])
    shortname     = TextField(_(u'short name'), description=[_(u'E.g. FDN')],
                              validators=[Optional(), Length(min=2, max=15), Unique(ISP, ISP.shortname)])
    description   = TextField(_(u'description'), description=[None, _(u'Short text describing the project')])
    logo_url      = TextField(_(u'logo url'), validators=[Optional(), URL(require_tld=True)])
    website       = TextField(_(u'website'), validators=[Optional(), URL(require_tld=True)])
    contact_email = TextField(_(u'contact email'), validators=[Optional(), Email()],
                              description=[None, _(u'General contact email address')])
    main_ml       = TextField(_(u'main mailing list'), validators=[Optional(), Email()],
                              description=[None, u'Address of your main <b>public</b> mailing list'])
    creation_date = DateField(_(u'creation date'), validators=[Optional()],
                              description=[None, u'Date at which the legal structure for your project was created'])
    chatrooms     = FieldList(TextField(_(u'chatrooms')), min_entries=1, widget=InputListWidget(),
                              description=[None, _(u'In URI form, e.g. <code>irc://irc.isp.net/#isp</code> or '+
                                                    '<code>xmpp:isp@chat.isp.net?join</code>')])
    covered_areas = FieldList(MyFormField(CoveredArea, widget=partial(InputListWidget(), class_='formfield')), min_entries=1, widget=InputListWidget(),
                                          description=[None, _(u'Descriptive name of the covered areas and technologies deployed')])
    latitude      = DecimalField(_(u'latitude'), validators=[Optional()],
                             description=[None, _(u'Geographical coordinates of your registered office or usual meeting location.')])
    longitude     = DecimalField(_(u'longitude'), validators=[Optional()])
    step          = SelectField(_(u'step'), choices=[(k, u'%u - %s' % (k, STEPS[k])) for k in STEPS], coerce=int)
    member_count     = DecimalField(_(u'members'), validators=[Optional(), NumberRange(min=0)],
                                    description=[None, _('Number of members')])
    subscriber_count = DecimalField(_(u'subscribers'), validators=[Optional(), NumberRange(min=0)],
                                    description=[None, _('Number of subscribers to an internet access')])

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
        optstr('email', self.contact_email.data)
        optstr('mainMailingList', self.main_ml.data)
        optstr('creationDate', self.creation_date.data)
        optstr('progressStatus', self.step.data)
        optlist('chatrooms', filter(bool, self.chatrooms.data)) # remove empty strings
        return json

    @classmethod
    def edit_json(cls, json):
        obj=type('abject', (object,), {})
        def set_attr(attr, itemk=None):
            if itemk is None:
                itemk=attr
            if itemk in json:
                setattr(obj, attr, json[itemk])
        set_attr('name')
        set_attr('shortname')
        set_attr('description')
        set_attr('logo_url', 'logoURL')
        set_attr('website')
        set_attr('contact_email', 'email')
        set_attr('main_ml', 'mainMailingList')
        set_attr('creation_date', 'creationDate')
        set_attr('step', 'progressStatus')
        return cls(obj=obj)


class ProjectJSONForm(Form):
    url = TextField(_(u'link url'), validators=[Optional(), URL(require_tld=True)])
