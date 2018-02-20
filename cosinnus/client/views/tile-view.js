'use strict';

var BaseView = require('views/base/view');
var Result = require('models/result');
var util = require('lib/util');

module.exports = BaseView.extend({
	
	// reference back to the main App
	App: null,
	
	model: Result,

	template: require('map/tile'),
	
	attributes: {
		'class': 'col-xs-12 col-md-6'
	},
	
    initialize: function (options, app) {
        var self = this;
    	BaseView.prototype.initialize.call(self, options);
    	self.App = app;
    },
    
    
    
});
