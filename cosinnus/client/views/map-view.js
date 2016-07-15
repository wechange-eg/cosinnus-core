'use strict';

var View = require('views/base/view');
var MapControlsView = require('views/map-controls-view');
var popupTemplate = require('map/popup');
var template = require('map/map');
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

    latLngBuffer: 0.1,

    maxClusterRadius: 15,

    default: {
        zoom: 7,
        location: [
            52.5233,
            13.4138
        ]
    },

    initialize: function (options) {
        var self = this;
        self.template = template;
        self.options = $.extend(true, {}, self.default, options);
        self.model.on('change:results', self.updateMarkers, self);
        self.model.on('change:bounds', self.fitBounds, self);
        Backbone.mediator.subscribe('resize:window', function () {
            self.leaflet.invalidateSize();
            self.handleViewportChange();
        });
        View.prototype.initialize.call(this);
    },

    afterRender: function () {
        var self = this;

        if (self.model.get('controlsEnabled')) {
            self.controlsView = new MapControlsView({
                el: self.$el.find('.map-controls'),
                model: self.model,
                options: self.options
            }).render();
            self.controlsView.on('change:layer', self.handleSwitchLayer, self);
        }

        self.renderMap();
        self.model.initialSearch();
    },

    // Private
    // -------

    renderMap: function () {
        this.markers = [];
        this.leaflet = L.map(this.options.el.replace('#', ''))
            .setView(this.options.location, this.options.zoom);
        this.setLayer(this.model.get('layer'));

        // Setup the cluster layer
        this.clusteredMarkers = L.markerClusterGroup({
            maxClusterRadius: this.maxClusterRadius
        });
        this.leaflet.addLayer(this.clusteredMarkers);
        this.setClusterState();

        this.leaflet.on('zoomend', this.handleViewportChange, this);
        this.leaflet.on('dragend', this.handleViewportChange, this);
        this.leaflet.on('popupopen', this.handlePopup, this);
        this.leaflet.on('popupclose', this.handlePopup, this);
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
        var paddedBounds = bounds.pad(this.latLngBuffer);
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
        var iconUrl = null;
        if (this.options.markerIcons && this.options.markerIcons[resultType]) {
            iconUrl = this.options.markerIcons[resultType];
        } else {
            iconUrl = '/static/js/vendor/images/marker-icon-2x-' +
                this.resultColours[resultType] + '.png';
        }
        var marker = L.marker([result.lat, result.lon], {
            icon: L.icon({
                iconUrl: iconUrl,
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

        if (this.markerNotPopup(marker)) {
            if (this.state.clustering) {
                this.clusteredMarkers.addLayer(marker);
            } else {
                marker.addTo(this.leaflet);
            }
            this.markers.push(marker);
        }
    },

    setClusterState: function () {
        // Set clustering state: cluster only when zoomed in enough.
        var zoom = this.leaflet.getZoom();
        this.state.clustering = zoom > this.clusterZoomThreshold;
    },

    markerNotPopup: function (marker) {
        var p = this.state.popup;
        return !p || !_(p.getLatLng()).isEqual(marker.getLatLng());
    },

    removeMarker: function (marker) {
        if (this.state.clustering) {
            this.clusteredMarkers.removeLayer(marker);
        } else {
            this.leaflet.removeLayer(marker);
        }
    },

    // Event Handlers
    // --------------

    // Render the search results as markers on the map.
    updateMarkers: function () {
        var self = this,
            results = self.model.get('results');

        // Remove previous markers from map based on current clustering state.
        if (self.markers) {
            _(self.markers).each(function (marker) {
                if (self.markerNotPopup(marker)) {
                    self.removeMarker(marker);
                }
            });
        }

        self.setClusterState();
        self.markers = [];
        if (self.state.popup) {
            self.markers.push(self.state.popup._source);
        }

        // Add the individual markers.
        _(this.model.activeFilterList()).each(function (resultType) {
            _(results[resultType]).each(function (result) {
                self.addMarker(result, resultType);
            });
        });
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
    },

    handlePopup: function (event) {
        if (event.type === 'popupopen') {
            this.state.popup = event.popup;
        } else {
            var popLatLng = this.state.popup.getLatLng();
            var marker = event.popup._source;
            // Remove the popup's marker if it's now off screen.
            if (!this.leaflet.getBounds().pad(this.latLngBuffer).contains(popLatLng)) {
                this.removeMarker(marker);
            }
            this.state.popup = null;
        }
    }
});
