'use strict'

var MapView = require('views/map-view');
var util = require('lib/util.js');

module.exports = Backbone.Router.extend({
	
    routes: {
        'map/': 'route_app_map_tiles'
    },

    route_app_map_tiles: function () {
        // If the base app view hasn't been instantiated, create and render it.
    	util.log('router.js: routed ')
        Backbone.mediator.publish('navigate:map');
    },
    
    /** Triggered by the mediator event 'navigate:router' */
    on_navigate: function(url) {
    	util.log('router.js: got a navigate event!')
    	util.log(url)
    	
        if (url) {
        	Backbone.Router.prototype.navigate.call(this, url, { 
                trigger: false
            });
        }
    }
    
    
});
