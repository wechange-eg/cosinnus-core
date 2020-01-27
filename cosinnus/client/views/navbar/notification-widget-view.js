'use strict';

var DelegatedWidgetView = require('views/base/delegated-widget-view');
var util = require('lib/util');

module.exports = DelegatedWidgetView.extend({

	app: null,
    template: require('navbar/notification-widget'),
    
    fetchURL: '/profile/api/alerts/get/', // overridden for subview
    
    // will be set to self.options during initialization
    defaults: {
    	
    	type: null, // the type of the content the widget displays
    	loadMoreEnabled: true, // widget template options
        
        state: {
            newestTimestamp: null,
            seenCount: 0,
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	'click .show-more': 'onShowMoreClicked',
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        DelegatedWidgetView.prototype.initialize.call(self, options);
        self.options.type = options.type; // would have happened in initialize already but let's be explicit
    },
    
    /** Overriding base function for unique widget ID. */
    getWidgetId: function() {
        return 'notification-widget';
    },
    
    /** Overriding params for request */
    getParamsForFetchRequest: function(loadOptions) {
    	var self = this;
    	if (typeof loadOptions !== "undefined" && loadOptions.isPoll == true) {
            return {
                urlSuffix: self.state.newestTimestamp,
                urlParams: null
            };
    	}
    	var urlParams = null;
        if (self.options.loadMoreEnabled && self.state.offsetTimestamp) {
            urlParams = {
                'offset_timestamp': self.state.offsetTimestamp,
            }
        }
        return {
            urlSuffix: null,
            urlParams: urlParams,
        }
    },
    
    
    /** Handles data that has been loaded */
    handleData: function (response) {
        var self = this;
        DelegatedWidgetView.prototype.handleData.call(self, response);
        
        var data = response['data'];
        if (data.polled_timestamp) {
            // was a poll, prepend new items 
            Array.prototype.push.apply(data['items'], self.widgetData['items'])
            self.widgetData['items'] = data['items'];
        } 
        
        if (data['newest_timestamp'] !== "undefined") {
            self.state.newestTimestamp = data['newest_timestamp'];
        }
        if (data['unseen_count'] !== "undefined") {
            self.state.unseenCount = data['unseen_count'];
        }
    },
    
    render: function () {
        var self = this;
        DelegatedWidgetView.prototype.render.call(self);
        
        util.log('# ## Rendered notification widget ' + self.widgetId);
    	
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = DelegatedWidgetView.prototype.getTemplateData.call(self);
        return data;
    },
    
    
    

});
