# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http.response import HttpResponseNotAllowed, HttpResponseForbidden
from cosinnus.utils.http import JSONResponse
from django.views.decorators.csrf import csrf_protect
from cosinnus.models.feedback import CosinnusReportedObject
from django.contrib.contenttypes.models import ContentType
from django.db.models import get_model
from cosinnus.utils.context_processors import cosinnus as cosinnus_context
from cosinnus.core.mail import get_common_mail_context, send_mail_or_fail
from cosinnus.templatetags.cosinnus_tags import full_name
from django.utils.encoding import force_text
from cosinnus.models.tagged import BaseTaggableObjectModel
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from cosinnus.models.group import CosinnusPortal, CosinnusGroup
from django.core.urlresolvers import reverse


def _notify_users_for_reported_objects(report_obj, request=None):
    template = 'cosinnus/mail/reported_object_submitted.html'
    subj_template = 'cosinnus/mail/reported_object_submitted_subj.txt'
    if request:
        context = get_common_mail_context(request, user=report_obj.creator)
        context.update(cosinnus_context(request))
    else:
        context = {} 
    
    target_obj = report_obj.target_object
    title = getattr(target_obj, 'title', getattr(target_obj, 'name', force_text(target_obj)))
    report_url = reverse('admin:cosinnus_cosinnusreportedobject_change', args=(report_obj.id,))
    
    portal = None   
    if issubclass(target_obj.__class__, BaseTaggableObjectModel):
        portal = target_obj.group.portal
    elif issubclass(target_obj.__class__, CosinnusGroup):
        portal = target_obj.portal
    else:
        portal = CosinnusPortal.get_current()
    portal_admins = get_user_model().objects.all().exclude(is_active=False).exclude(last_login__exact=None).filter(id__in=portal.admins)
    
    for receiver in portal_admins:
        context.update({
            'receiver':receiver, 
            'receiver_name':full_name(receiver), 
            'sender':report_obj.creator, 
            'sender_name':full_name(report_obj.creator), 
            'object':report_obj,
            'object_name': title, 
            'report_admin_url': report_url,
            'report_text': report_obj.text,
            'object_url':report_obj.get_absolute_url(),
        })
        
        subject = render_to_string(subj_template, context)
        send_mail_or_fail(receiver.email, subject, template, context)
        

@csrf_protect
def report_object(request):
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated():
        return HttpResponseForbidden('Not authenticated.')
    
    cls = request.POST.get('cls', None)  # expects 'cosinnus_note.Note'
    obj_id = request.POST.get('id', None)
    text = request.POST.get('text', None)
    
    if not cls and obj_id and text:
        raise ValueError('Incomplete data submitted.')
    
    app_label, model = cls.split('.')
    
    if model.lower() == 'user':
        model_cls = get_user_model()
    else:
        model_cls = get_model(app_label, model)
    
    content_type = ContentType.objects.get_for_model(model_cls)
    report_obj = CosinnusReportedObject.objects.create(content_type=content_type, object_id=obj_id, text=text, creator=request.user)
    
    # TODO: notification to portal admins
    _notify_users_for_reported_objects(report_obj, request)
    
    """
    data = {
        'status': 'error',
    }
    """
    
    data = {
        'status': 'success',
    }
    return JSONResponse(data, safe=False)