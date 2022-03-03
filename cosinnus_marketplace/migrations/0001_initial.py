# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import cosinnus.utils.lanugages
import django.utils.timezone
from django.conf import settings
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0019_cosinnusportal_saved_infos'),
        migrations.swappable_dependency(settings.COSINNUS_GROUP_OBJECT_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created', editable=False)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('text', models.TextField(verbose_name='Text')),
                ('creator', models.ForeignKey(related_name='marketplace_comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Creator', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_on'],
                'verbose_name': 'Comment',
                'verbose_name_plural': 'Comments',
            },
        ),
        migrations.CreateModel(
            name='Offer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(max_length=55, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('type', models.PositiveIntegerField(default=1, verbose_name='Type', choices=[(1, 'Looking for'), (2, 'Offering')])),
                ('is_active', models.BooleanField(default=False, verbose_name='Offer currently active?')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128)),
                ('attached_objects', models.ManyToManyField(to='cosinnus.AttachedObject', null=True, blank=True)),
            ],
            options={
                'ordering': ['-created'],
                'abstract': False,
                'verbose_name': 'Marketplace',
                'verbose_name_plural': 'Marketplaces',
            },
        ),
        migrations.CreateModel(
            name='OfferCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('name_en', models.CharField(max_length=250, null=True, verbose_name='Name (EN)', blank=True)),
                ('name_ru', models.CharField(max_length=250, null=True, verbose_name='Name (RU)', blank=True)),
                ('name_uk', models.CharField(max_length=250, null=True, verbose_name='Name (UK)', blank=True)),
                ('order_key', models.CharField(help_text='Set this to the same key for multiple categories to group them together on the form.', max_length=30, verbose_name='Order Key', blank=True)),
            ],
            options={
                'ordering': ['order_key'],
            },
            bases=(cosinnus.utils.lanugages.MultiLanguageFieldMagicMixin, models.Model),
        ),
        migrations.AddField(
            model_name='offer',
            name='categories',
            field=models.ManyToManyField(related_name='offers', null=True, verbose_name='Offer Category', to='cosinnus_marketplace.OfferCategory', blank=True),
        ),
        migrations.AddField(
            model_name='offer',
            name='creator',
            field=models.ForeignKey(related_name='cosinnus_marketplace_offer_set', verbose_name='Creator', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='offer',
            name='group',
            field=models.ForeignKey(related_name='cosinnus_marketplace_offer_set', verbose_name='Team', to=settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='offer',
            name='media_tag',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.COSINNUS_TAG_OBJECT_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='offer',
            field=models.ForeignKey(related_name='comments', to='cosinnus_marketplace.Offer', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='offer',
            unique_together=set([('group', 'slug')]),
        ),
    ]
