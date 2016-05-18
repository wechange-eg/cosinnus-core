'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var template = require('map/map');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
        this.markers = [];
        this.controlsView = new MapControlsView({
            el: $('#map-controls'),
            model: this.model
        });
        this.model.on('change', this.handleControlsChange, this);
    },

    getTemplateData: function () {
        return {
            msg: 'messageable!!!!!'
        };
    },

    afterRender: function () {
        this.renderMap();
        this.updateMarkers();
    },

    renderMap: function () {
        console.log('MapView#renderMap');
        var startPos = [52.52,13.405];

        this.leaflet = L.map('map-fullscreen-surface').setView(startPos, 13);

        L.tileLayer('https://otile1-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png', {
            attribution: 'Open Streetmap',
            maxZoom: 15,
            minZoom:3
        }).addTo(this.leaflet);

        this.leaflet.on('zoomend', this.handleViewportChange, this);
        this.leaflet.on('dragend', this.handleViewportChange, this);
        this.updateBounds();
    },

    updateMarkers: function () {
        var self = this,
            controls = this.controlsView.model;

        // Remove previous markers from map.
        _(this.markers).each(function (marker) {
            self.leaflet.removeLayer(marker);
        });

        var resultColours = {
            people: 'blue',
            events: 'red',
            projects: 'green',
            groups: 'orange'
        };

        // Do search and add markers for the results.
        this.model.search(function (results) {
            _(results).each(function (result) {
                self.markers.push(L
                    .marker([result.lat, result.lon], {
                        icon: L.icon({
                            iconUrl: '/static/js/vendor/images/marker-icon-2x-' + resultColours[result.type] + '.png',
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        })
                    })
                    .addTo(self.leaflet));
            });
        });
    },

    updateBounds: function () {
        var bounds = this.leaflet.getBounds();
        this.model.set({
            south: bounds.getSouth(),
            west: bounds.getWest(),
            north: bounds.getNorth(),
            east: bounds.getEast()
        });
    },

    // Event Handlers
    // --------------

    handleViewportChange: function () {
        this.updateBounds();
        this.updateMarkers();
    },

    handleControlsChange: function (event) {
        this.updateMarkers();
    }
});
