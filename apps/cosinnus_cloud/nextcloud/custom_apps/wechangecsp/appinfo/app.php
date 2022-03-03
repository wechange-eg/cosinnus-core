<?php

$csp = new \OCP\AppFramework\Http\ContentSecurityPolicy();
foreach(\OC::$server->query(\OCP\IConfig::class)->getSystemValue('wechange_csp_domains', []) as $domain) {

  $csp->addAllowedScriptDomain($domain);
  $csp->addAllowedImageDomain($domain);
  $csp->addAllowedConnectDomain($domain);
  $csp->addAllowedFormActionDomain($domain);
  $csp->addAllowedFrameDomain($domain);
  $csp->addAllowedFrameAncestorDomain($domain);
}
$cspManager = \OC::$server->query(\OCP\Security\IContentSecurityPolicyManager::class);
$cspManager->addDefaultPolicy($csp);
