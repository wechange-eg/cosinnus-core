# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.encoding import force_text
from django.views.generic import View

from cosinnus.core.decorators.views import (require_admin_access,
    require_read_access, require_write_access, staff_required,
    superuser_required)
from cosinnus.models.group import (MEMBERSHIP_PENDING, MEMBERSHIP_MEMBER,
    MEMBERSHIP_ADMIN, CosinnusGroup as Group,
    CosinnusGroupMembership as Membership)


class TestAdminView(View):
    @require_admin_access()
    def dispatch(self, request, *args, **kwargs):
        return super(TestAdminView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.group.name)


class TestReadView(View):
    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        return super(TestReadView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.group.name)


class TestWriteView(View):
    @require_write_access()
    def dispatch(self, request, *args, **kwargs):
        return super(TestWriteView, self).dispatch(request, *args, **kwargs)

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


class TestRequireAdminAccessDecorator(TestCase):

    def setUp(self):
        self.view = TestAdminView
        self.rf = RequestFactory()

        self.anon = AnonymousUser()
        self.user = User.objects.create_user('user', 'user@localhost', 'pw')
        self.pending = User.objects.create_user('pending', 'pending@localhost', 'pw')
        self.member = User.objects.create_user('member', 'member@localhost', 'pw')
        self.admin = User.objects.create_user('admin', 'admin@localhost', 'pw')
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')

        self.public = Group.objects.create(name='Public group', public=True)
        Membership.objects.create(group_id=self.public.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.public.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.public.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

        self.private = Group.objects.create(name='Private group')
        Membership.objects.create(group_id=self.private.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.private.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.private.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

    def test_anonymous(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

    def test_user(self):
        request = self.rf.get('/')
        request.user = self.user
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

    def test_pending(self):
        request = self.rf.get('/')
        request.user = self.pending
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

    def test_member(self):
        request = self.rf.get('/')
        request.user = self.member
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

    def test_admin(self):
        request = self.rf.get('/')
        request.user = self.admin
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_superuser(self):
        request = self.rf.get('/')
        request.user = self.superuser
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_not_existing_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

    def test_no_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)


class TestRequireReadAccessDecorator(TestCase):

    def setUp(self):
        self.view = TestReadView
        self.rf = RequestFactory()

        self.anon = AnonymousUser()
        self.user = User.objects.create_user('user', 'user@localhost', 'pw')
        self.pending = User.objects.create_user('pending', 'pending@localhost', 'pw')
        self.member = User.objects.create_user('member', 'member@localhost', 'pw')
        self.admin = User.objects.create_user('admin', 'admin@localhost', 'pw')
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')

        self.public = Group.objects.create(name='Public group', public=True)
        Membership.objects.create(group_id=self.public.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.public.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.public.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

        self.private = Group.objects.create(name='Private group')
        Membership.objects.create(group_id=self.private.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.private.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.private.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

    def test_anonymous(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_user(self):
        request = self.rf.get('/')
        request.user = self.user
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_pending(self):
        request = self.rf.get('/')
        request.user = self.pending
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_member(self):
        request = self.rf.get('/')
        request.user = self.member
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_admin(self):
        request = self.rf.get('/')
        request.user = self.admin
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_superuser(self):
        request = self.rf.get('/')
        request.user = self.superuser
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_not_existing_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

    def test_no_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)


class TestRequireWriteAccessDecorator(TestCase):

    def setUp(self):
        self.view = TestWriteView
        self.rf = RequestFactory()

        self.anon = AnonymousUser()
        self.user = User.objects.create_user('user', 'user@localhost', 'pw')
        self.pending = User.objects.create_user('pending', 'pending@localhost', 'pw')
        self.member = User.objects.create_user('member', 'member@localhost', 'pw')
        self.admin = User.objects.create_user('admin', 'admin@localhost', 'pw')
        self.superuser = User.objects.create_superuser('superuser', 'super@localhost', 'pw')

        self.public = Group.objects.create(name='Public group', public=True)
        Membership.objects.create(group_id=self.public.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.public.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.public.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

        self.private = Group.objects.create(name='Private group')
        Membership.objects.create(group_id=self.private.pk, user_id=self.pending.pk, status=MEMBERSHIP_PENDING)
        Membership.objects.create(group_id=self.private.pk, user_id=self.member.pk, status=MEMBERSHIP_MEMBER)
        Membership.objects.create(group_id=self.private.pk, user_id=self.admin.pk, status=MEMBERSHIP_ADMIN)

    def test_anonymous(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

    def test_user(self):
        request = self.rf.get('/')
        request.user = self.user
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_pending(self):
        request = self.rf.get('/')
        request.user = self.pending
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Access denied')
        self.assertEqual(response.status_code, 403)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_member(self):
        request = self.rf.get('/')
        request.user = self.member
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_admin(self):
        request = self.rf.get('/')
        request.user = self.admin
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_superuser(self):
        request = self.rf.get('/')
        request.user = self.superuser
        response = self.view.as_view()(request, group=self.private.slug)
        self.assertEqual(force_text(response.content), 'Private group')
        self.assertEqual(response.status_code, 200)

        response = self.view.as_view()(request, group=self.public.slug)
        self.assertEqual(force_text(response.content), 'Public group')
        self.assertEqual(response.status_code, 200)

    def test_not_existing_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request, group='other-group')
        self.assertEqual(force_text(response.content), 'No group found with this name')
        self.assertEqual(response.status_code, 404)

    def test_no_group(self):
        request = self.rf.get('/')
        request.user = self.anon
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.user
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.pending
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.member
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.admin
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)

        request.user = self.superuser
        response = self.view.as_view()(request)
        self.assertEqual(force_text(response.content), 'No team provided')
        self.assertEqual(response.status_code, 404)
