# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import range, zip
from typing import Set

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase

from cosinnus import tasks
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.core.signals import user_deactivated
from cosinnus.models.group import (
    CosinnusGroup,
    CosinnusGroupManager,
    CosinnusGroupMembership,
)
from cosinnus.models.membership import MEMBER_STATUS, MEMBERSHIP_INVITED_PENDING, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING
from cosinnus.tests.utils import catch_signal

_GROUP_CACHE_KEY = CosinnusGroupManager._GROUP_CACHE_KEY % (1, 'CosinnusGroupManager', '%s')
_GROUPS_PK_CACHE_KEY = CosinnusGroupManager._GROUPS_PK_CACHE_KEY % (1, 'CosinnusGroupManager')
_GROUPS_SLUG_CACHE_KEY = CosinnusGroupManager._GROUPS_SLUG_CACHE_KEY % (1, 'CosinnusGroupManager')

# load needed model hooks, since they are loaded in middleware during startup
initialize_cosinnus_after_startup()

User = get_user_model()


def create_multiple_groups():
    groups = []
    pks = []
    slugs = []
    for i in range(10):
        g = CosinnusGroup.objects.create(name='Group %d' % i)
        groups.append(g)
        pks.append(g.pk)
        slugs.append(g.slug)
    cache.clear()
    return groups, pks, slugs


class CosinnusGroupSlugPKCacheTest(TestCase):
    def tearDown(self):
        cache.clear()

    def test_get_slugs(self):
        groups, pks, slugs = create_multiple_groups()
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)
        for slug in slugs:
            self.assertEqual(cache.get(_GROUP_CACHE_KEY % slug), None)

        cached_slugs_dict = CosinnusGroup.objects.get_slugs()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_slugs_dict, dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)

    def test_get_slugs_after_create(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_slugs()

        g = CosinnusGroup.objects.create(name='New group')
        new_slug = g.slug
        new_pk = g.pk
        groups.append(g)
        pks.append(g.pk)
        slugs.append(g.slug)

        cached_slugs_dict = CosinnusGroup.objects.get_slugs()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_slugs_dict, dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(new_slug in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_pk in cache.get(_GROUPS_PK_CACHE_KEY))

    def test_get_slugs_after_delete(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_slugs()

        del_slug = slugs.pop()
        del_pk = pks.pop()
        del_group = groups.pop()
        del_group.delete()

        cached_slugs_dict = CosinnusGroup.objects.get_slugs()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_slugs_dict, dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(del_slug not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(del_pk not in cache.get(_GROUPS_PK_CACHE_KEY))

    def test_get_slugs_after_update(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_slugs()

        del_slug_1 = slugs.pop()
        del_slug_2 = slugs.pop()
        new_slug_1 = 'fancy-slug-1'
        new_slug_2 = 'awesome-slug-1'
        CosinnusGroup.objects.filter(pk=groups[-1].pk).update(slug=new_slug_1)
        CosinnusGroup.objects.filter(pk=groups[-2].pk).update(slug=new_slug_2)
        slugs.extend([new_slug_2, new_slug_1])  # add in reverse order

        cached_slugs_dict = CosinnusGroup.objects.get_slugs()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_slugs_dict, dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(del_slug_1 not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(del_slug_2 not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_slug_1 in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_slug_2 in cache.get(_GROUPS_SLUG_CACHE_KEY))

    def test_get_ids(self):
        groups, pks, slugs = create_multiple_groups()
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)
        for slug in slugs:
            self.assertEqual(cache.get(_GROUP_CACHE_KEY % slug), None)

        cached_pks_dict = CosinnusGroup.objects.get_pks()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_pks_dict, dict_pks_slugs)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)

    def test_get_pks_after_create(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_slugs()

        g = CosinnusGroup.objects.create(name='New group')
        new_slug = g.slug
        new_pk = g.pk
        groups.append(g)
        pks.append(g.pk)
        slugs.append(g.slug)

        cached_pks_dict = CosinnusGroup.objects.get_pks()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_pks_dict, dict_pks_slugs)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(new_slug in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_pk in cache.get(_GROUPS_PK_CACHE_KEY))

    def test_get_pks_after_delete(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_pks()

        del_slug = slugs.pop()
        del_pk = pks.pop()
        del_group = groups.pop()
        del_group.delete()

        cached_pks_dict = CosinnusGroup.objects.get_pks()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_pks_dict, dict_pks_slugs)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(del_slug not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(del_pk not in cache.get(_GROUPS_PK_CACHE_KEY))

    def test_get_pks_after_update(self):
        groups, pks, slugs = create_multiple_groups()
        CosinnusGroup.objects.get_pks()

        del_slug_1 = slugs.pop()
        del_slug_2 = slugs.pop()
        new_slug_1 = 'fancy-slug-1'
        new_slug_2 = 'awesome-slug-1'
        CosinnusGroup.objects.filter(pk=groups[-1].pk).update(slug=new_slug_1)
        CosinnusGroup.objects.filter(pk=groups[-2].pk).update(slug=new_slug_2)
        slugs.extend([new_slug_2, new_slug_1])  # add in reverse order

        cached_pks_dict = CosinnusGroup.objects.get_pks()
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(cached_pks_dict, dict_pks_slugs)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)
        self.assertTrue(del_slug_1 not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(del_slug_2 not in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_slug_1 in cache.get(_GROUPS_SLUG_CACHE_KEY))
        self.assertTrue(new_slug_2 in cache.get(_GROUPS_SLUG_CACHE_KEY))


class CosinnusGroupGetCachedTest(TestCase):
    def tearDown(self):
        cache.clear()

    def test_get_single_by_slug(self):
        groups, pks, slugs = create_multiple_groups()
        s = slugs[-1]

        self.assertEqual(cache.get(_GROUP_CACHE_KEY % s), None)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

        g = CosinnusGroup.objects.get_cached(slugs=s)

        self.assertEqual(g, groups[-1])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % s), g)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

    def test_get_multiple_by_slugs(self):
        groups, pks, slugs = create_multiple_groups()
        ss = slugs[-2:]

        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[0]), None)
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[1]), None)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

        gs = CosinnusGroup.objects.get_cached(slugs=ss)

        self.assertEqual(gs, groups[-2:])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[0]), gs[0])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[1]), gs[1])
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

    def test_get_single_by_pk(self):
        groups, pks, slugs = create_multiple_groups()
        s = slugs[-1]
        p = pks[-1]

        self.assertEqual(cache.get(_GROUP_CACHE_KEY % s), None)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

        g = CosinnusGroup.objects.get_cached(pks=p)
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(g, groups[-1])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % s), g)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)

    def test_get_multiple_by_pks(self):
        groups, pks, slugs = create_multiple_groups()
        ss = slugs[-2:]
        ps = pks[-2:]

        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[0]), None)
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[1]), None)
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), None)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), None)

        gs = CosinnusGroup.objects.get_cached(pks=ps)
        dict_slugs_pks = dict(list(zip(slugs, pks)))
        dict_pks_slugs = dict(list(zip(pks, slugs)))

        self.assertEqual(gs, groups[-2:])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[0]), gs[0])
        self.assertEqual(cache.get(_GROUP_CACHE_KEY % ss[1]), gs[1])
        self.assertEqual(cache.get(_GROUPS_SLUG_CACHE_KEY), dict_slugs_pks)
        self.assertEqual(cache.get(_GROUPS_PK_CACHE_KEY), dict_pks_slugs)


class MembershipCacheTest(TestCase):
    def tearDown(self):
        cache.clear()

    def test_clear_local_caching(self):
        """Regression test for #45"""
        group = CosinnusGroup.objects.create(name='testgroup1')
        user = User.objects.create(username='test1')

        self.assertEqual(group.admins, [])
        self.assertEqual(group.members, [])
        self.assertEqual(group.pendings, [])

        membership = CosinnusGroupMembership.objects.create(user=user, group=group, status=MEMBERSHIP_MEMBER)
        self.assertEqual(group.admins, [])
        self.assertEqual(group.members, [user.pk])
        self.assertEqual(group.pendings, [])

        membership.delete()
        self.assertEqual(group.admins, [])
        self.assertEqual(group.members, [])
        self.assertEqual(group.pendings, [])


class RemovePendingMembershipTestMixin:
    @staticmethod
    def get_memberships(user: User, status__in=None) -> Set[CosinnusGroupMembership]:
        kwargs = dict()
        if status__in is not None:
            kwargs.update(status__in=status__in)
        return set(CosinnusGroupMembership.objects.filter(user__id=user.id, **kwargs))

    @classmethod
    def setUpTestData(cls):
        """Create test data once."""
        cls.user_target = User.objects.create_user('user_target')
        cls.user_other = User.objects.create_user('user_other')

        # create the same group memberships for both users containing PENDING and MEMBER status
        group1 = CosinnusGroup.objects.create(name='testgroup1')
        group2 = CosinnusGroup.objects.create(name='testgroup2')
        group3 = CosinnusGroup.objects.create(name='testgroup3')
        CosinnusGroupMembership.objects.create(user=cls.user_target, group=group1, status=MEMBERSHIP_PENDING)
        CosinnusGroupMembership.objects.create(user=cls.user_target, group=group2, status=MEMBERSHIP_INVITED_PENDING)
        CosinnusGroupMembership.objects.create(user=cls.user_target, group=group3, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=cls.user_other, group=group1, status=MEMBERSHIP_PENDING)
        CosinnusGroupMembership.objects.create(user=cls.user_other, group=group2, status=MEMBERSHIP_INVITED_PENDING)
        CosinnusGroupMembership.objects.create(user=cls.user_other, group=group3, status=MEMBERSHIP_MEMBER)

        # save membership sets for the expected state after the change
        cls.user_target_memberships_expected = cls.get_memberships(cls.user_target, status__in=MEMBER_STATUS)
        cls.user_other_memberships_expected = cls.get_memberships(cls.user_other)


class RemovePendingMembershipsTaskTests(RemovePendingMembershipTestMixin, TestCase):
    def test_removes_pending_memberships_for_target_user(self):
        tasks.remove_pending_memberships_for_user_task(self.user_target.id)
        self.assertEqual(self.get_memberships(user=self.user_target), self.user_target_memberships_expected)

    def test_does_not_affect_other_users_memberships(self):
        tasks.remove_pending_memberships_for_user_task(self.user_target.id)
        self.assertEqual(self.get_memberships(user=self.user_other), self.user_other_memberships_expected)


class RemovePendingMembersSignalIntegrationTests(RemovePendingMembershipTestMixin, TransactionTestCase):
    def setUp(self):
        self.setUpTestData()

    def test_user_deactivation_emits_signal(self):
        with catch_signal(user_deactivated) as handler:
            self.user_target.is_active = False
            self.user_target.save()

        handler.assert_called_with(signal=user_deactivated, sender=User, user=self.user_target)

    def test_removes_pending_memberships_for_target_user(self):
        self.user_target.is_active = False
        self.user_target.save()
        self.assertEqual(
            self.get_memberships(user=self.user_target),
            self.user_target_memberships_expected,
            msg='target user memberships were not deactivated',
        )
        self.assertEqual(
            self.get_memberships(user=self.user_other),
            self.user_other_memberships_expected,
            msg='other user memberships were deactivated',
        )
