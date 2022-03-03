# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import inspect

from copy import copy
from django.apps import apps
from django.db.models import Q

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel,\
    BaseTagObject, BaseTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.filters import exclude_special_folders
from cosinnus.conf import settings
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin


class StreamManagerMixin(object):
    
    def _get_querysets_for_stream(self, stream, user, include_public=False):
        """ Returns all (still-lazy) querysets for models that will appear 
            in the current stream. Only works for classes inheriting BaseTaggableObjectModel. """
        querysets = []
        # [u'cosinnus_etherpad.Etherpad', u'cosinnus_event.Event', u'cosinnus_file.FileEntry', 'cosinnus_todo.TodoEntry']
        for registered_model in aor:
            Renderer = aor[registered_model]
            
            # filter out unwanted model types if set in the Stream
            if stream and stream.models and registered_model not in stream.models.split(','):
                continue
            
            app_label, model_name = registered_model.split('.')
            model_class = apps.get_model(app_label, model_name)
            
            # get base collection of models for that type
            if BaseHierarchicalTaggableObjectModel in inspect.getmro(model_class):
                queryset = model_class._default_manager.filter(is_container=False)
                queryset = exclude_special_folders(queryset)
            elif BaseTaggableObjectModel in inspect.getmro(model_class):
                queryset = model_class._default_manager.all()
            else:
                continue
            
            # filter for stream
            queryset = self._filter_queryset_for_stream(queryset, stream, user, include_public=include_public)
            
            # mix in reflected objects
            if registered_model.lower() in settings.COSINNUS_REFLECTABLE_OBJECTS and \
                        BaseTaggableObjectModel in inspect.getmro(model_class):
                mixin = MixReflectedObjectsMixin()
                queryset = mixin.mix_queryset(queryset, model_class, None, user)
            
            # filter for read permissions for user
            queryset = filter_tagged_object_queryset_for_user(queryset, user)
            # sorting
            queryset = self._sort_queryset(queryset, stream)
            querysets.append(queryset)
            
        return querysets
    
    
    def _get_stream_objectset(self, querysets):
        def get_sort_key(item):
            return item[1].stream_sort_key if hasattr(item[1], 'stream_sort_key') else item[1].sort_key

        limit = 30
        count = 0
        start = 0
        slice_len = 10
        
        """ We sample the first-sorted item from each of the querysets in each run,
            determining which of them is the overall-first-sorted.
            We slice the querysets to reduce database hits during this sampling and only
            evaluate a new slice as soon as we need to access older items from that queryset """
        
        self.total_count = 0
        
        # build iterator setlist to split-iterate over querysets
        setlist = {}
        for queryset in querysets:
            # build total count and ignore queryset if empty
            qs_count = queryset.count()
            if qs_count <= 0:
                continue
            
            self.total_count += qs_count
            setlist[queryset.model.__name__] = {
                'qs': queryset,
                'objs': [],
                'offset': start
            } 
            
        objects = []
        
        while count < limit:
            first_items = {}
            for key, cur_set in list(copy(setlist).items()):
                # if obj list in set is empty, sample new items from qs
                if not cur_set['objs']:
                    from_index = cur_set['offset']
                    cur_set['objs'] = list(cur_set['qs'][from_index:from_index+slice_len])
                    cur_set['offset'] = from_index+slice_len
                    if not cur_set['objs']:
                        # if queryset has no more items, remove it from the setlist of compilable sets
                        del setlist[key]
                        continue
                # objs now guaranteed to contain an item
                first_items[key] = cur_set['objs'][0]
            
            # stop collecting if all querysets are exhausted
            if not first_items:
                break
            
            # sort the list of each queryset's first item to get the very first
            # remove it from the set and add it to the final items
            first_item = sorted(iter(first_items.items()), key=get_sort_key, reverse=True)[0]
            setlist[first_item[0]]['objs'].pop(0)
            objects.append(first_item[1])
            
            count = len(objects)
        
        self.has_more = count < self.total_count
        return objects
    
    
    def _sort_queryset(self, queryset, stream):
        queryset = queryset.order_by('-created')
        return queryset
    
    def _filter_queryset_for_stream(self, queryset, stream, user, include_public=False):
        """ Filter a BaseTaggableObjectModel-queryset depending on the settings 
            of the current stream.
            Called during the getting of the querysets and before objects are extracted.
        """
        # always filter for portals
        if stream.portals:
            queryset = queryset.filter(group__portal__id__in=stream.portal_list)
        
        if stream.is_my_stream:
            # objects only from user-groups for My-Stream
            if user.is_authenticated:
                self.stream_user_group_ids = getattr(self, 'user_group_ids', get_cosinnus_group_model().objects.get_for_user_pks(user))
                filter_q = Q(group__pk__in=self.stream_user_group_ids)
                # if the switch is on, also include public posts from all portals
                if include_public:
                    filter_q = filter_q | Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
                queryset = queryset.filter(filter_q)
            else:
                # public objects for Public Stream
                queryset = queryset.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        else:
            # filter by group if set in stream
            if stream.group:
                queryset = queryset.filter(group__pk=stream.group.pk)
            
            # filter special streams group_ids
            if stream.special_groups:
                group_ids = [int(gid) for gid in stream.special_groups.split(',')]
                queryset = queryset.filter(group__pk__in=group_ids)
            
            if stream.media_tag:
                if stream.media_tag.topics:
                    q = None
                    # beware: this simple filter works because topics are built on a comma-separated
                    # integer field and have only ids from 1 to 9. as soon as there would be ids like
                    # id=12, id=1 would match that as well!
                    for topic in stream.media_tag.topics.split(','):
                        newq = Q(media_tag__topics__contains=topic)
                        q = q and q|newq or newq
                    queryset = queryset.filter(q)
                # filter for tags (this is the only way to handle this with taggit!)
                if stream.media_tag.tags.count() > 0:
                    ids = stream.media_tag.tags.values_list('id', flat=True)
                    queryset = queryset.filter(media_tag__tagged_items__tag__in=ids).distinct()
                # filter for tagged persons (as authors, OR combined)
                if stream.media_tag.persons.count() > 0:
                    ids = stream.media_tag.persons.values_list('id', flat=True)
                    queryset = queryset.filter(creator__id__in=ids).distinct()
                # filter location by range search of lat/lon
                if stream.media_tag.location_lat and stream.media_tag.location_lon:
                    # 1 latitude == 111 km
                    # 1 longitude at europe ~= 108 km 
                    geo_range = 0.22 # 0.22 lat/lon ~= 20km radius
                    lat_range = (stream.media_tag.location_lat-geo_range, stream.media_tag.location_lat+geo_range)
                    lon_range = (stream.media_tag.location_lon-geo_range, stream.media_tag.location_lon+geo_range)
                    queryset = queryset.filter(media_tag__location_lat__range=lat_range, media_tag__location_lon__range=lon_range)
                    
        return queryset
    
    def get_stream_objects_for_user(self, user, include_public=False):
        stream_querysets = self._get_querysets_for_stream(self, user, include_public=include_public)
        return self._get_stream_objectset(stream_querysets)
    
    def unread_count(self, force=False):
        if not hasattr(self, 'creator'):
            return 0
        # object cache, will be able to retrieved after object stored in django cache
        if not force and hasattr(self, 'last_unread_count'):
            return self.last_unread_count
        
        total_count = 0
        for queryset in self._get_querysets_for_stream(self, self.creator):
            count = queryset.exclude(creator=self.creator).filter(created__gte=self.last_seen_safe).count()
            total_count += count
        
        self.last_unread_count = total_count
        self.update_cache(self.creator)
        return total_count
    