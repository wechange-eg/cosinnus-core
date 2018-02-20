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

    
    // the map Layer Buttons (Sattelite, Street, Terrain)
    mapLayerButtonsView: null,
    
    // handle on the current popup
    popup: null,
    
    // leaflet instance
    leaflet: null,
    
    // Marker storage dict of {<resultModel.id>: <L.marker>, ...}
    // id corresponds to self.collection.get(<id>)
    // updated through the handlers of self.collection's signals
    markers: {},
    
    
    // will be set to self.options during initialization
    defaults: {
    	// is the window in full-screen mode (instead of inside a widget or similar)
    	fullscreen: true,
    	
    	// is this view shown together with the map view as a 50% split screen?
    	splitscreen: false,
    	
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
    	
    	// correcspond to the model values of Result.type
    	resultColours: {
    		people: 'red',
    		events: 'green',
    		projects: 'blue',
    		groups: 'yellow'
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
	        
	        // fallback default coordinates when navigated without loc params
	        north: util.ifundef(COSINNUS_MAP_DEFAULT_COORDINATES.ne_lat, 55.78), 
	        east: util.ifundef(COSINNUS_MAP_DEFAULT_COORDINATES.ne_lon, 23.02),
	        south: util.ifundef(COSINNUS_MAP_DEFAULT_COORDINATES.sw_lat, 49.00),
	        west: util.ifundef(COSINNUS_MAP_DEFAULT_COORDINATES.sw_lon, 3.80),
	    }
    },
    
    initialize: function (options, app, collection) {
        var self = this;
        // this calls self.initializeSearchParameters()
        ContentControlView.prototype.initialize.call(self, options, app, collection);
        
        self.state.currentlyClustering = self.options.clusteringEnabled;
        
        Backbone.mediator.subscribe('change:bounds', self.fitBounds, self);
        Backbone.mediator.subscribe('resize:window', function () {
            self.leaflet.invalidateSize();
            self.handleViewportChange();
        }, self);
        Backbone.mediator.subscribe('change:layer', self.setLayer, self);
        
        // result events
        self.collection.on({
    	   'add' : self.thisContext(self.markerAdd),
    	   'change:hover': self.thisContext(self.markerChangeHover),
    	   'change:selected': self.thisContext(self.markerChangeSelected),
    	   'change': self.thisContext(self.markerUpdate),
    	   'remove': self.thisContext(self.markerRemove),
    	});
    },

    render: function () {
    	var self = this;
        ContentControlView.prototype.render.call(self);
    	self.renderMap();
    	return self;
    },
    
    afterRender: function () {
        var self = this;
        self.mapLayerButtonsView = new MapLayerButtonsView({
        	el: self.$el.find('.map-layers-buttons'),
        	layer: self.options.layer,
        	mapView: self
        }).render();
    },
    
    // extended from content-control-view.js
    initializeSearchParameters: function (urlParams) {
    	util.log('map-view.js: url params on init: ')
    	util.log(urlParams)
        _.extend(this.state, {
            north: util.ifundef(urlParams.ne_lat, this.state.north),
            east: util.ifundef(urlParams.ne_lon, this.state.east),
            south: util.ifundef(urlParams.sw_lat, this.state.south),
            west: util.ifundef(urlParams.sw_lon, this.state.west),
        });
    },
    
    // extended from content-control-view.js
    contributeToSearchParameters: function(forAPI) {
    	var padded = forAPI;
        var searchParams = {
            ne_lat: padded ? this.state.paddedNorth : this.state.north,
            ne_lon: padded ? this.state.paddedEast : this.state.east,
            sw_lat: padded ? this.state.paddedSouth : this.state.south,
            sw_lon: padded ? this.state.paddedWest : this.state.west,
        };
    	return searchParams
    },
    
    
    // ResultCollection Event handlers
    // --------------

    markerAdd: function(result) {
    	var self = this;
    	// adding a marker that is already there? impossibru! but best be sure.
    	if (result.id in this.markers) {
    		this.markerRemove(result);
    	}
    	
    	var markerIcon = this.getMarkerIconForType(result.get('type'));
    	var coords = [result.get('lat'), result.get('lon')];
    	
    	util.log('adding marker at coords ' + JSON.stringify(coords))
        var marker = L.marker(coords, {
            icon: L.icon({
                iconUrl: markerIcon.iconUrl,
                iconSize: [markerIcon.iconWidth, markerIcon.iconHeight],
                iconAnchor: [markerIcon.iconWidth / 2, markerIcon.iconHeight],
                popupAnchor: [1, -27],
                shadowSize: [28, 28]
            })
        }).bindPopup(popupTemplate.render({
            imageURL: result.get('imageUrl'),
            title: result.get('title'),
            url: result.get('url'),
            address: result.get('address'),
            description: result.get('description')
        }));
        
        if (!this.options.keepOpenMarkersAfterResultChange || (this.markerNotPopup(marker) && this.markerNotSpiderfied(marker))) {
	        if (this.state.currentlyClustering) {
	            this.clusteredMarkers.addLayer(marker);
	        } else {
	            marker.addTo(this.leaflet);
	        }
	        this.markers[result.id] = marker;
        }
    },
    

    markerChangeHover: function(result) {
    	
    },
    

    markerChangeSelected: function(result) {
    	
    },
    

    markerUpdate: function(result) {
    	// don't use this trigger when only hover/selected state was changed - they have their own handlers
    	if (result.changedAttributes && (result.changedAttributes.selected || result.changedAttributes.hover)) {
    		util.log('map-view.js: WOWWEEEE! canceled a markerUpdate when selected/hover was changed')
    		return;
    	}
    	util.log('map-view.js: TODO: actually *update* the marker and dont just remove/add it!')
    	if (!result.selected) {
    		this.markerRemove(result);
    		this.markerAdd(result);
    	} else {
    		util.log('map-view.js: TODO:: was ordered to remove a marker that is currently selected. NOT DOING ANYTHING RN!')
    	}
    },
    
    /** Remove a leaflet marker from the map. 
     *  Acts as handler for model Result removal from self.collection */
    markerRemove: function(result) {
    	if (result.id in this.markers) {
    		var marker = this.markers[result.id];
    		
    		if (this.state.currentlyClustering) {
    			this.clusteredMarkers.removeLayer(marker);
    		} else {
    			this.leaflet.removeLayer(marker);
    		}
    		delete this.markers[result.id];
    		util.log('Removed marker at ' + result.get('lat') + ', ' + result.get('lon'));
    	}
    },
    
    
    
    

    // Private
    // -------

    renderMap: function () {
    	util.log('++++++ map-view.js renderMap called! This should only happen once at init! +++++++++++++++++++')
    	
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
        
        this.fitBounds();

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
        _.extend(this.state, {
            south: bounds.getSouth(),
            paddedSouth: paddedBounds.getSouth(),
            west: bounds.getWest(),
            paddedWest: paddedBounds.getWest(),
            north: bounds.getNorth(),
            paddedNorth: paddedBounds.getNorth(),
            east: bounds.getEast(),
            paddedEast: paddedBounds.getEast()
        });
        this.state.zoom = this.leaflet._zoom;
    },

    setClusterState: function () {
    	if (this.options.clusteringEnabled) {
    		// Set clustering state: cluster only when zoomed in enough.
    		var zoom = this.leaflet.getZoom();
    		this.state.currentlyClustering = zoom > this.options.clusterZoomThreshold;
    	}
    },
    
    /** Gets a dict of {iconUrl: <str>, iconWidth: <int>, iconHeight: <int>}
     *  for a given type corresponding to model Result.type. */
    getMarkerIconForType: function(resultType) {
    	var markerIcon;
    	// if custom marker icons are supplied, use those, else default ones
        if (this.options.markerIcons && this.options.markerIcons[resultType]) {
            var iconSettings = this.options.markerIcons[resultType];
            markerIcon = {
        		iconUrl: iconSettings.url,
        		iconWidth: iconSettings.width,
        		iconHeight: iconSettings.height
            };
        } else {
        	markerIcon = {
	            iconUrl: '/static/js/vendor/images/marker-icon-2x-' +
	                this.options.resultColours[resultType] + '.png',
	            iconWidth: 17,
	            iconHeight: 28
        	};
        }
        return markerIcon;
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

    // Event Handlers
    // --------------

    // Render the search results as markers on the map.
    // TODO: remove! deprecated and unused.
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
        Backbone.mediator.publish('app:stale-results', {reason: 'viewport-changed'});
    },

    // Handle change bounds (from URL).
    fitBounds: function () {
    	if (this.leaflet) {
    		util.log('map-view.js: fitBounds called')
    		this.leaflet.fitBounds(L.latLngBounds(
    				L.latLng(this.state.south, this.state.west),
    				L.latLng(this.state.north, this.state.east)
    		));
    	} else {
    		util.log('map-view.js: fitBounds fizzled')
    	}
    },

    handlePopup: function (event) {
        if (event.type === 'popupopen') {
            this.popup = event.popup;
        } else {
            var popLatLng = this.popup.getLatLng();
            var marker = event.popup._source;
            // Remove the popup's marker if it's now off screen.
            /*
            if (!this.leaflet.getBounds().pad(this.options.latLngBuffer).contains(popLatLng)) {
                this.removeMarker(marker);
            }
            */
            this.popup = null;
        }
    },

    handleSpiderfied: function (event) {
        this.state.currentSpiderfied = event.cluster;
    }
});
