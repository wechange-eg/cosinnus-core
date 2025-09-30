import unicodecsv as csv
from django.template.defaultfilters import linebreaksbr
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal
from cosinnus.models.mitwirkomat import MitwirkomatSettings
from cosinnus.templatetags.cosinnus_tags import safe_text
from cosinnus.utils.mitwirkomat import MitwirkomatFilterExporterUnformatted

if settings.COSINNUS_MITWIRKOMAT_INTEGRATION_ENABLED:

    class MitwirkomatCSVRenderer(CSVRenderer):
        writer_opts = {
            'delimiter': ';',
            'quoting': csv.QUOTE_ALL,
            #'lineterminator': ';\r\n',  # probably not needed, uncomment if we want to end all lines with ';'
        }

        def tablize(self, data, header=None, labels=None):
            """This override returns the data as it was passed, without any headers.
            Otherwise, rest's CSVRenderer force-adds some kind of header row."""
            return data

    class MitwirkomatExportView(APIView):
        """
        API endpoint for exporting all `MitwirkomatSettings` that have `is_active=True` and whose groups are enabled
        for this portal.
        The CSV generated here isn't really a proper CSV format as such, as rows are basically just key/value pairs.
        """

        renderer_classes = (MitwirkomatCSVRenderer,) + tuple(api_settings.DEFAULT_RENDERER_CLASSES)
        permission_classes = ()

        def get(self, request, *args, **kwargs):
            rows = self._get_active_mitwirkomat_settings()
            return Response(rows)

        def _get_active_mitwirkomat_settings(self):
            all_rows = []

            active_mitwirkomat_settings = MitwirkomatSettings.objects.filter(
                is_active=True, group__portal=CosinnusPortal.get_current(), group__is_active=True
            ).prefetch_related('group')

            for mom in active_mitwirkomat_settings:
                rows = []
                group = mom.group

                platzhalter = group.slug
                name = mom.name or group.name or ''
                raw_description = mom.description or group.description_long or group.description or ''
                beschreibung = linebreaksbr(safe_text(raw_description).strip())
                logo_url = (
                    mom.get_avatar_thumbnail_url(size=(200, 200)) or ''
                )  # will automatically inherit group.avatar
                if logo_url:
                    logo_url = self.request.build_absolute_uri(logo_url)
                link = group.get_absolute_url()

                # build the questions value list. these are the chosen field values from the
                # `MitwirkomatSettings.questions` list, for *each* of the question keys in
                # `settings.COSINNUS_MITWIRKOMAT_QUESTION_LABELS`, in sorted order!
                # so this doesn't list all question values contained in `MitwirkomatSettings.questions`, but only
                # those who are contained and are currently configured in settings.COSINNUS_MITWIRKOMAT_QUESTION_LABELS`
                # (this allows us to add some new questions in the config, and keeping the already answered ones, while
                # using the default value for unanswered new ones, because each question is identified by its key)
                mom_questions_dict = dict((item.get('question'), item.get('answer')) for item in mom.questions)
                sorted_keys = sorted(settings.COSINNUS_MITWIRKOMAT_QUESTION_LABELS.keys(), key=lambda k: int(k))
                answer_values_list = [
                    mom_questions_dict.get(key, MitwirkomatSettings.QUESTION_DEFAULT) for key in sorted_keys
                ]

                # build the filter span string from the dynamic fields if filled, or their fallbacks if set
                # requirements: The selected filter values should be displayed in the CSV file in a common span element
                # located behind the description, i.e.,
                # `"Beschreibung";"${WERT DES FELDS BESCHREIBUNG}<span class='filter-values' data-a='xyz'
                #   data-b='123'></span>"`.
                # It is important to use single quotes for the attributes!
                beschreibung_filter = ''  # `<span class='filter-values' data-a='xyz' data-b='123'></span>`
                filter_attr_str = self._export_dynamic_fields_filter_attribute_str(mom)
                if settings.COSINNUS_MITWIRKOMAT_INCLUDE_LOCATION:
                    filter_attr_str += ' ' + self._export_location_filter_attribute_str(mom)
                filter_attr_str = filter_attr_str.strip()
                if filter_attr_str:
                    beschreibung_filter = f"<span class='filter-values' {filter_attr_str}></span>"

                # Build Mitwirk-O-Mat-flavored "CSV"-format:
                rows += [
                    ['Abkürzung', platzhalter],
                    ['Name', name],
                    ['Beschreibung', beschreibung + beschreibung_filter],
                    ['Link', link],
                    ['Logo', logo_url],
                ]
                rows += [[f'{val}', ''] for val in answer_values_list]  # questions list, second value is blank!
                rows += [['###', 'Freizeile']]  # entry item seperator
                all_rows.extend(rows)
            return all_rows

        def _export_dynamic_fields_filter_attribute_str(self, mom):
            """For a given MitwirkomatSettings instance, return the filter string for the mitwirkomat CSV generated by
                the exporter class set as `mom_filter_exporter` for each dynamic `CosinnusMitwirkomatDynamicField`
                set in `mom_filter_exporter` in the field settings.
            @param mom: instance of `MitwirkomatSettings`
            @return: str like `data-a='xyz' data-b='123', or empty string if no dynamic fields are set.
            """
            filter_attrs = []
            for field_name, field_class in settings.COSINNUS_MITWIRKOMAT_EXTRA_FIELDS.items():
                field_value = mom.dynamic_fields.get(field_name)
                exporter = field_class.mom_filter_exporter or MitwirkomatFilterExporterUnformatted
                filter_attrs.append(exporter.export_mom_attribute(field_value, field_class, mom))
            return ' '.join(filter_attrs)

        def _export_location_filter_attribute_str(self, mom):
            """For a given MitwirkomatSettings instance, return the filter string for the inherited group location
                (first location entry in the group).
            @param mom: instance of `MitwirkomatSettings`
            @return: str like `data-lat='48.8902' data-lon='8.99458'`, or empty string if no location is set in group
                settings.
            """
            location_lat = ''
            location_lon = ''
            if mom.group.locations.exists():
                location = mom.group.locations.first()
                if location.location_lat and location.location_lon:
                    location_lat = location.location_lat
                    location_lon = location.location_lon
            return f"data-lat='{location_lat}' data-lon='{location_lon}'"

        def finalize_response(self, request, response, *args, **kwargs):
            """
            Renders the csv output
            """
            if request.GET.get('format') == 'csv':
                response['Content-Disposition'] = 'attachment, filename=exported_mitwirkomat_initiativen.csv'
            return super().finalize_response(request, response, *args, **kwargs)
