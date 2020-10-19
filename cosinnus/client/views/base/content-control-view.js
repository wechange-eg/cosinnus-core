'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    // the resultCollection data source this view operates on.
    // often the same collection other views use as well
    collection: null,

    initialize: function (options, app, collection) {
        var self = this;
        BaseView.prototype.initialize.call(self, options);
        self.App = app;
        self.collection = collection;
    },
    
    /** Called at the end of initialization.
     * 
     *  Purpose is to initialize the combined parameters from URL and initial App options
     *  into self.state = {}, so that they are ready to be built into a search API URL 
     *  using params from each ContentControlView's `contributeToSearchParameters()` 
     *  
     *  */
    applyUrlSearchParameters: function(urlParams) {
        // stub, extend this in the inheriting view
    },
    
    /** Add all relevant search parameters to the search API query for your view.
     *  Anything happening in your view that affects the search should be involved here.
     *  
     *  @param forAPI: if true, contains all search parameters.
     *         if false, contains only these that should be visible in the browser URL 
     *  @return: dict of params 
     */
    contributeToSearchParameters: function(forAPI) {
        // stub, extend this in the inheriting view
        return {}
    },
    
    /** Called during search */
    disableInput: function() {
        // stub, extend this in the inheriting view
    },
    
    /** Called when searches end */
    enableInput: function() {
        // stub, extend this in the inheriting view
    },
    
    // private

    parseUrl: function (url) {
        if (url.indexOf('?') >= 0) {
            var json = JSON.parse('{"' + decodeURI(url.replace(/\%2C/g, ',').replace(/\+/g,' ').replace(/[^?]*\?/, '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
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
            json['topics'] = json['topics'].toString().split(',').map(Number);
        }
        if (typeof json['sdgs'] === "number" || (typeof json['sdgs'] === "string" && json['sdgs'].length > 0)) {
            json['sdgs'] = json['sdgs'].toString().split(',').map(Number);
        }
        if (typeof json['managed_tags'] === "number" || (typeof json['managed_tags'] === "string" && json['managed_tags'].length > 0)) {
            json['managed_tags'] = json['managed_tags'].toString().split(',').map(Number);
        }
        return json;
    },
    
    
});
