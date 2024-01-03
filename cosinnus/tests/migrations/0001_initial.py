# Generated by Django 3.2.18 on 2024-01-03 12:15

import cosinnus.models.mixins.indexes
import cosinnus.models.tagged
from django.conf import settings
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.COSINNUS_TAG_OBJECT_MODEL),
        ('cosinnus', '0142_auto_20231124_1501'),
        migrations.swappable_dependency(settings.COSINNUS_GROUP_OBJECT_MODEL),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SlugTestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(blank=True, max_length=55)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('last_action', models.DateTimeField(auto_now_add=True, help_text='A datetime for when a significant action last happened for this object, which users might be interested in. I.e. new comments, special edits, etc.', verbose_name='Last action date')),
                ('settings', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('attached_objects', models.ManyToManyField(blank=True, to='cosinnus.AttachedObject')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tests_slugtestmodel_set', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tests_slugtestmodel_set', to=settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name='Team')),
                ('last_action_user', models.ForeignKey(help_text='The user which caused the last significant action to update the `last_action` datetime.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last action user')),
                ('media_tag', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
            ],
            options={
                'abstract': False,
                'unique_together': {('group', 'slug')},
            },
            bases=(cosinnus.models.tagged.LastVisitedMixin, cosinnus.models.mixins.indexes.IndexingUtilsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ChoicesTestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(blank=True, max_length=55)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='Last modified')),
                ('last_action', models.DateTimeField(auto_now_add=True, help_text='A datetime for when a significant action last happened for this object, which users might be interested in. I.e. new comments, special edits, etc.', verbose_name='Last action date')),
                ('settings', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('state', models.PositiveIntegerField(choices=[(0, 'Scheduled'), (1, 'Voting open'), (2, 'Canceled')], default=1, editable=False, verbose_name='State')),
                ('attached_objects', models.ManyToManyField(blank=True, to='cosinnus.AttachedObject')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tests_choicestestmodel_set', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tests_choicestestmodel_set', to=settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name='Team')),
                ('last_action_user', models.ForeignKey(help_text='The user which caused the last significant action to update the `last_action` datetime.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last action user')),
                ('media_tag', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.COSINNUS_TAG_OBJECT_MODEL)),
            ],
            options={
                'abstract': False,
                'unique_together': {('group', 'slug')},
            },
            bases=(cosinnus.models.tagged.LastVisitedMixin, cosinnus.models.mixins.indexes.IndexingUtilsMixin, models.Model),
        ),
    ]
