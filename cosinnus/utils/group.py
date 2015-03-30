# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import get_model


DEFAULT_CONTENT_MODELS = [
    'cosinnus_note.Note', 
    'cosinnus_file.FileEntry',
    'cosinnus_event.Event',
    'cosinnus_todo.TodoEntry',
    'cosinnus_etherpad.Etherpad'
]

def move_group_content(from_group, to_group, models=None, verbose=False):
    """ Moves all BaseTaggableObject content from one CosinnusGroup to another. """
    if not models:
        models = DEFAULT_CONTENT_MODELS
    
    actions_done = []
    for model_str in models:
        app_label, model = model_str.split('.')
        model_cls = get_model(app_label, model)
        for obj in model_cls.objects.filter(group=from_group):
            obj.group = to_group
            obj.save()
            s = "moved '%d' %s: from group %d to group %d" % (obj.id, model_str, from_group.id, to_group.id)
            if verbose:
                print s
            actions_done.append(s)
    return actions_done
