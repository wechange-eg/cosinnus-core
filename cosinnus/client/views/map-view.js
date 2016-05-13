'use strict';

var View = require('views/base/view');
var template = require('map/map');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
    },

    getTemplateData: function () {
        return {
            msg: 'messageable!!!!!'
        };
    },

    afterRender: function () {
        this.renderMap();
    },

    renderMap: function () {
        console.log('MapView#renderMap');
        var startPos = [52.52,13.405],
            map = L.map('map-fullscreen-surface').setView(startPos, 13);

        L.tileLayer('https://otile1-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png', {
            attribution: 'Open Streetmap',
            maxZoom: 15,
            minZoom:3
        }).addTo(map);
    }
});
