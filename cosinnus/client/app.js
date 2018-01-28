'use strict';

// Main application class

var Router = require('router');
var mediator = require('mediator');

var Map = require('models/map');
var MapView = require('views/map-view');


var App = function App () {
    self = this;
    
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
		fullscreen: true
	};
    self.displayOptions = {}
    

    self.start = function () {
        self.initMediator();
        
        // set default options, these will be used if the page is auto-inited by a route during page load
        // otherwise, an init:app must be published

        // (The first routing will autoinitialize views and model)
        Backbone.mediator.subscribe('navigate:map', self.navigate_map);
        // event for manual initialization (non-fullscreen view)
        Backbone.mediator.subscribe('init:map', self.init_app);
        
        console.log('app.js: init routing')
        // Start routing...
        Backbone.history.start({
            pushState: true
        });
        // A global resize event
        $(window).on('resize', function () {
            Backbone.mediator.publish('resize:window');
        });
        
        
        Backbone.mediator.publish('init:client');
        
        console.log('app.js: finish start()')
        return self;
    };

    self.initMediator = function () {
        self.mediator = Backbone.mediator = mediator;
        self.mediator.settings = window.settings || {};
        self.mediator.subscribe('navigate:router', function (event, url) {
            if (url) {
                self.router.navigate(url, {
                    trigger: false
                });
            }
        });
    };
    
    self.navigate_map = function (event) {
    	if (self.controlView.length == 0) {
    		self.auto_init_app();
    	}
    	self.initialSearch();
    	
    };
    
    /** Called when the App is auto-initied on a fullscreen page with no further parameters
     *  (triggered by navigation). 
     *  Uses mostly default settings self.defaultSettings and self.defaultDisplay */
    self.auto_init_app = function () {
    	// add defaults into params
    	var params = {
    		el: '#map-fullscreen',
    	}
    	self.init_app(null, params);
    };
    
    /** This is called from the event init:app and is used to initialize the non-fullscreen app
     * 	after page load (when no navigation occurs) */
    self.init_app = function (event, params) {
    	console.log('app.js: init_map called')
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
        console.log('TODO: at end of refactor remove thisss check for markerIcons and TopicsHtml!')
        if (!topicsHtml) {alert('no topicsHtml!')}
        if (!markerIcons) {alert('no markerIcons!')}
        
        
        /** TODO next: 
         * - depending on display-settings: load each view
         * - remove Map model, put most of it into controlView and MapView
         * - refactor these settings and params and data into sensible different variables! */
        var map = new Map({}, {
        });

        if (self.displayOptions.showControls) {
            self.controlsView = new MapControlsView({
                el: self.$el.find('.map-controls'), // TODO put in el in root div!
                availableFilters: settings.availableFilters,
                activeFilters: settings.activeFilters,
                topicsHtml: topicsHtml,
                controlsEnabled: self.displayOptions.showControls,
                filterGroup: settings.filterGroup,
            }).render();
            self.controlsView.on('change:layer', self.handleSwitchLayer, self);
        }

        new MapView({
            el: params.el,
            model: map,
            location: settings.location,
            markerIcons: markerIcons
        }).render();
    };
    
    
    
};

module.exports = App;

$(function () {
	window.App = new App().start();
});