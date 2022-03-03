<?php

declare(strict_types=1);

$app = \OC::$server->query(\OCA\FullTextSearch_AdminAPI\AppInfo\Application::class);
$app->registerClasses();
