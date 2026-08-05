def migrate_description(obj, description):
    """
    Helper to get the description of an object migrated to another service.
    Appends URLs to attached objects and comments to the description.
    Used to migrate todos and events to NextCloud for the v3 frontend.
    """
    if hasattr(obj, 'attached_objects') and obj.attached_objects.exists():
        # append attached objects
        attachments = '\n\nAttachments:\n\n'
        for attachment in obj.attached_objects.all():
            if hasattr(attachment.target_object, 'get_absolute_url'):
                url = attachment.target_object.get_absolute_url()
                attachments += f'- [{url}]({url})\n'
        attachments += '\n\n'
        description += attachments

    if hasattr(obj, 'comments') and obj.comments.exists():
        # append comments
        comments = '\n\nComments:\n\n'
        for comment in obj.comments.all():
            creator = comment.creator.get_full_name()
            comments += f'- {creator}:\n{comment.text}\n'
        description += comments

    return description
