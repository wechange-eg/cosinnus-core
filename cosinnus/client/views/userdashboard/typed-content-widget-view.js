'use strict';

var DelegatedWidgetView = require('views/base/delegated-widget-view');
var util = require('lib/util');

module.exports = DelegatedWidgetView.extend({

	app: null,
    template: require('userdashboard/typed-content-widget'),
    
    fetchURL: '/dashboard/api/user_typed_content/', // overridden for subview
    
    // will be set to self.options during initialization
    defaults: {
    	
    	type: null, // the type of the content the widget displays
    	isMovable: true, // widget template options
    	isHidable: true, // widget template options
        
        state: {
        	sortIndex: 0,
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	//'focus .nav-search-box': 'onSearchBoxFocusIn',
    },
    

    initialize: function (options, app) {
        var self = this;
        self.app = app;
        self.type = options.type; // would have happened in initialize already but let's be explicit
        DelegatedWidgetView.prototype.initialize.call(self, options);
        self.state.sortIndex = options.sortIndex;
    },
    
    /** Overriding base function for unique widget ID. */
    getWidgetId: function() {
        return this.type + '-content-widget';
    },
    
    /** Overriding params for request */
    getParamsForFetchRequest: function() {
    	return {urlSuffix: this.type, urlParams: {}}
    },
    

    render: function () {
        var self = this;
        DelegatedWidgetView.prototype.render.call(self);
        
        util.log('# ## Rendered widget ' + self.widgetId);
    			
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = DelegatedWidgetView.prototype.getTemplateData.call(self);
        return data;
    },
    
    
    

});
