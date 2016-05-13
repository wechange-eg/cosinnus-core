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
        this.search();
    },

    renderMap: function () {
        console.log('MapView#renderMap');
        var startPos = [52.52,13.405];

        this.map = L.map('map-fullscreen-surface').setView(startPos, 13);

        L.tileLayer('https://otile1-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png', {
            attribution: 'Open Streetmap',
            maxZoom: 15,
            minZoom:3
        }).addTo(this.map);
    },

    search: function () {
        var self = this;

        // Generate some mock results and create markers for them.

        var resultTypes = [
            {
                name: 'people',
                markerColour: 'blue'
            },
            {
                name: 'events',
                markerColour: 'red'
            },
            {
                name: 'projects',
                markerColour: 'green'
            },
            {
                name: 'groups',
                markerColour: 'orange'
            }
        ];

        _(resultTypes).each(function (type) {
            _(6).times(function () {
                var bounds = self.map.getBounds();
                var markerLat = bounds.getSouth() + Math.random() * (bounds.getNorth() - bounds.getSouth());
                var markerLon = bounds.getWest() + Math.random() * (bounds.getEast() - bounds.getWest());
                var marker = L
                    .marker([markerLat, markerLon], {
                        icon: L.icon({
                            iconUrl: '/static/js/vendor/images/marker-icon-2x-' + type.markerColour + '.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        })
                    })
                    .addTo(self.map);
            });
        });
    }
});
