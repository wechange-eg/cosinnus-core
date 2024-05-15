from cosinnus.fields import Select2MultipleChoiceField
from cosinnus_organization.models import CosinnusOrganization


class OrganizationSelect2MultipleChoiceField(Select2MultipleChoiceField):
    model = CosinnusOrganization
    search_fields = [
        'name__icontains',
    ]
    data_view = ''
    select_type = 'organization'
