from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import migrations, models


def add_user_index(apps, schema_editor):
    User = get_user_model()
    email_index = models.Index(fields=['email'], name='auth_user_email')
    last_login_index = models.Index(fields=['last_login'], name='auth_user_last_login')
    schema_editor.add_index(User, email_index)
    schema_editor.add_index(User, last_login_index)


def revert_add_user_index(apps, schema_editor):
    User = get_user_model()
    email_index = models.Index(fields=['email'], name='auth_user_email')
    last_login_index = models.Index(fields=['last_login'], name='auth_user_last_login')
    schema_editor.remove_index(User, email_index)
    schema_editor.remove_index(User, last_login_index)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cosinnus', '0144_group_subtitle'),
    ]

    operations = [
        migrations.RunPython(add_user_index, revert_add_user_index),
    ]
