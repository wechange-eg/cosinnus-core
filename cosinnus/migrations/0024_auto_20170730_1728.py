# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0023_cosinnusunreggroupinv'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseTaggableObjectReflection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('creator', models.ForeignKey(related_name='+', verbose_name='Creator', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(related_name='reflected_objects', to=settings.COSINNUS_GROUP_OBJECT_MODEL)),
            ],
            options={
                'ordering': ('content_type',),
                'verbose_name': 'Reflected Object',
                'verbose_name_plural': 'Reflected Objects',
            },
        ),
        migrations.AlterUniqueTogether(
            name='basetaggableobjectreflection',
            unique_together=set([('content_type', 'object_id', 'group')]),
        ),
    ]
