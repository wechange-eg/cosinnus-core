# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import urllib.parse

from django.http.response import JsonResponse
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import RedirectView, TemplateView
from rest_framework.views import APIView

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.user_dashboard import DashboardItem
from cosinnus.views.mixins.group import RequireReadMixin
from cosinnus.views.user_dashboard import BasePagedOffsetWidgetView
from cosinnus_cloud.hooks import get_email_for_user, get_nc_user_id
from cosinnus_cloud.utils import nextcloud

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


class CloudFilesContentWidgetView(BasePagedOffsetWidgetView):
    """Shows Nextcloud files retrieved via Webdav for the user"""

    model = None
    # if True: will show only content that the user has recently visited
    # if False: will show all of the users content, sorted by creation date
    show_recent = False

    def get(self, request, *args, **kwargs):
        self.show_recent = kwargs.pop('show_recent', False)
        if self.show_recent:
            self.offset_model_field = 'visited'
        else:
            self.offset_model_field = 'created'
        return super(CloudFilesContentWidgetView, self).get(request, *args, **kwargs)

    def get_data(self, **kwargs):
        # we do not use timestamps, but instead just simple paging offsets
        # because Elasticsearch gives that to us for free
        page = 1
        if self.offset_timestamp:
            page = int(self.offset_timestamp)

        has_more = False
        had_error = False
        try:
            dataset = nextcloud.find_newest_files(
                userid=get_nc_user_id(self.request.user), page=page, page_size=self.page_size
            )
        except Exception as e:
            logger.error(
                'An error occured during Nextcloud widget data retrieval! Exception in extra.',
                extra={'exc_str': force_str(e), 'exception': e},
            )
            had_error = True

        if had_error:
            items = []
        else:
            items = self.get_items_from_dataset(dataset)
            has_more = page * self.page_size < dataset['meta']['total']

        return {
            'items': items,
            'widget_title': _('Cloud Files'),
            'has_more': has_more,
            'offset_timestamp': page + 1,
        }

    def get_items_from_dataset(self, dataset):
        """Returns a list of converted item data from the ES result"""
        items = []
        for doc in dataset['documents']:
            item = DashboardItem()
            item['icon'] = 'fa-cloud'
            try:
                item['text'] = escape(doc['info']['file'])
                item['subtext'] = escape(doc['info']['dir'])
            except KeyError:
                continue
            # cloud_file.download_url for a direct download or cloud_file.url for a link into Nextcloud
            item['url'] = f"{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{doc['link']}"
            items.append(item)
        return items


api_user_cloud_files_content = CloudFilesContentWidgetView.as_view()
