# Generated by Django 2.1.15 on 2020-11-09 13:10

import cosinnus.models.mixins.indexes
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0073_merge_20201105_1542'),
    ]

    operations = [
        migrations.CreateModel(
            name='CosinnusManagedTagType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('prefix_label', models.CharField(blank=True, help_text='The label that will be prepended before Managed Tags of this type, instead of `name`', max_length=250, null=True, verbose_name='Prefix label')),
                ('color', models.CharField(blank=True, help_text='Optional color code (css hex value, with or without "#")', max_length=10, null=True, validators=[django.core.validators.MaxLengthValidator(7)], verbose_name='Color')),
            ],
            options={
                'verbose_name': 'Managed Tag Type',
                'verbose_name_plural': 'Managed Tag Types',
                'ordering': ('name',),
            },
        ),
        migrations.AlterModelOptions(
            name='cosinnusmanagedtag',
            options={'ordering': ('name',), 'verbose_name': 'Managed Tag', 'verbose_name_plural': 'Managed Tag'},
        ),
        migrations.AlterModelOptions(
            name='cosinnusmanagedtagassignment',
            options={'verbose_name': 'Managed Tag Assignment', 'verbose_name_plural': 'Managed Tag Assignments'},
        ),
        migrations.RemoveField(
            model_name='cosinnusmanagedtag',
            name='color',
        ),
        migrations.AddField(
            model_name='cosinnusportal',
            name='dynamic_field_choices',
            field=jsonfield.fields.JSONField(default={}, help_text='A dict storage for all choice lists for the dynamic fields of type `DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT`', verbose_name='Dynamic choice field choices'),
        ),
        migrations.AddField(
            model_name='cosinnusmanagedtagtype',
            name='portal',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='managed_tag_types', to='cosinnus.CosinnusPortal', verbose_name='Portal'),
        ),
        migrations.AddField(
            model_name='cosinnusmanagedtag',
            name='type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_tags', to='cosinnus.CosinnusManagedTagType', verbose_name='Managed Tag Type'),
        ),
        migrations.AlterUniqueTogether(
            name='cosinnusmanagedtagtype',
            unique_together={('name', 'portal')},
        ),
    ]
