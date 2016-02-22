# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings


def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

def attach_swappable_dependencies(regular_dependencies):
    """ Adds the apps containing active swappable models to the migration dependencies.
        This needs to be done to ALL new cosinnus core migrations to enable the swappable
        models to exist in an app that is not cosinnus at a later point.
        
        This gets rid of the following error when trying to run ``./manage.py migrate``:
        "ValueError: Lookup failed for model referenced by field <...>"
        
        To use, wrap your migration's dependency list in this function, as such: 
        
        ``
        from cosinnus.utils.migrations import attach_swappable_dependencies
        
        class Migration(migrations.Migration):
            
            dependencies = attach_swappable_dependencies([
                ('cosinnus', '0003_auto_20160125_1339'),
            ])
        
            operations = [
            ...
        `` 
    """
    app_name, __ = settings.COSINNUS_GROUP_OBJECT_MODEL.split('.')
    extra_dependencies = []
    
    dependency_target_from_settings = getattr(settings, 'COSINNUS_SWAPPABLE_MIGRATION_DEPENDENCY_TARGET', None)
    if dependency_target_from_settings:
        extra_dependencies = [(app_name, dependency_target_from_settings), ]
    elif module_exists('%s.migrations.0001_initial' % app_name):
        extra_dependencies = [(app_name, '0001_initial'), ]
    
    return extra_dependencies + regular_dependencies
    