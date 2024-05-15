"""
Created on 05.08.2014

@author: Sascha
"""

from builtins import object

from django.db.models.aggregates import Count
from django.utils.translation import gettext_lazy as _

from cosinnus.forms.filters import AllObjectsFilter, DropdownChoiceWidget, SelectCreatorWidget
from cosinnus.views.mixins.filters import CosinnusFilterSet, CosinnusOrderingFilter
from cosinnus_note.models import Note


class NoteFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)

    o = CosinnusOrderingFilter(
        fields=(
            ('created', 'created'),
            ('num_comments', 'num_comments'),
        ),
        choices=(
            ('-created', _('Newest Created')),
            ('-num_comments', _('Popularity')),
        ),
        default='-created',
        widget=DropdownChoiceWidget,
    )

    class Meta(object):
        model = Note
        fields = ['creator', 'o']

    @property
    def qs(self):
        if not hasattr(self, '_qs') and hasattr(self, 'queryset'):
            self.queryset = self.queryset.annotate(num_comments=Count('comments'))
        return super(NoteFilter, self).qs
