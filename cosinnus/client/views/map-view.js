'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var popupTemplate = require('map/popup');

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
        this.controlsView = new MapControlsView({
            el: $('#map-controls'),
            model: this.model
        });
        this.controlsView.on('change:layer', this.handleSwitchLayer, this);
        this.model.on('change:results', this.updateMarkers, this);
        View.prototype.initialize.call(this);
    },

    render: function () {
        this.renderMap();
        this.model.search();
    },

    renderMap: function () {
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

    updateMarkers: function () {
        var self = this,
            controls = this.controlsView.model;

        // Remove previous markers from map.
        // _(this.markers).each(function (marker) {
        //     self.leaflet.removeLayer(marker);
        // });
        if (self.markers) {
            self.leaflet.removeLayer(self.markers);
        }
        self.markers = L.markerClusterGroup({
            maxClusterRadius: 30
        });

        // Add markers for the new results.
        _(self.model.get('results')).each(function (result) {
            self.markers.addLayer(L
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
                .bindPopup(popupTemplate.render({
                    imageURL: result.imageUrl,
                    title: result.title,
                    url: result.url,
                    address: result.address
                })));
                // .addTo(self.leaflet));
        });

        self.leaflet.addLayer(this.markers);
    },

    handleViewportChange: function () {
        this.updateBounds();
        this.model.wantsToSearch();
    },

    // Change between layers.
    handleSwitchLayer: function (layer) {
        this.setLayer(layer);
    }
});
