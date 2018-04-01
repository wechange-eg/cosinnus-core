'use strict';

// Main application class

var Router = require('router');
var mediator = require('mediator');
var util = require('lib/util.js');

var ControlView = require('views/control-view');
var MapView = require('views/map-view');
var TileListView = require('views/tile-list-view');
var TileDetailView = require('views/tile-detail-view');


var App = function App () {
    self = this;
    
    self.el = null;
    
    // contains all views that can display Results
    self.contentViews = [];
    self.controlView = null;

    self.router = new Router();
    self.mediator = null;
    
    // should have them all here
    self.defaultSettings = {
    	
    };
    
    self.defaulDisplayOptions = {
		showMap: true,
		showTiles: true,
		showControls: true,
		fullscreen: true,
		routeNavigation: true
	};
    self.displayOptions = {}
    

    self.start = function () {
        self.initMediator();
        
        // set default options, these will be used if the page is auto-inited by a route during page load
        // otherwise, an init:app must be published

        // (The first routing will autoinitialize views and model)
        Backbone.mediator.subscribe('navigate:map', self.navigate_map, self);
        Backbone.mediator.subscribe('navigate:router', self.router.on_navigate, self);
        
        // event for manual initialization (non-fullscreen view)
        Backbone.mediator.subscribe('init:app', self.init_app, self);
        Backbone.mediator.subscribe('init:map-standalone', function(){alert('app.js: tried to init map-standalone but found no handlers')}, self);
        Backbone.mediator.subscribe('init:map', function(){alert('app.js: tried to init "map" but this is no longer supported')}, self);
        
        util.log('app.js: init routing')
        
        // Start routing...
        Backbone.history.start({
            pushState: true
        });
        // Use this param for the history if we don't want any default apps
        // on auto start
        // silent: true  // starts without the router listening for a match of the current url
        
        

        var triggerResizeEvent = function (){
        	Backbone.mediator.publish('resize:window');
        }
        var resizeTimer;
        // A global resize event with a delay so it won't fire constantly
        $(window).on('resize', function () {
        	clearTimeout(resizeTimer);
        	resizeTimer = setTimeout(triggerResizeEvent, 500);
        });
        
        // we trigger both on the mediator and on html, in case scripts loaded earlier than this
        // have already subsribed on 'html'
        Backbone.mediator.publish('init:client');
        $('html').trigger('init:client');
        
        util.log('app.js: finish start()')
        return self;
    };

    self.initMediator = function () {
        self.mediator = Backbone.mediator = mediator;
        self.mediator.settings = window.settings || {};
    };
    
    self.navigate_map = function (event) {
    	if (self.controlView == null) {
    		self.init_default_app();
    	} else {
    		Backbone.mediator.publish('app:stale-results', {reason: 'map-navigate'});
    	}
    };
    
    /** Called when the App is auto-initied on a fullscreen page with no further parameters
     *  (triggered by navigation). 
     *  Uses mostly default settings self.defaultSettings and self.defaultDisplay */
    self.init_default_app = function () {
    	// add defaults into params
    	var params = {
    		el: '#app-fullscreen',
    		display: self.defaulDisplayOptions
    	}
    	self.init_app(params);
    };
    
    /** This is called from the event init:app and is used to initialize the non-fullscreen app
     * 	after page load (when no navigation occurs) */
    self.init_app = function (params) {
    	util.log('app.js: init_app called with event, params')
    	
    	/* params contains:
    	 * - el: DOM element
    	 * - settings: JSON config dict
    	 */
    	var settings = params.settings ? JSON.parse(params.settings) : {};
        settings = $.extend(true, {}, self.defaultSettings, settings);
        var display = params.display || {};
        self.displayOptions = $.extend(true, {}, self.defaultDisplayOptions, display);
        
        var topicsHtml = typeof COSINNUS_MAP_TOPICS_HTML !== 'undefined' ? $("<div/>").html(COSINNUS_MAP_TOPICS_HTML).text() : '';
        var markerIcons = typeof COSINNUS_MAP_MARKER_ICONS !== 'undefined' ? COSINNUS_MAP_MARKER_ICONS : {};
        
        // TODO: remove!
        util.log('TODO: at end of refactor remove thisss check for markerIcons and TopicsHtml!')
        if (!topicsHtml) {alert('no topicsHtml!')}
        if (!markerIcons) {alert('no markerIcons!')}
        
        // TODO: set to actual current URL!
        var basePageURL = '/map/';
        
        self.el = params.el;
        
        self.controlView = new ControlView({
	        	elParent: params.el, // TODO put in el in root div!
	        	availableFilters: settings.availableFilters,
	        	activeFilters: settings.activeFilters,
	        	topicsHtml: topicsHtml,
	        	controlsEnabled: self.displayOptions.showControls,
	        	scrollControlsEnabled: self.displayOptions.showControls && self.displayOptions.showMap,
	        	filterGroup: settings.filterGroup,
	        	basePageURL: basePageURL,
	        }, 
	        self, 
	        null
        ); // collection=null here, gets instantiated in the control view
        self.contentViews.push(self.controlView);
        
        util.log('app.js: TODO: really do this if check for controlsEnabled?')
        util.log(self.displayOptions)
        
        if (self.displayOptions.showControls) {
        	util.log('app.js: actually rendering controls')
        	self.controlView.render();
        }
        
        if (self.displayOptions.showMap) {
        	var mapView = new MapView({
        		elParent: params.el,
        		location: settings.location,
        		markerIcons: markerIcons,
        		fullscreen: self.displayOptions.fullscreen,
        		splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles
        	}, 
        	self,
        	self.controlView.collection
        	).render();
        	self.contentViews.push(mapView);
        }
        
        if (self.displayOptions.showTiles) {
        	var tileListView = new TileListView({
        		elParent: params.el,
        		fullscreen: self.displayOptions.fullscreen,
        		splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles
        	}, 
        	self,
        	self.controlView.collection
        	).render();
        	self.contentViews.push(tileListView);
        }
        
        var tileDetailView = new TileDetailView({
        	model: null,
    		elParent: params.el,
    		fullscreen: self.displayOptions.fullscreen,
    		splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles
    	}, 
    	self
    	).render();
        
        
        Backbone.mediator.publish('app:ready');
    };
    
    
    
};

module.exports = App;

$(function () {
	window.App = new App().start();
});