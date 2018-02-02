'use strict';

var ContentControlView = require('views/base/content-control-view');
var MapLayerButtonsView = require('views/map-layer-buttons-view');
var popupTemplate = require('map/popup');
var util = require('lib/util');

module.exports = ContentControlView.extend({
    
	template: require('map/map'),
	
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

    
    // TODO
    mapLayerButtonsView: null,
    
    // handle on the current popup
    popup: null,
    
    
    // will be set to self.options during initialization
    defaults: {
    	// shall we cluster close markers together
    	clusteringEnabled: false,
    	clusterZoomThreshold: 5,
    	maxClusterRadius: 15,
    	
    	// if a marker popup is open, but the search results change and the marker would be removed,
    	// should we still keep it and the popup?
    	keepOpenMarkersAfterResultChange: false, 
    	
    	// added percentage to visible map area
    	// the resulting area is actually sent as coords to the search API 
    	latLngBuffer: 0.01,
    	
    	resultColours: {
    		people: 'red',
    		events: 'yellow',
    		projects: 'green',
    		groups: 'blue'
    	},
    	
        zoom: 7,
        location: [
            52.5233,
            13.4138
        ],
        // the current layer option as string
	    layer: 'street',
	    
	    state: {
	        // the curren Leaflet layer object
	        currentLayer: null,

	        // are we currently seeing clustered markers?
	        currentlyClustering: false,
	        // the current open spider cluster handle, or null if no spider open
	        currentSpiderfied: null,
	        
	        // TODO: somewhere we need to set fallback defaults when navigated without loc params!!
	        north: null, 
	        east: null,
	        south: null,
	        west: null,
	    }
    },
    
    initialize: function (options) {
        var self = this;
        // this calls self.initializeSearchParameters()
        ContentControlView.prototype.initialize.call(self, options);
        
        Backbone.mediator.subscribe('change:results', self.updateMarkers, self);
        Backbone.mediator.subscribe('change:bounds', self.fitBounds, self);
        Backbone.mediator.subscribe('resize:window', function () {
            self.leaflet.invalidateSize();
            self.handleViewportChange();
        }, self);
        Backbone.mediator.subscribe('change:layer', self.setLayer, self);
        
        self.state.currentlyClustering = self.options.clusteringEnabled;
    },

    afterRender: function () {
        var self = this;
        self.mapLayerButtonsView = new MapLayerButtonsView({
        	el: self.$el.find('.map-layers-buttons'),
        	layer: self.options.layer,
        	mapView: self
        }).render();
        self.renderMap();
    },
    
    // extended from content-control-view.js
    initializeSearchParameters: function (urlParams) {
    	console.log('map-view.js: url params on init: ' + urlParams)
        _.extend(this.state, {
            north: util.ifundef(urlParams.ne_lat, this.state.north),
            east: util.ifundef(urlParams.ne_lon, this.state.east),
            south: util.ifundef(urlParams.sw_lat, this.state.south),
            west: util.ifundef(urlParams.sw_lon, this.state.west),
        });
    },
    
    // extended from content-control-view.js
    contributeToSearchParameters: function() {
    	console.log('TODO: completely ignoring coordinate padding rn!')
    	var padded = false;
        var searchParams = {
            ne_lat: padded ? this.state.paddedNorth : this.state.north,
            ne_lon: padded ? this.state.paddedEast : this.state.east,
            sw_lat: padded ? this.state.paddedSouth : this.state.south,
            sw_lon: padded ? this.state.paddedWest : this.state.west,
        };
    	return searchParams
    },

    // Private
    // -------

    renderMap: function () {
        this.markers = [];
        this.leaflet = L.map('map-container')
            .setView(this.options.location, this.options.zoom);
        this.setLayer(this.options.layer);
        
        if (this.options.clusteringEnabled) {
        	// Setup the cluster layer
        	this.clusteredMarkers = L.markerClusterGroup({
        		maxClusterRadius: this.options.maxClusterRadius
        	});
        	this.clusteredMarkers.on('spiderfied', this.handleSpiderfied, this);
        	this.leaflet.addLayer(this.clusteredMarkers);
        	this.setClusterState();
        }

        this.leaflet.on('zoomend', this.handleViewportChange, this);
        this.leaflet.on('dragend', this.handleViewportChange, this);
        this.leaflet.on('popupopen', this.handlePopup, this);
        this.leaflet.on('popupclose', this.handlePopup, this);
        
        // disable drag dropping inside map controls
        var div = this.$el.find('.map-controls')[0];
        if (div) {
            if (!L.Browser.touch) {
                L.DomEvent.disableClickPropagation(div);
                L.DomEvent.on(div, 'mousewheel', L.DomEvent.stopPropagation);
            } else {
                L.DomEvent.on(div, 'click', L.DomEvent.stopPropagation);
            }
        }
        
        this.updateBounds();
    },

    setLayer: function (layer) {
        this.state.currentLayer && this.leaflet.removeLayer(this.state.currentLayer);
        var options = _(this.layers[layer].options).extend({
            maxZoom: 15,
            minZoom:3
        });
        this.state.currentLayer = L.tileLayer(this.layers[layer].url, options)
            .addTo(this.leaflet);
    },

    updateBounds: function () {
        var bounds = this.leaflet.getBounds()
        var paddedBounds = bounds.pad(this.options.latLngBuffer);
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
        var iconUrl, iconWidth, iconHeight = null;
        if (this.options.markerIcons && this.options.markerIcons[resultType]) {
            var iconSettings = this.options.markerIcons[resultType];
            iconUrl = iconSettings.url;
            iconWidth = iconSettings.width;
            iconHeight = iconSettings.height;
        } else {
            iconUrl = '/static/js/vendor/images/marker-icon-2x-' +
                this.options.resultColours[resultType] + '.png';
            iconWidth = 17;
            iconHeight = 28;
        }
        var marker = L.marker([result.lat, result.lon], {
            icon: L.icon({
                iconUrl: iconUrl,
                iconSize: [iconWidth, iconHeight],
                iconAnchor: [iconWidth / 2, iconHeight],
                popupAnchor: [1, -27],
                shadowSize: [28, 28]
            })
        }).bindPopup(popupTemplate.render({
            imageURL: result.imageUrl,
            title: result.title,
            url: result.url,
            address: result.address,
            description: result.description
        }));
        

        if (!self.options.keepOpenMarkersAfterResultChange || (this.markerNotPopup(marker) && this.markerNotSpiderfied(marker))) {
	        if (this.state.currentlyClustering) {
	            this.clusteredMarkers.addLayer(marker);
	        } else {
	            marker.addTo(this.leaflet);
	        }
	        this.markers.push(marker);
        }
    },

    setClusterState: function () {
    	if (self.options.clusteringEnabled) {
    		// Set clustering state: cluster only when zoomed in enough.
    		var zoom = this.leaflet.getZoom();
    		this.state.currentlyClustering = zoom > this.options.clusterZoomThreshold;
    	}
    },

    markerNotPopup: function (marker) {
        var p = this.popup;
        return !p || !_(p.getLatLng()).isEqual(marker.getLatLng());
    },

    markerNotSpiderfied: function (marker) {
        var s = this.state.currentSpiderfied;
        var ret = !s || !_(s.getAllChildMarkers()).find(function (m) {
            return _(m.getLatLng()).isEqual(marker.getLatLng());
        });
        return ret;
    },

    removeMarker: function (marker) {
        if (this.state.currentlyClustering) {
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

            	if (!self.options.keepOpenMarkersAfterResultChange || (self.markerNotPopup(marker) && self.markerNotSpiderfied(marker))) {
            		self.removeMarker(marker);
            	}
            });
        }

        self.setClusterState();
        self.markers = [];

        // Ensure popup and spiderfied markers are in the markers array;
        // even when they aren't included in the latest results.
        if (self.options.keepOpenMarkersAfterResultChange) {
	        if (self.popup) {
	            self.markers.push(self.popup._source);
	        } else if (self.state.currentSpiderfied) {
	            _(self.state.currentSpiderfied.getAllChildMarkers()).each(function (m) {
	                self.markers.push(m);
	            });
	        }
        }

        // Add the individual markers.
        _(this.model.activeFilterList()).each(function (resultType) {
            _(results[resultType]).each(function (result) {
                self.addMarker(result, resultType);
            });
        });
    },

    handleViewportChange: function () {
        this.setClusterState();
        this.updateBounds();
        this.model.attemptSearch();
    },

    // Handle change bounds (from URL).
    fitBounds: function () {
        this.leaflet.fitBounds(L.latLngBounds(
            L.latLng(this.state.south, this.state.west),
            L.latLng(this.state.north, this.state.east)
        ));
    },

    handlePopup: function (event) {
        if (event.type === 'popupopen') {
            this.popup = event.popup;
        } else {
            var popLatLng = this.popup.getLatLng();
            var marker = event.popup._source;
            // Remove the popup's marker if it's now off screen.
            if (!this.leaflet.getBounds().pad(this.options.latLngBuffer).contains(popLatLng)) {
                this.removeMarker(marker);
            }
            this.popup = null;
        }
    },

    handleSpiderfied: function (event) {
        this.state.currentSpiderfied = event.cluster;
    }
});
