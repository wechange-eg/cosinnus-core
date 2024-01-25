# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.urls import reverse
from django.utils.encoding import smart_str

from cosinnus_document.models import Document
from cosinnus_file.models import FileEntry
from cosinnus_etherpad.models import Etherpad
from tests.view_tests.base import ViewTestCase


class ArchiveTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(ArchiveTest, self).setUp(*args, **kwargs)
        self.pad = Etherpad.objects.create(group=self.group, title='testpad')
        self.kwargs = {'group': self.group.slug, 'slug': self.pad.slug}
        self.url = reverse('cosinnus:etherpad:pad-detail', kwargs=self.kwargs)
        self.client_kwargs = {'SERVER_NAME': 'localhost.sinnwerkstatt.com'}

    def tearDown(self, *args, **kwargs):
        # be nice to remote server and delete pad also there
        self.pad.delete()
        super(ArchiveTest, self).tearDown(*args, **kwargs)

    def _has(self, kind):
        """
        Helper for common functionality for has archive tests
        """
        has_kind = 'has_' + kind
        response = self.client.get(self.url, **self.client_kwargs)
        self.assertIn(has_kind, response.context)

        # remove app from INSTALLED_APPS
        appname = 'cosinnus_' + kind
        settings.INSTALLED_APPS = tuple(
            [x for x in settings.INSTALLED_APPS if x != appname])

        response = self.client.get(self.url, **self.client_kwargs)
        self.assertNotIn(has_kind, response.context)


    def test_has_document(self):
        """
        Should have has_document in context if cosinnus_document is installed
        and should not have have_document in context if cosinnus_document is
        not installed
        """
        self._has('document')

    def test_has_file(self):
        """
        Should have has_file in context if cosinnus_file is installed and
        should not have have_file in context if cosinnus_file is not installed
        """
        self._has('file')

    def _archive(self, kind):
        """
        Helper for common functionality for archive tests
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url, **self.client_kwargs)

        url = reverse('cosinnus:etherpad:pad-archive-' + kind, kwargs=self.kwargs)
        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 301)
        self.assertIn(self.url, response.get('location'))

    def test_archive_document(self):
        """
        Should have archived a pad to a document
        """
        self._archive('document')
        doc = Document.objects.all()[0]
        self.assertIn(settings.COSINNUS_ETHERPAD_PREFIX_TITLE, doc.title)
        self.assertEqual(doc.content, self.pad.content)
        self.assertFalse(doc.is_draft)
        doc.delete() # ProtectedError otherwise when deleting CosinnusGroup

    def test_archive_file(self):
        """
        Should have archived a pad to a file entry
        """
        self._archive('file')
        # we should have two FileEntry objects now

        folder = FileEntry.objects.filter(isfolder=True)[0]
        self.assertIn(settings.COSINNUS_ETHERPAD_FILE_PATH, folder.path)

        entry = FileEntry.objects.filter(isfolder=False)[0]
        self.assertIn(settings.COSINNUS_ETHERPAD_FILE_PATH, folder.path)

        # using entry.file.read() fails due to binary content
        # using `with entry.file.open('r')` fails with AttributeError: __exit__
        with open(entry.file.file.name, 'r') as f:
            file_content = smart_str(f.read())
        self.assertEqual(file_content, self.pad.content)

        # ProtectedError otherwise when deleting CosinnusGroup
        folder.delete()
        entry.delete()
