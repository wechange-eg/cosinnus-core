'use strict'

var MapView = require('views/map-view');
var util = require('lib/util.js');

module.exports = Backbone.Router.extend({
	
    routes: {
        'map/': 'route_app_map_tiles'
    },
    
    first_route_event: true,

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
    			trigger: false,
    			replace: App.router.first_route_event
    		});
    		
    		if (App.router.first_route_event) {
    			util.log('router.js: THIS IS THE FIRST NAVIGATE EVENT. Replacing history state instead of adding a new one!')
    			App.router.first_route_event = false;
    		}
        }
    }
    
    
});
