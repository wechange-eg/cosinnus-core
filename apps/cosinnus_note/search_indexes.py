# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseTaggableObjectIndex

from cosinnus_note.models import Note


class NoteIndex(BaseTaggableObjectIndex, indexes.Indexable):

    def get_model(self):
        return Note
