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
            this.mapFullscreen = new Map();
            var view = new MapView({
                el: '#map-fullscreen',
                model: this.mapFullscreen
            });
            view.render();
        // Otherwise navigation has occurred between map states.
        } else {
            Backbone.mediator.publish('navigate:map');
        }
    }
});
