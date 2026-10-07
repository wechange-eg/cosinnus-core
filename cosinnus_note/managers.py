from django.db.models.functions import Length

from cosinnus.models import BaseTaggableObjectManager


class NoteManager(BaseTaggableObjectManager):
    def get_recommendations(self, user):
        queryset = super().get_recommendations(user)
        queryset = queryset.prefetch_related('comments')
        queryset = queryset.annotate(text_length=Length('text')).filter(text_length__gte=100)
        return queryset
