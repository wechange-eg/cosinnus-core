from django import forms
from django.views.generic import FormView, TemplateView


class MainContentTestView(TemplateView):
    template_name = 'cosinnus/tests/main_content_test.html'


class MainContentTestForm(forms.Form):
    test_field = forms.CharField(required=True)


class MainContentFormTestView(FormView):
    form_class = MainContentTestForm
    template_name = 'cosinnus/tests/main_content_form_test.html'
    success_url = '/success/'


main_content_test_view = MainContentTestView.as_view()
main_content_form_test_view = MainContentFormTestView.as_view()
