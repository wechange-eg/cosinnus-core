# Generated by Django 2.1.15 on 2021-05-16 20:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_organization', '0004_auto_20220126_1128'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cosinnusorganization',
            old_name='extra_fields',
            new_name='dynamic_fields',
        ),
    ]
