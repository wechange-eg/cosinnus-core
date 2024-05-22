"""
Created on 05.08.2014

@author: Sascha
"""

from builtins import object

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from django_filters.filters import ChoiceFilter

from cosinnus.forms.filters import AllObjectsFilter, DropdownChoiceWidget, SelectCreatorWidget
from cosinnus.views.mixins.filters import CosinnusFilterSet, CosinnusOrderingFilter
from cosinnus_file.models import FileEntry

FILE_TYPE_FILTER_CHOICES = [
    ('images', _('Pictures')),
    ('documents', _('Documents')),
    ('audio', _('Audio Files')),
    ('videos', _('Videos')),
]


class FileTypeFilter(ChoiceFilter):
    file_extensions = {
        'images': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
        'documents': ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlx', 'xlsx', 'rtf', 'txt', 'odt', 'odf', 'odp'],
        'audio': ['wav', 'mp3', 'ogg'],
        'videos': ['mov', 'avi', 'mp4', 'mpeg', 'mpg', 'flv'],
    }

    def filter(self, qs, value):
        if not value:
            return qs
        if value not in self.file_extensions:
            raise ImproperlyConfigured('FileType filer %s not found!' % value)

        result_qs = self.model._default_manager.none()
        for ext in self.file_extensions.get(value):
            filter_value = ('.%s' % ext, 'iendswith')
            result_qs |= super(FileTypeFilter, self).filter(qs, filter_value)

        return result_qs


class FileFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    filetype = FileTypeFilter(
        label=_('File Type'),
        field_name='_sourcefilename',
        choices=FILE_TYPE_FILTER_CHOICES,
        widget=DropdownChoiceWidget,
    )

    o = CosinnusOrderingFilter(
        fields=(
            ('created', 'created'),
            ('_filesize', 'filesize'),
            ('title', 'title'),
        ),
        choices=(
            ('title', _('File Name')),
            ('-title', _('File Name (descending)')),
            ('-created', _('Newest Created')),
            ('filesize', _('Smallest Files')),
            ('-filesize', _('Largest Files')),
        ),
        default='-title',
        widget=DropdownChoiceWidget,
    )

    class Meta(object):
        model = FileEntry
        fields = ['creator', 'filetype', 'o']
