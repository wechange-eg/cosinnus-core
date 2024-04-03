# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, UpdateView, CreateView
from django.views.generic.list import ListView
from django.utils.timezone import now

from extra_views import (CreateWithInlinesView, FormSetView, InlineFormSetFactory,
    UpdateWithInlinesView)

from django_ical.views import ICalFeed

from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    GroupFormKwargsMixin, FilterGroupMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.attached_object import AttachableViewMixin

from cosinnus_poll.conf import settings
from cosinnus_poll.forms import PollForm, OptionForm, VoteForm,\
    PollNoFieldForm, CommentForm
from cosinnus_poll.models import Poll, Option, Vote, current_poll_filter,\
    past_poll_filter, Comment
from django.shortcuts import get_object_or_404
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_poll.filters import PollFilter
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access, check_ug_membership
from cosinnus.core.decorators.views import require_read_access,\
    require_user_token_access
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from annoying.functions import get_object_or_None
from cosinnus.templatetags.cosinnus_tags import has_write_access
from annoying.exceptions import Redirect
from django import forms
from cosinnus.views.common import DeleteElementView, apply_likefollowstar_object
from cosinnus.views.mixins.tagged import EditViewWatchChangesMixin,\
    RecordLastVisitedMixin
from cosinnus_poll import cosinnus_notifications
from django.contrib.auth import get_user_model
from ajax_forms.ajax_forms import AjaxFormsCommentCreateViewMixin,\
    AjaxFormsDeleteViewMixin


class PollIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:poll:list', kwargs={'group': self.group})

index_view = PollIndexView.as_view()


class PollListView(RequireReadMixin, FilterGroupMixin, CosinnusFilterMixin, ListView):

    model = Poll
    filterset_class = PollFilter
    poll_view = 'current'   # 'current' or 'past'
    template_name = 'cosinnus_poll/poll_list.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.poll_view = kwargs.get('poll_view', 'current')
        return super(PollListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """ In the calendar we only show scheduled polls """
        qs = super(PollListView, self).get_queryset()
        self.unfiltered_qs = qs
        if self.poll_view == 'current':
            qs = current_poll_filter(qs)
        elif self.poll_view == 'past':
            qs = past_poll_filter(qs)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PollListView, self).get_context_data(**kwargs)
        running_polls_count = self.queryset.count() if self.poll_view == 'current' else current_poll_filter(self.unfiltered_qs).count()
        past_polls_count = self.queryset.count() if self.poll_view == 'past' else past_poll_filter(self.unfiltered_qs).count()
        
        context.update({
            'running_polls_count': running_polls_count,
            'past_polls_count': past_polls_count,
            'poll_view': self.poll_view,
            'polls': context['object_list'],
        })
        return context

poll_list_view = PollListView.as_view()


class OptionInlineFormset(InlineFormSetFactory):
    factory_kwargs = {
        'extra': 25,
        'max_num': 25,
    }
    form_class = OptionForm
    model = Option
    
    
class PollFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    form_class = PollForm
    model = Poll
    inlines = [OptionInlineFormset]
    message_success = _('Poll "%(title)s" was edited successfully.')
    message_error = _('Poll "%(title)s" could not be edited.')
    pre_voting_editing_enabled = True
    
    def dispatch(self, request, *args, **kwargs):
        self.form_view = kwargs.get('form_view', None)
        return super(PollFormMixin, self).dispatch(request, *args, **kwargs)
    
    def _deactivate_non_editable_fields_after_votes_or_completion(self):
        """ Shuts of all fields or formsets that shouldn't be editable
            after votes have been placed or the poll has been closed. """
        self.inlines = []
        self.pre_voting_editing_enabled = False
    
    def get_object(self, *args, **kwargs):
        poll = super(PollFormMixin, self).get_object(*args, **kwargs)
        if poll.state != Poll.STATE_VOTING_OPEN or poll.options.filter(votes__isnull=False).count() > 0:
            self._deactivate_non_editable_fields_after_votes_or_completion()
        return poll
    
    def get_context_data(self, **kwargs):
        context = super(PollFormMixin, self).get_context_data(**kwargs)
        tags = Poll.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
            'pre_voting_editing_enabled': self.pre_voting_editing_enabled,
        })
        return context

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:poll:detail'
        else:
            urlname = 'cosinnus:poll:list'
        return group_aware_reverse(urlname, kwargs=kwargs)

    def forms_valid(self, form, inlines):
        ret = super(PollFormMixin, self).forms_valid(form, inlines)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret

    def forms_invalid(self, form, inlines):
        ret = super(PollFormMixin, self).forms_invalid(form, inlines)
        if self.object:
            messages.error(self.request,
                self.message_error % {'title': self.object.title})
        return ret



class PollAddView(PollFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Poll "%(title)s" was added successfully.')
    message_error = _('Poll "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        form.instance.state = Poll.STATE_VOTING_OPEN  # be explicit
        ret = super(PollAddView, self).forms_valid(form, inlines)
        # creator follows their own poll
        apply_likefollowstar_object(form.instance, self.request.user, follow=True)
    
        # Check for non or a single option and set it and inform the user
        num_options = self.object.options.count()
        if num_options == 0:
            messages.info(self.request, _('You should define at least one poll option!'))
        return ret

poll_add_view = PollAddView.as_view()

class NoLongerEditableException(Exception):
    pass

class PollEditView(EditViewWatchChangesMixin, PollFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    
    changed_attr_watchlist = ['title', 'description', 'get_attached_objects_hash', 'get_options_hash']
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(PollEditView, self).dispatch(request, *args, **kwargs)
        except NoLongerEditableException:
            messages.error(self.request, _('This poll is archived and cannot be edited anymore!'))
            return HttpResponseRedirect(self.object.get_absolute_url())
    
    def get_object(self, queryset=None):
        obj = super(PollEditView, self).get_object(queryset=queryset)
        self.object = obj
        if obj.state == Poll.STATE_ARCHIVED:
            raise NoLongerEditableException()
        return obj
    
    def get_context_data(self, *args, **kwargs):
        context = super(PollEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'has_active_votes': self.object.options.filter(votes__isnull=False).count() > 0,
        })
        return context
    
    def forms_valid(self, form, inlines):
        
        # Save the options first so we can directly
        # access the amount of options afterwards
        #for formset in inlines:
        #    formset.save()


        return super(PollEditView, self).forms_valid(form, inlines)

    def on_save_changed_attrs(self, obj, changed_attr_dict):
        # send out a notification to all followers for the change
        followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
        cosinnus_notifications.following_poll_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator))
        
poll_edit_view = PollEditView.as_view()


class PollDeleteView(RequireWriteMixin, FilterGroupMixin, DeleteView):
    model = Poll
    message_success = _('Poll "%(title)s" was deleted successfully.')
    message_error = _('Poll "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:poll:list', kwargs={'group': self.group})

poll_delete_view = PollDeleteView.as_view()


class PollVoteView(RequireReadMixin, RecordLastVisitedMixin, FilterGroupMixin, SingleObjectMixin,
        FormSetView):

    message_success = _('Your votes were saved successfully.')
    message_error = _('Your votes could not be saved.')

    factory_kwargs = {'extra': 0}
    form_class = VoteForm
    model = Poll
    template_name = 'cosinnus_poll/poll_vote.html'
    mode = 'vote' # 'vote' or 'view'
    MODES = ('vote', 'view',)
    
    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        poll = self.object
        self.mode = 'view'
        if poll.state == Poll.STATE_VOTING_OPEN and request.user.is_authenticated:
            if check_object_read_access(poll, request.user) and (poll.anyone_can_vote or check_ug_membership(request.user, self.group)):
                if not request.user.is_guest or settings.COSINNUS_USER_GUEST_ACCOUNTS_ENABLE_SOFT_EDITS:
                    self.mode = 'vote'
        try:
            return super(PollVoteView, self).dispatch(request, *args, **kwargs)
        except Redirect:
            return HttpResponseRedirect(self.object.get_absolute_url())
        
    def post(self, request, *args, **kwargs):
        if self.mode != 'vote':
            messages.error(request, _('The voting phase for this poll is over. You cannot vote for it any more.'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(PollVoteView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PollVoteView, self).get_context_data(**kwargs)
        
        self.option_formsets_dict = {} # { option-pk --> form }
        if self.mode == 'vote':
            # create a formset dict matching forms to option-pks so we can pull them together in the template easily
            for form in context['formset'].forms:
                self.option_formsets_dict[form.initial['option']] = form
        
        context.update({
            'object': self.object,
            'options': self.options,
            'option_formsets_dict': self.option_formsets_dict,
            'user_votes_dict': self.user_votes_dict,
            'options_votes_dict': self.options_votes_dict,
            'mode': self.mode,
        })
        return context

    def get_initial(self):
        """ get initial and create user-vote-dict """
        self.object = self.get_object()
        self.options = self.object.options.all().order_by('pk')
        
        self.max_num = self.options.count()
        self.initial = []
        self.user_votes_dict = {} # {<option-pk --> vote-choice }
        self.options_votes_dict = {} # {<option-pk --> [num_votes_no, num_votes_maybe, num_votes_yes] }
        
        for option in self.options:
            vote = None
            if self.request.user.is_authenticated:
                try:
                    vote = option.votes.filter(voter=self.request.user).get()
                except Vote.DoesNotExist:
                    pass
            self.initial.append({
                'option': option.pk,
                'choice': vote.choice if vote else 0,
            })
            self.user_votes_dict[option.pk] = vote.choice if vote else -1
            
            # count existing votes
            option_counts = [0, 0, 0] # [num_votes_no, num_votes_maybe, num_votes_yes]
            for vote in option.votes.all():
                option_counts[vote.choice] += 1
            self.options_votes_dict[option.pk] = option_counts
            
        return self.initial

    def get_success_url(self):
        return self.object.get_absolute_url()

    def formset_valid(self, formset):
        option_choices = {} # { option_id --> choice }
        
        for form in formset:
            cd = form.cleaned_data
            option = int(cd.get('option'))
            choice = int(cd.get('choice', 0))
            if option:
                option_choices[option] = choice
        
        if not self.object.multiple_votes and not len([True for choice in list(option_choices.values()) if choice == Vote.VOTE_YES]) == 1:
            messages.error(self.request, _('In this poll you must vote for exactly one item!'))
            raise Redirect()
        
        for option, choice in list(option_choices.items()):
            if not self.object.can_vote_maybe and choice == Vote.VOTE_MAYBE:
                choice = Vote.VOTE_NO
            vote, _created = Vote.objects.get_or_create(option_id=option, voter=self.request.user)
            vote.choice = choice
            vote.save()
            
        
        ret = super(PollVoteView, self).formset_valid(formset)
        self.object.update_last_action(now(), self.request.user, save=True)
        
        messages.success(self.request, self.message_success )
        return ret
    
    def formset_invalid(self, formset):
        ret = super(PollVoteView, self).formset_invalid(formset)
        if self.object:
            messages.error(self.request, self.message_error)
        return ret


poll_vote_view = PollVoteView.as_view()


class PollCompleteView(RequireWriteMixin, FilterGroupMixin, UpdateView):
    """ Completes a poll for a selected option, setting the poll to completed/archived.
        Notification triggers are handled in the model. """
    form_class = PollNoFieldForm
    model = Poll
    option_id = None
    mode = 'complete' # 'complete' or 'reopen' or 'archive'
    MODES = ('complete', 'reopen', 'archive')
    
    def dispatch(self, request, *args, **kwargs):
        self.option_id = kwargs.pop('option_id', None)
        self.mode = kwargs.pop('mode')
        return super(PollCompleteView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        obj = super(PollCompleteView, self).get_object(queryset)
        return obj
    
    def get(self, request, *args, **kwargs):
        # we don't accept GETs on this, just POSTs
        messages.error(request, _('The complete request can only be sent via POST!'))
        return HttpResponseRedirect(self.get_object().get_absolute_url())
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        poll = self.object
        
        # check if valid action requested depending on poll state
        if self.mode not in self.MODES:
            messages.error(request, _('Invalid action for this poll. The request could not be completed!'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        if (poll.state, self.mode) not in \
                ((Poll.STATE_VOTING_OPEN, 'complete'), (Poll.STATE_CLOSED, 'reopen'), (Poll.STATE_CLOSED, 'archive')):
            messages.error(request, _('This action is not permitted for this poll at this stage!'))
            return HttpResponseRedirect(poll.get_absolute_url())

        # change poll state        
        if (poll.state, self.mode) == (Poll.STATE_VOTING_OPEN, 'complete'):
            # complete the poll. a winning option may be selected, but doesn't have to be
            option = get_object_or_None(Option, pk=self.option_id)
            if option:
                poll.winning_option = option
            poll.closed_date = now()
            poll.state = Poll.STATE_CLOSED
            poll.save()
            messages.success(request, _('The poll was closed successfully.'))
        if (poll.state, self.mode) == (Poll.STATE_CLOSED, 'reopen'):
            # reopen poll, set winning option and closed_date to none
            poll.winning_option = None
            poll.closed_date = None
            poll.state = Poll.STATE_VOTING_OPEN
            poll.save()
            messages.success(request, _('The poll was re-opened successfully.'))
        if (poll.state, self.mode) == (Poll.STATE_CLOSED, 'archive'):
            poll.state = Poll.STATE_ARCHIVED
            poll.save()
            messages.success(request, _('The poll was archived successfully.'))
        
        return HttpResponseRedirect(self.object.get_absolute_url())
    
poll_complete_view = PollCompleteView.as_view()



class CommentCreateView(RequireWriteMixin, FilterGroupMixin, AjaxFormsCommentCreateViewMixin,
        CreateView):

    form_class = CommentForm
    group_field = 'poll__group'
    model = Comment
    template_name = 'cosinnus_poll/poll_vote.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.poll = self.poll
        messages.success(self.request, self.message_success)
        ret = super(CommentCreateView, self).form_valid(form)
        self.poll.update_last_action(now(), self.request.user, save=True)
        return ret

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the poll as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'poll': self.poll,
            'object': self.poll, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.poll = get_object_or_404(Poll, group=self.group, slug=self.kwargs.get('poll_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.poll = get_object_or_404(Poll, group=self.group, slug=self.kwargs.get('poll_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.poll.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    group_field = 'poll__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'poll': self.object.poll})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.poll.group.get_absolute_url())
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
    group_field = 'poll__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'poll': self.object.poll})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.poll.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()


class PollDeleteElementView(DeleteElementView):
    model = Poll

delete_element_view = PollDeleteElementView.as_view()
