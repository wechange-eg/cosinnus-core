# -*- coding: utf-8 -*-
"""
Created on 08.07.2014

@author: Sascha Narr
"""
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_note.models import Note


class NoteRenderer(BaseRenderer):
    
    model = Note

    template = 'cosinnus_note/attached_notes.html'
    template_v2 = 'cosinnus_note/v2/attached_notes.html'
    template_single = 'cosinnus_note/single_note_detailed.html'
    template_list = 'cosinnus_note/note_list_standalone.html'
    

    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return super(NoteRenderer, cls).render(context, notes=myobjs, **kwargs)
