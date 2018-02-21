'use strict';

var BaseView = require('views/base/view');
var Result = require('models/result');
var util = require('lib/util');

module.exports = BaseView.extend({
	
	// reference back to the main App
	App: null,
	
	model: Result,

	template: require('map/tile'),
	
	// The DOM events specific to an item.
    events: {
        'click .link': 'select',
    },
	
    initialize: function (options, app) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	self.App = app;
    	
    	self.model.on({
    		'change:selected': self.thisContext(self.render),
    		'change:hover': self.thisContext(self.render),
    	});
    },
    
    select: function() {
    	util.log('tile-view.js: got a select click event!')
    	this.App.controlView.setSelectedResult(this.model);
    },
    
});
