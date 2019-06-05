'use strict';

var DelegatedWidgetView = require('views/base/delegated-widget-view');
var util = require('lib/util');

module.exports = DelegatedWidgetView.extend({

	app: null,
    template: require('userdashboard/typed-content-widget'),
    
    fetchURL: '/dashboard/api/user_typed_content/recent/', // overridden for subview
    
    // will be set to self.options during initialization
    defaults: {
    	
    	type: null, // the type of the content the widget displays
    	isMovable: true, // widget template options
    	isHidable: false, // widget template options
    	loadMoreEnabled: true, // widget template options
        
        state: {
        	sortIndex: 0,
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	'click .sort-up': 'onMoveUpClicked',
    	'click .sort-down': 'onMoveDownClicked',
    	'click .show-more': 'onShowMoreClicked',
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        DelegatedWidgetView.prototype.initialize.call(self, options);
        self.options.type = options.type; // would have happened in initialize already but let's be explicit
        self.state.sortIndex = options.sortIndex;
    },
    
    /** Overriding base function for unique widget ID. */
    getWidgetId: function() {
        return this.type + '-content-widget';
    },
    
    /** Overriding params for request */
    getParamsForFetchRequest: function() {
    	var self = this;
    	var superParams = DelegatedWidgetView.prototype.getParamsForFetchRequest.call(self);
    	return {urlSuffix: this.options.type, urlParams: superParams['urlParams']}
    },
    
    onMoveUpClicked: function (event) {
    	var self = this;
    	App.userDashboardView.moveRightSideWidget(self.options.type, true);
    },
    
    onMoveDownClicked: function (event) {
    	var self = this;
    	App.userDashboardView.moveRightSideWidget(self.options.type, false);
    },

    render: function () {
        var self = this;
        DelegatedWidgetView.prototype.render.call(self);
        
        util.log('# ## Rendered widget ' + self.widgetId);
    	
        // remove widget if empty
        if (self.widgetData && self.widgetData.items && self.widgetData.items.length == 0) {
        	self.$el.remove()
        }
        
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = DelegatedWidgetView.prototype.getTemplateData.call(self);
        return data;
    },
    
    
    

});
