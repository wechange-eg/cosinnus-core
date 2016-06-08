'use strict'

var Map = require('models/map');
var MapView = require('views/map-view');

module.exports = Backbone.Router.extend({
    routes: {
        'map/': 'map'
    },

    map: function () {
        var map = new Map();
        var view = new MapView({
            el: '#map-fullscreen',
            model: map
        });
        view.render();
    }
});
