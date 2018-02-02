'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({

    initialize: function (options) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	
    	var urlParams = this.parseUrl(window.location.href.replace(window.location.origin, ''));
        self.initializeSearchParameters(urlParams);
    },
    
    /** Called at the end of initialization.
     * 
     *  Purpose is to initialize the combined parameters from URL and initial App options
     *  into self.state = {}, so that they are ready to be built into a search API URL 
     *  using params from each ContentControlView's `contributeToSearchParameters()` 
     *  
     *  */
    initializeSearchParameters: function(urlParams) {
    	// stub, extend this in the inheriting view
    },
    
    /** Add all relevant search parameters to the search API query for your view.
     *  Anything happening in your view that affects the search should be involved here.
     *  @return: dict of params */
    contributeToSearchParameters: function() {
    	// stub, extend this in the inheriting view
    	return {}
    },
    
    
    
    // private

    parseUrl: function (url) {
        if (url.indexOf('?') >= 0) {
            var json = JSON.parse('{"' + decodeURI(url.replace(/\%2C/g, ',').replace(/[^?]*\?/, '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
        } else {
            var json = {};
        }
        _(_(json).keys()).each(function (key) {
            if (json[key] !== '') {
                try {
                    json[key] = JSON.parse(json[key]);
                } catch (err) {}
            }
        });
        if (typeof json['topics'] === "number" || (typeof json['topics'] === "string" && json['topics'].length > 0)) {
            json['topics'] = json['topics'].toString().split(',');
        }
        return json;
    },
    
    
});
