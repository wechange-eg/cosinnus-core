from django.conf import settings
from django.contrib import admin

from cosinnus_organization.models import CosinnusOrganization

if settings.COSINNUS_ORGANIZATIONS_ENABLED:

    class CosinnusOrganizationAdmin(admin.ModelAdmin):
        list_display = ('name', 'created', 'creator', 'portal')
        list_filter = ('created', 'portal')
        search_fields = ('slug', 'name', 'creator__first_name', 'creator__last_name', 'creator__email')
        readonly_fields = ('created',)
        raw_id_fields = ('creator',)

    admin.site.register(CosinnusOrganization, CosinnusOrganizationAdmin)