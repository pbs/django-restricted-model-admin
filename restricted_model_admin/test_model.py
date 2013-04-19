from django.db import models
from models import RestrictedFieldsMixin
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _


class TestModel(RestrictedFieldsMixin, models.Model):
    test_field1 = models.CharField(unique=True, max_length=255)
    test_field2 = models.TextField(_("Description"), blank=True)
    publish_date = models.DateTimeField(blank=True, null=True)
    sites = models.ManyToManyField(
        Site, null=False, blank=True,
        help_text=_('Select on which sites the model will be available.'),
        verbose_name='sites')

    def get_readonly_fields_for_stuff_users(self):
        return ['publish_date'] + \
            super(TestModel, self).get_readonly_fields_for_stuff_users()