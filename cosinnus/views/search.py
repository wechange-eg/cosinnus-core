# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack.views import SearchView, search_view_factory

from cosinnus.forms.search import TaggableModelSearchForm


class TaggableSearchView(SearchView):
    
    results_per_page = 50

    def __call__(self, request):
        self.request = request
        self.form = self.build_form(form_kwargs=self.get_form_kwargs())
        self.query = self.get_query()
        self.results = self.get_results()
        return self.create_response()

    def get_form_kwargs(self):
        return {
            'request': self.request
        }


search = search_view_factory(TaggableSearchView,
    template='cosinnus/search.html',
    # load_all=True,
    form_class=TaggableModelSearchForm,
    # searchqueryset=None,
    # context_class=RequestContext,
    # results_per_page=None
)
