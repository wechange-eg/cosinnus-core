from cosinnus.models import BaseTaggableObjectManager


class NoteManager(BaseTaggableObjectManager):
    def get_personal_items(self, user):
        queryset = super().get_personal_items(user)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_note')
        return queryset
