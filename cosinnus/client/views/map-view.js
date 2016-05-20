'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var template = require('map/map');

module.exports = View.extend({
    layers: {
        street: {
            url: 'https://otile1-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
            options: {
                attribution: 'Open Streetmap'
            }
        },
        satellite: {
            url: 'http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            options: {
                attribution: 'Google Maps',
                subdomains:['mt0','mt1','mt2','mt3']
            }
        },
        terrain: {
            url: 'http://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            options: {
                attribution: 'Google Maps',
                subdomains:['mt0','mt1','mt2','mt3']
            }
        }
    },

    resultColours: {
        people: 'blue',
        events: 'red',
        projects: 'green',
        groups: 'orange'
    },

    initialize: function () {
        this.template = template;
        this.markers = [];
        this.controlsView = new MapControlsView({
            el: $('#map-controls'),
            model: this.model
        });
        this.controlsView.on('change:layer', this.handleSwitchLayer, this);
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

        this.setLayer(this.model.get('layer'));

        this.leaflet.on('zoomend', this.handleViewportChange, this);
        this.leaflet.on('dragend', this.handleViewportChange, this);
        this.updateBounds();
    },

    setLayer: function (layer) {
        this.currentLayer && this.leaflet.removeLayer(this.currentLayer);
        var options = _(this.layers[layer].options).extend({
            maxZoom: 15,
            minZoom:3
        });
        this.currentLayer = L.tileLayer(this.layers[layer].url, options)
            .addTo(this.leaflet);
    },

    updateMarkers: function () {
        var self = this,
            controls = this.controlsView.model;

        // Remove previous markers from map.
        _(this.markers).each(function (marker) {
            self.leaflet.removeLayer(marker);
        });

        // Do search and add markers for the results.
        this.model.search(function (results) {
            _(results).each(function (result) {
                self.markers.push(L
                    .marker([result.lat, result.lon], {
                        icon: L.icon({
                            iconUrl: '/static/js/vendor/images/marker-icon-2x-' +
                                self.resultColours[result.type] + '.png',
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

    // Update the result markers if search controls where changed
    handleControlsChange: function (event) {
        if (!event.changed.layer) {
            this.updateMarkers();
        }
    },

    // Change between layers.
    handleSwitchLayer: function (layer) {
        this.setLayer(layer);
    }
});
