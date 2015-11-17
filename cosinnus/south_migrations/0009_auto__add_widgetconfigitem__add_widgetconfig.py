# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WidgetConfigItem'
        db.create_table('cosinnus_widgetconfigitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('config', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cosinnus.WidgetConfig'])),
            ('config_key', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('config_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('cosinnus', ['WidgetConfigItem'])

        # Adding model 'WidgetConfig'
        db.create_table('cosinnus_widgetconfig', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app_name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('widget_name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cosinnus.CosinnusGroup'], null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('cosinnus', ['WidgetConfig'])


    def backwards(self, orm):
        # Deleting model 'WidgetConfigItem'
        db.delete_table('cosinnus_widgetconfigitem')

        # Deleting model 'WidgetConfig'
        db.delete_table('cosinnus_widgetconfig')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True', 'symmetrical': 'False'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'object_name': 'Permission', 'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'user_set'", 'to': "orm['auth.Group']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'user_set'", 'to': "orm['auth.Permission']", 'symmetrical': 'False'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'db_table': "'django_content_type'", 'object_name': 'ContentType', 'unique_together': "(('app_label', 'model'),)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'cosinnus.attachedobject': {
            'Meta': {'ordering': "('content_type',)", 'object_name': 'AttachedObject', 'unique_together': "(('content_type', 'object_id'),)"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'cosinnus.cosinnusgroup': {
            'Meta': {'ordering': "('name',)", 'object_name': 'CosinnusGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'blank': 'True', 'unique': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'through': "orm['cosinnus.CosinnusGroupMembership']", 'related_name': "'cosinnus_groups'", 'to': "orm['auth.User']", 'symmetrical': 'False'})
        },
        'cosinnus.cosinnusgroupmembership': {
            'Meta': {'object_name': 'CosinnusGroupMembership', 'unique_together': "(('user', 'group'),)"},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cosinnus.CosinnusGroup']", 'related_name': "'memberships'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True', 'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'related_name': "'cosinnus_memberships'"})
        },
        'cosinnus.tagobject': {
            'Meta': {'object_name': 'TagObject'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'place': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'cosinnus.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'related_name': "'cosinnus_profile'", 'unique': 'True'})
        },
        'cosinnus.widgetconfig': {
            'Meta': {'object_name': 'WidgetConfig'},
            'app_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cosinnus.CosinnusGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'widget_name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'cosinnus.widgetconfigitem': {
            'Meta': {'object_name': 'WidgetConfigItem'},
            'config': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cosinnus.WidgetConfig']"}),
            'config_key': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'config_value': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['cosinnus']