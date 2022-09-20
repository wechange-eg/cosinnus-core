import datetime
import logging

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models.query_utils import Q
from django.http.response import HttpResponseNotAllowed, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import ListView

from cosinnus.conf import settings
from cosinnus.models.profile import get_user_profile_model, UserMatchObject
from cosinnus.models.tagged import LikeObject
from cosinnus.utils.functions import is_number
from cosinnus.utils.permissions import check_user_can_see_user
from cosinnus.utils.user import filter_active_users


logger = logging.getLogger('cosinnus')


class UserMatchListView(ListView):
    model = get_user_profile_model()
    template_name = 'cosinnus/user/user_match_list.html'

    def get_hashset_likes_for_user(self, user=None):
        """ todo: comment what this does """
        values_liked = LikeObject.objects.filter(user=self.request.user, liked=True).values_list('content_type', 'object_id')
        user_liked_set = set(f'{liketuple[0]}::{liketuple[1]}' for liketuple in values_liked)
        return user_liked_set

    def get_context_data(self, **kwargs): # TODO: cache after!
        context = super().get_context_data(**kwargs)
        
        already_liked_users = UserMatchObject.objects.filter(type__in=[UserMatchObject.LIKE, UserMatchObject.DISLIKE])\
            .values_list('to_user_id', flat=True)
        # filter only users I haven't liked or disliked yet
        user_profiles = self.model.objects.exclude(user=self.request.user).\
                exclude(user_id__in=already_liked_users)
        # filter active users
        user_profiles = filter_active_users(user_profiles, filter_on_user_profile_model=True)
        
        # TODO: also filter users for their profile visibility (like `check_user_can_see_user` but for the entire QS)
        
        # filter user to be active within the last year
        last_year = datetime.date.today() - relativedelta(years=+1) # timedelta to pass users who have logged in at least once within the last year; TODO: as prio?
        user_profiles = user_profiles.filter(user__last_login__gte=last_year)

        request_user_liked_set = self.get_hashset_likes_for_user(self.request.user)
        score_dict = {}
        
        for profile in user_profiles:
            score = 0
            # profile fields score
            if profile.description and len(profile.description) > 10:
                score += 1
            if profile.avatar:
                score += 1
            if profile.website:
                score += 1
            if profile.email_verified:
                score += 1
            if profile.dynamic_fields:
                for value in profile.dynamic_fields.values():
                    if value:
                        score += 1
            
            # TODO: add score for topics (only for same topics?)            
            
            # mutual likes score
            this_user_liked_set = self.get_hashset_likes_for_user(profile) 
            set_union = this_user_liked_set.union(request_user_liked_set) 
            shared_like_count = len(set_union)
            score += shared_like_count
            
            score_dict[profile.id] = score

        score_dict = sorted(score_dict.items(), key=lambda score: score[1], reverse=True)
        result_score = {k: v for k, v in score_dict}

        selected_user_profiles = list(result_score.keys())[:3] # get first 3 user profiles with the highest counted score
        
        
        scored_user_profiles = self.model.objects.select_related('user').\
               filter(id__in=selected_user_profiles) # all active users related to the selected user profiles

        context.update({
            'scored_user_profiles': scored_user_profiles,
        })

        return context


def check_for_user_match(from_user, to_user):
    """ Checks if between two users, a MatchObject exists, in a way that both users
        "like" each other, and if so, triggers different effects. """
    print(f'>> checking user match {from_user} {to_user}')
    try:
        match_case_from = UserMatchObject.objects.get(from_user=from_user, to_user=to_user, type=UserMatchObject.LIKE)
        match_case_to = UserMatchObject.objects.get(from_user=to_user, to_user=from_user, type=UserMatchObject.LIKE)
        
        # TODO: create NotificationAlert
        # TODO: create email notification
        print('We matched, create notifications!')
        # open rocketchat
        
        if settings.COSINNUS_ROCKET_ENABLED:
            room_url = match_case_from.get_rocketchat_room_url()
            if match_case_from.rocket_chat_room_id and match_case_from.rocket_chat_room_name:
                match_case_to.rocket_chat_room_id = match_case_from.rocket_chat_room_id
                match_case_to.rocket_chat_room_name = match_case_from.rocket_chat_room_name
                match_case_to.save()
        else:
            logger.info('RocketChat is not enabled on this portal!')
    except UserMatchObject.DoesNotExist:
        pass


def match_create_view(request):
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated.')

    # check if `user_id` is a number
    user_id = request.POST.get('user_id')
    if user_id is None or not is_number(user_id):
        raise ValidationError(message=_('User id should be an integer and it should not be None.'))
    
    # check if `action` matches the given ones
    action = request.POST.get('action')
    if action is None or not int(action) in dict(UserMatchObject.TYPE_CHOICES).keys():
        raise ValueError(f'Action should be either "like", "dislike" or "ignore" and it should not be None.')

    # check if certain user exists
    user = get_user_model().objects.get(id=user_id)
    if not user or user is None:
        raise ObjectDoesNotExist('User matching query does not exist')
    
    # check if request.user can interact with a certain user
    if not check_user_can_see_user(request.user, user):
        raise ValidationError(message=_('Privacy settings of the user you would like to interact with do not allow this action.'))
    
    # TODO: current user can not like themselves!
    
    # create UserMatchObject
    match_object, created = UserMatchObject.objects.get_or_create(from_user=request.user, to_user=user, defaults={'type': action})
    if not created and not match_object.type == action:
        match_object.type = action
        match_object.save()
    print(f'>> created ma {match_object} {created}')

    check_for_user_match(request.user, user)
    
    return redirect('cosinnus:user-match')



user_match_list_view = UserMatchListView.as_view()

