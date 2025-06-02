from django.urls import path

from cosinnus.core.registries.group_models import group_model_registry
from cosinnus_deck.api.views import DeckLabelsView, DeckLabelView, DeckStacksView, DeckStackView

urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    # add project/group/conference-specific URLs like this
    urlpatterns += [
        # path(f'{url_key}/<str:group>/members/', select2.group_members, name=prefix+'group-members'),
    ]

urlpatterns += [
    path('api/v3/boards/<int:board_id>/stacks/', DeckStacksView.as_view(), name='deck-stacks'),
    path('api/v3/boards/<int:board_id>/stacks/<int:stack_id>/', DeckStackView.as_view(), name='deck-stack-update'),
    path('api/v3/boards/<int:board_id>/labels/', DeckLabelsView.as_view(), name='deck-labels'),
    path('api/v3/boards/<int:board_id>/labels/<int:label_id>/', DeckLabelView.as_view(), name='deck-label-update'),
]
