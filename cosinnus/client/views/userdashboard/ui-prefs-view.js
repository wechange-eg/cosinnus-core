'use strict';

var util = require('lib/util.js');

module.exports = Backbone.View.extend({
    
	uiPrefs: null,
	fetchUrl: '/dashboard/api/save_ui_prefs/',
	
    initialize: function (uiPrefs) {
        var self = this;
        Backbone.View.prototype.initialize.call(self);
        $('body').on('click', '[data-target="ui-pref"]', self.onUiPrefLinkClicked.bind(this));
        self.uiPrefs = uiPrefs;
    },
    
    /** Returns a uiPref for the given ui_pref key, e.g. 'timeline__only_mine' */
    getUiPref: function(uiPref) {
    	if (uiPref in this.uiPrefs) {
    		return this.uiPrefs[uiPref];
    	}
    	return null;
    },
    
    /** Applies the given uiPrefs into the current state and
     * 	sends a request to persist them in the DB for this user.
     * 	The API only persists well-formed, existing ui prefs, so
     *  we don't need to worry about validating them. */
    saveUiPrefs: function(uiPrefDict) {
    	var url = this.fetchUrl;
    	$.extend(true, self.uiPrefs, uiPrefDict);
    	return new Promise(function(resolve, reject) {
			$.ajax(url, {
                type: 'POST',
                timeout: 15000,
                data: uiPrefDict,
                success: function (response, textStatus, xhr) {
                    if (xhr.status == 200) {
                		resolve();
                    } else {
                    	reject(xhr.statusText);
                    }
                },
                error: function (xhr, textStatus) {
                	reject(xhr.statusText);
                }
            });
    	});
    	
    },
    
    /** A listener for clicks on links that cause ui pref changes. 
     * 	Required attributes on the link are:
     * 		- `data-target="ui-pref"`: as identifier
     * 		- `data-ui-pref`: set to the name of the ui pref
     * 		- `data-ui-pref-value`: set to the value the ui pref should take
     * 		- `data-hide-after`: (optional) a selector for an element that should be hidden 
     * 				after the ui pref was saved
     *  */
    onUiPrefLinkClicked: function(event) {
    	var self = this;
    	var prefs = {};
    	var $link = $(event.target);
    	
    	prefs[$link.attr('data-ui-pref')] = $link.attr('data-ui-pref-value');
    	this.saveUiPrefs(prefs);
    	
    	// if an element is given in `data-hide-after`, hide that element
    	var hideAfter = $link.attr('data-hide-after');
    	if (hideAfter) {
    		$(hideAfter).fadeOut();
    	}
    },
    
});
