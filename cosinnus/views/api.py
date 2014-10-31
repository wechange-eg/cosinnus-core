# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.loading import get_model
from cosinnus.utils.http import JSONResponse
from cosinnus.utils.permissions import check_object_write_access
from django.views.generic.base import View
from django.utils.importlib import import_module
from django.conf import settings



DEFAULT_DJAJAX_VIEW_CLASS = 'cosinnus.views.api.DjajaxEndpoint'

    
def _resolve_class(path_to_class):
    modulename, _, klass = path_to_class.rpartition('.')
    module = import_module(modulename)
    cls = getattr(module, klass, None)
    if cls is None:
        raise ImportError("Cannot import class %s from %s" % (
            klass, path_to_class))
    return cls


class DjajaxEndpoint(View):
    
    def dispatch(self, request, *args, **kwargs):
        """
            An introspective API endpoint that allows modification of arbitraty django models.
            
            The request must be a POST, be authenticated and supply a csrf token.
            
            By a given app_label, model_name and pk, the model instance to be modified is resolved.
                - write permissions will be checked for that instance via default Cosinnus permissions.
            
            By a given property_name, the field that is supposed to be updated is resolved
                - the field value will be set to ``property_data`` and the instance will be saved
                - Only django fields that are set to be editable can be changed.
                - Related fields are supported. 
                    - We expect ``property_data`` to be the pk of the 
                    related field's target.
                    - The target of the related pk will attempted to be found via the model class set in the
                    related field. If it is not found, the related field's value will be set to None.
                    
        """
        if request.method == "POST":
            # TODO: Django<=1.5: Django 1.6 removed the cookie check in favor of CSRF
            #request.session.set_test_cookie()
            
            app_label = request.POST.get('app_label')
            model_name = request.POST.get('model_name')
            pk = request.POST.get('pk')
            property_name = request.POST.get('property_name')
            property_data = request.POST.get('property_data')
            
            # resolve model class and get instance
            model_class = get_model(app_label, model_name)
            if not model_class:
                return JSONResponse('Model class %s.%s not found!' % (app_label, model_name), status=400)
            try:
                instance = model_class._default_manager.get(pk=pk)
            except model_class.DoesNotExist:
                instance = None
            if not instance:
                return JSONResponse('Object with pk "%s" not found for class "%s"!' % (pk, model_class), status=400)
            
            #check permissions:
            if not check_object_write_access(instance, request.user):
                return JSONResponse('You do not have the necessary permissions to modify this object!', status=403)
            
            # check field exists
            fields = model_class._meta.get_field_by_name(property_name)
            field = fields[0] if fields else None
            if not field or not field.editable:
                return JSONResponse('Field "%s" not found for class "%s"!' % (property_name, model_class), status=400)
    
            # resolve supplied ids for related fields
            is_related_field = hasattr(field, 'related')
            if is_related_field:
                related_class = field.related.parent_model
                try:
                    property_data = related_class._default_manager.get(pk=property_data)
                except related_class.DoesNotExist:
                    property_data = None
            
            value = getattr(instance, property_name, None)
            
            dict_key = None
            if type(value) is dict:
                # we have a dictionary, set its key to the split data
                try:
                    dict_key, property_data = property_data.split(':', 1)
                except ValueError:
                    raise Exception("Could not split value %s into a 'key,value' pair. Is the value seperated with a colon?" % property_data)
                value[dict_key] = property_data
            else:
                # attempt the change the object's attribute
                setattr(instance, property_name, property_data)
            instance.save()
            
            # for related fields, return the pk instead of the object
            return_value =  getattr(instance, property_name, '')
            if dict_key:
                return_value = return_value[dict_key]
            # if the save was not successful we return the data as it is in the backend
            if return_value != property_data:
                return JSONResponse({'status':'error', 'property_name': property_name, 'property_data': return_value})
    
            if return_value and is_related_field:
                return_value = return_value.pk
            
            return JSONResponse({'status':'success', 'property_name': property_name, 'property_data': return_value})
        else:
            return JSONResponse({}, status=405)  # Method not allowed



djajax_endpoint = _resolve_class(settings.DJAJAX_VIEW_CLASS or DEFAULT_DJAJAX_VIEW_CLASS).as_view()
