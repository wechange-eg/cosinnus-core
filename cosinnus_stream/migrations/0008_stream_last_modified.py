# Generated by Django 2.0.9 on 2018-11-16 18:44

from django.db import migrations, models


def set_last_modified(apps, schema_editor):
    Stream = apps.get_model('cosinnus_stream', 'Stream')
    Stream.objects.update(last_modified=models.F('created'))


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_stream', '0007_auto_20181105_1310'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='Last modified'),
        ),
        migrations.RunPython(set_last_modified, migrations.RunPython.noop)
    ]