'use strict'

var Map = require('models/map');
var MapView = require('views/map-view');

module.exports = Backbone.Router.extend({
    routes: {
        'map/': 'app_map_tiles'
    },

    app_map_tiles: function () {
        // If the base app view hasn't been instantiated, create and render it.
    	console.log('router.js: routed ')
        Backbone.mediator.publish('navigate:map');
    }
    
});
