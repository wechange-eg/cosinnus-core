'use strict';

var DelegatedWidgetView = require('views/base/delegated-widget-view');
var util = require('lib/util');

module.exports = DelegatedWidgetView.extend({

	app: null,
    template: require('userdashboard/ideas-widget'),
    
    fetchURL: '/dashboard/api/user_liked_ideas/', // overridden for subview
    
    // will be set to self.options during initialization
    defaults: {
        
        state: {
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	//'focus .nav-search-box': 'onSearchBoxFocusIn',
    },

    /** Overriding base function for unique widget ID. */
    getWidgetId: function() {
        return 'ideas-widget';
    },
    
    /** Overriding params for request */
    getParamsForFetchRequest: function() {
    	return {urlSuffix: null, urlParams: {}}
    },
    

    render: function () {
        var self = this;
        DelegatedWidgetView.prototype.render.call(self);
        
        util.log('*** Rendered ideas-widget! ***')
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = DelegatedWidgetView.prototype.getTemplateData.call(self);
        return data;
    },
    
    
    

});
