from django.views.generic import TemplateView


class MainContentTestView(TemplateView):
    template_name = 'cosinnus/tests/main_content_test.html'


main_content_test_view = MainContentTestView.as_view()
