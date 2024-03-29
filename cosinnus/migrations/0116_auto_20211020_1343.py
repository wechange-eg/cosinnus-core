# Generated by Django 2.1.15 on 2021-10-20 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0115_add_translations_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cosinnusgroupmembership',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited'), (4, 'manager')], db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name='cosinnusportalmembership',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited'), (4, 'manager')], db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name='cosinnusunregisterdusergroupinvite',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'pending'), (1, 'member'), (2, 'admin'), (3, 'pending-invited'), (4, 'manager')], db_index=True, default=0),
        ),
    ]
