# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0033_auto_20180601_1752'),
    ]

    operations = [
        migrations.CreateModel(
            name='LikeObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('liked', models.BooleanField(default=True, verbose_name='Liked')),
                ('followed', models.BooleanField(default=True, verbose_name='Following')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('user', models.ForeignKey(related_name='likes', verbose_name='User', to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('content_type',),
                'verbose_name': 'Like',
                'verbose_name_plural': 'Likes',
            },
        ),
        migrations.AlterField(
            model_name='cosinnusidea',
            name='creator',
            field=models.ForeignKey(related_name='ideas', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='likeobject',
            unique_together=set([('content_type', 'object_id', 'user')]),
        ),
    ]
