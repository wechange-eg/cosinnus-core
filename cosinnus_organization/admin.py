from django.conf import settings
from django.contrib import admin

from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationMembership

if settings.COSINNUS_ORGANIZATIONS_ENABLED:

    class CosinnusOrganizationMembershipInline(admin.TabularInline):
        model = CosinnusOrganizationMembership
        extra = 0

    class CosinnusOrganizationAdmin(admin.ModelAdmin):
        list_display = ('name', 'created', 'creator', 'portal')
        list_filter = ('created', 'portal')
        search_fields = ('slug', 'name', 'creator__first_name', 'creator__last_name', 'creator__email')
        readonly_fields = ('created',)
        raw_id_fields = ('creator',)
        inlines = [CosinnusOrganizationMembershipInline, ]

    admin.site.register(CosinnusOrganization, CosinnusOrganizationAdmin)

