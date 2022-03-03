import csv
from datetime import datetime
import errno
import os
import re
import shutil
import zipfile

from cosinnus.utils.urls import group_aware_reverse
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.http.response import HttpResponse
from django.template.defaultfilters import slugify
from rest_framework.views import APIView

from postman.models import Message, STATUS_ACCEPTED


class MessageExportView(APIView):

    format = 'old'

    def _get_users(self, user_ids=None):
        """
        Return users
        :return:
        """
        users = []
        qs = get_user_model().objects.filter(is_active=True, email__isnull=False)
        if user_ids:
            qs = qs.filter(id__in=user_ids)

        for user in qs:
            profile = user.cosinnus_profile
            if not profile:
                continue
            users.append([user.id, profile.rocket_username, profile.rocket_user_email, profile.get_external_full_name()])
        return users

    def _get_channels(self, user_ids, format='old'):
        """
        Return channels (conversations and direct messages)
        :param user_ids:
        :return:
        """
        channels, direct_messages = [], []
        qs = Message.objects.filter(
            sender__in=user_ids,
            #sender_archived=False,
            #recipient_archived=False,
            moderation_status=STATUS_ACCEPTED,
            parent__isnull=True,
        )
        qs = qs.exclude(sender_deleted_at__isnull=False, recipient_deleted_at__isnull=False)
        qs = qs.filter(Q(multi_conversation__isnull=True, thread__isnull=True) |
                       Q(multi_conversation__isnull=True, thread_id=F('id')) |
                       Q(multi_conversation__isnull=False, master_for_sender=True, thread__isnull=True) |
                       Q(multi_conversation__isnull=False, master_for_sender=True, thread_id=F('id')))
        for message in qs:
            if message.multi_conversation:
                sender_profile = message.sender.cosinnus_profile
                if not sender_profile:
                    continue
                participants = ';'.join(str(u.cosinnus_profile.rocket_username)
                                        for u in message.multi_conversation.participants.all()
                                        if u.id in user_ids and u.cosinnus_profile)
                if participants:
                    channel_name = f'{slugify(message.subject)}-{message.id}'
                    channels.append([message.id, channel_name, sender_profile.rocket_username, 'private', participants])
            elif message.sender_id in user_ids and message.recipient_id in user_ids:
                sender_profile, recipient_profile = message.sender.cosinnus_profile, message.recipient.cosinnus_profile
                if not sender_profile or not recipient_profile:
                    continue
                if format == 'old':
                    channel_name = slugify(f'{sender_profile.rocket_username} x {recipient_profile.rocket_username}')
                    channels.append([message.id, channel_name, sender_profile.rocket_username, 'direct',
                                     recipient_profile.rocket_username])
                else:
                    direct_messages.append([message.id, sender_profile.rocket_username,
                                            recipient_profile.rocket_username])

        return channels, direct_messages

    def format_message(self, text):
        """
        Replace WECHANGE formatting language with Rocket.Chat formatting language:
        Rocket.Chat:
            Bold: *Lorem ipsum dolor* ;
            Italic: _Lorem ipsum dolor_ ;
            Strike: ~Lorem ipsum dolor~ ;
            Inline code: `Lorem ipsum dolor`;
            Image: ![Alt text](https://rocket.chat/favicon.ico) ;
            Link: [Lorem ipsum dolor](https://www.rocket.chat/) or <https://www.rocket.chat/ |Lorem ipsum dolor> ;
        :param text:
        :return:
        """
        # Unordered lists: _ to - / * to -
        text = re.sub(r'\n_ ', '\n- ', text)
        text = re.sub(r'\n\* ', '\n- ', text)
        # Italic: * to _
        text = re.sub(r'(^|\n|[^\*])\*($|\n|[^\*])', r'\1_\2', text)
        # Bold: ** to *
        text = re.sub(r'\*\*', '*', text)
        # Strike: ~~ to ~
        text = re.sub(r'~~', '~', text)
        return text

    def _get_messages(self, channel, user_ids, since=None, format='old'):
        """
        Return messages in channel
        :return:
        """
        messages, attachments = [], []
        qs = Message.objects.filter(
            sender__in=user_ids,
            #sender_archived=False,
            #recipient_archived=False,
            moderation_status=STATUS_ACCEPTED,
        )
        qs = qs.exclude(sender_deleted_at__isnull=False, recipient_deleted_at__isnull=False)
        qs = qs.filter(Q(id=channel[0]) |
                       Q(thread_id=channel[0]))
        if since:
            qs = qs.filter(sent_at__gte=since)
        qs = qs.order_by('sent_at')
        for message in qs:
            text = self.format_message(message.body)
            # if message.thread_id == message.id and message.subject:
            if message.subject:
                text = f"*{message.subject}*\n{text}"
            timestamp = int(message.sent_at.timestamp() * 1000)
            sender_profile = message.sender.cosinnus_profile
            if not sender_profile:
                continue
            if format == 'old':
                messages.append([sender_profile.rocket_username, timestamp, text])
            else:
                recipient_profile = message.recipient.cosinnus_profile
                if not recipient_profile:
                    continue
                messages.append([sender_profile.rocket_username, recipient_profile.rocket_username, timestamp, text])

            for att in message.attached_objects.all():
                fileentry = att.target_object
                if not fileentry:
                    continue
                url = group_aware_reverse('cosinnus:file:rocket-download',
                                          kwargs={'group': fileentry.group, 'slug': att.target_object.slug})
                if not fileentry:
                    continue
                attachments.append([
                    sender_profile.rocket_username,
                    timestamp,
                    url
                ])
        return messages, attachments

    def make_archive(self, file_list, archive, root):
        """
        'fileList' is a list of file names - full path each name
        'archive' is the file name for the archive with a full path
        """
        zip_file = zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED)

        for f in file_list:
            zip_file.write(os.path.join(root, f), f)
        zip_file.close()

    def get(self, request, *args, **kwargs):
        """
        Return users/channels as ZIP file (required by Rocket.Chat)
        see https://rocket.chat/docs/administrator-guides/import/csv/
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # Limit to given users, if specified
        user_ids = request.GET.get('users')
        if user_ids:
            user_ids = set([int(u) for u in user_ids.split(',')])

        since = request.GET.get('since')
        if since:
            since = datetime.strptime(since, '%Y-%m-%d-%H-%M')

        # Recreate folder
        path = 'export'
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        # Create ZIP contents
        users = self._get_users(user_ids)
        with open(f'{path}/users.csv', 'w') as csv_file:
            writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
            for user in users:
                writer.writerow(user[1:])
        user_ids = set(u[0] for u in users)

        channels, direct_messages = self._get_channels(user_ids, format=self.format)
        with open(f'{path}/channels.csv', 'w') as csv_file:
            channel_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)

            for channel in channels:
                messages, attachments = self._get_messages(channel, user_ids, since=since, format=self.format)

                if not messages:
                    continue
                # Create folder
                channel_path = f'{path}/{channel[1]}'
                if not os.path.exists(channel_path):
                    try:
                        os.makedirs(channel_path)
                    except OSError as exc:  # Guard against race condition
                        if exc.errno != errno.EEXIST:
                            raise
                with open(f'{channel_path}/messages.csv', 'a') as csv_file:
                    writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
                    writer.writerows(messages)
                if attachments:
                    with open(f'{channel_path}/uploads.csv', 'a') as csv_file:
                        writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
                        writer.writerows(attachments)
                channel_writer.writerow(channel[1:])

        if self.format != 'old':
            dm_path = f'{path}/directmessages'
            os.makedirs(dm_path)
            for dm in direct_messages:
                messages, attachments = self._get_messages(dm, user_ids, format='direct')

                with open(f'{dm_path}/{dm[0]}-messages.csv', 'a') as csv_file:
                    writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
                    writer.writerows(messages)
                if attachments:
                    with open(f'{dm_path}/{dm[0]}-uploads.csv', 'a') as csv_file:
                        writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
                        writer.writerows(attachments)

        # Return zip file
        zip_filename = 'export.zip'
        file_list = [os.path.relpath(os.path.join(dp, f), 'export')
                     for dp, dn, fn in os.walk(os.path.expanduser(path)) for f in fn]
        self.make_archive(file_list, zip_filename, path)
        response = HttpResponse(open(zip_filename, 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response
