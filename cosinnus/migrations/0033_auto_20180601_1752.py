# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import cosinnus.utils.files


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0032_cosinnusfailedloginratelimitlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusIdea',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250, verbose_name='Title')),
                ('slug', models.SlugField(help_text='Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!', verbose_name='Slug')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('description', models.TextField(help_text='Short Description. Internal, will not be shown publicly.', verbose_name='Short Description', blank=True)),
                ('image', models.ImageField(upload_to=cosinnus.utils.files.get_idea_image_filename, max_length=250, blank=True, help_text='Shown as large banner image', null=True, verbose_name='Lmage')),
                ('public', models.BooleanField(default=False, verbose_name='Public')),
                ('is_active', models.BooleanField(default=True, help_text='If an idea is not active, it counts as non-existent for all purposes and views on the website.', verbose_name='Is active')),
                ('created_groups', models.ManyToManyField(related_name='_cosinnusidea_created_groups_+', null=True, verbose_name='Created Projects', to=settings.COSINNUS_GROUP_OBJECT_MODEL, blank=True)),
                ('creator', models.ForeignKey(related_name='cosinnus_cosinnusidea_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True)),
                ('media_tag', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
                ('portal', models.ForeignKey(related_name='ideas', default=1, verbose_name='Portal', to='cosinnus.CosinnusPortal')),
            ],
            options={
                'ordering': ('created',),
                'verbose_name': 'Cosinnus Idea',
                'verbose_name_plural': 'Cosinnus Ideas',
            },
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusidea',
            unique_together=set([('slug', 'portal')]),
        ),
    ]
