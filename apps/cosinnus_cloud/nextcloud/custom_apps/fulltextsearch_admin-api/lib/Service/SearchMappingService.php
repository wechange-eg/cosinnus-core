<?php

declare(strict_types=1);

namespace OCA\FullTextSearch_AdminAPI\Service;

use OCP\FullTextSearch\Model\IDocumentAccess;
use OCP\FullTextSearch\Model\ISearchRequest;

/**
 * Extend the SearchMappingService to support sorting of results
 * and limit searching to specific fields via the pseudo "search_only" option
 */
class SearchMappingService extends \OCA\FullTextSearch_Elasticsearch\Service\SearchMappingService {
    public function generateSearchQueryParams(
        ISearchRequest $request, IDocumentAccess $access, string $providerId
        ): array {

        // Allow limiting search to specific fields
        $limitFields = $request->getOptionArray('search_only');
        if ($limitFields) {
            foreach ($limitFields as $f) {
                $request->addLimitField($f);
            }
        }
        $params = parent::generateSearchQueryParams($request, $access, $providerId);
        // filter out files without a name/title (these can occur if we do an empty search)
        // and the SearchService then gets confused trying to get a nonexisitant file.
        $params['body']['query']['bool']['filter'][]['bool']['must_not']['term']['title'] = '';
        $sort = $request->getOptionArray('sort');
        if ($sort) {
            $params['body']['sort'] = $sort;
        }
        return $params;
        }
}

