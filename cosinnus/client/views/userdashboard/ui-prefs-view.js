'use strict';

var util = require('lib/util.js');

module.exports = Backbone.View.extend({
    
	uiPrefs: null,
	fetchUrl: '/dashboard/api/save_ui_prefs/',
	
    initialize: function (uiPrefs) {
        var self = this;
        Backbone.View.prototype.initialize.call(self);
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
    
});
