<script type="text/javascript" nonce="<?php p(\OC::$server->getContentSecurityPolicyNonceManager()->getNonce()) ?>">
    var _paq = _paq || [];
    /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
    _paq.push(['trackPageView']);
    _paq.push(['enableLinkTracking']);
    (function() {
      var u="https://stats.wechange.de/";
      _paq.push(['setTrackerUrl', u+'piwik.php']);
      _paq.push(['setSiteId', '<?php print_unescaped(\OC::$server->getConfig()->getSystemValue('wechange_piwik_site_id', '19')); ?>']);
      var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
      g.type='text/javascript'; g.async=true; g.defer=true; g.src=u+'piwik.js'; s.parentNode.insertBefore(g,s);
    })();
</script>
<script src="https://stats.wechange.de/piwik.js" nonce="<?php p(\OC::$server->getContentSecurityPolicyNonceManager()->getNonce()) ?>"></script>