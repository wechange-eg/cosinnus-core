# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import traceback

from django.core.management.base import BaseCommand
from django.utils.encoding import force_str

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import (
    initialize_cosinnus_after_startup,
)
from django.contrib.auth import get_user_model
from cosinnus_cloud.hooks import (
    create_user_from_obj,
    generate_group_nextcloud_id,
    get_nc_user_id,
)
from cosinnus_cloud.utils.nextcloud import OCSException
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_cloud.utils import nextcloud
import requests
from bs4 import BeautifulSoup


logger = logging.getLogger("cosinnus")


class Command(BaseCommand):
    help = "Checks all active groups to create any missing nextcloud groups and group folders"

    def handle(self, *args, **options):
        file_list = nextcloud.list_group_folder_files('Cloud projekt')
        self.stdout.write(str(file_list))
        import ipdb;ipdb.set_trace()
        
        if response.status_code == 507:
            pass
            #raise NotEnoughSpace()
        if response.status_code == 404:
            pass
            #raise RemoteResourceNotFound(path=path)
        if response.status_code == 405:
            pass
            #raise MethodNotSupported(name=action, server=self.webdav.hostname)
        if response.status_code >= 400:
            pass
            #raise ResponseErrorCode(url=self.get_url(path), code=response.status_code, message=response.content)
        return response
            
            
            
            
            