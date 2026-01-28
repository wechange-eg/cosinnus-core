from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from cosinnus.models.tagged import AttachedObject
from cosinnus.utils.files import shorten_file_name
from cosinnus.utils.functions import clean_single_line_text
from cosinnus_cloud.models import CloudFile
from cosinnus_file.models import FileEntry, get_or_create_attachment_folder


class AttachedFileEntySerializer(serializers.ModelSerializer):
    """Serializer for attached FileEntry instances. Used by AttachedFileSerializer."""

    name = serializers.CharField(source='title')
    url = serializers.URLField(source='get_download_url', read_only=True)
    icon_or_thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = FileEntry
        fields = (
            'name',
            'url',
            'icon_or_thumbnail',
        )

    def get_icon_or_thumbnail(self, obj):
        if obj.is_image:
            return obj.static_image_url_thumbnail()
        return obj.get_icon()


class AttachedCloudFileSerializer(serializers.ModelSerializer):
    """Serializer for attached CloudFile instances. Used by AttachedFileSerializer."""

    name = serializers.CharField(source='title')
    url = serializers.URLField(source='download_url', read_only=True)
    icon_or_thumbnail = serializers.CharField(source='icon')

    class Meta:
        model = CloudFile
        fields = (
            'name',
            'url',
            'icon_or_thumbnail',
        )


class AttachedFileSerializer(serializers.ModelSerializer):
    """
    Serializer for file attachments.

    Example usage:
        attached_files = serializers.SerializerMethodField()
        def get_attached_files(self, obj):
            attached_files = []
            for attached_object in obj.file_attachments:
                serialized_attached_object = AttachedFileSerializer(attached_object).data
                attached_files.append(serialized_attached_object)
            return attached_files
    """

    file = serializers.SerializerMethodField()

    class Meta:
        model = AttachedObject
        fields = (
            'id',
            'file',
        )

    def get_target_object_serializer(self, model_name):
        if model_name == 'cosinnus_file.FileEntry':
            return AttachedFileEntySerializer
        elif model_name == 'cosinnus_cloud.LinkedCloudFile':
            return AttachedCloudFileSerializer
        raise NotImplementedError('Unsupported attached object model.')

    def get_file(self, obj):
        file_object_serializer = self.get_target_object_serializer(obj.model_name)
        return file_object_serializer(obj.target_object).data


class AttachFileSerializer(serializers.Serializer):
    """
    Serializer for attached file uploads.
    Validates the file upload and adds the file as FileEntry to attached_objects.
    Expects the data as multipart/form-data, as suggested by DRF.

    Example usage for an event:
        serializer = AttachedFileSerializer(event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    """

    file = serializers.FileField(required=True)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        group = self.context['group']
        file = validated_data['file']

        # create upload folder for attachment
        upload_folder = get_or_create_attachment_folder(group)

        # clean and shorten filename
        file._name = clean_single_line_text(file._name)
        max_length = FileEntry._meta.get_field('_sourcefilename').max_length
        shorten_file_name(file, max_length)

        # create FileEntry without triggering notifications
        file_entry = FileEntry(
            title=file._name,
            file=file,
            group=group,
            creator=user,
            path=upload_folder.path,
            _filesize=file.size,
            mimetype=file.content_type,
        )
        file_entry.no_notification = True
        file_entry.save()

        # set visibility
        file_entry.media_tag.visibility = instance.media_tag.visibility
        file_entry.media_tag.save()

        # create AttachedObject
        content_type = ContentType.objects.get_for_model(FileEntry)
        attached_object = AttachedObject.objects.create(content_type=content_type, object_id=file_entry.id)
        instance.attached_objects.add(attached_object)
        return instance


class DeleteAttachedFileSerializer(serializers.Serializer):
    """
    Deletes an attached_object (not the linked FileEnty).

    Example usage for an event:
        serializer = DeleteAttachedFileSerializer(event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    """

    id = serializers.IntegerField()

    def validate_id(self, value):
        if not self.instance.attached_objects.filter(pk=value).exists():
            raise serializers.ValidationError('Attached file does not exist.')
        return value

    def update(self, instance, validated_data):
        attached_file_id = validated_data['id']
        self.instance.attached_objects.filter(pk=attached_file_id).delete()
        return instance
