# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView


class IndexView(RedirectView):
    url = reverse_lazy('cosinnus:group-list')

index = IndexView.as_view()
