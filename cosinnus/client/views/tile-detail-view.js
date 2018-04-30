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
    	'click .result-link': 'onResultLinkClicked',
        'click .tile-close-button': 'onDeselectClicked',
    	'click .topic-filter-link': 'onTopicLinkClicked',
    },
	
    initialize: function (options, app) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	self.App = app;
    	
    	// TODO: delete once new detail open/close logic is in place
//    	Backbone.mediator.subscribe('result:selected', self.onResultSelected, self);
//    	Backbone.mediator.subscribe('result:reselected', self.onResultSelected, self);
//    	Backbone.mediator.subscribe('result:unselected', self.onResultUnselected, self);
    	
    	Backbone.mediator.subscribe('result:detail-opened', self.onDetailOpened, self);
    	Backbone.mediator.subscribe('result:detail-closed', self.onDetailClosed, self);
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
    onDetailOpened: function (result) {
    	this.model = result;
    	this.render();
    },
    
    // a result is being unselected
    onDetailClosed: function () {
    	this.model = null;
    	this.render();
    },
    
    /** Called when a topic link is clicked to filter for that topic only */
    onTopicLinkClicked: function(event) {
    	// make sure to close
    	this.App.controlView.displayDetailResult(null);
    	this.App.controlView.onTopicLinkClicked(event);
    },
    
    /**
     * Called when a tile detail close button is clicked.
     * We only change the Result model's .selected property and
     * don't do any rendering here (this is mediated through signals from the control view).
     */
    onDeselectClicked: function () {
    	util.log('tile-view.js: got a deselect click event!');
    	this.App.controlView.displayDetailResult(null);
    },
    

    /**
     * Called when a link is clicked that leads to opening a detail view.
     * We only change the Result model's .selected property and
     * don't do any rendering here.
     */
    onResultLinkClicked: function (event) {
    	this.App.controlView.onResultLinkClicked(event);
    },
    
});
