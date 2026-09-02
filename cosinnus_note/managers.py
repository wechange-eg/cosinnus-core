from django.db.models.functions import Length

from cosinnus.models import BaseTaggableObjectManager


class NoteManager(BaseTaggableObjectManager):
    def get_personal_items(self, user):
        queryset = super().get_personal_items(user)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_note')
        return queryset

    def get_recommendations(self, user):
        queryset = super().get_recommendations(user)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_note')
        queryset = queryset.annotate(text_length=Length('text')).filter(text_length__gte=100)
        return queryset
