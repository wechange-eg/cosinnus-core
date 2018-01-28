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
    },
    
    map_old: function () {
        // If the base app view hasn't been instantiated, create and render it.
    	console.log('router.js: checkin')
        if (!this.appView) {
        	console.log('heya')
        	/* TODO: this should not take JS default values, but should also check for settings
            defined in the HTML context (via global variable?)
            
            availableFilters: settings.availableFilters,
            activeFilters: settings.activeFilters,
        */
       // TODO: find a good solution for not using COSINNUS_MAP_MARKER_ICONS as a global JS variable
       var topicsHtml = typeof COSINNUS_MAP_TOPICS_HTML !== 'undefined' ? $("<div/>").html(COSINNUS_MAP_TOPICS_HTML).text() : '';
       this.mapFullscreen = new Map({}, {
           topicsHtml: topicsHtml
       });
       var view = new MapView({
           el: '#map-fullscreen',
           model: this.mapFullscreen,
           markerIcons: typeof COSINNUS_MAP_MARKER_ICONS !== 'undefined' ? COSINNUS_MAP_MARKER_ICONS : {},
       });
       view.render();
        // Otherwise navigation has occurred between map states.
        } else {
            Backbone.mediator.publish('navigate:map');
        }
    }
});
