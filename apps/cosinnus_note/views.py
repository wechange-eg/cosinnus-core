# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from cosinnus.views.attached_object import (CreateViewAttachable,
    UpdateViewAttachable)

from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    FilterGroupMixin, GroupFormKwargsMixin, DipatchGroupURLMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus_note.forms import CommentForm, NoteForm
from cosinnus_note.models import Note, Comment
from django.contrib import messages
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_note.filters import NoteFilter
from cosinnus_note import cosinnus_notifications
from cosinnus.utils.urls import group_aware_reverse, safe_redirect
from cosinnus.utils.pagination import PaginationTemplateMixin
from cosinnus.views.facebook_integration import FacebookIntegrationViewMixin
from django.utils.encoding import force_text
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin,\
    ReflectedObjectRedirectNoticeMixin, ReflectedObjectSelectMixin
from cosinnus.views.common import apply_likefollowstar_object
from cosinnus.views.mixins.tagged import EditViewWatchChangesMixin
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from ajax_forms.ajax_forms import AjaxFormsCommentCreateViewMixin,\
    AjaxFormsDeleteViewMixin, AjaxFormsCreateViewMixin
from cosinnus.core.decorators.views import redirect_to_403,\
    MSG_USER_NOT_VERIFIED
from cosinnus.utils.permissions import check_user_verified


class NoteCreateView(FacebookIntegrationViewMixin, RequireWriteMixin, FilterGroupMixin, 
                     GroupFormKwargsMixin, UserFormKwargsMixin, AjaxFormsCreateViewMixin,
                     CreateViewAttachable):

    form_class = NoteForm
    model = Note
    template_name = 'cosinnus_note/note_form.html'
    form_view = 'add'
    
    message_success = _('Your news post was added successfully.')
    
    ajax_form_partial = 'cosinnus_note/v2/note_form_core.html'
    ajax_result_partial = 'cosinnus_note/v2/dashboard/timeline_item_ajax_partial.html'
    
    def get_context_data(self, **kwargs):
        context = super(NoteCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        # special check: if user isn't verified, don't allow posts to the forum group
        if not check_user_verified(self.request.user) and CosinnusPortal.get_current().email_needs_verification and \
                (self.group.is_default_user_group or self.group.is_forum_group):
            messages.warning(self.request, MSG_USER_NOT_VERIFIED)
            form.add_error(None, MSG_USER_NOT_VERIFIED)
            return self.form_invalid(form)
        
        form.instance.creator = self.request.user
        ret = super(NoteCreateView, self).form_valid(form)
        # creator follows their own note
        apply_likefollowstar_object(form.instance, self.request.user, follow=True)
        return ret
        
    def form_invalid(self, form):
        """
        If the form is invalid, we simply redirect to the success url, except if we come from the create view.
        """
        return super(NoteCreateView, self).form_invalid(form)

    def post(self, request, *args, **kwargs):
        self.referer = self.request.GET.get('next', request.META.get('HTTP_REFERER', group_aware_reverse('cosinnus:note:list', kwargs={'group':self.group})))
        return super(NoteCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return safe_redirect(self.referer, self.request)

note_create = NoteCreateView.as_view()


class NoteDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    model = Note
    template_name_suffix = '_delete'
    
    message_success = _('Your news post was deleted successfully.')
    
    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:note:list', kwargs={'group':self.group})

note_delete = NoteDeleteView.as_view()


class NoteDetailView(ReflectedObjectRedirectNoticeMixin, ReflectedObjectSelectMixin, 
         RequireReadMixin, FilterGroupMixin, DetailView):

    model = Note
    template_name = 'cosinnus_note/note_detail.html'

note_detail = NoteDetailView.as_view()


class NoteIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:note:list', kwargs={'group': self.group})

note_index = NoteIndexView.as_view()


class NoteListView(RequireReadMixin, CosinnusFilterMixin, MixReflectedObjectsMixin, ReflectedObjectSelectMixin, FilterGroupMixin, 
                   PaginationTemplateMixin, ListView):
    model = Note
    filterset_class = NoteFilter
    per_page = 10
    
    def get_queryset(self, **kwargs):
        qs = super(NoteListView, self).get_queryset()
        qs = qs.prefetch_related('comments__creator__cosinnus_profile', 'attached_objects')
        return qs
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'form':  NoteForm(group=self.group)
        })
        return super(NoteListView, self).get_context_data(**kwargs)

note_list = NoteListView.as_view()


class NoteEmbedView(DipatchGroupURLMixin, MixReflectedObjectsMixin, FilterGroupMixin, PaginationTemplateMixin, ListView):
    model = Note
    per_page = 10
    template_name = 'cosinnus_note/note_embed.html'
    
    def get_queryset(self, **kwargs):
        """ Only ever show public notes """
        qs = super(NoteEmbedView, self).get_queryset()
        qs = qs.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL).prefetch_related('comments__creator__cosinnus_profile', 'attached_objects')
        return qs
    
note_embed = NoteEmbedView.as_view()


class NoteEmbedGlobalView(PaginationTemplateMixin, ListView):
    """ Displays all notes in all Portals in an embeddable view, not just from a specific group """
    
    model = Note
    per_page = 10
    template_name = 'cosinnus_note/note_embed.html'
    
    def get_queryset(self, **kwargs):
        """ Only ever show public notes """
        qs = Note.objects.all()
        qs = qs.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL).prefetch_related('comments__creator__cosinnus_profile', 'attached_objects')
        return qs
    
note_embed_global = NoteEmbedGlobalView.as_view()


class NoteEmbedCurrentPortalView(NoteEmbedGlobalView):
    """ Displays all notes in this Portal in an embeddable view, not just from a specific group """
    
    def get_queryset(self, **kwargs):
        """ Only ever show public notes """
        qs = super(NoteEmbedCurrentPortalView, self).get_queryset()
        qs = qs.filter(group__portal=CosinnusPortal.get_current())
        return qs
    
note_embed_current_portal = NoteEmbedCurrentPortalView.as_view()


class NoteUpdateView(EditViewWatchChangesMixin, RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin, UpdateViewAttachable):

    form_class = NoteForm
    model = Note
    template_name = 'cosinnus_note/note_form.html'
    form_view = 'edit'
    
    changed_attr_watchlist = ['title', 'text', 'get_attached_objects_hash', 'get_tagged_persons_hash']
    
    message_success = _('Your news post was edited successfully.')
    
    def get(self, request, *args, **kwargs):
        if not self.get_object().creator == request.user:
            return redirect_to_403(request, self, group=self.group)
        return super(NoteUpdateView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if not self.get_object().creator == request.user:
            return redirect_to_403(request, self, group=self.group)
        return super(NoteUpdateView, self).post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(NoteUpdateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def form_valid(self, form):
        messages.success(self.request, self.message_success)
        return super(NoteUpdateView, self).form_valid(form)
    
    def on_save_changed_attrs(self, obj, changed_attr_dict):
        # send out a notification to all followers for the change
        followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
        cosinnus_notifications.following_note_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator))
        
    def get_success_url(self):
        return group_aware_reverse('cosinnus:note:list', kwargs={'group': self.group})

note_update = NoteUpdateView.as_view()


class CommentCreateView(RequireWriteMixin, FilterGroupMixin, AjaxFormsCommentCreateViewMixin,
        CreateView):

    form_class = CommentForm
    group_field = 'note__group'
    model = Comment
    template_name = 'cosinnus_note/note_detail.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.note = self.note
        messages.success(self.request, self.message_success)
        ret = super(CommentCreateView, self).form_valid(form)
        self.note.update_last_action(now(), self.request.user, save=True)
        return ret

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the note as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'note': self.note,
            'object': self.note, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.note = get_object_or_404(Note, group=self.group, slug=self.kwargs.get('note_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.note = get_object_or_404(Note, group=self.group, slug=self.kwargs.get('note_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.note.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    group_field = 'note__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'note': self.object.note})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.note.group.get_absolute_url())
        return super(CommentDeleteView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success)
        return self.referer

comment_delete = CommentDeleteView.as_view()


class CommentDetailView(SingleObjectMixin, RedirectView):

    permanent = False
    model = Comment

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        return HttpResponseRedirect(obj.get_absolute_url())

comment_detail = CommentDetailView.as_view()


class CommentUpdateView(RequireWriteMixin, FilterGroupMixin, UpdateView):

    form_class = CommentForm
    group_field = 'note__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'note': self.object.note})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.note.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()


