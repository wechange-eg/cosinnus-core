'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var popupTemplate = require('map/popup');

module.exports = View.extend({
    layers: {
        street: {
            url: 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png',
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
        people: 'red',
        events: 'yellow',
        projects: 'green',
        groups: 'blue'
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
            controls = this.controlsView.model,
            results = self.model.get('results');

        // Remove previous markers from map.
        if (self.markers) {
            self.leaflet.removeLayer(self.markers);
        }
        self.markers = L.markerClusterGroup({
            maxClusterRadius: 30
        });

        _(this.model.activeFilters()).each(function (resultType) {
            _(results[resultType]).each(function (result) {
                self.markers.addLayer(L
                    .marker([result.lat, result.lon], {
                        icon: L.icon({
                            iconUrl: '/static/js/vendor/images/marker-icon-2x-' +
                                self.resultColours[resultType] + '.png',
                            iconSize: [17, 28],
                            iconAnchor: [8, 28],
                            popupAnchor: [1, -27],
                            shadowSize: [28, 28]
                        })
                    })
                    .bindPopup(popupTemplate.render({
                        imageURL: result.imageUrl,
                        title: result.title,
                        url: result.url,
                        address: result.address
                    })));
            });
        });
        self.leaflet.addLayer(this.markers);
    },

    handleViewportChange: function () {
        this.updateBounds();
        this.model.attemptSearch();
    },

    // Change between layers.
    handleSwitchLayer: function (layer) {
        this.setLayer(layer);
    }
});
