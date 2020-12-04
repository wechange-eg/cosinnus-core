# TODO: This file is only for a quickfix for a broken project setup. REMOVE AFTER IMPORT FIXING!
#

from django.utils.translation import ugettext_lazy as _

from cosinnus.dynamic_fields import dynamic_fields

LEGEND_FOR_FREETEXT_CHOICES = _('Wähle aus der Liste aus oder füge einen Wert ein')
LEGEND_FOR_MULTIPLE_FREETEXT_CHOICES = _('Wähle beliebig viele Einträge aus der Liste aus oder füge eigene hinzu')

BOELL_USERPROFILE_EXTRA_FIELDS = {
    'anrede': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT,
        label=_('Anrede'),
        legend=_('Anrede in E-Mails angesprochen  '),
        choices=(('Liebe', 'Liebe'), ('Lieber', 'Lieber'), ('Liebe_r', 'Liebe_r')),
        default='Liebe_r',
        hidden=True
    ),
    'ansprache': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT,
        label=_('Bevorzugte Ansprache'),
        legend=_('Nur als interner Hinweis, wie mit dir kommuniziert werden soll'),
        choices=(('Du' ,'Du'), ('Sie', 'Sie')),
        default='Du'
    ),
    'geburtsname': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
        label=_('Geburtsname'),
    ),
    'akademischer_titel': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
        label=_('Akademischer Titel'),
    ),
    'geburtsdatum': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_DATE,
        label=_('Geburtsdatum'),
    ),
    'geschlecht': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_PREDEFINED_CHOICES_TEXT,
        label=_('Geschlecht'),
        choices=(('', _('(No choice)')), ('männlich', 'männlich'), ('weiblich', 'weiblich'), ('divers', 'divers')),
        default='',
    ),
    'nationalitaet': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_COUNTRY,
        label=_('Nationalität'),
    ),
    'id_stiftung': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
        label=_('Stiftungs-Benutzer-ID'),
        legend=_('Benötigt für den Abgleich und Eindeutige Zuordnung zu Stiftungs-Datensatz'),
        hidden=True,
        readonly=True,
    ),
    'ansprechperson_referent': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD,
        label=_('WIP: Ansprechperson Referent/in'),
        required=False, # TODO: said True in fieldlist, but not possible for readonly
        readonly=True,
        note='User ID int. User choices are members of the managed tag chosen for this field'
    ),
    'ansprechperson_projektbearbeiter': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_MANAGED_TAG_USER_CHOICE_FIELD,
        label=_('WIP: Ansprechperson Projektbearbeiter/in'),
        required=False, # TODO: said True in fieldlist, but not possible for readonly
        readonly=True,
        note='User ID int. User choices are members of the managed tag chosen for this field'
    ),
    'foerder_beginn': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_DATE,
        label=_('Förderbeginn'),
        required=False, # TODO: said True in fieldlist, but not possible for readonly
        readonly=True, # for choice fields, if multiple can be shown
    ),
    'foerder_ende': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_DATE,
        label=_('Förderende'),
        required=False, # TODO: said True in fieldlist, but not possible for readonly
        readonly=True, # for choice fields, if multiple can be shown
    ),
    'postadresse': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_MULTI_ADDRESS,
        label=_('WIP: Post-Adressen'),
        legend=_('Hier kannst du deine Postanschriften eintragen und die aktuell gültige Auswählen'),
        note='Hardcode: own widget with "Active" Radio-button and ONE Textfield for address. Later: sub-fields: c/o, Strasse, PLZ, Ort, Bundesland, Staat'
    ),
    'telefon_festnetz': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_PHONE,
        label=_('Telefon (Festnetz)'),
    ),
    'telefon_mobil': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_PHONE,
        label=_('Telefon (Mobil)'),
    ),

    'promotionsthema': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
        label=_('Promotionsthema'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
        note='Hardcode: required for managed tag "Promovierende"'
    ),
    'promotionsbetreuer': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT,
        label=_('Promotionsbetreuer/in'),
        note='Hardcode: required for managed tag "Promovierende"'
    ),
    'faechergruppe': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
        label=_('Fächergruppe'),
        required=True, # whether to be required in forms
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'studienbereich': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
        label=_('Studienbereich'),
        required=True, # whether to be required in forms
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),

    'studienfach': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Studienfach'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        required=True, # whether to be required in forms
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'name_hochschule': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Name der Hochschule'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        required=True, # whether to be required in forms
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'hochschulort': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Hochschulort'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        required=True, # whether to be required in forms
    ),
    'hochschule_bundesland': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Hochschule Bundesland'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        required=True, # whether to be required in forms
    ),
    'hochschule_staat': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_COUNTRY,
        label=_('Hochschule Staat'),
        required=True, # whether to be required in forms
    ),

    'branche': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Branche'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'funktion': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Funktion'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'arbeitgeber': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Arbeitgeber/in'),
        legend=LEGEND_FOR_MULTIPLE_FREETEXT_CHOICES,
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'praktikumserfahrung': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA,
        label=_('Praktikumserfahrung'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'auslandserfahrung': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA,
        label=_('Auslandserfahrung'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'Engagement': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Engagement'),
        legend=LEGEND_FOR_MULTIPLE_FREETEXT_CHOICES,
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'mitgliedschaften': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Mitgliedschaften'),
        legend=LEGEND_FOR_MULTIPLE_FREETEXT_CHOICES,
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),
    'hobbies': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('Hobbies'),
        legend=LEGEND_FOR_MULTIPLE_FREETEXT_CHOICES,
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
    ),

    'regionale_expertise': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
        label=_('regionale Expertise'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
    ),
    'schwerpunkte': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA,
        label=_('Konkrete Arbeits-/Forschungsschwerpunkte'),
    ),

    'trainer_bool': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_BOOLEAN,
        label=_('Ich stehe als Trainer/in zur Verfügung'),
        default=False,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tag "Alumni"'
    ),
    'trainer_themen': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('für folgende Themen'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tag "Alumni", only selectable if `trainer_bool` active'
    ),
    'trainer_bereiche': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_FREE_CHOICES_TEXT,
        label=_('für Kompetenzentwicklung in folgenden Bereichen'),
        legend=LEGEND_FOR_FREETEXT_CHOICES,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tag "Alumni", only selectable if `trainer_bool` active'
    ),
    'trainer_qualification': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA,
        label=_('Qualifikationen, Weiterbildung, Zertifikate usw.'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
        note='Hardcode: Only visible for users with managed tag "Alumni", only selectable if `trainer_bool` active'
    ),

    'mentor_bool': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_BOOLEAN,
        label=_('Ich stehe als Mentor/in zur Verfügung'),
        default=False,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tags Alumni, VD, Gästen, Mitarbeitenden'
    ),
    'mentor_spezifizierung': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
        label=_('insbesondere für diese Themen'),
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tag Alumni, VD, Gästen, Mitarbeitenden, only selectable if `mentor_bool` active'
    ),
    'mentor_expertise': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT,
        label=_('Als Mentor liegt meine fachliche Expertise in den Bereichen'),
        multiple=True,
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_FACETTED,
        note='Hardcode: Only visible for users with managed tag Alumni, VD, Gästen, Mitarbeitenden, only selectable if `mentor_bool` active'
    ),
    'mentor_anmerkung': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_AREA,
        label=_('Weiterführende Anmerkungen der Mentorin / des Mentors (max. 1000 Zeichen)'),
        search_field_type=dynamic_fields.DYNAMIC_FIELD_SEARCH_FIELD_TYPE_MAIN_SEARCH,
        note='Hardcode: Only visible for users with managed tag Alumni, VD, Gästen, Mitarbeitenden, only selectable if `mentor_bool` active. Hardcode: 1000 zeichen max-val'
    ),
}
