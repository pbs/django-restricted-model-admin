from django.db import models
from django.utils.translation import ugettext_lazy as _

class RestrictedFieldsMixin(models.Model):
    pbs_provided = models.BooleanField(_('pbs provided'), default=False)
    read_only = models.BooleanField(_('read only'), default=False)

    class Meta:
        abstract = True

    def get_readonly_fields_for_stuff_users(self):
        return ['pbs_provided', 'read_only']
