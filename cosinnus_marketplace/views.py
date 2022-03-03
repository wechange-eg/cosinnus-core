# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, UpdateView, CreateView
from django.views.generic.list import ListView
from django.utils.timezone import now

from extra_views import (CreateWithInlinesView, UpdateWithInlinesView)

from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    GroupFormKwargsMixin, FilterGroupMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.attached_object import AttachableViewMixin

from cosinnus_marketplace.forms import CommentForm, OfferForm, OfferNoFieldForm
from cosinnus_marketplace.models import Offer, Comment
from django.shortcuts import get_object_or_404, redirect
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_marketplace.filters import OfferFilter
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.permissions import check_object_write_access
from cosinnus.core.decorators.views import require_read_access, redirect_to_not_logged_in, get_group_for_request
from cosinnus.utils.exceptions import CosinnusPermissionDeniedException
from cosinnus.views.common import DeleteElementView
from cosinnus.views.mixins.tagged import EditViewWatchChangesMixin,\
    RecordLastVisitedMixin
from cosinnus_marketplace import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.functions import ensure_list_of_ints
from ajax_forms.ajax_forms import AjaxFormsCommentCreateViewMixin,\
    AjaxFormsDeleteViewMixin


class MarketplaceIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:marketplace:list', kwargs={'group': self.group})

index_view = MarketplaceIndexView.as_view()


class MyActiveOfferCountMixin(object):
    
    def get_context_data(self, **kwargs):
        context = super(MyActiveOfferCountMixin, self).get_context_data(**kwargs)
        my_offer_count = 0
        if hasattr(self, 'group') and self.request and self.request.user.is_authenticated:
            qs = Offer.objects.all()
            my_offer_count = qs.filter(group=self.group, is_active=True, creator=self.request.user).count()
        context.update({
            'my_offer_count': my_offer_count,
        })
        return context


class OfferListView(RequireReadMixin, FilterGroupMixin, CosinnusFilterMixin, MyActiveOfferCountMixin, ListView):

    model = Offer
    filterset_class = OfferFilter
    offer_view = 'all'   # 'all' or 'mine'
    template_name = 'cosinnus_marketplace/offer_list.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.offer_view = kwargs.get('offer_view', 'all')
        if self.offer_view == 'mine' and not self.request.user.is_authenticated:
            return redirect_to_not_logged_in(view=self)
        return super(OfferListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        qs = super(OfferListView, self).get_queryset()
        
        # additional category AND filter:
        categories = ensure_list_of_ints(self.request.GET.getlist('categories'))
        
        if categories:
            qs = qs.filter(categories__in=categories)
        
        self.unfiltered_qs = qs
        if self.offer_view == 'all':
            qs = qs.filter(is_active=True)
        elif self.offer_view == 'mine':
            qs = qs.filter(creator=self.request.user)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(OfferListView, self).get_context_data(**kwargs)
        offers = context['object_list']
        # filter here so we don't filter on the DB
        offers_buying = [offer for offer in offers if offer.type == Offer.TYPE_BUYING]
        offers_selling = [offer for offer in offers if offer.type == Offer.TYPE_SELLING]
        context.update({
            'offer_view': self.offer_view,
            'offers': offers,
            'offers_buying': offers_buying,
            'offers_selling': offers_selling,
        })
        return context

offer_list_view = OfferListView.as_view()


    
class OfferFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    
    form_class = OfferForm
    model = Offer
    message_success = _('Offer "%(title)s" was edited successfully.')
    message_error = _('Offer "%(title)s" could not be edited.')
    
    def dispatch(self, request, *args, **kwargs):
        self.form_view = kwargs.get('form_view', None)
        return super(OfferFormMixin, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(OfferFormMixin, self).get_context_data(**kwargs)
        tags = Offer.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        messages.success(self.request, self.message_success % {'title': self.object.title})
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:marketplace:detail'
        else:
            urlname = 'cosinnus:marketplace:list'
        return group_aware_reverse(urlname, kwargs=kwargs)


class OfferAddView(OfferFormMixin, AttachableViewMixin, MyActiveOfferCountMixin, CreateWithInlinesView):
    
    message_success = _('Offer "%(title)s" was added successfully.')
    message_success_added = _('Offer "%(title)s" was saved successfully, but is not active yet.')
    message_error = _('Offer "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        ret = super(OfferAddView, self).forms_valid(form, inlines)
        return ret
    
    def get_success_url(self):
        ret = super(OfferAddView, self).get_success_url()
        if not self.object.is_active:
            # clear messages to display different success
            list(messages.get_messages(self.request))
            messages.success(self.request, self.message_success_added % {'title': self.object.title})
        return ret

offer_add_view = OfferAddView.as_view()


class OfferEditView(EditViewWatchChangesMixin, OfferFormMixin, AttachableViewMixin, 
                    MyActiveOfferCountMixin, UpdateWithInlinesView):
    
    changed_attr_watchlist = ['title', 'description', 'phone_number', 'get_attached_objects_hash']
    
    def get_object(self, queryset=None):
        obj = super(OfferEditView, self).get_object(queryset=queryset)
        self.object = obj
        return obj
    
    def on_save_changed_attrs(self, obj, changed_attr_dict):
        # send out a notification to all followers for the change
        followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
        cosinnus_notifications.following_offer_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator))
        
offer_edit_view = OfferEditView.as_view()


class OfferDeleteView(OfferFormMixin, AjaxFormsDeleteViewMixin, DeleteView):
    message_success = _('Offer "%(title)s" was deleted successfully.')
    message_error = _('Offer "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:marketplace:list', kwargs={'group': self.group})

offer_delete_view = OfferDeleteView.as_view()


class OfferDetailView(RequireReadMixin, RecordLastVisitedMixin,
        FilterGroupMixin, MyActiveOfferCountMixin, DetailView):

    model = Offer
    
    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        """ Only allow owners to see inactive offers """
        try:
            self.group = get_group_for_request(kwargs.get('group'), request)
            offer = self.get_object()
            if not offer.is_active and not check_object_write_access(offer, request.user):
                messages.error(request, _('The offer you requested is no longer active. Sorry!'))
                return redirect(group_aware_reverse('cosinnus:marketplace:list', kwargs={'group': self.group}))
            return super(OfferDetailView, self).dispatch(request, *args, **kwargs)
        except CosinnusPermissionDeniedException:
            return redirect_to_not_logged_in(request, view=self)

    def get_context_data(self, **kwargs):
        context = super(OfferDetailView, self).get_context_data(**kwargs)
        context.update({
            'offer': context['object'],
        })
        return context

offer_detail_view = OfferDetailView.as_view()


class OfferActivateOrDeactivateView(RequireWriteMixin, FilterGroupMixin, UpdateView):
    """ Completes a marketplace for a selected option, setting the marketplace to completed/archived.
        Notification triggers are handled in the model. """
    form_class = OfferNoFieldForm
    model = Offer
    mode = 'activate' # 'activate' or 'deactivate'
    MODES = ['activate', 'deactivate']
    
    def dispatch(self, request, *args, **kwargs):
        self.mode = kwargs.pop('mode')
        return super(OfferActivateOrDeactivateView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        obj = super(OfferActivateOrDeactivateView, self).get_object(queryset)
        return obj
    
    def get(self, request, *args, **kwargs):
        # we don't accept GETs on this, just POSTs
        messages.error(request, _('The complete request can only be sent via POST!'))
        return HttpResponseRedirect(self.get_object().get_absolute_url())
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        offer = self.object
        
        # check if valid action requested depending on marketplace state
        if self.mode not in self.MODES:
            messages.error(request, _('Invalid action for this offer. The request could not be completed!'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        if offer.is_active and self.mode == 'activate':
            messages.success(_('The offer is already active'))
            return HttpResponseRedirect(offer.get_absolute_url())
        if not offer.is_active and self.mode == 'deactivate':
            messages.success(_('The offer is already deactivated'))
            return HttpResponseRedirect(offer.get_absolute_url())

        if self.mode == 'deactivate':
            offer.is_active = False
            offer.save(update_fields=['is_active'])
            messages.success(request, _('The offer was deactivated successfully.'))
        elif self.mode == 'activate':
            reactivate = offer.has_expired
            offer.is_active = True
            offer.created = now()
            offer.save(update_fields=['is_active', 'created'])
            if reactivate:
                messages.success(request, _('The offer was reactivated successfully.'))
            else:
                messages.success(request, _('The offer was activated successfully.'))
        
        return HttpResponseRedirect(offer.get_absolute_url())
    
offer_activate_or_deactivate_view = OfferActivateOrDeactivateView.as_view()


class CommentCreateView(RequireWriteMixin, FilterGroupMixin, AjaxFormsCommentCreateViewMixin,
        CreateView):

    form_class = CommentForm
    group_field = 'offer__group'
    model = Comment
    template_name = 'cosinnus_marketplace/offer_detail.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.offer = self.offer
        messages.success(self.request, self.message_success)
        ret = super(CommentCreateView, self).form_valid(form)
        self.offer.update_last_action(now(), self.request.user, save=True)
        return ret

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the offer as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'offer': self.offer,
            'object': self.offer, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.offer = get_object_or_404(Offer, group=self.group, slug=self.kwargs.get('offer_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.offer = get_object_or_404(Offer, group=self.group, slug=self.kwargs.get('offer_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.offer.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    group_field = 'offer__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'offer': self.object.offer})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.offer.group.get_absolute_url())
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
    group_field = 'offer__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'offer': self.object.offer})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.offer.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()


class OfferDeleteElementView(DeleteElementView):
    model = Offer

delete_element_view = OfferDeleteElementView.as_view()
