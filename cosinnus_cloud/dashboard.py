# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_cloud.models import CloudFile
from cosinnus_cloud.utils import nextcloud
from cosinnus_cloud.hooks import get_nc_user_id
from cosinnus.conf import settings

import logging
from django.utils.encoding import force_str
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group
logger = logging.getLogger('cosinnus')


class LatestCloudFilesForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)


class Latest(DashboardWidget):

    app_name = 'cloud'
    form_class = LatestCloudFilesForm
    model = None
    title = _('Latest Cloud files')
    user_model_attr = None  # No filtering on user page
    widget_name = 'latest'

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        
        rows = []
        total_count = 0
        has_more = False
        had_error = False
        if (is_cloud_enabled_for_group(self.config.group) and 
                self.config.group.nextcloud_group_id and self.config.group.nextcloud_groupfolder_name):
            try:
                response = nextcloud.find_newest_files(
                    userid=get_nc_user_id(self.request.user), 
                    folder=self.config.group.nextcloud_groupfolder_name,
                    page_size=count,
                    page=offset/count + 1,
                )
            except Exception as e:
                logger.error('An error occured during Nextcloud widget data retrieval! Exception in extra.', extra={'exc_str': force_str(e), 'exception': e})
                had_error = True
                
            if had_error:
                total_count = ' '
                rows = []
            else:
                total_count = response['meta']['total']
                has_more = offset+len(rows) < total_count
                rows = [
                    CloudFile(
                        title=doc['info']['file'],
                        path=doc['info']['path'],
                        folder=doc['info']['dir'],
                        url=f"{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}{doc['link']}",
                        download_url=f"{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/remote.php/webdav{doc['info']['path']}"
                    )
                    for doc in response['documents']
                ]
            
        data = {
            'rows': rows,
            'had_error': had_error,
            'no_data': _('No cloud files yet'),
            'group': self.config.group,
            'total_count': total_count,
        }
        return (render_to_string('cosinnus_cloud/widgets/latest.html', data), len(rows), has_more)
    
    
    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return ''
        if self.config.group:
            return group_aware_reverse('cosinnus:cloud:index', kwargs={'group': self.config.group})
        return ''
    