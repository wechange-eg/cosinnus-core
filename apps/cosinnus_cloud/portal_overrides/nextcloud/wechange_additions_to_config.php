  'theme' => 'wechangetheme',
  'social_login_auto_redirect' => true, # can be circumvented by passing /login?noredir=1 to the login URL
  'default_language' => 'de',
  'default_locale' => 'de',
  'allow_user_to_change_display_name' => false,
  'overwriteprotocol' => 'https',
  'wechange_plattform_root' => '<root-domain-of-plattform-without-trailing-slash>',
  'wechange_nc_root' => '<root-domain-of-nextcloud-instance-without-trailing-slash>',
  'wechange_csp_domains' => ['wechange.de', '*.wechange.de', '<root-domain-of-plattform-without-trailing-slash>', '*.<root-domain-of-plattform-without-trailing-slash>'],
  'wechange_piwik_enabled' => false,
  'wechange_piwik_site_id' => <piwik-site-id-as-int>,
  'wechange_nc_app_title' => 'WE-Cloud', # cloud title, appears almost everywhere
  'wechange_nc_company_name' => 'WECHANGE eG', # name of the portal owners 
  'wechange_nc_slogan' => 'die Cloud von WECHANGE', # string slogan
  'wechange_nc_primary_color' => '#34b4b5', # hex-color code
  'wechange_firstrun_main_text' => '
<p>
    Die WE-Cloud bietet deinem Team eine flexible Dateiablage mit umfangreichen Office-Funktionen, um gemeinsam an Dokumenten, Tabellen und Präsentationen zu arbeiten. Sie basiert auf Nextcloud und OnlyOffice. So stehen dir zwei Apps zur Verfügung, mit denen du die Cloud auch unterwegs nutzen und Dateien mit deinem Desktop-Computer synchronisieren kannst.
</p>

<p>
    Gruppen und Projekten stehen jeweils maximal 1 GB zur Verfügung. Jede*r Nutzer*in hat davon unabhängig 100 MB privaten Speicherplatz - im Startfenster der WE-Cloud könnt ihr euch einfach einen privaten Ordner anlegen. Benötigt ihr mehr Speicherplatz, schreibt an 
    <a href="mailto:support@wechange.de" target="_blank" rel="noreferrer noopener">support@wechange.de</a>.
</p>
<p>
    Falls ihr eure Dateien mit der Windows-Desktop-App von Nextcloud synchronisieren wollt, bitte beachtet, dass Ordnernamen mit Sonderzeichen (&lt; &gt; : " / \ | ? *) nicht erkannt werden und zuerst bereinigt werden müssen.
</p>
', # first run wizard main text. HTML, can be multiline
  'wechange_firstrun_warning_enabled' => true, # whether to show a warning box in the first run wizard
  'wechange_firstrun_warning_header' => 'Achtung!',
  'wechange_firstrun_warning_text' => 'Wenn ihr gemeinsam mit OnlyOffice an einer Datei arbeitet, könnt ihr diese jederzeit manuell speichern (Shortcut strg+s), um die Datei zu synchronisieren - so könnt ihr auch später auf vorherige Versionen der Datei zurückgreifen. Ungeachtet dessen speichert OnlyOffice die Dateien regelmäßig automatisch ab.',
  'wechange_firstrun_learn_more_label' => 'Mehr erfahren',
  'wechange_firstrun_learn_more_url' => 'https://plattform-n.org/n/n-cloud/', # link will be hidden if this is set to null
  