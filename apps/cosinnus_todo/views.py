# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import json

from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView, View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import (CreateView, DeleteView, UpdateView)
from django.views.generic.list import ListView

from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
     FilterGroupMixin, GroupFormKwargsMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin
from cosinnus.conf import settings

from cosinnus_todo.forms import (TodoEntryAddForm, TodoEntryAssignForm,
    TodoEntryCompleteForm, TodoEntryNoFieldForm, TodoEntryUpdateForm,
    TodoListForm, CommentForm)
from cosinnus_todo.models import TodoEntry, TodoList, Comment


from cosinnus_todo.serializers import TodoEntrySerializer, TodoListSerializer
from cosinnus.views.mixins.ajax import ListAjaxableResponseMixin, AjaxableFormMixin, \
    DetailAjaxableResponseMixin
from django.views.decorators.csrf import csrf_protect
from cosinnus.utils.permissions import check_object_write_access
from cosinnus.utils.http import JSONResponse
from django.contrib.auth import get_user_model
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_todo.filters import TodoFilter
from django.http.request import QueryDict
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_todo import cosinnus_notifications
from cosinnus.views.attached_object import AttachableViewMixin
from django.http.response import HttpResponse
from django.utils.safestring import mark_safe
from cosinnus.views.hierarchy import MoveElementView
from cosinnus.models.group import CosinnusPortal
from cosinnus.views.mixins.tagged import RecordLastVisitedMixin,\
    EditViewWatchChangesMixin
from ajax_forms.ajax_forms import AjaxFormsCommentCreateViewMixin,\
    AjaxFormsDeleteViewMixin
from annoying.functions import get_object_or_None
from uuid import uuid1
from cosinnus.views.common import apply_likefollowstar_object
from cosinnus.utils.user import filter_active_users


class TodoIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:todo:list', kwargs={'group': self.group})

index_view = TodoIndexView.as_view()


class InteractiveTodoEntryMixin(object):
    
    def get_context_data(self, **kwargs):
        context = super(InteractiveTodoEntryMixin, self).get_context_data(**kwargs)
        context.update({
            'group_users': filter_active_users(get_user_model().objects.filter(id__in=self.group.members).prefetch_related('cosinnus_profile'))
        })
        return context


class TodoEntryListView(ListAjaxableResponseMixin, RequireReadMixin,
                        FilterGroupMixin, CosinnusFilterMixin, InteractiveTodoEntryMixin,
                        ListView):

    model = TodoEntry
    serializer_class = TodoEntrySerializer
    filterset_class = TodoFilter
        
    def dispatch(self, request, *args, **kwargs):
        list_filter = None
        if self.is_ajax_request_url and request.is_ajax():
            list_pk = request.GET.get('list', None)
            if list_pk:
                list_filter = {'pk': list_pk}
        else:
            list_slug = kwargs.get('listslug', None)
            if list_slug:
                list_filter = {'slug': list_slug}
        
        if list_filter:
            self.todolist = get_object_or_404(TodoList, **list_filter)
        else:
            self.todolist = None
            
        todo_slug = kwargs.get('todoslug', None)
        if todo_slug:
            self.todo = get_object_or_404(TodoEntry, slug=todo_slug)
        else:
            self.todo = None
            
        return super(TodoEntryListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TodoEntryListView, self).get_context_data(**kwargs)
        
        context.update({
            'todolists': TodoList.objects.filter(group_id=self.group.id).all(),
            'active_todolist': self.todolist,
            'active_todo': self.todo,
        })
        return context

    def get_queryset(self):
        # TODO Django>=1.7: change to chained select_related calls
        qs = super(TodoEntryListView, self).get_queryset(
            select_related=('assigned_to', 'completed_by', 'todolist'))
        if self.todolist:
            qs = qs.filter(todolist_id=self.todolist.pk)
        # Hide completed todos in normal view.
        if not self.kwargs.get('archived'):
            qs = qs.exclude(is_completed__exact=True)
        return qs

entry_list_view = TodoEntryListView.as_view()
entry_list_view_api = TodoEntryListView.as_view(is_ajax_request_url=True)


class TodoListCreateView(ListAjaxableResponseMixin, RequireReadMixin,
                        FilterGroupMixin, CosinnusFilterMixin, InteractiveTodoEntryMixin,
                        ListView):

    model = TodoEntry
    serializer_class = TodoEntrySerializer
    template_name = 'cosinnus_todo/todo_list.html'
    filterset_class = TodoFilter

    def dispatch(self, request, *args, **kwargs):
        
        list_filter = None
        list_slug = kwargs.get('listslug', None)
        if list_slug:
            list_filter = {'slug': list_slug, 'group__slug': kwargs.get('group'), 'group__portal': CosinnusPortal.get_current()}
        elif request.method == 'GET':
            # if we navigate to the index, redirect to the default todolist instead, if it exists
            default_todolist_slug = settings.COSINNUS_TODO_DEFAULT_TODOLIST_SLUG
            default_list_filter = {'slug': default_todolist_slug, 'group__slug': kwargs.get('group'), 'group__portal': CosinnusPortal.get_current()}
            default_todolist = get_object_or_None(TodoList, **default_list_filter)
            if default_todolist:
                return redirect(group_aware_reverse('cosinnus:todo:list-list', kwargs={'group': kwargs.get('group'), 'listslug': default_todolist.slug}))
            
        if list_filter:
            self.todolist = get_object_or_404(TodoList, **list_filter)
        else:
            self.todolist = None
            
        todo_slug = kwargs.get('todoslug', None)
        if todo_slug:
            self.todo = get_object_or_404(TodoEntry, slug=todo_slug, group__slug=kwargs.get('group'), group__portal=CosinnusPortal.get_current())
        else:
            self.todo = None
        
        # default filter for todos is completed=False
        if not 'is_completed' in request.GET:
            qdict = QueryDict('', mutable=True)
            qdict.update(request.GET)
            qdict.update({'is_completed':0}) # set this to '0' instead of 0 to show the "active filter" bubble
            request.GET = qdict
            
        ret = super(TodoListCreateView, self).dispatch(request, *args, **kwargs)
        return ret
    
    def get_queryset(self):
        if not hasattr(self, 'all_todolists'):
            self.all_todolists = TodoList.objects.filter(group_id=self.group.id).all()
            
        # TODO Django>=1.7: change to chained select_related calls
        qs = super(TodoListCreateView, self).get_queryset(
            select_related=('assigned_to', 'completed_by', 'todolist'))
        if not self.todolist and self.all_todolists.count() > 0:
            self.todolist = self.all_todolists[0]
        
        self.all_todos = qs
        if self.todolist:
            qs = qs.filter(todolist_id=self.todolist.pk)
            
        # Hide completed todos in normal view.
        #if not self.kwargs.get('archived'):
            #qs = qs.exclude(is_completed__exact=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super(TodoListCreateView, self).get_context_data(**kwargs)
        
        todos = context.get('object_list')#.exclude(is_completed__exact=True)
        #incomplete_todos = context.get('object_list').filter(is_completed__exact=True)
        
        #incomplete_all_todos = self.all_todos.exclude(is_completed__exact=True)
        for todolist in self.all_todolists:
            todolist.filtered_items = self.all_todos.filter(todolist=todolist)#incomplete_all_todos.filter(todolist=todolist)
        
        # collect todolists for the move modal
        all_folder_json = []
        for todolist in self.all_todolists:
            all_folder_json.append( {'id': todolist.slug, 'parent': '#', 'a_attr': {'target_folder':todolist.id}, 'text': todolist.title} )
            
        context.update({
            'todolists': self.all_todolists,
            'active_todolist': self.todolist,
            'active_todo': self.todo,
            'objects': todos,
            'todos': todos,
            
            # workarounds for move_elements applied to non-hierarchical BaseTaggableModel
            'current_folder': self.todolist,
            'all_folder_json': mark_safe(json.dumps(all_folder_json)),
        })
        return context


todo_list_create_view = TodoListCreateView.as_view()


class TodoEntryDetailView(DetailAjaxableResponseMixin, RequireReadMixin,
        RecordLastVisitedMixin, FilterGroupMixin, InteractiveTodoEntryMixin, DetailView):

    model = TodoEntry
    template_name = 'cosinnus_todo/todo_detail.html'
    serializer_class = TodoEntrySerializer

    def get_context_data(self, **kwargs):
        context = super(TodoEntryDetailView, self).get_context_data(**kwargs)
        obj = context['object']
        obj.can_assign = obj.can_user_assign(self.request.user)
        context.update({
            'active_todolist': self.object.todolist,
        })
        return context

entry_detail_view = TodoEntryDetailView.as_view()
entry_detail_view_api = TodoEntryDetailView.as_view(is_ajax_request_url=True)


class TodoEntryFormMixin(RequireWriteMixin, FilterGroupMixin,
                         GroupFormKwargsMixin, UserFormKwargsMixin, InteractiveTodoEntryMixin):
    model = TodoEntry

    def get_context_data(self, **kwargs):
        context = super(TodoEntryFormMixin, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
            'tags': TodoEntry.objects.filter(group=self.group).tag_names()
        })
        return context

    def get_success_url(self):
        return group_aware_reverse('cosinnus:todo:entry-detail',
            kwargs={'group': self.group, 'slug': self.object.slug})

    def form_valid(self, form):
        new_list = form.cleaned_data.get('new_list', None)
        todolist = form.instance.todolist
        if new_list:
            todolist = TodoList.objects.create(title=new_list, group=self.group)
            # selection or current
            todolist = form.cleaned_data.get('todolist', form.instance.todolist)
        form.instance.todolist = todolist

        if form.instance.pk is None:
            form.instance.creator = self.request.user

        if form.instance.completed_by:
            if not form.instance.completed_date:
                form.instance.completed_date = now()
        else:
            form.instance.completed_date = None

        ret = super(TodoEntryFormMixin, self).form_valid(form)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret


class TodoEntryAddView(AjaxableFormMixin, TodoEntryFormMixin, AttachableViewMixin, CreateView):
    form_class = TodoEntryAddForm
    form_view = 'add'
    message_success = _('Todo "%(title)s" was added successfully.')
    message_error = _('Todo "%(title)s" could not be added.')
    
    def _ensure_todolist(self, **kwargs):
        try:
            self.todolist = TodoList.objects.get(slug=self.kwargs.get('listslug'), group=self.group)
        except TodoList.DoesNotExist:
            messages.error(self.request, _('You were trying to add a todo to a todolist that does not exist!'))
            return redirect(group_aware_reverse('cosinnus:todo:list', kwargs={'group': kwargs.get('group')}))
        return None
    
    def get(self, request, *args, **kwargs):
        error = self._ensure_todolist(**kwargs)
        if error:
            return error
        return super(TodoEntryAddView, self).get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        error = self._ensure_todolist(**kwargs)
        if error:
            return error
        return super(TodoEntryAddView, self).post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(TodoEntryAddView, self).get_context_data(**kwargs)
        context.update({
            'active_todolist': self.todolist,
        })
        return context
    
    def form_valid(self, form):
        ret = super(TodoEntryAddView, self).form_valid(form)
        # creator follows their own todo
        apply_likefollowstar_object(form.instance, self.request.user, follow=True)
        return ret
    
    def get_success_url(self):
        return group_aware_reverse('cosinnus:todo:todo-in-list-list',
            kwargs={'group': self.group, 'listslug': self.todolist.slug, 'todoslug': self.object.slug})


entry_add_view = TodoEntryAddView.as_view()
entry_add_view_api = TodoEntryAddView.as_view(is_ajax_request_url=True)


class TodoEntryEditView(EditViewWatchChangesMixin, AjaxableFormMixin, TodoEntryFormMixin,
                        AttachableViewMixin, UpdateView):
    
    changed_attr_watchlist = ['title', 'note', 'due_date', 'get_attached_objects_hash']
    
    form_class = TodoEntryUpdateForm
    form_view = 'edit'
    message_success = _('Todo "%(title)s" was edited successfully.')
    message_error = _('Todo "%(title)s" could not be edited.')
    
    
    def get_context_data(self, **kwargs):
        context = super(TodoEntryEditView, self).get_context_data(**kwargs)
        context.update({
            'active_todolist': self.object.todolist,
        })
        return context
    
    def on_save_changed_attrs(self, obj, changed_attr_dict):
        # send out a notification to all followers for the change
        followers_except_creator = [pk for pk in obj.get_followed_user_ids() if not pk in [obj.creator_id]]
        cosinnus_notifications.following_todo_changed.send(sender=self, user=obj.creator, obj=obj, audience=get_user_model().objects.filter(id__in=followers_except_creator))
        

entry_edit_view = TodoEntryEditView.as_view()
entry_edit_view_api = TodoEntryEditView.as_view(is_ajax_request_url=True)


class TodoEntryDeleteView(AjaxableFormMixin, TodoEntryFormMixin, DeleteView):
    form_class = TodoEntryNoFieldForm
    form_view = 'delete'
    message_success = _('Todo "%(title)s" was deleted successfully.')
    message_error = _('Todo "%(title)s" could not be deleted.')

    def get_success_url(self):
        messages.success(self.request, self.message_success % {'title': self.object.title})
        return group_aware_reverse('cosinnus:todo:list-list', kwargs={'listslug': self.object.todolist.slug, 'group': self.group})

entry_delete_view = TodoEntryDeleteView.as_view()
entry_delete_view_api = TodoEntryDeleteView.as_view(is_ajax_request_url=True)


class TodoEntryAssignView(TodoEntryEditView):
    form_class = TodoEntryAssignForm
    form_view = 'assign'
    message_success = _('Todo "%(title)s" was assigned successfully.')
    message_error = _('Todo "%(title)s" could not be assigned.')

    def get_object(self, queryset=None):
        obj = super(TodoEntryAssignView, self).get_object(queryset)
        if obj.can_user_assign(self.request.user):
            return obj
        else:
            raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(TodoEntryAssignView, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            messages.error(request,
                _('You are not allowed to assign this Todo entry.'))
            kwargs = {'group': self.group}
            url = group_aware_reverse('cosinnus:todo:list', kwargs=kwargs)
            return HttpResponseRedirect(url)

entry_assign_view = TodoEntryAssignView.as_view()
entry_assign_view_api = TodoEntryAssignView.as_view(is_ajax_request_url=True)


class TodoEntryAssignMeView(TodoEntryAssignView):
    form_class = TodoEntryNoFieldForm
    form_view = 'assign-me'
    message_success = _('Todo "%(title)s" was assigned to You successfully.')
    message_error = _('Todo "%(title)s" could not be assigned to You.')

    def form_valid(self, form):
        form.instance.assigned_to = self.request.user
        return super(TodoEntryAssignMeView, self).form_valid(form)

entry_assign_me_view = TodoEntryAssignMeView.as_view()
entry_assign_me_view_api = TodoEntryAssignMeView.as_view(is_ajax_request_url=True)


class TodoEntryUnassignView(TodoEntryAssignView):
    form_class = TodoEntryNoFieldForm
    form_view = 'unassign'
    message_success = _('Todo "%(title)s" was unassigned successfully.')
    message_error = _('Todo "%(title)s" could not be unassigned.')

    def form_valid(self, form):
        form.instance.assigned_to = None
        return super(TodoEntryUnassignView, self).form_valid(form)

entry_unassign_view = TodoEntryUnassignView.as_view()
entry_unassign_view_api = TodoEntryUnassignView.as_view(is_ajax_request_url=True)


class TodoEntryCompleteView(TodoEntryEditView):
    form_class = TodoEntryCompleteForm
    form_view = 'complete'
    message_success = _('Todo "%(title)s" was completed successfully.')
    message_error = _('Todo "%(title)s" could not be completed.')

entry_complete_view = TodoEntryCompleteView.as_view()
entry_complete_view_api = TodoEntryCompleteView.as_view(is_ajax_request_url=True)


class TodoEntryCompleteMeView(TodoEntryEditView):
    form_class = TodoEntryNoFieldForm
    form_view = 'complete-me'
    message_success = _('Todo "%(title)s" was completed by You successfully.')
    message_error = _('Todo "%(title)s" could not be completed by You.')

    def form_valid(self, form):
        form.instance.completed_by = self.request.user
        form.instance.completed_date = now()
        
        session_id = uuid1().int
        # send notification of completion to creator of todo
        if form.instance.completed_by != form.instance.creator:
            cosinnus_notifications.user_completed_my_todo.send(sender=self, user=self.request.user, obj=form.instance, audience=[form.instance.creator])
        # also send notification to all followers except the user who completed this
        followers_except_self = [pk for pk in form.instance.get_followed_user_ids() if not pk in [self.request.user.id]]
        followers_except_self = get_user_model().objects.filter(id__in=followers_except_self)
        cosinnus_notifications.following_todo_completed.send(sender=self, user=self.request.user, obj=form.instance, audience=followers_except_self, session_id=session_id, end_session=True)
        
        return super(TodoEntryCompleteMeView, self).form_valid(form)

entry_complete_me_view = TodoEntryCompleteMeView.as_view()
entry_complete_me_view_api = TodoEntryCompleteMeView.as_view(is_ajax_request_url=True)


@csrf_protect
def entry_toggle_complete_me_view_api(request, pk, group):
    """
    Logs the user specified by the `authentication_form` in.
    """
    if request.method == "POST":
        # TODO: Django<=1.5: Django 1.6 removed the cookie check in favor of CSRF
        request.session.set_test_cookie()
        
        pk = request.POST.get('pk')
        is_completed = request.POST.get('is_completed')
        
        instance = get_object_or_404(TodoEntry, pk=pk)
        if not check_object_write_access(instance, request.user):
            return JSONResponse('You do not have the necessary permissions to modify this object!', status=403)
        
        if is_completed == "true":
            instance.completed_by = request.user
            instance.completed_date = now()
            if instance.completed_by != instance.creator:
                sender = instance
                sender.request = request
                cosinnus_notifications.user_completed_my_todo.send(sender=sender, user=instance.completed_by, obj=instance, audience=[instance.creator])
        
        else:
            instance.completed_by = None
            instance.completed_date = None
        instance.save()
        
        return JSONResponse({'status':'success', 'is_completed':instance.is_completed})

class TodoEntryIncompleteView(TodoEntryEditView):
    form_class = TodoEntryNoFieldForm
    form_view = 'incomplete'
    message_success = _('Todo "%(title)s" was set to incomplete successfully.')
    message_error = _('Todo "%(title)s" could not be set to incomplete.')

    def form_valid(self, form):
        form.instance.completed_by = None
        form.instance.completed_date = None
        return super(TodoEntryIncompleteView, self).form_valid(form)

entry_incomplete_view = TodoEntryIncompleteView.as_view()
entry_incomplete_view_api = TodoEntryIncompleteView.as_view(is_ajax_request_url=True)


class TodoListListView(ListAjaxableResponseMixin, RequireReadMixin,
        FilterGroupMixin, ListView):

    model = TodoList
    serializer_class = TodoListSerializer

todolist_list_view = TodoListListView.as_view()
todolist_list_view_api = TodoListListView.as_view(is_ajax_request_url=True)


class TodoListDetailView(DetailAjaxableResponseMixin, RequireReadMixin,
        FilterGroupMixin, DetailView):

    model = TodoList
    serializer_class = TodoListSerializer

    def dispatch(self, request, *args, **kwargs):
        if not self.is_ajax_request_url or not request.is_ajax():
            return HttpResponseBadRequest()
        else:
            return super(TodoListDetailView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # TODO Django>=1.7: change to chained select_relatad calls
        return super(TodoListDetailView, self).get_queryset(
            select_related=('todos'))

# `todolist_detail_view` is not used in the URLs
todolist_detail_view_api = TodoListDetailView.as_view(is_ajax_request_url=True)


class TodoListFormMixin(RequireWriteMixin, FilterGroupMixin,
                        GroupFormKwargsMixin):
    model = TodoList
    message_success = _('Todolist "%(title)s" was edited successfully.')
    message_error = _('Todolist "%(title)s" could not be edited.')

    def get_context_data(self, **kwargs):
        context = super(TodoListFormMixin, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view
        })
        return context

    def get_success_url(self):
        return group_aware_reverse('cosinnus:todo:list',
            kwargs={'group': self.group, 'listslug': self.object.slug})

    def form_valid(self, form):
        ret = super(TodoListFormMixin, self).form_valid(form)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret

    def form_invalid(self, form):
        ret = super(TodoListFormMixin, self).form_invalid(form)
        messages.error(self.request,
            self.message_error % {'title': self.object.title})
        return ret


class TodoListAddView(AjaxableFormMixin, TodoListFormMixin, CreateView):
    form_class = TodoListForm
    form_view = 'add'
    message_success = _('Todolist "%(title)s" was added successfully.')
    message_error = _('Todolist "%(title)s" could not be added.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:todo:list-list',
            kwargs={'group': self.group, 'listslug': self.object.slug})

todolist_add_view = TodoListAddView.as_view()
todolist_add_view_api = TodoListAddView.as_view(is_ajax_request_url=True)


class TodoListEditView(AjaxableFormMixin, TodoListFormMixin, UpdateView):
    form_class = TodoListForm
    form_view = 'edit'

todolist_edit_view = TodoListEditView.as_view()
todolist_edit_view_api = TodoListEditView.as_view(is_ajax_request_url=True)


class TodoListDeleteView(AjaxableFormMixin, RequireWriteMixin, FilterGroupMixin, DeleteView):

    model = TodoList
    
    def delete(self, request, *args, **kwargs):
        todolist = self.get_object()
        list_todos = todolist.todos.all()
        if not all([check_object_write_access(todo, request.user) for todo in list_todos]):
            messages.error(request, _('You cannot delete this folder because you do not have permission to delete one or more items it contains!'))
            return HttpResponseRedirect(todolist.get_absolute_url())
        return super(TodoListDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:todo:list', kwargs={'group': self.group})

todolist_delete_view = TodoListDeleteView.as_view()
todolist_delete_view_api = TodoListDeleteView.as_view(is_ajax_request_url=True)




class CommentCreateView(RequireWriteMixin, FilterGroupMixin, AjaxFormsCommentCreateViewMixin,
        CreateView):

    form_class = CommentForm
    group_field = 'todo__group'
    model = Comment
    template_name = 'cosinnus_todo/todo_detail.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.todo = self.todo
        messages.success(self.request, self.message_success)
        ret = super(CommentCreateView, self).form_valid(form)
        self.todo.update_last_action(now(), self.request.user, save=True)
        return ret

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the todo as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'todo': self.todo,
            'object': self.todo, 
            'active_todolist': self.todo.todolist,
        })
        return context

    def get(self, request, *args, **kwargs):
        self.todo = get_object_or_404(TodoEntry, group=self.group, slug=self.kwargs.get('todo_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.todo = get_object_or_404(TodoEntry, group=self.group, slug=self.kwargs.get('todo_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.todo.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, AjaxFormsDeleteViewMixin, DeleteView):

    group_field = 'todo__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'todo': self.object.todo})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.todo.group.get_absolute_url())
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
    group_field = 'todo__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'todo': self.object.todo})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.todo.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()



class TodoMoveElementView(MoveElementView):
    """ Moves a Todo to a different Todolist. """
    
    model = TodoEntry
    folder_model = TodoList
    
    def move_element(self, element, target_folder):
        element.todolist = target_folder
        element.save()
        return True
        
        
move_element_view = TodoMoveElementView.as_view()

