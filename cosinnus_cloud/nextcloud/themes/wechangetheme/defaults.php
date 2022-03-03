<?php

class OC_Theme {

	/**
     * Returns the base URL
     * @return string URL
     */
    public function getBaseUrl() {
        return '/';
    }
    
	/**
	 * Returns the documentation URL
	 * @return string URL
	 */
	public function getDocBaseUrl() {
		return 'https://docs.nextcloud.com';
	}

	/**
	 * Returns the title
	 * @return string title
	 */
	public function getTitle() {
		return \OC::$server->getConfig()->getSystemValue('wechange_nc_app_title', 'nextcloud');
	}

	/**
     * Returns the short name of the software
     * @return string title
     */
    public function getName() {
        return \OC::$server->getConfig()->getSystemValue('wechange_nc_app_title', 'nextcloud');
    }
    
	/**
	 * Returns the short name of the software containing HTML strings
	 * @return string title
	 */
	public function getHTMLName() {
		return \OC::$server->getConfig()->getSystemValue('wechange_nc_app_title', 'nextcloud');
	}

	/**
	 * Returns entity (e.g. company name) - used for footer, copyright
	 * @return string entity name
	 */
	public function getEntity() {
		return \OC::$server->getConfig()->getSystemValue('wechange_nc_company_name', 'wechange');
	}

	/**
	 * Returns slogan
	 * @return string slogan
	 */
	public function getSlogan() {
		return \OC::$server->getConfig()->getSystemValue('wechange_nc_slogan', 'die Cloud von wechange');
	}

	/**
	 * Returns logo claim
	 * @return string logo claim
	 * @deprecated 13.0.0 not used anymore
	 */
	public function getLogoClaim() {
		return '';
	}

	/**
	 * Returns short version of the footer
	 * @return string short footer
	 */
	public function getShortFooter() {
		$footer = '© ' . date('Y') . ' <a href="' . $this->getBaseUrl() . '" target="_blank">' . $this->getEntity() . '</a>';
		return $footer;
	}

	/**
	 * Returns long version of the footer
	 * @return string long footer
	 */
	public function getLongFooter() {
		$footer = '© ' . date('Y') . ' <a href="' . $this->getBaseUrl() . '" target="_blank">' . $this->getEntity() . '</a>';
		return $footer;
	}

	/**
	 * Generate a documentation link for a given key
	 * @return string documentation link
	 */
	public function buildDocLinkToKey($key) {
		return $this->getDocBaseUrl() . '/server/15/go.php?to=' . $key;
	}


	/**
	 * Returns mail header color
	 * @return string
	 */
	public function getColorPrimary() {
		return \OC::$server->getConfig()->getSystemValue('wechange_nc_primary_color', '#315F72');
	}

	/**
	 * Returns variables to overload defaults from core/css/variables.scss
	 * @return array
	 */
	public function getScssVariables() {
		return [
			'color-primary' => \OC::$server->getConfig()->getSystemValue('wechange_nc_primary_color', '#315F72')
		];
	}
	

}
