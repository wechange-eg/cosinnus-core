<?php

namespace OCA\FullTextSearch_AdminAPI\Service;

use OCP\FullTextSearch\Model\IIndexDocument;

/**
 * Extend the original IndexMappingService to also index the modification time
 */
class IndexMappingService extends \OCA\FullTextSearch_Elasticsearch\Service\IndexMappingService {

        public function generateIndexBody(IIndexDocument $doc): array {
            $res = parent::generateIndexBody($doc);
            $res['mtime'] = $doc->getModifiedTime();
            return $res;
        }

}

