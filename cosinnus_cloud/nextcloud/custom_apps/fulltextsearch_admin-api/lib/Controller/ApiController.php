<?php
declare(strict_types=1);

namespace OCA\FullTextSearch_AdminAPI\Controller;

use daita\MySmallPhpTools\Traits\Nextcloud\TNCDataResponse;
use Exception;
use OCA\FullTextSearch\AppInfo\Application;
use OCA\FullTextSearch\Model\SearchRequest;
use OCA\FullTextSearch\Service\ConfigService;
use OCA\FullTextSearch\Service\MiscService;
use OCA\FullTextSearch\Service\SearchService;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\DataResponse;
use OCP\IRequest;


/**
 * Class ApiController
 *
 * @package OCA\FullTextSearch_AdminAPI\Controller
 */
class ApiController extends Controller {


    use TNCDataResponse;

    /** @var SearchService */
    private $searchService;

    /** @var ConfigService */
    private $configService;

    /** @var MiscService */
    private $miscService;

    /**
     * ApiController constructor.
     *
     * @param IRequest $request
     * @param ConfigService $configService
     * @param SearchService $searchService
     * @param MiscService $miscService
     */
    public function __construct(
        IRequest $request, ConfigService $configService,
        MiscService $miscService
    ) {
        parent::__construct(Application::APP_NAME, $request);
        $this->configService = $configService;
        $this->miscService = $miscService;
    }

    /**
     * @NoCSRFRequired
     *
     * @param string $request
     *
     * @return DataResponse
     */
    public function searchFromRemote(string $request): DataResponse {
        return $this->searchDocuments(SearchRequest::fromJSON($request));
    }

    /**
     * @param SearchRequest $request
     *
     * @return DataResponse
     */
    private function searchDocuments(SearchRequest $request): DataResponse {
        try {
            // HACK: SearchService (in fulltextsearch addon) will call FilesProvider#improveSearchResults (in files_fulltextsearch)
             // which will instantiate a files_fulltextsearch version of SearchService, that version will get the current userId
            // during initialization, and use that. So we have to make sure that the current user id is the one we want.
            // Therefore, we first set the user in the session, and then request the SearchService (from fulltextsearch). This
            // seems to work and cause the files_fulltextsearch version of SearchService to get the userId we want.
            \OC::$server->getUserSession()->setUser(\OC::$server->getUserManager()->get($request->getAuthor()));
            $result = \OC::$server->query("OCA\FullTextSearch\Service\SearchService")->search($request->getAuthor(), $request);

            return $this->success(
                $result,
                [
                    'request' => $request,
                    'version' => $this->configService->getAppValue('installed_version')
                ]
            );
        } catch (Exception $e) {
            return $this->fail(
                $e,
                [
                    'request' => $request,
                    'version' => $this->configService->getAppValue('installed_version')
                ]
            );
        }
    }

}
