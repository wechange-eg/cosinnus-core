# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.decorators.csrf import csrf_protect
from django.db.models.loading import get_model
from cosinnus.utils.http import JSONResponse
from cosinnus.utils.permissions import check_object_write_access


@csrf_protect
def taggable_object_update_api(request):
    """
    Logs the user specified by the `authentication_form` in.
    """
    if request.method == "POST":
        # TODO: Django<=1.5: Django 1.6 removed the cookie check in favor of CSRF
        request.session.set_test_cookie()
        
        print ">> received request POST", request.POST
        app_label = request.POST.get('app_label')
        model_name = request.POST.get('model_name')
        pk = request.POST.get('pk')
        property_name = request.POST.get('property_name')
        property_data = request.POST.get('property_data')
        
        print ">> getting model:", app_label, model_name
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
        # check attribute exists
        if not hasattr(instance, property_name):
            return JSONResponse('Property "%s" not found for class "%s"!' % (property_name, model_class), status=400)
        
        # attempt the change the object's attribute
        setattr(instance, property_name, property_data)
        instance.save()
        
        # if the save was not successful we return the data that exists in the backend
        if getattr(instance, property_name, None) != property_data:
            return JSONResponse({'status':'error', 'property_name': property_name, 'property_data': getattr(instance, property_name, '')})
        
        return JSONResponse({'status':'success', 'property_name': property_name, 'property_data': getattr(instance, property_name, '')})
    else:
        return JSONResponse({}, status=405)  # Method not allowed
