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
    },
	
    initialize: function (options, app) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	self.App = app;
    	
    	Backbone.mediator.subscribe('result:selected', self.onResultSelected, self);
    	Backbone.mediator.subscribe('result:reselected', self.onResultSelected, self);
    	Backbone.mediator.subscribe('result:unselected', self.onResultUnselected, self);
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
