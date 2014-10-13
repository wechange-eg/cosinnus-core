# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_MEMBER, CosinnusGroupManager)

_GROUP_CACHE_KEY = CosinnusGroupManager._GROUP_CACHE_KEY % ('group', '%s')
_GROUPS_PK_CACHE_KEY = CosinnusGroupManager._GROUPS_PK_CACHE_KEY % 'group'
_GROUPS_SLUG_CACHE_KEY = CosinnusGroupManager._GROUPS_SLUG_CACHE_KEY % 'group'

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        groups[-2].slug = new_slug_2
        groups[-2].save()
        slugs.extend([new_slug_2, new_slug_1])  # add in reverse order

        cached_slugs_dict = CosinnusGroup.objects.get_slugs()
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        groups[-2].slug = new_slug_2
        groups[-2].save()
        slugs.extend([new_slug_2, new_slug_1])  # add in reverse order

        cached_pks_dict = CosinnusGroup.objects.get_pks()
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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
        dict_slugs_pks = dict(zip(slugs, pks))
        dict_pks_slugs = dict(zip(pks, slugs))

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

        self.assertIsNone(group._admins)
        self.assertEqual(group.admins, [])
        self.assertEqual(group._admins, [])

        self.assertIsNone(group._members)
        self.assertEqual(group.members, [])
        self.assertEqual(group._members, [])

        self.assertIsNone(group._pendings)
        self.assertEqual(group.pendings, [])
        self.assertEqual(group._pendings, [])

        membership = CosinnusGroupMembership.objects.create(
            user=user, group=group, status=MEMBERSHIP_MEMBER)
        self.assertIsNone(group._admins)
        self.assertEqual(group.admins, [])
        self.assertEqual(group._admins, [])

        self.assertIsNone(group._members)
        self.assertEqual(group.members, [user.pk])
        self.assertEqual(group._members, [user.pk])

        self.assertIsNone(group._pendings)
        self.assertEqual(group.pendings, [])
        self.assertEqual(group._pendings, [])

        membership.delete()
        self.assertIsNone(group._admins)
        self.assertEqual(group.admins, [])
        self.assertEqual(group._admins, [])

        self.assertIsNone(group._members)
        self.assertEqual(group.members, [])
        self.assertEqual(group._members, [])

        self.assertIsNone(group._pendings)
        self.assertEqual(group.pendings, [])
        self.assertEqual(group._pendings, [])
