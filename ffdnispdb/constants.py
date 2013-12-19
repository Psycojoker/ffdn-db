# -*- coding: utf-8 -*-

from flask.ext.babel import lazy_gettext as _

STEPS = {
    1: _(u'Project considered'),
    2: _(u'Primary members found'),
    3: _(u'Legal structure being created'),
    4: _(u'Legal structure created'),
    5: _(u'Base tools created (bank account, first members)'),
    6: _(u'ISP partially functional (first subscribers, maybe in degraded mode)'),
    7: _(u'ISP fully working')
}

STEPS_LABELS = {
    1: '',
    2: 'info',
    3: 'info',
    4: 'important',
    5: 'important',
    6: 'warning',
    7: 'success'
}
