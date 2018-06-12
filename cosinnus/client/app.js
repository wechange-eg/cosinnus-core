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
    
    // emulate a view's anchorpoint
    self.el = null;
    self.$el = null;
    
    // contains all views that can display Results
    self.contentViews = [];
    self.controlView = null;
    self.tileListView = null;
    self.mapView = null;

    self.router = new Router();
    self.mediator = null;
    
    // should have them all here
    self.defaultSettings = {
        // we can't actually define them here, as these get set in controlView.defaults!
    	// see controlView.defaults for all their default values
		/*
		 * filterGroup: <int> if given, filters all content by the given group id
		 * availableFilters: <dict> the shown result filters by type
		 * activeFilters: <dict> the active (selected) current result filters by type
		 */
    };
    
    self.defaulDisplayOptions = {
        showMap: true,
        showTiles: true,
        showControls: true,
        fullscreen: true,
        routeNavigation: true
    };
    self.displayOptions = {}
    
    /** Main entry point */
    self.start = function () {
        self.mediator = Backbone.mediator = mediator;
        self.mediator.settings = window.settings || {};
        
        var triggerResizeEvent = function (){
            Backbone.mediator.publish('resize:window');
        }
        var resizeTimer;
        // A global resize event with a delay so it won't fire constantly
        $(window).on('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(triggerResizeEvent, 500);
        });
        
        // init-module calls. inside a listener to the 'init:client' event,
        // one of these need to be called from the template to initialize the required modules
        Backbone.mediator.subscribe('init:module-full-routed', self.initModuleFullRouted, self);
        Backbone.mediator.subscribe('init:module-embed', self.initModuleEmbed, self);
        
        // - the 'init:client' signal is the marker for all pages using this client.js to now
        //      publish the "init:<module>" event for whichever module configuration they wish to load (see above)
        util.log('app.js: finish start() and publishing "init:client"')
        Backbone.mediator.publish('init:client');
        // we trigger both on the mediator and on html, in case scripts loaded earlier than this have already subsribed on 'html'
        $('html').trigger('init:client');
        
        return self;
    };
    
    /** Module configuration for a fullscreen App with full control of the page, that uses routing and history.
     *  This module uses the full set of default options and gets passed no options */
    self.initModuleFullRouted = function () {
        // (The first routing will autoinitialize views and model)
        Backbone.mediator.subscribe('navigate:map', self.navigate_map, self);
        Backbone.mediator.subscribe('navigate:router', self.router.on_navigate, self);
        
        // Start routing... this will automatically call `self.navigate_map()` once
        util.log('app.js: init routing')
        Backbone.history.start({
            pushState: true
        });
    };
    
    /** Module configuration for an embeddable App (in a widget or iframe).
     *  Many options can be configured for hiding the tile-list, disabling the visual control-view
     *  or enabling only specific Result model types. */
    self.initModuleEmbed = function (options) {
        // add passed options into params
        var params = {
            el: options.el,
            display: options.display,
            settings: options.settings,
        }
        self.init_app(params);
    };
    
    /** Called on navigate, from router.js */
    self.navigate_map = function (event) {
        if (self.controlView == null) {
            self.init_default_app();
        } else {
            Backbone.mediator.publish('app:stale-results', {reason: 'map-navigate'});
        }
    };
    
    /** Called when the App is auto-initied on a fullscreen page with no further parameters. 
     *  Uses mostly default settings self.defaultSettings and self.defaultDisplay */
    self.init_default_app = function () {
        // add defaults into params
        var params = {
            el: '#app-fullscreen',
            display: self.defaulDisplayOptions
        }
        self.init_app(params);
    };
    
    /** Main initialization function, this eventually gets called no matter which modules we load. */
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
        
        var topicsJson = typeof COSINNUS_MAP_TOPICS_JSON !== 'undefined' ? COSINNUS_MAP_TOPICS_JSON : {};
        var portalInfo = typeof COSINNUS_PORTAL_INFOS !== 'undefined' ? COSINNUS_PORTAL_INFOS : {};
        var markerIcons = typeof COSINNUS_MAP_MARKER_ICONS !== 'undefined' ? COSINNUS_MAP_MARKER_ICONS : {};
        
        // TODO: remove!
        util.log('TODO: at end of refactor remove thisss check for markerIcons and topicsJson!')
        if (!topicsJson) {alert('no topicsJson!')}
        if (!portalInfo) {alert('no topicsJson!')}
        if (!markerIcons) {alert('no markerIcons!')}
        
        // TODO: set to actual dynamic current URL!
        var basePageURL = '/map/';
        
        self.el = params.el;
        self.$el = $(self.el);
        
        self.controlView = new ControlView({
                el: null, // will only be set if attached to tile-view
                availableFilters: settings.availableFilters,
                activeFilters: settings.activeFilters,
                allTopics: topicsJson,
                portalInfo: portalInfo,
                controlsEnabled: self.displayOptions.showControls,
                scrollControlsEnabled: self.displayOptions.showControls && self.displayOptions.showMap,
                paginationControlsEnabled: self.displayOptions.showTiles,
                filterGroup: settings.filterGroup,
                basePageURL: basePageURL,
            }, 
            self, 
            null
        ); // collection=null here, gets instantiated in the control view
        self.contentViews.push(self.controlView);
        
        util.log('app.js: TODO: really do this if check for controlsEnabled?')
        util.log(self.displayOptions)
        
        
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
            self.mapView = mapView;
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
            self.tileListView = tileListView;
            
            // render control-view controls inside tile-list-view
            if (self.displayOptions.showControls) {
                util.log('app.js: actually rendering controls')
                self.controlView.setElement(tileListView.$el.find('.controls'));
                self.controlView.render();
            }
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
