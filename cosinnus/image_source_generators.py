# -*- coding: utf-8 -*-

from io import BytesIO

from easy_thumbnails import utils as easy_thumbnails_utils


def cosinnus_restricted_pil_image_source_generator(source, exif_orientation=True, **options):
    """
    Try to open the source file directly using PIL, ignoring any errors.
    This custom source generator only allows JPEG, PNG, BMP, and GIF image formats.

    Directly taken and adjusted from `easy_thumbnails.source_generators.pil_image`.

    exif_orientation

        If EXIF orientation data is present, perform any required reorientation
        before passing the data along the processing pipeline.

    """
    # Use a BytesIO wrapper because if the source is an incomplete file like
    # object, PIL may have problems with it. For example, some image types
    # require tell and seek methods that are not present on all storage
    # File objects.
    from PIL import Image, ImageFile

    if not source:
        return
    source = BytesIO(source.read())

    image = Image.open(source, formats=['JPEG', 'PNG', 'BMP', 'GIF'])
    # Fully load the image now to catch any problems with the image contents.
    try:
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        image.load()
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = False

    if exif_orientation:
        image = easy_thumbnails_utils.exif_orientation(image)

    return image
