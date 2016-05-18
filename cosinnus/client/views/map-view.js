'use strict';

var View = require('views/base/view');
var template = require('map/map');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
        this.markers = [];
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

        this.map.on('zoomstart', this.handleZoomStart, this);
        this.map.on('zoomend', this.handleZoomEnd, this);
        this.map.on('dragend', this.handleDragEnd, this);
    },

    search: function () {
        var self = this;

        // Remove previous markers from map.
        _(this.markers).each(function (marker) {
            self.map.removeLayer(marker);
        });

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
            _(15).times(function () {
                var bounds = self.map.getBounds();
                var markerLat = bounds.getSouth() + Math.random() * (bounds.getNorth() - bounds.getSouth());
                var markerLon = bounds.getWest() + Math.random() * (bounds.getEast() - bounds.getWest());
                self.markers.push(L
                    .marker([markerLat, markerLon], {
                        icon: L.icon({
                            iconUrl: '/static/js/vendor/images/marker-icon-2x-' + type.markerColour + '.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        })
                    })
                    .addTo(self.map));
            });
        });
    },

    // Event Handlers
    // --------------

    handleZoomStart: function () {
        this.previousZoomLevel = this.map._zoom;
    },

    handleZoomEnd: function () {
        // Perform a new search only when zooming out.
        if (this.map._zoom < this.previousZoomLevel) {
            this.search();
        }
    },

    handleDragEnd: function (event) {
        this.search();
    }

});
