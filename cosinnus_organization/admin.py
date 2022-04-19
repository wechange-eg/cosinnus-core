from django.conf import settings
from django.contrib import admin

from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationMembership, \
    CosinnusOrganizationGroup, CosinnusOrganizationLocation

if settings.COSINNUS_ORGANIZATIONS_ENABLED:

    class CosinnusOrganizationLocationInline(admin.TabularInline):
        model = CosinnusOrganizationLocation
        extra = 0

    class CosinnusOrganizationMembershipInline(admin.TabularInline):
        model = CosinnusOrganizationMembership
        extra = 0
        raw_id_fields = ('user', )

    class CosinnusOrganizationGroupInline(admin.TabularInline):
        model = CosinnusOrganizationGroup
        extra = 0
        raw_id_fields = ('group', )

    class CosinnusOrganizationAdmin(admin.ModelAdmin):
        list_display = ('name', 'created', 'creator', 'portal', 'last_modified')
        list_filter = ('created', 'portal')
        search_fields = ('slug', 'name', 'creator__first_name', 'creator__last_name', 'creator__email')
        readonly_fields = ('created',)
        raw_id_fields = ('creator',)
        inlines = [CosinnusOrganizationLocationInline, CosinnusOrganizationMembershipInline,
                   CosinnusOrganizationGroupInline]

    admin.site.register(CosinnusOrganization, CosinnusOrganizationAdmin)

