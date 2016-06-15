'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var popupTemplate = require('map/popup');
var util = require('lib/util');

module.exports = View.extend({
    layers: {
        street: {
            url: (util.protocol() === 'http:' ?
                'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png' :
                'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png'),
            options: {
                attribution: 'CartoDB | Open Streetmap'
            }
        },
        satellite: {
            url: util.protocol() + '//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            options: {
                attribution: 'Google Maps',
                subdomains:['mt0','mt1','mt2','mt3']
            }
        },
        terrain: {
            url: util.protocol() + '//{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
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

    clusterZoomThreshold: 5,

    initialize: function () {
        var self = this;
        self.controlsView = new MapControlsView({
            el: $('#map-controls'),
            model: self.model
        });
        self.controlsView.on('change:layer', self.handleSwitchLayer, self);
        self.model.on('change:results', self.updateMarkers, self);
        self.model.on('change:bounds', self.fitBounds, self);
        Backbone.mediator.subscribe('resize:window', function () {
            self.leaflet.invalidateSize();
            self.handleViewportChange();
        });
        View.prototype.initialize.call(this);
    },

    render: function () {
        var self = this;

        self.setStartPos(function () {
            self.renderMap();
            self.model.initialSearch();
        });
    },

    // Private
    // -------

    setStartPos: function (cb) {
        var self = this;

        if (Backbone.mediator.settings.mapStartPos) {
            self.mapStartPos = Backbone.mediator.settings.mapStartPos;
            cb();
        } else {
            $.get('http://ip-api.com/json', function (res) {
                self.mapStartPos = [res.lat, res.lon];
                cb();
            }).fail(function() {
                self.mapStartPos = [0, 0];
                cb();
            });
        }
    },

    renderMap: function () {
        this.leaflet = L.map('map-fullscreen-surface').setView(this.mapStartPos, 13);

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
        var bounds = this.leaflet.getBounds()
        var paddedBounds = bounds.pad(0.1);
        this.model.set({
            south: bounds.getSouth(),
            paddedSouth: paddedBounds.getSouth(),
            west: bounds.getWest(),
            paddedWest: paddedBounds.getWest(),
            north: bounds.getNorth(),
            paddedNorth: paddedBounds.getNorth(),
            east: bounds.getEast(),
            paddedEast: paddedBounds.getEast()
        });
    },

    addMarker: function (result, resultType) {
        var marker = L.marker([result.lat, result.lon], {
            icon: L.icon({
                iconUrl: '/static/js/vendor/images/marker-icon-2x-' +
                    this.resultColours[resultType] + '.png',
                iconSize: [17, 28],
                iconAnchor: [8, 28],
                popupAnchor: [1, -27],
                shadowSize: [28, 28]
            })
        }).bindPopup(popupTemplate.render({
            imageURL: result.imageUrl,
            title: result.title,
            url: result.url,
            address: result.address
        }));

        if (this.state.clustering) {
            this.markers.addLayer(marker);
        } else {
            marker.addTo(this.leaflet);
            this.markers.push(marker);
        }
    },

    // Event Handlers
    // --------------

    // Render the search results as markers on the map.
    updateMarkers: function () {
        var self = this,
            controls = this.controlsView.model,
            results = self.model.get('results');

        // Remove previous markers from map based on current clustering state.
        if (self.markers) {
            if (self.state.clustering) {
                self.leaflet.removeLayer(self.markers);
            } else {
                _(self.markers).each(function (marker) {
                    self.leaflet.removeLayer(marker);
                });
            }
        }

        // Set clustering state: cluster only when zoomed in enough.
        var zoom = self.leaflet.getZoom();
        self.state.clustering = zoom > self.clusterZoomThreshold;

        // Set a new marker collection.
        if (self.state.clustering) {
            self.markers = L.markerClusterGroup({
                maxClusterRadius: 30
            });
        } else {
            self.markers = [];
        }

        // Add the individual markers.
        _(this.model.activeFilters()).each(function (resultType) {
            _(results[resultType]).each(function (result) {
                self.addMarker(result, resultType);
            });
        });

        // If clustering, add the cluster object to the map.
        if (self.state.clustering) {
            self.leaflet.addLayer(this.markers);
        }
    },


    handleViewportChange: function () {
        var zoom = this.leaflet.getZoom();
        this.model.set({
            clustering: zoom > self.clusterZoomThreshold
        });
        this.updateBounds();
        this.model.attemptSearch();
    },

    // Change between layers.
    handleSwitchLayer: function (layer) {
        this.setLayer(layer);
    },

    // Handle change bounds (from URL).
    fitBounds: function () {
        this.leaflet.fitBounds(L.latLngBounds(
            L.latLng(this.model.get('south'), this.model.get('west')),
            L.latLng(this.model.get('north'), this.model.get('east'))
        ));
    }
});
