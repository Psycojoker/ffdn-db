from functools import partial
import itertools
from flask.ext.wtf import Form
from wtforms import Form as InsecureForm
from wtforms import TextField, DecimalField, SelectField, SelectMultipleField, FieldList, FormField
from wtforms.widgets import TextInput, ListWidget, html_params, HTMLString, CheckboxInput, Select
from wtforms.validators import DataRequired, Optional, URL, Email, Length
from flask.ext.babel import Babel, gettext as _
from settings import STEPS


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
    name          = TextField(_(u'full name'), validators=[DataRequired(), Length(min=2)], description=[_(u'E.g. French Data Network')])
    short_name    = TextField(_(u'short name'), validators=[Optional(), Length(min=2, max=15)], description=[_(u'E.g. FDN')])
    description   = TextField(_(u'description'), description=[None, _(u'Short text describing the project')])
    website       = TextField(_(u'website'), validators=[Optional(), URL(require_tld=True)])
    contact_email = TextField(_(u'contact email'), validators=[Optional(), Email()])
    chatrooms     = FieldList(TextField(_(u'chatrooms')), min_entries=1, widget=InputListWidget(),
                              description=[None, _(u'In URI form, e.g. <code>irc://irc.isp.net/#isp</code> or <code>xmpp:isp@chat.isp.net?join</code>')])
    covered_areas = FieldList(MyFormField(CoveredArea, widget=partial(InputListWidget(), class_='formfield')), min_entries=1, widget=InputListWidget(),
                                        description=[None, _(u'Descriptive name of the covered areas and technologies deployed')])
    latitude      = DecimalField(_(u'latitude'), validators=[Optional()],
                             description=[None, _(u'Geographical coordinates of your registered office or usual meeting location.')])
    longitude     = DecimalField(_(u'longitude'), validators=[Optional()])
    step          = SelectField(_(u'step'), choices=[(k, u'%u - %s' % (k, STEPS[k])) for k in STEPS], coerce=int)
