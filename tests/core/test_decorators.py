# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import unittest
from django.views.generic import View

from cosinnus.core.decorators.views import (require_admin_group,
    require_populate_group, staff_required, superuser_required)


class TestViewDecorators(TestCase):

    def setUp(self):
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
        request.user= self.nostaff
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.staff
        response = view(request)
        self.assertEqual(response.status_code, 302)

        request.user= self.superuser
        response = view(request)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('Not implemented yet.')
    def test_require_admin_group(self):
        class TestView(View):
            @require_admin_group()
            def dispatch(self, request, *args, **kwargs):
                return super(TestView, self).dispatch(request, *args, **kwargs)

    @unittest.skip('Not implemented yet.')
    def test_require_populate_group(self):
        class TestView(View):
            @require_admin_group()
            def dispatch(self, request, *args, **kwargs):
                return super(TestView, self).dispatch(request, *args, **kwargs)
