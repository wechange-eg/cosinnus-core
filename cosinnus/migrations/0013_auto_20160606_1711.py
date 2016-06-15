# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import cosinnus.utils.files
from django.conf import settings
from cosinnus.utils.migrations import attach_swappable_dependencies


class Migration(migrations.Migration):

    dependencies = attach_swappable_dependencies([
        ('cosinnus', '0012_auto_20160531_1635'),
    ])

    operations = [
        migrations.CreateModel(
            name='CosinnusGroupGalleryImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250, null=True, verbose_name='Title', blank=True)),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('image', models.ImageField(upload_to=cosinnus.utils.files.get_group_gallery_image_filename, max_length=250, verbose_name='Group Image')),
                ('group', models.ForeignKey(related_name='gallery_images', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL)),
            ],
            options={
                'verbose_name': 'CosinnusGroup GalleryImage',
                'verbose_name_plural': 'CosinnusGroup GalleryImages',
            },
        ),
    ]
