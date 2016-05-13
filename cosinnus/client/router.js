'use strict'

var MapView = require('views/map-view');

module.exports = Backbone.Router.extend({
    routes: {
        'map/': 'map'
    },

    map: function () {
        var view = new MapView({
            el: '#map-full'
        });
        view.render();
    }
});
