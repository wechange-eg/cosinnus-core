from django.views.generic.base import TemplateView
from django.shortcuts import redirect, render
from django.utils.translation import ugettext as _
from django.contrib import messages

from cosinnus.models import CosinnusPortal
from cosinnus.forms.dynamic_fields import DynamicFieldFormGenerator


class DynamicFieldFormView(TemplateView):
    
    template_name = 'cosinnus/dynamic_fields/dynamic_field_form.html'
    form_generator_class = DynamicFieldFormGenerator
    
    def get(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=CosinnusPortal.get_current())
        forms = generator.get_forms()

        return render(request, template_name=self.template_name, context={'forms': forms})

    def post(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=CosinnusPortal.get_current(), data=request.POST)
        forms = generator.get_forms()

        generator.try_save()
        if generator.saved:
            messages.success(self.request, _("Your data was set successfully!"))

        return render(request, template_name=self.template_name, context={'forms': forms})

dynamic_field_form_view = DynamicFieldFormView.as_view()
