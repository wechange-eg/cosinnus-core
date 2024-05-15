# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.timezone import now

from cosinnus.models import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.membership import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER
from cosinnus.models.tagged import BaseTagObject
from cosinnus_todo.models import TodoEntry, TodoList


class ViewTestCase(TestCase):
    def setUp(self, *args, **kwargs):
        super(ViewTestCase, self).setUp(*args, **kwargs)
        self.client = Client()
        self.group = CosinnusGroup.objects.create(name='testgroup', public=True)
        self.group.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        self.group.media_tag.save()
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email='admin@example.com', password=self.credential, last_login=now()
        )
        self.admin.cosinnus_profile.tos_accepted = True
        self.admin.cosinnus_profile.email_verified = True
        self.admin.cosinnus_profile.save()
        CosinnusGroupMembership.objects.create(user=self.admin, group=self.group, status=MEMBERSHIP_ADMIN)
        todo_list = TodoList.objects.first()
        self.todo = TodoEntry.objects.create(group=self.group, title='testtodo', creator=self.admin, todolist=todo_list)
        self.kwargs = {'group': self.group.slug, 'slug': self.todo.slug}

    def add_user(self, credential):
        self.user = User.objects.create_user(
            username=credential, password=credential, email=f'{credential}@example.com', last_login=now()
        )
        CosinnusGroupMembership.objects.create(user=self.user, group=self.group, status=MEMBERSHIP_MEMBER)
        return self.user

    def execute_no_field(self, urlname):
        """
        Executes a post to given urlname, which should be a view with no
        form fields, and then returns the modified Todo entry.
        """
        url = reverse('cosinnus:todo:' + urlname, kwargs=self.kwargs)
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('cosinnus:todo:entry-detail', kwargs=self.kwargs), response.get('location'))
        return TodoEntry.objects.get(pk=self.todo.pk)
