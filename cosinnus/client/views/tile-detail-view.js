'use strict';

var BaseView = require('views/base/view');
var Result = require('models/result');
var util = require('lib/util');

var detailTemplate = require('tiles/tile-detail');

module.exports = BaseView.extend({
	
	// reference back to the main App
	App: null,
	
	model: Result,

	template: detailTemplate,
	
	// The DOM events specific to an item.
    events: {
        'click .tile-close-button': 'onDeselectClicked',
    	'click .topic-filter-link': 'onTopicLinkClicked',
    },
	
    initialize: function (options, app) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	self.App = app;
    	
    	Backbone.mediator.subscribe('result:selected', self.onResultSelected, self);
    	Backbone.mediator.subscribe('result:reselected', self.onResultSelected, self);
    	Backbone.mediator.subscribe('result:unselected', self.onResultUnselected, self);
    },

    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
    	var self = this;
    	var data = BaseView.prototype.getTemplateData.call(self);
    	data['controlView'] = _.extend(
    		{},
    		self.App.controlView.options,
    		self.App.controlView.state
    	);
    	return data;
    },
    
    // a new result is being selected
    onResultSelected: function (result) {
    	this.model = result;
    	this.render();
    },
    
    // a result is being unselected
    onResultUnselected: function (result) {
    	this.model = null;
    	this.render();
    },
    
    /** Called when a topic link is clicked to filter for that topic only */
    onTopicLinkClicked: function(event) {
    	// make sure to close
    	this.App.controlView.setSelectedResult(null);
    	this.App.controlView.onTopicLinkClicked(event);
    },
    
    /**
     * Called when a tile detail close button is clicked.
     * We only change the Result model's .selected property and
     * don't do any rendering here (this is mediated through signals from the control view).
     */
    onDeselectClicked: function () {
    	util.log('tile-view.js: got a deselect click event!');
    	this.App.controlView.setSelectedResult(null);
    },
    
});
