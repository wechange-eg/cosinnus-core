'use strict';

var View = require('views/base/view');
var util = require('lib/util.js');

module.exports = View.extend({
	
	template: require('map/map-layers'),
	
	mapView: null,
	
	options: {
		layer: null
	},
	
    initialize: function (options) {
    	var self = this;
    	self.options.layer = options.layer;
    	self.mapView = options.mapView;
        View.prototype.initialize.call(self, options);
    },

    events: {
        'click .layer-button': 'switchLayerClicked',
    },

    // Event Handlers
    // --------------

    // Switch layers if clicked layer isn't the active layer.
    switchLayerClicked: function (event) {
        var layer = $(event.currentTarget).data('layer');
        if (this.mapView.options.layer !== layer) {
            this.mapView.options.layer = layer;
            this.layer = layer;
            // TODO: is layer arriving in the template?
            console.log('map-layer-buttons-view.js: TODO: is layer arriving in the template?')
            this.render();
            Backbone.mediator.publish('change:layer', layer);
        }
    },
    
});
