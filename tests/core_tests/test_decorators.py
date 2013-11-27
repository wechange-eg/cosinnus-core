# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.encoding import force_text
from django.views.generic import View

from cosinnus.core.decorators.views import (require_admin,
    require_membership, staff_required, superuser_required)
from cosinnus.models import CosinnusGroup, GroupAdmin


class TestAdminView(View):
    @require_admin()
    def dispatch(self, request, *args, **kwargs):
        return super(TestAdminView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.group.name)


class TestMembershipView(View):
    @require_membership()
    def dispatch(self, request, *args, **kwargs):
        return super(TestMembershipView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.group.name)


class TestViewPermissionDecorators(TestCase):

    def setUp(self):
        self.anon = AnonymousUser()
        self.nostaff = User.objects.create_user('nostaff', 'nostaff@localhost', 'pw')
        self.staff = User.objects.create_user('staff', 'staff@localhost', 'pw')
        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')
        self.rf = RequestFactory()

    def test_staff_required(self):
        @staff_required
        def view(request):
            return HttpResponse('success')

        request = self.rf.get('/')
        request.user = self.anon
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.nostaff
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.staff
        response = view(request)
        self.assertEqual(response.status_code, 200)

        request.user= self.superuser
        response = view(request)
        self.assertEqual(response.status_code, 200)


    def test_superuser_required(self):
        @superuser_required
        def view(request):
            return HttpResponse('success')

        request = self.rf.get('/')
        request.user = self.anon
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.nostaff
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.staff
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.superuser
        response = view(request)
        self.assertEqual(response.status_code, 200)


class TestRequireAdminDecorator(TestCase):

    def setUp(self):
        self.anon = AnonymousUser()
        self.nostaff = User.objects.create_user('nostaff', 'nostaff@localhost', 'pw')
        self.staff = User.objects.create_user('staff', 'staff@localhost', 'pw')
        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')
        self.rf = RequestFactory()

    def test_allowed(self):
        group = CosinnusGroup.objects.create(name='Group 1')
        GroupAdmin.objects.create(group_id=group.pk, user_id=self.nostaff.pk)
        GroupAdmin.objects.create(group_id=group.pk, user_id=self.staff.pk)
        GroupAdmin.objects.create(group_id=group.pk, user_id=self.superuser.pk)

        request = self.rf.get('/')
        request.user = self.anon
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.nostaff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

        request.user = self.staff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

        request.user = self.superuser
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

    def test_no_member(self):
        group = CosinnusGroup.objects.create(name='Group 1')

        request = self.rf.get('/')
        request.user = self.anon
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.nostaff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.staff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.superuser
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

    def test_no_admin(self):
        group = CosinnusGroup.objects.create(name='Group 1')
        group.users.add(self.nostaff)
        group.users.add(self.staff)
        group.users.add(self.superuser)

        request = self.rf.get('/')
        request.user = self.anon
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.nostaff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.staff
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not an admin of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.superuser
        response = TestAdminView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

    def test_not_existing_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = TestAdminView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.nostaff
        response = TestAdminView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.staff
        response = TestAdminView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = TestAdminView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

    def test_no_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = TestAdminView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.nostaff
        response = TestAdminView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.staff
        response = TestAdminView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = TestAdminView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)


class TestRequireMembershipDecorator(TestCase):

    def setUp(self):
        self.anon = AnonymousUser()
        self.nostaff = User.objects.create_user('nostaff', 'nostaff@localhost', 'pw')
        self.staff = User.objects.create_user('staff', 'staff@localhost', 'pw')
        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')
        self.rf = RequestFactory()

    def test_allowed(self):
        group = CosinnusGroup.objects.create(name='Group 1')
        group.users.add(self.nostaff)
        group.users.add(self.staff)
        group.users.add(self.superuser)

        request = self.rf.get('/')
        request.user = self.anon
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not a member of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.nostaff
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

        request.user = self.staff
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

        request.user = self.superuser
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

    def test_no_member(self):
        group = CosinnusGroup.objects.create(name='Group 1')

        request = self.rf.get('/')
        request.user = self.anon
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not a member of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.nostaff
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not a member of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.staff
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), 'Not a member of this group')
        self.assertEqual(response.status_code, 403)

        request.user = self.superuser
        response = TestMembershipView.as_view()(request, group=group.slug)
        self.assertEqual(force_text(response.content), group.name)
        self.assertEqual(response.status_code, 200)

    def test_not_existing_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = TestMembershipView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.nostaff
        response = TestMembershipView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.staff
        response = TestMembershipView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = TestMembershipView.as_view()(request, group='Other Group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

    def test_no_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = TestMembershipView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.nostaff
        response = TestMembershipView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.staff
        response = TestMembershipView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = TestMembershipView.as_view()(request)
        self.assertEqual(force_text(response.content), 'No group provided')
        self.assertEqual(response.status_code, 404)
