'use strict';

var ContentControlView = require('views/base/content-control-view');
var MapLayerButtonsView = require('views/map-layer-buttons-view');
var popupTemplate = require('map/popup');
var util = require('lib/util');

module.exports = ContentControlView.extend({

    template: require('map/map'),
    
    // The DOM events specific to an item.
    events: {
        'click .map-expand-button': 'onExpandButtonClicked',
    },
    
    layers: {
        street: {
            url: (util.protocol() === 'http:' ?
                'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png' :
                'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png'),
            options: {
                attribution: 'CartoDB'
            }
        },
    },
    
    // path to a geojson file in static folder containing regions that should be outlined on the map
    // You can configure a geojson region here: http://opendatalab.de/projects/geojson-utilities/ 
    geoRegionUrl: util.ifundef(COSINNUS_MAP_OPTIONS.geojson_region, null), 

    
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
    
    // if not null, this is an active, draggable marker
    draggableMarker: null,
    
    // will be set to self.options during initialization
    defaults: {
        // is the window in full-screen mode (instead of inside a widget or similar)
        fullscreen: true,
        
        // is this view shown together with the map view as a 50% split screen?
        splitscreen: false,
        
        // will a popup be shown when a map marker is clicked?
        enablePopup: false,
        
        // will clicking on a marker cause its result to be selected?
        enableDetailSelection: true,
        
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
        
        // the amount of decimals to round all coordinates to
        latLngRoundToDecimals: 5,
        
        resultMarkerSizes: {
            width: 14,
            height: 14,
            widthLarge: 28,
            heightLarge: 37,
            widthStacked: 23,
            heightStacked: 23,
            widthBase: 28,
            heightBase: 37,
        },
        
        // calculated dynamically depending on zoom, in `handleViewportChange()`
        resultMarkerClusterDistance: {
            x: 0,
            y: 0,
            perZoom: 0, // hardcoded function of px per zoom level, if you want to offset in px for current zoom
        },
        
        MARKER_NUMBER_OF_LARGE_MARKERS: 8, // this many of the most relevant results become large markers
        
        MARKER_CLUSTER_RADIUS_LIMIT: 0.85, // cluster radius multiplier: modifier for how aggressively the clusters should pull in markers
        MARKER_STACK_PX_OFFSET_PER_CLUSTER_LEVEL: 12, // offset in px for clustered stack-makers per level
        MARKER_STACK_PX_OFFSET_BASE: 8, // additional offset in px of first clustered stack-marker (level 1) from the base marker

        // if location is set to a location pair at initialization,
        // the `COSINNUS_MAP_OPTIONS.default_coordinates` will be ignored and the
        // set `location` is used with the zoom setting instead!
        location: [], // [52.5233, 13.4138],
        zoom: 7,
        
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
            north: util.ifundef(COSINNUS_MAP_OPTIONS.default_coordinates.ne_lat, 55.78), 
            east: util.ifundef(COSINNUS_MAP_OPTIONS.default_coordinates.ne_lon, 23.02),
            south: util.ifundef(COSINNUS_MAP_OPTIONS.default_coordinates.sw_lat, 49.00),
            west: util.ifundef(COSINNUS_MAP_OPTIONS.default_coordinates.sw_lon, 3.80),
        }
    },
    
    initialize: function (options, app, collection) {
        var self = this;
        // this calls self.applyUrlSearchParameters()
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
           'change:hovered': self.thisContext(self.markerChangeHovered),
           'change:selected': self.thisContext(self.markerChangeSelected),
           'change': self.thisContext(self.markerUpdate),
           'remove': self.thisContext(self.markerRemove),
           'reset': self.thisContext(self.markersReset),
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
        if (self.mapLayerButtonsView == null) {
        	self.mapLayerButtonsView = new MapLayerButtonsView({
        		el: self.$el.find('.map-layers-buttons'),
        		layer: self.options.layer,
        		mapView: self
        	}).render();
        } else {
        	self.mapLayerButtonsView.render();
        }
    },
    
    // extended from content-control-view.js
    applyUrlSearchParameters: function (urlParams) {
        util.log('map-view.js: url params on init: ')
        util.log(urlParams)
        _.extend(this.state, {
            north: util.ifundef(urlParams.ne_lat, this.state.north),
            east: util.ifundef(urlParams.ne_lon, this.state.east),
            south: util.ifundef(urlParams.sw_lat, this.state.south),
            west: util.ifundef(urlParams.sw_lon, this.state.west),
        });
        this.fitBounds();
        this.updateBounds();
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
    
    /**
     * 
     * @param result: Result model
     * @param isLargeMarker: (optional) bool. make this marker icon large?
     * @param clusterLevel: (optional) int. if supplied, the result is considered in a cluster, at this rank. 0 means base cluster-marker
     * @param clusterCoords: (optional) {lat: int, lon: int} if result is in a cluster, the coords (rank will be added as offset)
     */
    markerAdd: function(result, isLargeMarker, clusterLevel, clusterCoords) {
        var self = this;
        
        if (!result.get('lat') || !result.get('lon')) {
            // if the result has no location, the map cannot handle it. 
            util.log('Cancelled adding a marker for a result with no location.')
            return;
        }
        
        // adding a marker that is already there? impossibru! but best be sure.
        if (result.id in this.markers) {
            this.markerRemove(result);
        }
        
        // for clustered markers, every marker but the base marker becomes a stacked marker.
        var markerIcon = this.getMarkerIconForType(result.get('type'), isLargeMarker, clusterLevel > 0, clusterLevel == 0);
        var coords = clusterCoords ? clusterCoords : [result.get('lat'), result.get('lon')];
        var isPointedMarker = isLargeMarker || typeof clusterLevel !== 'undefined' || clusterLevel == 0;
        var clusterOffset = 0;
        
        // add clusterLevel as offset
        if (typeof clusterLevel !== 'undefined' && clusterLevel > 0) {
            clusterOffset = this.options.MARKER_STACK_PX_OFFSET_BASE + (this.options.MARKER_STACK_PX_OFFSET_PER_CLUSTER_LEVEL * clusterLevel);
        }
        //util.log('adding marker at coords ' + JSON.stringify(coords))
        
        var marker = L.marker(coords, {
            icon: L.divIcon({
                iconSize: [markerIcon.iconWidth, markerIcon.iconHeight],
                iconAnchor: [markerIcon.iconWidth / 2, (markerIcon.iconHeight / (isPointedMarker ? 1 : 2)) + clusterOffset],
                className: markerIcon.className + (result.get('selected') ? ' marker-selected' : ''),
//                popupAnchor: [1, -27],
            }),
            zIndexOffset: clusterLevel ? (1000 + (100*clusterLevel)) : null,
            riseOnHover: false
        });

        
        // bind click/hover events 
        if (this.options.enablePopup) {
            marker.bindPopup(popupTemplate.render({
                imageURL: result.get('imageUrl'),
                title: result.get('title'),
                url: result.get('url'),
                address: result.get('address'),
                description: result.get('description')
            }));
        } 
        if (this.options.enableDetailSelection) {
            marker.on('click', function(){
                self.App.controlView.onResultLinkClicked(null, result.id);
            });
        }
        marker.on('mouseover', function(){
            self.App.controlView.setHoveredResult(result);
        });
        marker.on('mouseout', function(){
            self.App.controlView.setHoveredResult(null);
        });
        
        
        if (!this.options.keepOpenMarkersAfterResultChange || (this.markerNotPopup(marker) && this.markerNotSpiderfied(marker))) {
            if (this.state.currentlyClustering) {
                this.clusteredMarkers.addLayer(marker);
            } else {
                marker.addTo(this.leaflet);
            }
            this.markers[result.id] = marker;
        }
    },
    
    markerChangeHovered: function(result) {
        if (result.id in this.markers) {
            var marker = this.markers[result.id];
            $(marker._icon).toggleClass('marker-hovered', result.get('hovered'));
        }
    },
    

    markerChangeSelected: function(result) {
        if (result.id in this.markers) {
            var marker = this.markers[result.id];
            $(marker._icon).toggleClass('marker-selected', result.get('selected'));
        }
    },
    
    /**
     * On marker update. This happens extremely infrequently, as on new searches the whole
     * result collections gets exchanged (which triggers `markersReset()`)
     */
    markerUpdate: function(result, what) {
        // don't use this trigger when only hovered/selected state was changed! - they have their own handlers
        var attrs = result.changedAttributes();
        if (attrs && ('selected' in attrs || 'hovered' in attrs)) {
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
            //util.log('Removed marker at ' + result.get('lat') + ', ' + result.get('lon'));
        }
    },
    
    /** Handler for when the entire collection changes */
    markersReset: function(resultCollection, options) {
        var self = this;
        _.each(options.previousModels, function(result){
            self.markerRemove(result);
        });
        
        /**
         * Cluster results by maximum radius
         * [
         *        { // cluster
         *            loc: {lat: 0, lon: 0},
         *         items: [ <result>, ...]
         *        },
         *        ...
         * ]
         */
        
        var clusters = [];
        //_.each(resultCollection.models, function(result){
        for (var i=0; i < resultCollection.models.length; i++) {
            var result = resultCollection.models[i];
            if (!result.get('lat') || !result.get('lon')) {
                // results without locations are ignored
                continue;
            }
            
            //_.each(resultCollection.models, function(cluster){
            for (var j=0; j < clusters.length; j++) {
                var cluster = clusters[j];
                // calculate distance from this result to each cluster
                var distx = Math.abs(cluster['loc']['lon'] - result.get('lon'));
                var disty = Math.abs(cluster['loc']['lat'] - result.get('lat'));
                if (distx < self.options.resultMarkerClusterDistance['x'] && disty < self.options.resultMarkerClusterDistance['y']) {
                    // result lies within radius of cluster
                    cluster['items'].push(result);
                    result = null;
                    break;
                } 
            };
            // result didn't lie within radius of cluster, make a new one
            if (result != null) {
                clusters.push({
                    loc: {
                        lat: result.get('lat'),
                        lon: result.get('lon')
                    },
                    items: [result]
                });
            }
        };
        
        // remove all single-result clusters and add their results into a single list
        var singleResults = [];
        for (var k=clusters.length-1; k >= 0; k--) {
            var cluster = clusters[k];
            if (cluster['items'].length == 1) {
                singleResults.push(cluster['items'][0]);
                clusters.splice(k, 1);
            } else {
                // sort the items inside a cluster, most important last (highest in stack)
                cluster['items'].sort(function(a, b) {
                    return a.get('relevance') - b.get('relevance');
                });
            }
        }
        
        // all cluster bases are large markers
        var remainingLargeMarkers = self.options.MARKER_NUMBER_OF_LARGE_MARKERS;
        for (var i=0; i < clusters.length; i++) {
            var cluster = clusters[i];
            // for each cluster, add all results in a stacking offset
            for (var j=cluster['items'].length-1; j >= 0; j--) {
                var item = cluster['items'][j];
                self.markerAdd(item, false, j, cluster['loc']);
            }
            remainingLargeMarkers -= 1;
        }
        
        // sort (by relevance) and add the results that aren't in a cluster
        singleResults.sort(function(a, b) {
            return b.get('relevance') - a.get('relevance');
        });
        _.each(singleResults, function(result){
            if (remainingLargeMarkers > 0) {
                self.markerAdd(result, true);
                remainingLargeMarkers -= 1;
            } else {
                self.markerAdd(result);
            }
        });
    },
    
    /** Activates the Map-Marker-Place mode where a draggable marker is shown
     * in the center of the map and all other markers are hidden. */
    activateDraggableMarker: function (resultType) {
    	var self = this;
    	// hide all other markers
    	$('.leaflet-marker-pane').addClass('marker-place-mode');
    	var width = this.options.resultMarkerSizes['widthLarge'];
    	var height = this.options.resultMarkerSizes['heightLarge']
    	
    	this.draggableMarker = L.marker(this.leaflet.getCenter(), {
            icon: L.divIcon({
                iconSize: [width, this.options.resultMarkerSizes['heightLarge']],
                iconAnchor: [width / 2, height],
                className: 'draggable-placemark placemark l icon ' + resultType,
            }),
            riseOnHover: false,
            draggable: true,
            keyboard: false
        });
    	this.draggableMarker.on("dragend", function(e) {
    	    var marker = e.target;
    	    self.leaflet.panTo(marker.getLatLng());
    	});
    	this.draggableMarker.addTo(this.leaflet);
    },
    
    /** Deactivates the Map-Marker-Place mode. */
    deactivateDraggableMarker: function () {
    	this.leaflet.removeLayer(this.draggableMarker);
    	this.draggableMarker = null;
    	// show other markers again
    	$('.leaflet-marker-pane').removeClass('marker-place-mode');
    },
    
    /** If the Map-Marker-Place mode is active, return the LatLng object of
     *  the draggable marker, else return null. */
    getDraggableMarkerLatLng: function () {
    	if (this.draggableMarker) {
    		return this.draggableMarker.getLatLng();
    	} else {
    		return null;
    	}
    },
    

    /**
     * Called when the expand button is clicked for expanding or contracting
     * the map (splitscreen vs maximized).
     */
    onExpandButtonClicked: function (event) {
    	this.App.controlView.switchDisplayState(true, !this.options.splitscreen);
    },
    
    
    /** Shows and reloads the map with current settings */
    reload: function () {
    	util.log('*** Reloading Map View ***')
        this.$el.toggleClass('map-splitscreen', this.options.splitscreen);
    	this.$el.show();
        Backbone.mediator.publish('resize:window');
    },
    
    /** Hides the map */
    hide: function () {
    	util.log('*** Hiding Map View ***')
    	this.$el.hide();
    },

    // Private
    // -------

    renderMap: function () {
        var self = this;
        
        util.log('++++++ map-view.js renderMap called! This should only happen once at init! +++++++++++++++++++')
        
        this.leaflet = L.map('map-container');
        this.setLayer(this.options.layer);
        
        if (self.geoRegionUrl) {
            $.ajax({
                dataType: "json",
                url: self.geoRegionUrl,
                success: function(data) {
                    // style see https://leafletjs.com/reference-1.3.0.html#path-option
                    var district_boundary = new L.geoJson(null, {
                        style: function (feature) {
                            return util.ifundef(COSINNUS_MAP_OPTIONS.geojson_style, {
                                width: 1,
                                weight: 0.5,
                                fillOpacity: 0.035,
                            });
                        }
                    });
                    district_boundary.addTo(self.leaflet);
                    $(data.features).each(function(key, data) {
                        district_boundary.addData(data);
                    });
                }
            }).error(function() {});
            
        }
        
        
        if (this.options.clusteringEnabled) {
            // Setup the cluster layer
            this.clusteredMarkers = L.markerClusterGroup({
                maxClusterRadius: this.options.maxClusterRadius
            });
            this.clusteredMarkers.on('spiderfied', this.handleSpiderfied, this);
            this.leaflet.addLayer(this.clusteredMarkers);
            this.setClusterState();
        }
        
        // if an initial location was defined, set that location and zoom as initial viewport
        // otherwise, use fitBounds to adjust the viewport to the one 
        // defined in `state` with `COSINNUS_MAP_OPTIONS.default_coordinates.ne_lat`
        if (this.options.location && this.options.location.length == 2) {
        	this.leaflet.setView(this.options.location, this.options.zoom);
        } else {
        	this.fitBounds();
        }
        this.updateClusterDistances();

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
            south: L.Util.formatNum(bounds.getSouth(), this.options.latLngRoundToDecimals),
            paddedSouth: L.Util.formatNum(paddedBounds.getSouth(), this.options.latLngRoundToDecimals),
            west: L.Util.formatNum(bounds.getWest(), this.options.latLngRoundToDecimals),
            paddedWest: L.Util.formatNum(paddedBounds.getWest(), this.options.latLngRoundToDecimals),
            north: L.Util.formatNum(bounds.getNorth(), this.options.latLngRoundToDecimals),
            paddedNorth: L.Util.formatNum(paddedBounds.getNorth(), this.options.latLngRoundToDecimals),
            east: L.Util.formatNum(bounds.getEast(), this.options.latLngRoundToDecimals),
            paddedEast: L.Util.formatNum(paddedBounds.getEast(), this.options.latLngRoundToDecimals)
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
    getMarkerIconForType: function(resultType, isLargeMarker, isStackedMarker, isBaseMarker) {
        var markerIcon;
        var suffix = '';
        var className = 'placemark';
        
        if (isBaseMarker) {
            suffix = 'Base';
            className += ' l';
        } else if (isStackedMarker) {
            suffix = 'Stacked';
            className += ' m';
        } else if (isLargeMarker) {
            suffix = 'Large';
            className += ' l icon';
        } else {
            className += ' s';
        }
        // type of the marker
        className += ' ' + resultType;
        
        markerIcon = {
            iconWidth: this.options.resultMarkerSizes['width' + suffix],
            iconHeight: this.options.resultMarkerSizes['height' + suffix],
            className: className
        };
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
    /*
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
    */

    handleViewportChange: function () {
        this.setClusterState();
        this.updateBounds();
        this.updateClusterDistances();
        Backbone.mediator.publish('app:stale-results', {reason: 'viewport-changed'});
    },
    
    /** Recalculate clustering distances based on current map area and zoom */
    updateClusterDistances: function () {
        var ns = Math.abs(this.state.south - this.state.north) / this.$el.height();
        var we = Math.abs(this.state.east - this.state.west) / this.$el.width();
        this.options.resultMarkerClusterDistance['x'] = we * this.options.resultMarkerSizes['widthLarge'] * this.options.MARKER_CLUSTER_RADIUS_LIMIT;
        this.options.resultMarkerClusterDistance['y'] = ns * this.options.resultMarkerSizes['heightLarge'] * this.options.MARKER_CLUSTER_RADIUS_LIMIT;
        this.options.resultMarkerClusterDistance['perZoom'] = 1 / (Math.pow(2, this.leaflet.getZoom()));
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
