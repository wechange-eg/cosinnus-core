'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    fetchURL: null, // to be overridden in subclass

    widgetId: null, // set at initialization
    widgetData: {},
    
    // will be set to self.options during initialization
    defaults: {
    	
    	isMovable: false, // widget template options
    	isHidable: false, // widget template options
    	loadMoreEnabled: false, // widget template options
    	
        state: {
        	sortIndex: 0,
        	hasMore: false,
    		offsetTimestamp: null,
        }
    },
    
    // You will need to add these events to extending widget views as well!
    events: {
    	'click .show-more': 'onShowMoreClicked',
    },

    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        self.widgetId = self.getWidgetId();
    },
    
    /** 
     * Set the unique widget ID for this widget.
     * Stub to be overridden. 
     *  */
    getWidgetId: function() {
    	alert('ImproperlyImplemented: this view must implement the function "setWidgetId"!');
    },
    
    /** 
     *  Get all params required for the fetch of widget data to the URL `self.fetchURL`
     *  Stub to be overridden.
     *  */
    getParamsForFetchRequest: function() {
    	var self = this;
    	var urlParams = {};
    	if (self.options.loadMoreEnabled && self.state.offsetTimestamp) {
    		urlParams = {
				'offset_timestamp': self.state.offsetTimestamp,
				'page_size': 5,
    		}
    	}
    	return {
    		urlSuffix: null,
    		urlParams: urlParams,
    	}
    },
       
    /**
     * Loads the contents for this widget from `self.fetchUrl`, sets them as data for this view and
     * renders the widget.
     * 
     * Returns a promise which resolves after the chain completes or an error occured 
     * (the widget shows an error message then). Never rejects.
     */
    load: function() {
    	var self = this;
    	return new Promise(function(resolve, reject) {
    		self.loadData()
	    		.then(self.thisContext(self.render))
	    		.then(function(){
	    			util.log('# ### loaded and resolving widget ' + self.widgetId);
	    			resolve();
	    		});
    	});
    },
    
    loadData: function() {
    	var self = this;
		return new Promise(function(resolve, reject) {
			self.state['hadErrors'] = false;
			
			// build URL
			var params = self.getParamsForFetchRequest();
			var url = self.fetchURL + (params.urlSuffix ? params.urlSuffix + '/' : '');
			if (params.urlParams) {
				url += '?' + $.param(params.urlParams);
			}
			
			$.ajax(url, {
                type: 'GET',
                success: function (response, textStatus, xhr) {
                    util.log('# # Fetched data for widget ' + self.widgetId);
    			
                    if (xhr.status == 200) {
                    	self.handleData(response);
                    } else {
                    	self.state['hadErrors'] = true;
                    }
                },
                error: function (xhr, textStatus) {
                    self.state['hadErrors'] = true;
                },
                complete: function (xhr, textStatus) {
                	resolve();
                }
            });
    	});
    },
    
    /** Handles data that has been loaded */
    handleData: function (response) {
    	var self = this;
    	var data = response['data'];
    	
    	if (self.state.offsetTimestamp) {
    		// append item data
    		Array.prototype.push.apply(self.widgetData['items'], data['items'])
    	} else {
    		// first data load
    		self.widgetData = data;
    	}
    	
    	if (self.options.loadMoreEnabled) {
    		if ('has_more' in data) {
    			self.state.hasMore = data['has_more'];
    		}
    		if ('offset_timestamp' in data) {
    			self.state.offsetTimestamp = data['offset_timestamp'];
    		}
    	}
    },
    
    /** Load more items */
    onShowMoreClicked: function (event) {
    	this.load().then(function(){
    		$.cosinnus.renderMomentDataDate();
    	});
    },
    
    /**
     *  Default implementation to retrieve data to be rendered.
     *  If a model is set, return its attributes as JSON, otherwise
     *  an empty object with any options and state attributes on the 
     *  view mixed in.
     */
    getTemplateData: function () {
    	var self = this;
        var data = BaseView.prototype.getTemplateData(self);
        var data = _.extend(
        	data,
        	self.state,
        	self.options,
            self.widgetData
        );
        return data;
    },
    
});
