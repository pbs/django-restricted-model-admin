from django.db import models
from django.utils.translation import ugettext_lazy as _

#BlogEntry and Robots Rule inherit from this class because they don't have read_only field
class RestrictedPBSProvidedMixin(models.Model):
    pbs_provided = models.BooleanField(_('pbs provided'), default=False)

    class Meta:
        abstract = True

    def get_readonly_fields_for_stuff_users(self):
        return ['pbs_provided']


class RestrictedFieldsMixin(RestrictedPBSProvidedMixin):
    """
    #Some model classes have both fields(SmartSnippet and Template)
    In case of templates(and also snippets), the difference between
    'PBS Provided' and 'Read Only' is the following: a 'PBS Provided'
    template (and snippet) is available to ALL users and READ_ONLY to
    ALL users, while a 'Read Only' template is available to SOME users
    and READ_ONLY to SOME users. So a template/snippet can have 'PBS Provided'
    field to False an still be read only (if 'Read Only field is True').
    """
    read_only = models.BooleanField(_('read only'), default=False)

    class Meta:
        abstract = True

    def get_readonly_fields_for_stuff_users(self):
        return super(RestrictedFieldsMixin, self).get_readonly_fields_for_stuff_users() + \
            ['read_only']
