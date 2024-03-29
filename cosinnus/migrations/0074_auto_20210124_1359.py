# Generated by Django 2.1.15 on 2021-01-24 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0073_auto_20201126_1152'),
    ]

    operations = [
        migrations.AddField(
            model_name='cosinnusportal',
            name='bbb_server',
            field=models.PositiveSmallIntegerField(choices=[(0, '(None)')], default=0, help_text='The chosen BBB-Server/Cluster for the entire portal. WARNING: changing this will cause new meeting connections to use the new server, even for ongoing meetings on the old server, essentially splitting a running meeting in two!', verbose_name='BBB Server'),
        ),
        migrations.AlterField(
            model_name='cosinnusportal',
            name='video_conference_server',
            field=models.URLField(blank=True, help_text='For old-style events meeting popups only! If entered, will enable Jitsi-like video conference functionality across the site. Needs to be a URL up to the point where any random room name can be appended.', max_length=250, null=True, verbose_name='Video Conference Server'),
        ),
    ]
