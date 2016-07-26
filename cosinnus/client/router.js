'use strict'

var Map = require('models/map');
var MapView = require('views/map-view');

module.exports = Backbone.Router.extend({
    routes: {
        'map/': 'map'
    },

    map: function () {
        // If the map view hasn't been instantiated, create and render it.
        if (!this.mapFullscreen) {
            /* TODO: this should not take JS default values, but should also check for settings
                 defined in the HTML context (via global variable?)
                 
                 availableFilters: settings.availableFilters,
                 activeFilters: settings.activeFilters,
             */
            // TODO: find a good solution for not using COSINNUS_MAP_MARKER_ICONS as a global JS variable
            this.mapFullscreen = new Map();
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
