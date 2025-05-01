# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import urllib.parse

from django.http.response import JsonResponse
from django.views.generic.base import RedirectView, TemplateView
from rest_framework.views import APIView

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup
from cosinnus.views.mixins.group import RequireReadMixin
from cosinnus_cloud.hooks import get_email_for_user

logger = logging.getLogger('cosinnus')


def get_nextcloud_group_folder_url(group):
    """Returns the direct link to a groupfolder in nextcloud for a given group"""
    if group.nextcloud_group_id and group.nextcloud_groupfolder_name:
        relative_url = settings.COSINNUS_CLOUD_GROUP_FOLDER_IFRAME_URL % {
            'group_folder_name': urllib.parse.quote(group.nextcloud_groupfolder_name),
        }
    else:
        relative_url = ''
    return settings.COSINNUS_CLOUD_NEXTCLOUD_URL + relative_url


class CloudIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        # return group_aware_reverse("cosinnus:cloud:stub", kwargs={"group": self.group})
        return get_nextcloud_group_folder_url(self.group)


cloud_index_view = CloudIndexView.as_view()


class CloudStubView(RequireReadMixin, TemplateView):
    template_name = 'cosinnus_cloud/cloud_stub.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CloudStubView, self).get_context_data(*args, **kwargs)
        context.update(
            {
                'iframe_url': get_nextcloud_group_folder_url(self.group),
            }
        )
        return context


cloud_stub_view = CloudStubView.as_view()


#  ---
class OAuthView(APIView):
    """
    Used by Oauth2 authentication of Nextcloud to retrieve user details
    """

    def get(self, request, **kwargs):
        if request.user.is_authenticated and not request.user.is_guest:
            user = request.user
            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ''
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            return JsonResponse(
                {
                    'success': True,
                    'id': user.id,
                    'email': get_email_for_user(user),
                    'displayName': user.cosinnus_profile.get_external_full_name(),
                    'avatar': avatar_url,
                    'groups': [group.name for group in CosinnusGroup.objects.get_for_user(user)],
                }
            )
        else:
            return JsonResponse(
                {
                    'success': False,
                }
            )


oauth_view = OAuthView.as_view()
