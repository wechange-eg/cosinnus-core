# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import range, zip
from unittest import skip
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from cosinnus import tasks
from cosinnus.core.signals import user_deactivated
from cosinnus.models.group import (
    CosinnusGroup,
    CosinnusGroupManager,
    CosinnusGroupMembership,
    remove_stale_pending_memberships,
)
from cosinnus.models.membership import MEMBER_STATUS, MEMBERSHIP_INVITED_PENDING, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING

_GROUP_CACHE_KEY = CosinnusGroupManager._GROUP_CACHE_KEY % (1, 'CosinnusGroupManager', '%s')
_GROUPS_PK_CACHE_KEY = CosinnusGroupManager._GROUPS_PK_CACHE_KEY % (1, 'CosinnusGroupManager')
_GROUPS_SLUG_CACHE_KEY = CosinnusGroupManager._GROUPS_SLUG_CACHE_KEY % (1, 'CosinnusGroupManager')

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


class MembershipSignalHandlerTest(TestCase):
    def setUpTestData():
        group1 = CosinnusGroup.objects.create(name='testgroup1')
        group2 = CosinnusGroup.objects.create(name='testgroup2')
        group3 = CosinnusGroup.objects.create(name='testgroup3')
        user1 = User.objects.create_user('user1')
        user2 = User.objects.create_user('user2')

        CosinnusGroupMembership.objects.create(user=user1, group=group1, status=MEMBERSHIP_PENDING)
        CosinnusGroupMembership.objects.create(user=user1, group=group2, status=MEMBERSHIP_INVITED_PENDING)
        CosinnusGroupMembership.objects.create(user=user1, group=group3, status=MEMBERSHIP_MEMBER)

        CosinnusGroupMembership.objects.create(user=user2, group=group1, status=MEMBERSHIP_PENDING)
        CosinnusGroupMembership.objects.create(user=user2, group=group2, status=MEMBERSHIP_INVITED_PENDING)
        CosinnusGroupMembership.objects.create(user=user2, group=group3, status=MEMBERSHIP_MEMBER)

    def setUp(self):
        self.user1 = User.objects.get(username='user1')
        self.user1_memberships_before = set(CosinnusGroupMembership.objects.filter(user=self.user1))
        self.user1_memberships_after = set(
            CosinnusGroupMembership.objects.filter(user=self.user1, status__in=MEMBER_STATUS)
        )
        self.user2 = User.objects.get(username='user2')
        self.user2_memberships_before = set(CosinnusGroupMembership.objects.filter(user=self.user2))
        self.user2_memberships_after = self.user2_memberships_before

    def test_remove_pending_memberships_for_user_task(self):
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_before
        )
        tasks.remove_pending_memberships_for_user_task(self.user1.id)
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_after
        )

    def test_remove_pending_memberships_for_user_task_no_sideeffect(self):
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_before
        )
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user2.id)), self.user2_memberships_before
        )
        tasks.remove_pending_memberships_for_user_task(self.user1.id)
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_after
        )
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user2.id)), self.user2_memberships_after
        )

    @skip('depends on CosinnusWorkerThread non-threaded celery fallback in tests')
    def test_remove_stale_pending_memberships_for_user_signal_handler(self):
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_before
        )
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user2.id)), self.user2_memberships_before
        )
        remove_stale_pending_memberships(None, self.user1)
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user1.id)), self.user1_memberships_after
        )
        self.assertEqual(
            set(CosinnusGroupMembership.objects.filter(user__id=self.user2.id)), self.user2_memberships_after
        )

    @skip('depends on working TransactionTestCase with fixture restore')
    def test_user_deactivation_signal(self):
        mock_handler = MagicMock()
        user_deactivated.connect(mock_handler)
        self.user1.is_active = False
        self.user1.save()
        mock_handler.assert_called()

    @skip('depends on working TransactionTestCase with fixture restore')
    def test_remove_stale_pending_memberships_for_user_deactivation(self):
        with patch('cosinnus.models.group.remove_stale_pending_memberships') as mock_handler:
            self.user1.is_active = False
            self.user1.save()
            mock_handler.assert_called_once_with(sender=self.user1, user=self.user1)
