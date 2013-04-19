# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RestrictedFields'
        db.create_table('restricted_model_admin_restrictedfields', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pbs_provided', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('read_only', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('restricted_model_admin', ['RestrictedFields'])


    def backwards(self, orm):
        # Deleting model 'RestrictedFields'
        db.delete_table('restricted_model_admin_restrictedfields')


    models = {
        'restricted_model_admin.restrictedfields': {
            'Meta': {'object_name': 'RestrictedFields'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pbs_provided': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'read_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['restricted_model_admin']