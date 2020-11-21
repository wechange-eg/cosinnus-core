'use strict';

// Main application class

var Router = require('router');
var mediator = require('mediator');
var util = require('lib/util.js');

var ControlView = require('views/control-view');
var MapView = require('views/map-view');
var TileListView = require('views/tile-list-view');
var TileDetailView = require('views/tile-detail-view');
var NavbarQuickSearchView = require('views/navbar/quicksearch-view');
var NavbarMainMenuView = require('views/navbar/main-menu-view');
var NavbarNotificationWidgetView = require('views/navbar/notification-widget-view');
var UserDashboardView = require('views/userdashboard/userdashboard-view');


var App = function App () {
    var self = this;
    
    // emulate a view's anchorpoint
    self.el = null;
    self.$el = null;
    
    // contains all views that can display Results
    self.contentViews = [];
    self.controlView = null;
    self.tileListView = null;
    self.mapView = null;
    self.tileDetailView = null;
    
    // other views
    self.navbarQuickSearchView = null;
    self.navbarMainMenuView = null;
    self.navbarNotificationWidget = null;
    self.userDashboardView = null;

    self.router = null;
    self.mediator = null;
    
    // should have them all here
    self.defaultSettings = {
        // we can't actually define them here, as these get set in controlView.defaults!
    	// see controlView.defaults for all their default values
		/*
		 * filterGroup: <int> if given, filters all content by the given group id
		 * availableFilters: <dict> the shown result filters by type
		 * activeFilters: <dict> the active (selected) current result filters by type
		 * basePageUrl: <str> the eg "/map/" url fragment as base of this page, used to build history URLs 
		 * 		(independent of search endpoint URLs)
		 */
    };
    
    self.defaultDisplayOptions = {
        showMap: true,
        showTiles: true,
        showControls: true,
        fullscreen: true,
        routeNavigation: true,
        forcePaginationControlsEnabled: false
    };
    self.displayOptions = {}
    self.defaultEl = '#app-fullscreen';
    self.defaultBasePageUrl = '/map/';
    
    self.passedOptions = null;
    
    // the most recent complete settings the app was initialized with
    self.settings = null;
    
    
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
        Backbone.mediator.subscribe('init:module-embed', self.initAppFromOptions, self);
        Backbone.mediator.subscribe('init:module-navbar-quicksearch', self.initNavbarQuicksearchFromOptions, self);
        Backbone.mediator.subscribe('init:module-navbar-main-menu', self.initNavbarMainMenuFromOptions, self);
        Backbone.mediator.subscribe('init:module-navbar-notification-widget', self.initNavbarNotificationWidgetFromOptions, self);
        Backbone.mediator.subscribe('init:module-user-dashboard', self.initUserDashboardFromOptions, self);
        
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
    self.initModuleFullRouted = function (options) {
    	self.passedOptions = options;
    	
    	self.router = new Router();
    	
        // (The first routing will autoinitialize views and model in self.navigate_map())
        Backbone.mediator.subscribe('navigate:map', self.navigate_map, self);
        Backbone.mediator.subscribe('navigate:router', self.router.on_navigate, self);
        
        // Start routing... this will automatically call `self.navigate_map()` once
        util.log('app.js: init routing')
        var root = options.basePageUrl || self.defaultBasePageUrl;
        Backbone.history.start({
            pushState: true,
            root: root
        });
    };
    
    /** Called on navigate, from router.js */
    self.navigate_map = function (event) {
    	// this will be called the on the first navigate to the URL, so we use
    	// it to init the app
        if (self.controlView == null) {
            self.initAppFromOptions(self.passedOptions);
        } else {
            Backbone.mediator.publish('app:stale-results', {reason: 'map-navigate'});
        }
    };
    

    /** Inits the app with many or no passed options.
     *  Default settings will be used for any options not passed.
     * 
     *  Many options can be configured for hiding the tile-list, disabling the visual control-view
     *  or enabling only specific Result model types. */
    self.initAppFromOptions = function (options) {
        // add passed options into params extended over the default options
    	var el = options.el ? options.el : self.defaultEl;
        var displayOptions = $.extend(true, {}, self.defaultDisplayOptions, options.display || {});
        var settings = $.extend(true, {}, self.defaultSettings, options.settings || {});
        var basePageUrl = options.basePageUrl || self.defaultBasePageUrl;
        
        self.init_app(el, basePageUrl, settings, displayOptions);
    };
    
    /** Main initialization function, this eventually gets called no matter which modules we load. */
    self.init_app = function (el, basePageUrl, settings, displayOptions) {
        util.log('app.js: init_app called with event, params')
        
        self.el = el;
        self.$el = $(self.el);
        
        self.settings = settings;
        self.displayOptions = displayOptions;
        
        var topicsJson = typeof COSINNUS_MAP_TOPICS_JSON !== 'undefined' ? COSINNUS_MAP_TOPICS_JSON : {};
        var sdgsJson = typeof COSINNUS_MAP_SDGS_JSON !== 'undefined' ? COSINNUS_MAP_SDGS_JSON : {};
        var allManagedTags = typeof COSINNUS_MANAGED_TAGS_JSON !== 'undefined' ? COSINNUS_MANAGED_TAGS_JSON : {};
        var managedTagsLabels = typeof COSINNUS_MANAGED_TAGS_LABELS_JSON !== 'undefined' ? COSINNUS_MANAGED_TAGS_LABELS_JSON : {};
        var portalInfo = typeof COSINNUS_PORTAL_INFOS !== 'undefined' ? COSINNUS_PORTAL_INFOS : {};

        self.controlView = new ControlView({
                el: null, // will only be set if attached to tile-view
                availableFilters: self.settings.availableFilters,
                activeFilters: self.settings.activeFilters,
                allTopics: topicsJson,
                allSDGS: sdgsJson,
                allManagedTags: allManagedTags,
                managedTagsLabels: managedTagsLabels,
                portalInfo: portalInfo,
                controlsEnabled: self.displayOptions.showControls,
                scrollControlsEnabled: self.displayOptions.showControls && self.displayOptions.showMap,
                paginationControlsEnabled: self.displayOptions.forcePaginationControlsEnabled || self.displayOptions.showTiles,
                paginationControlsUseInfiniteScroll: !self.displayOptions.showMap && self.displayOptions.showTiles,
                filterGroup: self.settings.filterGroup,
                basePageURL: basePageUrl,
                showMine: self.settings.showMine,
                fullscreen: self.displayOptions.fullscreen,
                splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles,
                searchResultLimit: self.settings.searchResultLimit || 20,
            }, 
            self, 
            null
        ); // collection=null here, gets instantiated in the control view
        self.contentViews.push(self.controlView);
        
        util.log('app.js: TODO: really do this if check for controlsEnabled?')
        util.log(self.displayOptions)
        
        self.loadMapView();
        self.loadTileView();
        
        self.tileDetailView = new TileDetailView({
	            model: null,
	            elParent: self.el,
	            fullscreen: self.displayOptions.fullscreen,
	            splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles
	        }, 
	        self
        ).render();
        
        Backbone.mediator.publish('app:ready');
    };
    
    /**
     * Loads the map view based on display options
     */
    self.loadMapView = function() {
    	if (self.mapView == null) {
    		// load map from scratch
    		if (self.displayOptions.showMap) {
    			var options = {
    				elParent: self.el,
    				fullscreen: self.displayOptions.fullscreen,
    				splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles,
                    controlsEnabled: self.displayOptions.showControls,
    			};
    			if (self.settings.map && self.settings.map.location) {
    				options['location'] = self.settings.map.location;
    			}
    			if (self.settings.map && self.settings.map.zoom) {
    				options['zoom'] = self.settings.map.zoom;
    			}
    			
    			self.mapView = new MapView(
    				options, 
	    			self,
	    			self.controlView.collection
    			).render();
    			self.contentViews.push(self.mapView);
    		}
        } else {
        	if (self.displayOptions.showMap) {
        		// update settings to show/hide view
        		self.mapView.options.fullscreen = self.displayOptions.fullscreen;
        		self.mapView.options.splitscreen = self.displayOptions.showMap && self.displayOptions.showTiles;
        		self.mapView.reload();
        	} else {
        		// hide map and activate non-in-map-searching
        		self.mapView.hide();
        	}
        }
    };
    
    /**
     * Loads the tile view based on display options
     */
    self.loadTileView = function() {
    	if (self.tileListView == null) {
    		if (self.displayOptions.showTiles) {
    			// load tiles from scratch
    			self.tileListView = new TileListView({
	    				elParent: self.el,
	    				fullscreen: self.displayOptions.fullscreen,
	    				splitscreen: self.displayOptions.showMap && self.displayOptions.showTiles
	    			}, 
	    			self,
	    			self.controlView.collection
    			).render();
    			self.contentViews.push(self.tileListView);
    			
    			// render control-view controls inside tile-list-view
    			if (self.displayOptions.showControls) {
    				util.log('app.js: actually rendering controls')
    				self.controlView.setElement(self.tileListView.$el.find('.controls'));
    				self.controlView.render();
    			}
    		}
        } else {
        	if (self.displayOptions.showTiles) {
        		// update settings to show/hide view
        		self.tileListView.options.fullscreen = self.displayOptions.fullscreen;
        		self.tileListView.options.splitscreen = self.displayOptions.showMap && self.displayOptions.showTiles;
        		self.tileListView.reload();
        	} else {
        		// hide tiles (animate!) but keep search params! 
        		self.tileListView.hide();
        	}
        }
    };
    

    self.initNavbarQuicksearchFromOptions = function (options) {
        // add passed options into params extended over the default options
    	var el = options.el ? options.el : '#nav-quicksearch';
        var topicsJson = typeof COSINNUS_MAP_TOPICS_JSON !== 'undefined' ? COSINNUS_MAP_TOPICS_JSON : {};
        var sdgsJson = typeof COSINNUS_MAP_SDGS_JSON !== 'undefined' ? COSINNUS_MAP_SDGS_JSON : {};
        var portalInfo = typeof COSINNUS_PORTAL_INFOS !== 'undefined' ? COSINNUS_PORTAL_INFOS : {};
        
        if (self.navbarQuickSearchView == null) {
        	self.navbarQuickSearchView = new NavbarQuickSearchView({
        		model: null,
        		el: el,
        		topicsJson: topicsJson,
                sdgsJson: sdgsJson,
        		portalInfo: portalInfo,
        	}, 
        	self
        	).render();
        	Backbone.mediator.publish('navbar-quicksearch:ready');
        }
    };
    
    
    self.initNavbarMainMenuFromOptions = function (options) {
        // add passed options into params extended over the default options
        var el = options.el ? options.el : '#nav-main-menu';
        var topicsJson = typeof COSINNUS_MAP_TOPICS_JSON !== 'undefined' ? COSINNUS_MAP_TOPICS_JSON : {};
        var sdgsJson = typeof COSINNUS_MAP_SDGS_JSON !== 'undefined' ? COSINNUS_MAP_SDGS_JSON : {};
        var portalInfo = typeof COSINNUS_PORTAL_INFOS !== 'undefined' ? COSINNUS_PORTAL_INFOS : {};
        var contextData = options.contextData ? options.contextData : {};
        var contextDataJSON = options.contextDataJSON ? options.contextDataJSON : {};
        
        if (self.navbarMainMenuView == null) {
            self.navbarMainMenuView = new NavbarMainMenuView({
                model: null,
                el: el,
                contextData: contextData,
                contextDataJSON: contextDataJSON,
                topicsJson: topicsJson,
                sdgsJson: sdgsJson,
                portalInfo: portalInfo,
            }, 
            self
            ).render();
            Backbone.mediator.publish('navbar-main-manu:ready');
        }
    };
    
    self.initNavbarNotificationWidgetFromOptions = function (options) {
        // add passed options into params extended over the default options
        var el = options.el ? options.el : '#nav-notification-items';
        
        if (self.navbarNotificationWidgetView == null) {
            //        elParent: self.$el.find('.typed-widgets-root'),
            self.navbarNotificationWidgetView = new NavbarNotificationWidgetView({
                el: el,
            }, self.app);
            self.navbarNotificationWidgetView.load().then(function(){
                Backbone.mediator.publish('navbar-notification-widget:ready');
                util.log('# #### loaded notification widget.')
            });
        }
    };

    self.initUserDashboardFromOptions = function (options) {
        // add passed options into params extended over the default options
        var topicsJson = typeof COSINNUS_MAP_TOPICS_JSON !== 'undefined' ? COSINNUS_MAP_TOPICS_JSON : {};
        var sdgsJson = typeof COSINNUS_MAP_SDGS_JSON !== 'undefined' ? COSINNUS_MAP_SDGS_JSON : {};
        var portalInfo = typeof COSINNUS_PORTAL_INFOS !== 'undefined' ? COSINNUS_PORTAL_INFOS : {};
        
        if (self.userDashboardView == null) {
        	self.userDashboardView = new UserDashboardView({
        		model: null,
        		el: null,
        		topicsJson: topicsJson,
                sdgsJson: sdgsJson,
        		portalInfo: portalInfo,
        		uiPrefs: options.ui_prefs,
        		forceOnlyMine: options.force_only_mine,
        	}, 
        	self
        	).render();
        	Backbone.mediator.publish('user-dashboard:ready');
        }
    };
    
    
    
};

module.exports = App;

$(function () {
    window.App = new App().start();
});
