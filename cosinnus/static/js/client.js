/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;
/******/
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	// Main JavaScript file — main entry for webpack
	
	'use strict';
	
	var Application = __webpack_require__(1);
	
	$(function () {
	    new Application().start();
	});


/***/ },
/* 1 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';
	
	// Main application class
	
	var Router = __webpack_require__(2);
	var mediator = __webpack_require__(15);
	
	module.exports = function Application () {
	    self = this;
	
	    self.router = new Router();
	
	    self.start = function () {
	        self.initMediator();
	        // Start routing...
	        Backbone.history.start({
	            pushState: true
	        });
	        // A global resize event
	        $(window).on('resize', function () {
	            Backbone.mediator.publish('resize:window');
	        });
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
	};


/***/ },
/* 2 */
/***/ function(module, exports, __webpack_require__) {

	'use strict'
	
	var Map = __webpack_require__(3);
	var MapView = __webpack_require__(4);
	
	module.exports = Backbone.Router.extend({
	    routes: {
	        'map/': 'map'
	    },
	
	    map: function () {
	        // If the map view hasn't been instantiated, create and render it.
	        if (!this.mapFullscreen) {
	            this.mapFullscreen = new Map();
	            var view = new MapView({
	                el: '#map-fullscreen',
	                model: this.mapFullscreen
	            });
	            view.render();
	        // Otherwise navigation has occurred between map states.
	        } else {
	            Backbone.mediator.publish('navigate:map');
	        }
	    }
	});


/***/ },
/* 3 */
/***/ function(module, exports) {

	'use strict';
	
	module.exports = Backbone.Model.extend({
	    default: {
	        filters: {
	            people: true,
	            events: true,
	            projects: true,
	            groups: true
	        },
	        layer: 'street'
	    },
	
	    initialize: function () {
	        var self = this;
	        self.set('filters', _(self.default.filters).clone());
	        self.set('layer', self.default.layer);
	        self.searchDelay = 1000,
	        self.whileSearchingDelay = 5000;
	        Backbone.mediator.subscribe('navigate:map', function () {
	            self.initialSearch();
	        });
	    },
	
	    search: function () {
	        var self = this;
	        var url = this.buildURL();
	        self.set('searching', true);
	        $.get(url, function (res) {
	            self.set('searching', false);
	            self.trigger('end:search');
	            // (The search endpoint is single-thread).
	            // If there is a queued search, requeue it.
	            if (self.get('wantsToSearch')) {
	                self.attemptSearch();
	            // Update the results if there isn't a queued search.
	            } else {
	                self.set('results', res);
	                self.trigger('change:results');
	                // Save the search state in the url.
	                Backbone.mediator.publish('navigate:router', url.replace('/maps/search', '/map/'))
	            }
	        }).fail(function () {
	            self.set('searching', false);
	            self.trigger('end:search');
	            self.trigger('error:search');
	        });
	    },
	
	    initialSearch: function () {
	        var json = this.parseUrl(window.location.href.replace(window.location.origin, ''));
	        if (_(json).keys().length) {
	            this.set({
	                filters: {
	                    people: json.people,
	                    events: json.events,
	                    projects: json.projects,
	                    groups: json.groups
	                },
	                q: json.q,
	                north: json.ne_lat,
	                east: json.ne_lon,
	                south: json.sw_lat,
	                west: json.sw_lon
	            });
	            this.trigger('change:bounds');
	            this.trigger('change:controls');
	        }
	        this.search();
	    },
	
	    buildURL: function () {
	        var searchParams = {
	            q: this.get('q'),
	            ne_lat: this.get('north'),
	            ne_lon: this.get('east'),
	            sw_lat: this.get('south'),
	            sw_lon: this.get('west'),
	            people: this.get('filters').people,
	            events: this.get('filters').events,
	            projects: this.get('filters').projects,
	            groups: this.get('filters').groups
	        };
	        var query = $.param(searchParams);
	        return '/maps/search?' + query;
	    },
	
	    toggleFilter (resultType) {
	        var filters = this.get('filters');
	        filters[resultType] = !filters[resultType];
	        this.set('filters', filters);
	        this.attemptSearch();
	    },
	
	    resetFilters: function () {
	        this.set('filters', _(this.default.filters).clone());
	        this.attemptSearch();
	    },
	
	    // Register a change in the controls or the map UI which should queue
	    // a search attempt.
	    attemptSearch: function () {
	        var self = this,
	            // Increase the search delay when a search is in progress.
	            delay = self.get('searching') ?
	                self.whileSearchingDelay : self.searchDelay;
	        clearTimeout(this.searchTimeout);
	        self.set('wantsToSearch', true);
	        self.trigger('want:search');
	        self.searchTimeout = setTimeout(function () {
	            self.search();
	            self.set('wantsToSearch', false);
	        }, delay);
	    },
	
	    parseUrl: function (url) {
	        if (url.indexOf('?') >= 0) {
	            var json = JSON.parse('{"' + decodeURI(url.replace(/[^?]*\?/, '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
	        } else {
	            var json = {};
	        }
	        _(_(json).keys()).each(function (key) {
	            if (json[key] !== '') {
	                try {
	                    json[key] = JSON.parse(json[key]);
	                } catch (err) {}
	            }
	        });
	        return json;
	    },
	
	    activeFilters: function () {
	        return _(_(this.get('filters')).keys()).select(function (filter) {
	            return !!filter;
	        });
	    }
	});


/***/ },
/* 4 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';
	
	var View = __webpack_require__(5);
	var MapControlsView = __webpack_require__(6);
	var popupTemplate = __webpack_require__(13);
	var util = __webpack_require__(14);
	
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
	    },
	
	    // Handle change bounds (from URL).
	    fitBounds: function () {
	        this.leaflet.fitBounds(L.latLngBounds(
	            L.latLng(this.model.get('south'), this.model.get('west')),
	            L.latLng(this.model.get('north'), this.model.get('east'))
	        ));
	    },
	});


/***/ },
/* 5 */
/***/ function(module, exports) {

	'use strict';
	
	module.exports = Backbone.View.extend({
	    initialize: function (options) {
	        this.state = options && options.state || {};
	    },
	
	    render: function () {
	        var self = this;
	        // Collect the data to be rendered; can be overridden in child view.
	        var data = this.getTemplateData();
	        // Use nunjucks to render the template (specified in child view).
	        if (this.template && this.template.render &&
	            typeof this.template.render === 'function') {
	            this.$el.html(this.template.render(data));
	        }
	        // After a repaint (to allow further rendering in #afterRender),
	        // call the after render method if it exists.
	        setTimeout(function () {
	            self.afterRender && self.afterRender();
	        }, 0);
	        return this;
	    },
	
	    // Default implementation to retrieve data to be rendered.
	    // If a model is set, return its attributes as JSON, otherwise
	    // an empty object with any state attributes on the view mixed in.
	    getTemplateData: function () {
	        var modelData = this.model && this.model.toJSON() || {};
	        var data = _(modelData).extend(this.state);
	        return data;
	    }
	});


/***/ },
/* 6 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';
	
	var View = __webpack_require__(5);
	var ErrorView = __webpack_require__(7);
	var template = __webpack_require__(12);
	
	module.exports = View.extend({
	    initialize: function () {
	        this.template = template;
	        this.model.on('want:search', this.handleStartSearch, this);
	        this.model.on('end:search', this.handleEndSearch, this);
	        this.model.on('change:controls', this.render, this);
	        this.model.on('error:search', this.handleXhrError, this);
	        View.prototype.initialize.call(this);
	    },
	
	    events: {
	        'click .result-filter': 'toggleFilter',
	        'click .reset-filters': 'resetFilters',
	        'click .layer-button': 'switchLayer',
	        'focusin .q': 'toggleTyping',
	        'focusout .q': 'toggleTyping',
	        'keyup .q': 'handleTyping'
	    },
	
	    // Event Handlers
	    // --------------
	
	    toggleFilter: function (event) {
	        var resultType = $(event.currentTarget).data('result-type');
	        this.model.toggleFilter(resultType);
	        this.render();
	    },
	
	    resetFilters: function (event) {
	        event.preventDefault();
	        this.model.resetFilters();
	        this.render();
	    },
	
	    // Switch layers if clicked layer isn't the active layer.
	    switchLayer: function (event) {
	        var layer = $(event.currentTarget).data('layer');
	        if (this.model.get('layer') !== layer) {
	            this.model.set('layer', layer);
	            this.render();
	            this.trigger('change:layer', layer);
	        }
	    },
	
	    toggleTyping: function (event) {
	        this.state.typing = !this.state.typing;
	        this.$el.find('.icon-search').toggle();
	    },
	
	    handleTyping: function (event) {
	        var query = $(event.currentTarget).val();
	        if (query.length > 2 || query.length === 0) {
	            this.model.set({
	                q: query
	            });
	            this.model.attemptSearch();
	        }
	    },
	
	    handleStartSearch: function (event) {
	        this.$el.find('.icon-search').hide();
	        this.$el.find('.icon-loading').show();
	    },
	
	    handleEndSearch: function (event) {
	        if (!this.state.typing) {
	            this.$el.find('.icon-search').show();
	        }
	        this.$el.find('.icon-loading').hide();
	    },
	
	    handleXhrError: function (event) {
	        console.log('#handleXhrError');
	        var $message = this.$el.find('form .message');
	        var errorView = new ErrorView({
	            message: 'Ein Fehler ist bei der Suche aufgetreten.',
	            el: $message
	        }).render();
	    }
	});


/***/ },
/* 7 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';
	
	var View = __webpack_require__(5);
	var template = __webpack_require__(8);
	
	module.exports = View.extend({
	    initialize: function (options) {
	        this.template = template;
	        View.prototype.initialize.call(this);
	        this.state = {
	            message: options.message
	        };
	    }
	});


/***/ },
/* 8 */
/***/ function(module, exports, __webpack_require__) {

	var nunjucks = __webpack_require__(9);
	var env;
	if (!nunjucks.currentEnv){
		env = nunjucks.currentEnv = new nunjucks.Environment([], { autoescape: true });
	} else {
		env = nunjucks.currentEnv;
	}
	var configure = __webpack_require__(10)(env);
	var dependencies = nunjucks.webpackDependencies || (nunjucks.webpackDependencies = {});
	
	
	
	
	var shim = __webpack_require__(11);
	
	
	(function() {(nunjucks.nunjucksPrecompiled = nunjucks.nunjucksPrecompiled || {})["cosinnus/templates/cosinnus/universal/xhr-error.html"] = (function() {
	function root(env, context, frame, runtime, cb) {
	var lineno = null;
	var colno = null;
	var output = "";
	try {
	var parentTemplate = null;
	output += "<div class=\"error\">\n    ";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "message"), env.opts.autoescape);
	output += "\n</div>\n";
	if(parentTemplate) {
	parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
	} else {
	cb(null, output);
	}
	;
	} catch (e) {
	  cb(runtime.handleError(e, lineno, colno));
	}
	}
	return {
	root: root
	};
	
	})();
	})();
	
	
	
	module.exports = shim(nunjucks, env, nunjucks.nunjucksPrecompiled["cosinnus/templates/cosinnus/universal/xhr-error.html"] , dependencies)

/***/ },
/* 9 */
/***/ function(module, exports) {

	/*! Browser bundle of nunjucks 2.4.2 (slim, only works with precompiled templates) */
	var nunjucks =
	/******/ (function(modules) { // webpackBootstrap
	/******/ 	// The module cache
	/******/ 	var installedModules = {};
	
	/******/ 	// The require function
	/******/ 	function __webpack_require__(moduleId) {
	
	/******/ 		// Check if module is in cache
	/******/ 		if(installedModules[moduleId])
	/******/ 			return installedModules[moduleId].exports;
	
	/******/ 		// Create a new module (and put it into the cache)
	/******/ 		var module = installedModules[moduleId] = {
	/******/ 			exports: {},
	/******/ 			id: moduleId,
	/******/ 			loaded: false
	/******/ 		};
	
	/******/ 		// Execute the module function
	/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
	
	/******/ 		// Flag the module as loaded
	/******/ 		module.loaded = true;
	
	/******/ 		// Return the exports of the module
	/******/ 		return module.exports;
	/******/ 	}
	
	
	/******/ 	// expose the modules object (__webpack_modules__)
	/******/ 	__webpack_require__.m = modules;
	
	/******/ 	// expose the module cache
	/******/ 	__webpack_require__.c = installedModules;
	
	/******/ 	// __webpack_public_path__
	/******/ 	__webpack_require__.p = "";
	
	/******/ 	// Load entry module and return exports
	/******/ 	return __webpack_require__(0);
	/******/ })
	/************************************************************************/
	/******/ ([
	/* 0 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var lib = __webpack_require__(1);
		var env = __webpack_require__(2);
		var Loader = __webpack_require__(11);
		var loaders = __webpack_require__(3);
		var precompile = __webpack_require__(3);
	
		module.exports = {};
		module.exports.Environment = env.Environment;
		module.exports.Template = env.Template;
	
		module.exports.Loader = Loader;
		module.exports.FileSystemLoader = loaders.FileSystemLoader;
		module.exports.PrecompiledLoader = loaders.PrecompiledLoader;
		module.exports.WebLoader = loaders.WebLoader;
	
		module.exports.compiler = __webpack_require__(3);
		module.exports.parser = __webpack_require__(3);
		module.exports.lexer = __webpack_require__(3);
		module.exports.runtime = __webpack_require__(8);
		module.exports.lib = lib;
		module.exports.nodes = __webpack_require__(3);
	
		module.exports.installJinjaCompat = __webpack_require__(12);
	
		// A single instance of an environment, since this is so commonly used
	
		var e;
		module.exports.configure = function(templatesPath, opts) {
		    opts = opts || {};
		    if(lib.isObject(templatesPath)) {
		        opts = templatesPath;
		        templatesPath = null;
		    }
	
		    var TemplateLoader;
		    if(loaders.FileSystemLoader) {
		        TemplateLoader = new loaders.FileSystemLoader(templatesPath, {
		            watch: opts.watch,
		            noCache: opts.noCache
		        });
		    }
		    else if(loaders.WebLoader) {
		        TemplateLoader = new loaders.WebLoader(templatesPath, {
		            useCache: opts.web && opts.web.useCache,
		            async: opts.web && opts.web.async
		        });
		    }
	
		    e = new env.Environment(TemplateLoader, opts);
	
		    if(opts && opts.express) {
		        e.express(opts.express);
		    }
	
		    return e;
		};
	
		module.exports.compile = function(src, env, path, eagerCompile) {
		    if(!e) {
		        module.exports.configure();
		    }
		    return new module.exports.Template(src, env, path, eagerCompile);
		};
	
		module.exports.render = function(name, ctx, cb) {
		    if(!e) {
		        module.exports.configure();
		    }
	
		    return e.render(name, ctx, cb);
		};
	
		module.exports.renderString = function(src, ctx, cb) {
		    if(!e) {
		        module.exports.configure();
		    }
	
		    return e.renderString(src, ctx, cb);
		};
	
		if(precompile) {
		    module.exports.precompile = precompile.precompile;
		    module.exports.precompileString = precompile.precompileString;
		}
	
	
	/***/ },
	/* 1 */
	/***/ function(module, exports) {
	
		'use strict';
	
		var ArrayProto = Array.prototype;
		var ObjProto = Object.prototype;
	
		var escapeMap = {
		    '&': '&amp;',
		    '"': '&quot;',
		    '\'': '&#39;',
		    '<': '&lt;',
		    '>': '&gt;'
		};
	
		var escapeRegex = /[&"'<>]/g;
	
		var lookupEscape = function(ch) {
		    return escapeMap[ch];
		};
	
		var exports = module.exports = {};
	
		exports.prettifyError = function(path, withInternals, err) {
		    // jshint -W022
		    // http://jslinterrors.com/do-not-assign-to-the-exception-parameter
		    if (!err.Update) {
		        // not one of ours, cast it
		        err = new exports.TemplateError(err);
		    }
		    err.Update(path);
	
		    // Unless they marked the dev flag, show them a trace from here
		    if (!withInternals) {
		        var old = err;
		        err = new Error(old.message);
		        err.name = old.name;
		    }
	
		    return err;
		};
	
		exports.TemplateError = function(message, lineno, colno) {
		    var err = this;
	
		    if (message instanceof Error) { // for casting regular js errors
		        err = message;
		        message = message.name + ': ' + message.message;
	
		        try {
		            if(err.name = '') {}
		        }
		        catch(e) {
		            // If we can't set the name of the error object in this
		            // environment, don't use it
		            err = this;
		        }
		    } else {
		        if(Error.captureStackTrace) {
		            Error.captureStackTrace(err);
		        }
		    }
	
		    err.name = 'Template render error';
		    err.message = message;
		    err.lineno = lineno;
		    err.colno = colno;
		    err.firstUpdate = true;
	
		    err.Update = function(path) {
		        var message = '(' + (path || 'unknown path') + ')';
	
		        // only show lineno + colno next to path of template
		        // where error occurred
		        if (this.firstUpdate) {
		            if(this.lineno && this.colno) {
		                message += ' [Line ' + this.lineno + ', Column ' + this.colno + ']';
		            }
		            else if(this.lineno) {
		                message += ' [Line ' + this.lineno + ']';
		            }
		        }
	
		        message += '\n ';
		        if (this.firstUpdate) {
		            message += ' ';
		        }
	
		        this.message = message + (this.message || '');
		        this.firstUpdate = false;
		        return this;
		    };
	
		    return err;
		};
	
		exports.TemplateError.prototype = Error.prototype;
	
		exports.escape = function(val) {
		  return val.replace(escapeRegex, lookupEscape);
		};
	
		exports.isFunction = function(obj) {
		    return ObjProto.toString.call(obj) === '[object Function]';
		};
	
		exports.isArray = Array.isArray || function(obj) {
		    return ObjProto.toString.call(obj) === '[object Array]';
		};
	
		exports.isString = function(obj) {
		    return ObjProto.toString.call(obj) === '[object String]';
		};
	
		exports.isObject = function(obj) {
		    return ObjProto.toString.call(obj) === '[object Object]';
		};
	
		exports.groupBy = function(obj, val) {
		    var result = {};
		    var iterator = exports.isFunction(val) ? val : function(obj) { return obj[val]; };
		    for(var i=0; i<obj.length; i++) {
		        var value = obj[i];
		        var key = iterator(value, i);
		        (result[key] || (result[key] = [])).push(value);
		    }
		    return result;
		};
	
		exports.toArray = function(obj) {
		    return Array.prototype.slice.call(obj);
		};
	
		exports.without = function(array) {
		    var result = [];
		    if (!array) {
		        return result;
		    }
		    var index = -1,
		    length = array.length,
		    contains = exports.toArray(arguments).slice(1);
	
		    while(++index < length) {
		        if(exports.indexOf(contains, array[index]) === -1) {
		            result.push(array[index]);
		        }
		    }
		    return result;
		};
	
		exports.extend = function(obj, obj2) {
		    for(var k in obj2) {
		        obj[k] = obj2[k];
		    }
		    return obj;
		};
	
		exports.repeat = function(char_, n) {
		    var str = '';
		    for(var i=0; i<n; i++) {
		        str += char_;
		    }
		    return str;
		};
	
		exports.each = function(obj, func, context) {
		    if(obj == null) {
		        return;
		    }
	
		    if(ArrayProto.each && obj.each === ArrayProto.each) {
		        obj.forEach(func, context);
		    }
		    else if(obj.length === +obj.length) {
		        for(var i=0, l=obj.length; i<l; i++) {
		            func.call(context, obj[i], i, obj);
		        }
		    }
		};
	
		exports.map = function(obj, func) {
		    var results = [];
		    if(obj == null) {
		        return results;
		    }
	
		    if(ArrayProto.map && obj.map === ArrayProto.map) {
		        return obj.map(func);
		    }
	
		    for(var i=0; i<obj.length; i++) {
		        results[results.length] = func(obj[i], i);
		    }
	
		    if(obj.length === +obj.length) {
		        results.length = obj.length;
		    }
	
		    return results;
		};
	
		exports.asyncIter = function(arr, iter, cb) {
		    var i = -1;
	
		    function next() {
		        i++;
	
		        if(i < arr.length) {
		            iter(arr[i], i, next, cb);
		        }
		        else {
		            cb();
		        }
		    }
	
		    next();
		};
	
		exports.asyncFor = function(obj, iter, cb) {
		    var keys = exports.keys(obj);
		    var len = keys.length;
		    var i = -1;
	
		    function next() {
		        i++;
		        var k = keys[i];
	
		        if(i < len) {
		            iter(k, obj[k], i, len, next);
		        }
		        else {
		            cb();
		        }
		    }
	
		    next();
		};
	
		// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/indexOf#Polyfill
		exports.indexOf = Array.prototype.indexOf ?
		    function (arr, searchElement, fromIndex) {
		        return Array.prototype.indexOf.call(arr, searchElement, fromIndex);
		    } :
		    function (arr, searchElement, fromIndex) {
		        var length = this.length >>> 0; // Hack to convert object.length to a UInt32
	
		        fromIndex = +fromIndex || 0;
	
		        if(Math.abs(fromIndex) === Infinity) {
		            fromIndex = 0;
		        }
	
		        if(fromIndex < 0) {
		            fromIndex += length;
		            if (fromIndex < 0) {
		                fromIndex = 0;
		            }
		        }
	
		        for(;fromIndex < length; fromIndex++) {
		            if (arr[fromIndex] === searchElement) {
		                return fromIndex;
		            }
		        }
	
		        return -1;
		    };
	
		if(!Array.prototype.map) {
		    Array.prototype.map = function() {
		        throw new Error('map is unimplemented for this js engine');
		    };
		}
	
		exports.keys = function(obj) {
		    if(Object.prototype.keys) {
		        return obj.keys();
		    }
		    else {
		        var keys = [];
		        for(var k in obj) {
		            if(obj.hasOwnProperty(k)) {
		                keys.push(k);
		            }
		        }
		        return keys;
		    }
		};
	
		exports.inOperator = function (key, val) {
		    if (exports.isArray(val)) {
		        return exports.indexOf(val, key) !== -1;
		    } else if (exports.isObject(val)) {
		        return key in val;
		    } else if (exports.isString(val)) {
		        return val.indexOf(key) !== -1;
		    } else {
		        throw new Error('Cannot use "in" operator to search for "'
		            + key + '" in unexpected types.');
		    }
		};
	
	
	/***/ },
	/* 2 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var path = __webpack_require__(3);
		var asap = __webpack_require__(4);
		var lib = __webpack_require__(1);
		var Obj = __webpack_require__(6);
		var compiler = __webpack_require__(3);
		var builtin_filters = __webpack_require__(7);
		var builtin_loaders = __webpack_require__(3);
		var runtime = __webpack_require__(8);
		var globals = __webpack_require__(9);
		var Frame = runtime.Frame;
		var Template;
	
		// Unconditionally load in this loader, even if no other ones are
		// included (possible in the slim browser build)
		builtin_loaders.PrecompiledLoader = __webpack_require__(10);
	
		// If the user is using the async API, *always* call it
		// asynchronously even if the template was synchronous.
		function callbackAsap(cb, err, res) {
		    asap(function() { cb(err, res); });
		}
	
		var Environment = Obj.extend({
		    init: function(loaders, opts) {
		        // The dev flag determines the trace that'll be shown on errors.
		        // If set to true, returns the full trace from the error point,
		        // otherwise will return trace starting from Template.render
		        // (the full trace from within nunjucks may confuse developers using
		        //  the library)
		        // defaults to false
		        opts = this.opts = opts || {};
		        this.opts.dev = !!opts.dev;
	
		        // The autoescape flag sets global autoescaping. If true,
		        // every string variable will be escaped by default.
		        // If false, strings can be manually escaped using the `escape` filter.
		        // defaults to true
		        this.opts.autoescape = opts.autoescape != null ? opts.autoescape : true;
	
		        // If true, this will make the system throw errors if trying
		        // to output a null or undefined value
		        this.opts.throwOnUndefined = !!opts.throwOnUndefined;
		        this.opts.trimBlocks = !!opts.trimBlocks;
		        this.opts.lstripBlocks = !!opts.lstripBlocks;
	
		        this.loaders = [];
	
		        if(!loaders) {
		            // The filesystem loader is only available server-side
		            if(builtin_loaders.FileSystemLoader) {
		                this.loaders = [new builtin_loaders.FileSystemLoader('views')];
		            }
		            else if(builtin_loaders.WebLoader) {
		                this.loaders = [new builtin_loaders.WebLoader('/views')];
		            }
		        }
		        else {
		            this.loaders = lib.isArray(loaders) ? loaders : [loaders];
		        }
	
		        // It's easy to use precompiled templates: just include them
		        // before you configure nunjucks and this will automatically
		        // pick it up and use it
		        if((true) && window.nunjucksPrecompiled) {
		            this.loaders.unshift(
		                new builtin_loaders.PrecompiledLoader(window.nunjucksPrecompiled)
		            );
		        }
	
		        this.initCache();
	
		        this.globals = globals();
		        this.filters = {};
		        this.asyncFilters = [];
		        this.extensions = {};
		        this.extensionsList = [];
	
		        for(var name in builtin_filters) {
		            this.addFilter(name, builtin_filters[name]);
		        }
		    },
	
		    initCache: function() {
		        // Caching and cache busting
		        lib.each(this.loaders, function(loader) {
		            loader.cache = {};
	
		            if(typeof loader.on === 'function') {
		                loader.on('update', function(template) {
		                    loader.cache[template] = null;
		                });
		            }
		        });
		    },
	
		    addExtension: function(name, extension) {
		        extension._name = name;
		        this.extensions[name] = extension;
		        this.extensionsList.push(extension);
		        return this;
		    },
	
		    removeExtension: function(name) {
		        var extension = this.getExtension(name);
		        if (!extension) return;
	
		        this.extensionsList = lib.without(this.extensionsList, extension);
		        delete this.extensions[name];
		    },
	
		    getExtension: function(name) {
		        return this.extensions[name];
		    },
	
		    hasExtension: function(name) {
		        return !!this.extensions[name];
		    },
	
		    addGlobal: function(name, value) {
		        this.globals[name] = value;
		        return this;
		    },
	
		    getGlobal: function(name) {
		        if(typeof this.globals[name] === 'undefined') {
		            throw new Error('global not found: ' + name);
		        }
		        return this.globals[name];
		    },
	
		    addFilter: function(name, func, async) {
		        var wrapped = func;
	
		        if(async) {
		            this.asyncFilters.push(name);
		        }
		        this.filters[name] = wrapped;
		        return this;
		    },
	
		    getFilter: function(name) {
		        if(!this.filters[name]) {
		            throw new Error('filter not found: ' + name);
		        }
		        return this.filters[name];
		    },
	
		    resolveTemplate: function(loader, parentName, filename) {
		        var isRelative = (loader.isRelative && parentName)? loader.isRelative(filename) : false;
		        return (isRelative && loader.resolve)? loader.resolve(parentName, filename) : filename;
		    },
	
		    getTemplate: function(name, eagerCompile, parentName, ignoreMissing, cb) {
		        var that = this;
		        var tmpl = null;
		        if(name && name.raw) {
		            // this fixes autoescape for templates referenced in symbols
		            name = name.raw;
		        }
	
		        if(lib.isFunction(parentName)) {
		            cb = parentName;
		            parentName = null;
		            eagerCompile = eagerCompile || false;
		        }
	
		        if(lib.isFunction(eagerCompile)) {
		            cb = eagerCompile;
		            eagerCompile = false;
		        }
	
		        if (name instanceof Template) {
		             tmpl = name;
		        }
		        else if(typeof name !== 'string') {
		            throw new Error('template names must be a string: ' + name);
		        }
		        else {
		            for (var i = 0; i < this.loaders.length; i++) {
		                var _name = this.resolveTemplate(this.loaders[i], parentName, name);
		                tmpl = this.loaders[i].cache[_name];
		                if (tmpl) break;
		            }
		        }
	
		        if(tmpl) {
		            if(eagerCompile) {
		                tmpl.compile();
		            }
	
		            if(cb) {
		                cb(null, tmpl);
		            }
		            else {
		                return tmpl;
		            }
		        } else {
		            var syncResult;
		            var _this = this;
	
		            var createTemplate = function(err, info) {
		                if(!info && !err) {
		                    if(!ignoreMissing) {
		                        err = new Error('template not found: ' + name);
		                    }
		                }
	
		                if (err) {
		                    if(cb) {
		                        cb(err);
		                    }
		                    else {
		                        throw err;
		                    }
		                }
		                else {
		                    var tmpl;
		                    if(info) {
		                        tmpl = new Template(info.src, _this,
		                                            info.path, eagerCompile);
	
		                        if(!info.noCache) {
		                            info.loader.cache[name] = tmpl;
		                        }
		                    }
		                    else {
		                        tmpl = new Template('', _this,
		                                            '', eagerCompile);
		                    }
	
		                    if(cb) {
		                        cb(null, tmpl);
		                    }
		                    else {
		                        syncResult = tmpl;
		                    }
		                }
		            };
	
		            lib.asyncIter(this.loaders, function(loader, i, next, done) {
		                function handle(err, src) {
		                    if(err) {
		                        done(err);
		                    }
		                    else if(src) {
		                        src.loader = loader;
		                        done(null, src);
		                    }
		                    else {
		                        next();
		                    }
		                }
	
		                // Resolve name relative to parentName
		                name = that.resolveTemplate(loader, parentName, name);
	
		                if(loader.async) {
		                    loader.getSource(name, handle);
		                }
		                else {
		                    handle(null, loader.getSource(name));
		                }
		            }, createTemplate);
	
		            return syncResult;
		        }
		    },
	
		    express: function(app) {
		        var env = this;
	
		        function NunjucksView(name, opts) {
		            this.name          = name;
		            this.path          = name;
		            this.defaultEngine = opts.defaultEngine;
		            this.ext           = path.extname(name);
		            if (!this.ext && !this.defaultEngine) throw new Error('No default engine was specified and no extension was provided.');
		            if (!this.ext) this.name += (this.ext = ('.' !== this.defaultEngine[0] ? '.' : '') + this.defaultEngine);
		        }
	
		        NunjucksView.prototype.render = function(opts, cb) {
		          env.render(this.name, opts, cb);
		        };
	
		        app.set('view', NunjucksView);
		        return this;
		    },
	
		    render: function(name, ctx, cb) {
		        if(lib.isFunction(ctx)) {
		            cb = ctx;
		            ctx = null;
		        }
	
		        // We support a synchronous API to make it easier to migrate
		        // existing code to async. This works because if you don't do
		        // anything async work, the whole thing is actually run
		        // synchronously.
		        var syncResult = null;
	
		        this.getTemplate(name, function(err, tmpl) {
		            if(err && cb) {
		                callbackAsap(cb, err);
		            }
		            else if(err) {
		                throw err;
		            }
		            else {
		                syncResult = tmpl.render(ctx, cb);
		            }
		        });
	
		        return syncResult;
		    },
	
		    renderString: function(src, ctx, opts, cb) {
		        if(lib.isFunction(opts)) {
		            cb = opts;
		            opts = {};
		        }
		        opts = opts || {};
	
		        var tmpl = new Template(src, this, opts.path);
		        return tmpl.render(ctx, cb);
		    }
		});
	
		var Context = Obj.extend({
		    init: function(ctx, blocks, env) {
		        // Has to be tied to an environment so we can tap into its globals.
		        this.env = env || new Environment();
	
		        // Make a duplicate of ctx
		        this.ctx = {};
		        for(var k in ctx) {
		            if(ctx.hasOwnProperty(k)) {
		                this.ctx[k] = ctx[k];
		            }
		        }
	
		        this.blocks = {};
		        this.exported = [];
	
		        for(var name in blocks) {
		            this.addBlock(name, blocks[name]);
		        }
		    },
	
		    lookup: function(name) {
		        // This is one of the most called functions, so optimize for
		        // the typical case where the name isn't in the globals
		        if(name in this.env.globals && !(name in this.ctx)) {
		            return this.env.globals[name];
		        }
		        else {
		            return this.ctx[name];
		        }
		    },
	
		    setVariable: function(name, val) {
		        this.ctx[name] = val;
		    },
	
		    getVariables: function() {
		        return this.ctx;
		    },
	
		    addBlock: function(name, block) {
		        this.blocks[name] = this.blocks[name] || [];
		        this.blocks[name].push(block);
		        return this;
		    },
	
		    getBlock: function(name) {
		        if(!this.blocks[name]) {
		            throw new Error('unknown block "' + name + '"');
		        }
	
		        return this.blocks[name][0];
		    },
	
		    getSuper: function(env, name, block, frame, runtime, cb) {
		        var idx = lib.indexOf(this.blocks[name] || [], block);
		        var blk = this.blocks[name][idx + 1];
		        var context = this;
	
		        if(idx === -1 || !blk) {
		            throw new Error('no super block available for "' + name + '"');
		        }
	
		        blk(env, context, frame, runtime, cb);
		    },
	
		    addExport: function(name) {
		        this.exported.push(name);
		    },
	
		    getExported: function() {
		        var exported = {};
		        for(var i=0; i<this.exported.length; i++) {
		            var name = this.exported[i];
		            exported[name] = this.ctx[name];
		        }
		        return exported;
		    }
		});
	
		Template = Obj.extend({
		    init: function (src, env, path, eagerCompile) {
		        this.env = env || new Environment();
	
		        if(lib.isObject(src)) {
		            switch(src.type) {
		            case 'code': this.tmplProps = src.obj; break;
		            case 'string': this.tmplStr = src.obj; break;
		            }
		        }
		        else if(lib.isString(src)) {
		            this.tmplStr = src;
		        }
		        else {
		            throw new Error('src must be a string or an object describing ' +
		                            'the source');
		        }
	
		        this.path = path;
	
		        if(eagerCompile) {
		            var _this = this;
		            try {
		                _this._compile();
		            }
		            catch(err) {
		                throw lib.prettifyError(this.path, this.env.opts.dev, err);
		            }
		        }
		        else {
		            this.compiled = false;
		        }
		    },
	
		    render: function(ctx, parentFrame, cb) {
		        if (typeof ctx === 'function') {
		            cb = ctx;
		            ctx = {};
		        }
		        else if (typeof parentFrame === 'function') {
		            cb = parentFrame;
		            parentFrame = null;
		        }
	
		        var forceAsync = true;
		        if(parentFrame) {
		            // If there is a frame, we are being called from internal
		            // code of another template, and the internal system
		            // depends on the sync/async nature of the parent template
		            // to be inherited, so force an async callback
		            forceAsync = false;
		        }
	
		        var _this = this;
		        // Catch compile errors for async rendering
		        try {
		            _this.compile();
		        } catch (_err) {
		            var err = lib.prettifyError(this.path, this.env.opts.dev, _err);
		            if (cb) return callbackAsap(cb, err);
		            else throw err;
		        }
	
		        var context = new Context(ctx || {}, _this.blocks, _this.env);
		        var frame = parentFrame ? parentFrame.push(true) : new Frame();
		        frame.topLevel = true;
		        var syncResult = null;
	
		        _this.rootRenderFunc(
		            _this.env,
		            context,
		            frame || new Frame(),
		            runtime,
		            function(err, res) {
		                if(err) {
		                    err = lib.prettifyError(_this.path, _this.env.opts.dev, err);
		                }
	
		                if(cb) {
		                    if(forceAsync) {
		                        callbackAsap(cb, err, res);
		                    }
		                    else {
		                        cb(err, res);
		                    }
		                }
		                else {
		                    if(err) { throw err; }
		                    syncResult = res;
		                }
		            }
		        );
	
		        return syncResult;
		    },
	
	
		    getExported: function(ctx, parentFrame, cb) {
		        if (typeof ctx === 'function') {
		            cb = ctx;
		            ctx = {};
		        }
	
		        if (typeof parentFrame === 'function') {
		            cb = parentFrame;
		            parentFrame = null;
		        }
	
		        // Catch compile errors for async rendering
		        try {
		            this.compile();
		        } catch (e) {
		            if (cb) return cb(e);
		            else throw e;
		        }
	
		        var frame = parentFrame ? parentFrame.push() : new Frame();
		        frame.topLevel = true;
	
		        // Run the rootRenderFunc to populate the context with exported vars
		        var context = new Context(ctx || {}, this.blocks, this.env);
		        this.rootRenderFunc(this.env,
		                            context,
		                            frame,
		                            runtime,
		                            function(err) {
		        		        if ( err ) {
		        			    cb(err, null);
		        		        } else {
		        			    cb(null, context.getExported());
		        		        }
		                            });
		    },
	
		    compile: function() {
		        if(!this.compiled) {
		            this._compile();
		        }
		    },
	
		    _compile: function() {
		        var props;
	
		        if(this.tmplProps) {
		            props = this.tmplProps;
		        }
		        else {
		            var source = compiler.compile(this.tmplStr,
		                                          this.env.asyncFilters,
		                                          this.env.extensionsList,
		                                          this.path,
		                                          this.env.opts);
	
		            /* jslint evil: true */
		            var func = new Function(source);
		            props = func();
		        }
	
		        this.blocks = this._getBlocks(props);
		        this.rootRenderFunc = props.root;
		        this.compiled = true;
		    },
	
		    _getBlocks: function(props) {
		        var blocks = {};
	
		        for(var k in props) {
		            if(k.slice(0, 2) === 'b_') {
		                blocks[k.slice(2)] = props[k];
		            }
		        }
	
		        return blocks;
		    }
		});
	
		module.exports = {
		    Environment: Environment,
		    Template: Template
		};
	
	
	/***/ },
	/* 3 */
	/***/ function(module, exports) {
	
		
	
	/***/ },
	/* 4 */
	/***/ function(module, exports, __webpack_require__) {
	
		"use strict";
	
		// rawAsap provides everything we need except exception management.
		var rawAsap = __webpack_require__(5);
		// RawTasks are recycled to reduce GC churn.
		var freeTasks = [];
		// We queue errors to ensure they are thrown in right order (FIFO).
		// Array-as-queue is good enough here, since we are just dealing with exceptions.
		var pendingErrors = [];
		var requestErrorThrow = rawAsap.makeRequestCallFromTimer(throwFirstError);
	
		function throwFirstError() {
		    if (pendingErrors.length) {
		        throw pendingErrors.shift();
		    }
		}
	
		/**
		 * Calls a task as soon as possible after returning, in its own event, with priority
		 * over other events like animation, reflow, and repaint. An error thrown from an
		 * event will not interrupt, nor even substantially slow down the processing of
		 * other events, but will be rather postponed to a lower priority event.
		 * @param {{call}} task A callable object, typically a function that takes no
		 * arguments.
		 */
		module.exports = asap;
		function asap(task) {
		    var rawTask;
		    if (freeTasks.length) {
		        rawTask = freeTasks.pop();
		    } else {
		        rawTask = new RawTask();
		    }
		    rawTask.task = task;
		    rawAsap(rawTask);
		}
	
		// We wrap tasks with recyclable task objects.  A task object implements
		// `call`, just like a function.
		function RawTask() {
		    this.task = null;
		}
	
		// The sole purpose of wrapping the task is to catch the exception and recycle
		// the task object after its single use.
		RawTask.prototype.call = function () {
		    try {
		        this.task.call();
		    } catch (error) {
		        if (asap.onerror) {
		            // This hook exists purely for testing purposes.
		            // Its name will be periodically randomized to break any code that
		            // depends on its existence.
		            asap.onerror(error);
		        } else {
		            // In a web browser, exceptions are not fatal. However, to avoid
		            // slowing down the queue of pending tasks, we rethrow the error in a
		            // lower priority turn.
		            pendingErrors.push(error);
		            requestErrorThrow();
		        }
		    } finally {
		        this.task = null;
		        freeTasks[freeTasks.length] = this;
		    }
		};
	
	
	/***/ },
	/* 5 */
	/***/ function(module, exports) {
	
		/* WEBPACK VAR INJECTION */(function(global) {"use strict";
	
		// Use the fastest means possible to execute a task in its own turn, with
		// priority over other events including IO, animation, reflow, and redraw
		// events in browsers.
		//
		// An exception thrown by a task will permanently interrupt the processing of
		// subsequent tasks. The higher level `asap` function ensures that if an
		// exception is thrown by a task, that the task queue will continue flushing as
		// soon as possible, but if you use `rawAsap` directly, you are responsible to
		// either ensure that no exceptions are thrown from your task, or to manually
		// call `rawAsap.requestFlush` if an exception is thrown.
		module.exports = rawAsap;
		function rawAsap(task) {
		    if (!queue.length) {
		        requestFlush();
		        flushing = true;
		    }
		    // Equivalent to push, but avoids a function call.
		    queue[queue.length] = task;
		}
	
		var queue = [];
		// Once a flush has been requested, no further calls to `requestFlush` are
		// necessary until the next `flush` completes.
		var flushing = false;
		// `requestFlush` is an implementation-specific method that attempts to kick
		// off a `flush` event as quickly as possible. `flush` will attempt to exhaust
		// the event queue before yielding to the browser's own event loop.
		var requestFlush;
		// The position of the next task to execute in the task queue. This is
		// preserved between calls to `flush` so that it can be resumed if
		// a task throws an exception.
		var index = 0;
		// If a task schedules additional tasks recursively, the task queue can grow
		// unbounded. To prevent memory exhaustion, the task queue will periodically
		// truncate already-completed tasks.
		var capacity = 1024;
	
		// The flush function processes all tasks that have been scheduled with
		// `rawAsap` unless and until one of those tasks throws an exception.
		// If a task throws an exception, `flush` ensures that its state will remain
		// consistent and will resume where it left off when called again.
		// However, `flush` does not make any arrangements to be called again if an
		// exception is thrown.
		function flush() {
		    while (index < queue.length) {
		        var currentIndex = index;
		        // Advance the index before calling the task. This ensures that we will
		        // begin flushing on the next task the task throws an error.
		        index = index + 1;
		        queue[currentIndex].call();
		        // Prevent leaking memory for long chains of recursive calls to `asap`.
		        // If we call `asap` within tasks scheduled by `asap`, the queue will
		        // grow, but to avoid an O(n) walk for every task we execute, we don't
		        // shift tasks off the queue after they have been executed.
		        // Instead, we periodically shift 1024 tasks off the queue.
		        if (index > capacity) {
		            // Manually shift all values starting at the index back to the
		            // beginning of the queue.
		            for (var scan = 0, newLength = queue.length - index; scan < newLength; scan++) {
		                queue[scan] = queue[scan + index];
		            }
		            queue.length -= index;
		            index = 0;
		        }
		    }
		    queue.length = 0;
		    index = 0;
		    flushing = false;
		}
	
		// `requestFlush` is implemented using a strategy based on data collected from
		// every available SauceLabs Selenium web driver worker at time of writing.
		// https://docs.google.com/spreadsheets/d/1mG-5UYGup5qxGdEMWkhP6BWCz053NUb2E1QoUTU16uA/edit#gid=783724593
	
		// Safari 6 and 6.1 for desktop, iPad, and iPhone are the only browsers that
		// have WebKitMutationObserver but not un-prefixed MutationObserver.
		// Must use `global` instead of `window` to work in both frames and web
		// workers. `global` is a provision of Browserify, Mr, Mrs, or Mop.
		var BrowserMutationObserver = global.MutationObserver || global.WebKitMutationObserver;
	
		// MutationObservers are desirable because they have high priority and work
		// reliably everywhere they are implemented.
		// They are implemented in all modern browsers.
		//
		// - Android 4-4.3
		// - Chrome 26-34
		// - Firefox 14-29
		// - Internet Explorer 11
		// - iPad Safari 6-7.1
		// - iPhone Safari 7-7.1
		// - Safari 6-7
		if (typeof BrowserMutationObserver === "function") {
		    requestFlush = makeRequestCallFromMutationObserver(flush);
	
		// MessageChannels are desirable because they give direct access to the HTML
		// task queue, are implemented in Internet Explorer 10, Safari 5.0-1, and Opera
		// 11-12, and in web workers in many engines.
		// Although message channels yield to any queued rendering and IO tasks, they
		// would be better than imposing the 4ms delay of timers.
		// However, they do not work reliably in Internet Explorer or Safari.
	
		// Internet Explorer 10 is the only browser that has setImmediate but does
		// not have MutationObservers.
		// Although setImmediate yields to the browser's renderer, it would be
		// preferrable to falling back to setTimeout since it does not have
		// the minimum 4ms penalty.
		// Unfortunately there appears to be a bug in Internet Explorer 10 Mobile (and
		// Desktop to a lesser extent) that renders both setImmediate and
		// MessageChannel useless for the purposes of ASAP.
		// https://github.com/kriskowal/q/issues/396
	
		// Timers are implemented universally.
		// We fall back to timers in workers in most engines, and in foreground
		// contexts in the following browsers.
		// However, note that even this simple case requires nuances to operate in a
		// broad spectrum of browsers.
		//
		// - Firefox 3-13
		// - Internet Explorer 6-9
		// - iPad Safari 4.3
		// - Lynx 2.8.7
		} else {
		    requestFlush = makeRequestCallFromTimer(flush);
		}
	
		// `requestFlush` requests that the high priority event queue be flushed as
		// soon as possible.
		// This is useful to prevent an error thrown in a task from stalling the event
		// queue if the exception handled by Node.js’s
		// `process.on("uncaughtException")` or by a domain.
		rawAsap.requestFlush = requestFlush;
	
		// To request a high priority event, we induce a mutation observer by toggling
		// the text of a text node between "1" and "-1".
		function makeRequestCallFromMutationObserver(callback) {
		    var toggle = 1;
		    var observer = new BrowserMutationObserver(callback);
		    var node = document.createTextNode("");
		    observer.observe(node, {characterData: true});
		    return function requestCall() {
		        toggle = -toggle;
		        node.data = toggle;
		    };
		}
	
		// The message channel technique was discovered by Malte Ubl and was the
		// original foundation for this library.
		// http://www.nonblocking.io/2011/06/windownexttick.html
	
		// Safari 6.0.5 (at least) intermittently fails to create message ports on a
		// page's first load. Thankfully, this version of Safari supports
		// MutationObservers, so we don't need to fall back in that case.
	
		// function makeRequestCallFromMessageChannel(callback) {
		//     var channel = new MessageChannel();
		//     channel.port1.onmessage = callback;
		//     return function requestCall() {
		//         channel.port2.postMessage(0);
		//     };
		// }
	
		// For reasons explained above, we are also unable to use `setImmediate`
		// under any circumstances.
		// Even if we were, there is another bug in Internet Explorer 10.
		// It is not sufficient to assign `setImmediate` to `requestFlush` because
		// `setImmediate` must be called *by name* and therefore must be wrapped in a
		// closure.
		// Never forget.
	
		// function makeRequestCallFromSetImmediate(callback) {
		//     return function requestCall() {
		//         setImmediate(callback);
		//     };
		// }
	
		// Safari 6.0 has a problem where timers will get lost while the user is
		// scrolling. This problem does not impact ASAP because Safari 6.0 supports
		// mutation observers, so that implementation is used instead.
		// However, if we ever elect to use timers in Safari, the prevalent work-around
		// is to add a scroll event listener that calls for a flush.
	
		// `setTimeout` does not call the passed callback if the delay is less than
		// approximately 7 in web workers in Firefox 8 through 18, and sometimes not
		// even then.
	
		function makeRequestCallFromTimer(callback) {
		    return function requestCall() {
		        // We dispatch a timeout with a specified delay of 0 for engines that
		        // can reliably accommodate that request. This will usually be snapped
		        // to a 4 milisecond delay, but once we're flushing, there's no delay
		        // between events.
		        var timeoutHandle = setTimeout(handleTimer, 0);
		        // However, since this timer gets frequently dropped in Firefox
		        // workers, we enlist an interval handle that will try to fire
		        // an event 20 times per second until it succeeds.
		        var intervalHandle = setInterval(handleTimer, 50);
	
		        function handleTimer() {
		            // Whichever timer succeeds will cancel both timers and
		            // execute the callback.
		            clearTimeout(timeoutHandle);
		            clearInterval(intervalHandle);
		            callback();
		        }
		    };
		}
	
		// This is for `asap.js` only.
		// Its name will be periodically randomized to break any code that depends on
		// its existence.
		rawAsap.makeRequestCallFromTimer = makeRequestCallFromTimer;
	
		// ASAP was originally a nextTick shim included in Q. This was factored out
		// into this ASAP package. It was later adapted to RSVP which made further
		// amendments. These decisions, particularly to marginalize MessageChannel and
		// to capture the MutationObserver implementation in a closure, were integrated
		// back into ASAP proper.
		// https://github.com/tildeio/rsvp.js/blob/cddf7232546a9cf858524b75cde6f9edf72620a7/lib/rsvp/asap.js
	
		/* WEBPACK VAR INJECTION */}.call(exports, (function() { return this; }())))
	
	/***/ },
	/* 6 */
	/***/ function(module, exports) {
	
		'use strict';
	
		// A simple class system, more documentation to come
	
		function extend(cls, name, props) {
		    // This does that same thing as Object.create, but with support for IE8
		    var F = function() {};
		    F.prototype = cls.prototype;
		    var prototype = new F();
	
		    // jshint undef: false
		    var fnTest = /xyz/.test(function(){ xyz; }) ? /\bparent\b/ : /.*/;
		    props = props || {};
	
		    for(var k in props) {
		        var src = props[k];
		        var parent = prototype[k];
	
		        if(typeof parent === 'function' &&
		           typeof src === 'function' &&
		           fnTest.test(src)) {
		            /*jshint -W083 */
		            prototype[k] = (function (src, parent) {
		                return function() {
		                    // Save the current parent method
		                    var tmp = this.parent;
	
		                    // Set parent to the previous method, call, and restore
		                    this.parent = parent;
		                    var res = src.apply(this, arguments);
		                    this.parent = tmp;
	
		                    return res;
		                };
		            })(src, parent);
		        }
		        else {
		            prototype[k] = src;
		        }
		    }
	
		    prototype.typename = name;
	
		    var new_cls = function() {
		        if(prototype.init) {
		            prototype.init.apply(this, arguments);
		        }
		    };
	
		    new_cls.prototype = prototype;
		    new_cls.prototype.constructor = new_cls;
	
		    new_cls.extend = function(name, props) {
		        if(typeof name === 'object') {
		            props = name;
		            name = 'anonymous';
		        }
		        return extend(new_cls, name, props);
		    };
	
		    return new_cls;
		}
	
		module.exports = extend(Object, 'Object', {});
	
	
	/***/ },
	/* 7 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var lib = __webpack_require__(1);
		var r = __webpack_require__(8);
	
		function normalize(value, defaultValue) {
		    if(value === null || value === undefined || value === false) {
		        return defaultValue;
		    }
		    return value;
		}
	
		var filters = {
		    abs: function(n) {
		        return Math.abs(n);
		    },
	
		    batch: function(arr, linecount, fill_with) {
		        var i;
		        var res = [];
		        var tmp = [];
	
		        for(i = 0; i < arr.length; i++) {
		            if(i % linecount === 0 && tmp.length) {
		                res.push(tmp);
		                tmp = [];
		            }
	
		            tmp.push(arr[i]);
		        }
	
		        if(tmp.length) {
		            if(fill_with) {
		                for(i = tmp.length; i < linecount; i++) {
		                    tmp.push(fill_with);
		                }
		            }
	
		            res.push(tmp);
		        }
	
		        return res;
		    },
	
		    capitalize: function(str) {
		        str = normalize(str, '');
		        var ret = str.toLowerCase();
		        return r.copySafeness(str, ret.charAt(0).toUpperCase() + ret.slice(1));
		    },
	
		    center: function(str, width) {
		        str = normalize(str, '');
		        width = width || 80;
	
		        if(str.length >= width) {
		            return str;
		        }
	
		        var spaces = width - str.length;
		        var pre = lib.repeat(' ', spaces/2 - spaces % 2);
		        var post = lib.repeat(' ', spaces/2);
		        return r.copySafeness(str, pre + str + post);
		    },
	
		    'default': function(val, def, bool) {
		        if(bool) {
		            return val ? val : def;
		        }
		        else {
		            return (val !== undefined) ? val : def;
		        }
		    },
	
		    dictsort: function(val, case_sensitive, by) {
		        if (!lib.isObject(val)) {
		            throw new lib.TemplateError('dictsort filter: val must be an object');
		        }
	
		        var array = [];
		        for (var k in val) {
		            // deliberately include properties from the object's prototype
		            array.push([k,val[k]]);
		        }
	
		        var si;
		        if (by === undefined || by === 'key') {
		            si = 0;
		        } else if (by === 'value') {
		            si = 1;
		        } else {
		            throw new lib.TemplateError(
		                'dictsort filter: You can only sort by either key or value');
		        }
	
		        array.sort(function(t1, t2) {
		            var a = t1[si];
		            var b = t2[si];
	
		            if (!case_sensitive) {
		                if (lib.isString(a)) {
		                    a = a.toUpperCase();
		                }
		                if (lib.isString(b)) {
		                    b = b.toUpperCase();
		                }
		            }
	
		            return a > b ? 1 : (a === b ? 0 : -1);
		        });
	
		        return array;
		    },
	
		    dump: function(obj) {
		        return JSON.stringify(obj);
		    },
	
		    escape: function(str) {
		        if(typeof str === 'string') {
		            return r.markSafe(lib.escape(str));
		        }
		        return str;
		    },
	
		    safe: function(str) {
		        return r.markSafe(str);
		    },
	
		    first: function(arr) {
		        return arr[0];
		    },
	
		    groupby: function(arr, attr) {
		        return lib.groupBy(arr, attr);
		    },
	
		    indent: function(str, width, indentfirst) {
		        str = normalize(str, '');
	
		        if (str === '') return '';
	
		        width = width || 4;
		        var res = '';
		        var lines = str.split('\n');
		        var sp = lib.repeat(' ', width);
	
		        for(var i=0; i<lines.length; i++) {
		            if(i === 0 && !indentfirst) {
		                res += lines[i] + '\n';
		            }
		            else {
		                res += sp + lines[i] + '\n';
		            }
		        }
	
		        return r.copySafeness(str, res);
		    },
	
		    join: function(arr, del, attr) {
		        del = del || '';
	
		        if(attr) {
		            arr = lib.map(arr, function(v) {
		                return v[attr];
		            });
		        }
	
		        return arr.join(del);
		    },
	
		    last: function(arr) {
		        return arr[arr.length-1];
		    },
	
		    length: function(val) {
		        var value = normalize(val, '');
	
		        if(value !== undefined) {
		            if(
		                (typeof Map === 'function' && value instanceof Map) ||
		                (typeof Set === 'function' && value instanceof Set)
		            ) {
		                // ECMAScript 2015 Maps and Sets
		                return value.size;
		            }
		            return value.length;
		        }
		        return 0;
		    },
	
		    list: function(val) {
		        if(lib.isString(val)) {
		            return val.split('');
		        }
		        else if(lib.isObject(val)) {
		            var keys = [];
	
		            if(Object.keys) {
		                keys = Object.keys(val);
		            }
		            else {
		                for(var k in val) {
		                    keys.push(k);
		                }
		            }
	
		            return lib.map(keys, function(k) {
		                return { key: k,
		                         value: val[k] };
		            });
		        }
		        else if(lib.isArray(val)) {
		          return val;
		        }
		        else {
		            throw new lib.TemplateError('list filter: type not iterable');
		        }
		    },
	
		    lower: function(str) {
		        str = normalize(str, '');
		        return str.toLowerCase();
		    },
	
		    random: function(arr) {
		        return arr[Math.floor(Math.random() * arr.length)];
		    },
	
		    rejectattr: function(arr, attr) {
		      return arr.filter(function (item) {
		        return !item[attr];
		      });
		    },
	
		    selectattr: function(arr, attr) {
		      return arr.filter(function (item) {
		        return !!item[attr];
		      });
		    },
	
		    replace: function(str, old, new_, maxCount) {
		        var originalStr = str;
	
		        if (old instanceof RegExp) {
		            return str.replace(old, new_);
		        }
	
		        if(typeof maxCount === 'undefined'){
		            maxCount = -1;
		        }
	
		        var res = '';  // Output
	
		        // Cast Numbers in the search term to string
		        if(typeof old === 'number'){
		            old = old + '';
		        }
		        else if(typeof old !== 'string') {
		            // If it is something other than number or string,
		            // return the original string
		            return str;
		        }
	
		        // Cast numbers in the replacement to string
		        if(typeof str === 'number'){
		            str = str + '';
		        }
	
		        // If by now, we don't have a string, throw it back
		        if(typeof str !== 'string' && !(str instanceof r.SafeString)){
		            return str;
		        }
	
		        // ShortCircuits
		        if(old === ''){
		            // Mimic the python behaviour: empty string is replaced
		            // by replacement e.g. "abc"|replace("", ".") -> .a.b.c.
		            res = new_ + str.split('').join(new_) + new_;
		            return r.copySafeness(str, res);
		        }
	
		        var nextIndex = str.indexOf(old);
		        // if # of replacements to perform is 0, or the string to does
		        // not contain the old value, return the string
		        if(maxCount === 0 || nextIndex === -1){
		            return str;
		        }
	
		        var pos = 0;
		        var count = 0; // # of replacements made
	
		        while(nextIndex  > -1 && (maxCount === -1 || count < maxCount)){
		            // Grab the next chunk of src string and add it with the
		            // replacement, to the result
		            res += str.substring(pos, nextIndex) + new_;
		            // Increment our pointer in the src string
		            pos = nextIndex + old.length;
		            count++;
		            // See if there are any more replacements to be made
		            nextIndex = str.indexOf(old, pos);
		        }
	
		        // We've either reached the end, or done the max # of
		        // replacements, tack on any remaining string
		        if(pos < str.length) {
		            res += str.substring(pos);
		        }
	
		        return r.copySafeness(originalStr, res);
		    },
	
		    reverse: function(val) {
		        var arr;
		        if(lib.isString(val)) {
		            arr = filters.list(val);
		        }
		        else {
		            // Copy it
		            arr = lib.map(val, function(v) { return v; });
		        }
	
		        arr.reverse();
	
		        if(lib.isString(val)) {
		            return r.copySafeness(val, arr.join(''));
		        }
		        return arr;
		    },
	
		    round: function(val, precision, method) {
		        precision = precision || 0;
		        var factor = Math.pow(10, precision);
		        var rounder;
	
		        if(method === 'ceil') {
		            rounder = Math.ceil;
		        }
		        else if(method === 'floor') {
		            rounder = Math.floor;
		        }
		        else {
		            rounder = Math.round;
		        }
	
		        return rounder(val * factor) / factor;
		    },
	
		    slice: function(arr, slices, fillWith) {
		        var sliceLength = Math.floor(arr.length / slices);
		        var extra = arr.length % slices;
		        var offset = 0;
		        var res = [];
	
		        for(var i=0; i<slices; i++) {
		            var start = offset + i * sliceLength;
		            if(i < extra) {
		                offset++;
		            }
		            var end = offset + (i + 1) * sliceLength;
	
		            var slice = arr.slice(start, end);
		            if(fillWith && i >= extra) {
		                slice.push(fillWith);
		            }
		            res.push(slice);
		        }
	
		        return res;
		    },
	
		    sum: function(arr, attr, start) {
		        var sum = 0;
	
		        if(typeof start === 'number'){
		            sum += start;
		        }
	
		        if(attr) {
		            arr = lib.map(arr, function(v) {
		                return v[attr];
		            });
		        }
	
		        for(var i = 0; i < arr.length; i++) {
		            sum += arr[i];
		        }
	
		        return sum;
		    },
	
		    sort: r.makeMacro(['value', 'reverse', 'case_sensitive', 'attribute'], [], function(arr, reverse, caseSens, attr) {
		         // Copy it
		        arr = lib.map(arr, function(v) { return v; });
	
		        arr.sort(function(a, b) {
		            var x, y;
	
		            if(attr) {
		                x = a[attr];
		                y = b[attr];
		            }
		            else {
		                x = a;
		                y = b;
		            }
	
		            if(!caseSens && lib.isString(x) && lib.isString(y)) {
		                x = x.toLowerCase();
		                y = y.toLowerCase();
		            }
	
		            if(x < y) {
		                return reverse ? 1 : -1;
		            }
		            else if(x > y) {
		                return reverse ? -1: 1;
		            }
		            else {
		                return 0;
		            }
		        });
	
		        return arr;
		    }),
	
		    string: function(obj) {
		        return r.copySafeness(obj, obj);
		    },
	
		    striptags: function(input, preserve_linebreaks) {
		        input = normalize(input, '');
		        preserve_linebreaks = preserve_linebreaks || false;
		        var tags = /<\/?([a-z][a-z0-9]*)\b[^>]*>|<!--[\s\S]*?-->/gi;
		        var trimmedInput = filters.trim(input.replace(tags, ''));
		        var res = '';
		        if (preserve_linebreaks) {
		            res = trimmedInput
		                .replace(/^ +| +$/gm, '')     // remove leading and trailing spaces
		                .replace(/ +/g, ' ')          // squash adjacent spaces
		                .replace(/(\r\n)/g, '\n')     // normalize linebreaks (CRLF -> LF)
		                .replace(/\n\n\n+/g, '\n\n'); // squash abnormal adjacent linebreaks
		        } else {
		            res = trimmedInput.replace(/\s+/gi, ' ');
		        }
		        return r.copySafeness(input, res);
		    },
	
		    title: function(str) {
		        str = normalize(str, '');
		        var words = str.split(' ');
		        for(var i = 0; i < words.length; i++) {
		            words[i] = filters.capitalize(words[i]);
		        }
		        return r.copySafeness(str, words.join(' '));
		    },
	
		    trim: function(str) {
		        return r.copySafeness(str, str.replace(/^\s*|\s*$/g, ''));
		    },
	
		    truncate: function(input, length, killwords, end) {
		        var orig = input;
		        input = normalize(input, '');
		        length = length || 255;
	
		        if (input.length <= length)
		            return input;
	
		        if (killwords) {
		            input = input.substring(0, length);
		        } else {
		            var idx = input.lastIndexOf(' ', length);
		            if(idx === -1) {
		                idx = length;
		            }
	
		            input = input.substring(0, idx);
		        }
	
		        input += (end !== undefined && end !== null) ? end : '...';
		        return r.copySafeness(orig, input);
		    },
	
		    upper: function(str) {
		        str = normalize(str, '');
		        return str.toUpperCase();
		    },
	
		    urlencode: function(obj) {
		        var enc = encodeURIComponent;
		        if (lib.isString(obj)) {
		            return enc(obj);
		        } else {
		            var parts;
		            if (lib.isArray(obj)) {
		                parts = obj.map(function(item) {
		                    return enc(item[0]) + '=' + enc(item[1]);
		                });
		            } else {
		                parts = [];
		                for (var k in obj) {
		                    if (obj.hasOwnProperty(k)) {
		                        parts.push(enc(k) + '=' + enc(obj[k]));
		                    }
		                }
		            }
		            return parts.join('&');
		        }
		    },
	
		    urlize: function(str, length, nofollow) {
		        if (isNaN(length)) length = Infinity;
	
		        var noFollowAttr = (nofollow === true ? ' rel="nofollow"' : '');
	
		        // For the jinja regexp, see
		        // https://github.com/mitsuhiko/jinja2/blob/f15b814dcba6aa12bc74d1f7d0c881d55f7126be/jinja2/utils.py#L20-L23
		        var puncRE = /^(?:\(|<|&lt;)?(.*?)(?:\.|,|\)|\n|&gt;)?$/;
		        // from http://blog.gerv.net/2011/05/html5_email_address_regexp/
		        var emailRE = /^[\w.!#$%&'*+\-\/=?\^`{|}~]+@[a-z\d\-]+(\.[a-z\d\-]+)+$/i;
		        var httpHttpsRE = /^https?:\/\/.*$/;
		        var wwwRE = /^www\./;
		        var tldRE = /\.(?:org|net|com)(?:\:|\/|$)/;
	
		        var words = str.split(/(\s+)/).filter(function(word) {
		          // If the word has no length, bail. This can happen for str with
		          // trailing whitespace.
		          return word && word.length;
		        }).map(function(word) {
		          var matches = word.match(puncRE);
		          var possibleUrl = matches && matches[1] || word;
	
		          // url that starts with http or https
		          if (httpHttpsRE.test(possibleUrl))
		            return '<a href="' + possibleUrl + '"' + noFollowAttr + '>' + possibleUrl.substr(0, length) + '</a>';
	
		          // url that starts with www.
		          if (wwwRE.test(possibleUrl))
		            return '<a href="http://' + possibleUrl + '"' + noFollowAttr + '>' + possibleUrl.substr(0, length) + '</a>';
	
		          // an email address of the form username@domain.tld
		          if (emailRE.test(possibleUrl))
		            return '<a href="mailto:' + possibleUrl + '">' + possibleUrl + '</a>';
	
		          // url that ends in .com, .org or .net that is not an email address
		          if (tldRE.test(possibleUrl))
		            return '<a href="http://' + possibleUrl + '"' + noFollowAttr + '>' + possibleUrl.substr(0, length) + '</a>';
	
		          return word;
	
		        });
	
		        return words.join('');
		    },
	
		    wordcount: function(str) {
		        str = normalize(str, '');
		        var words = (str) ? str.match(/\w+/g) : null;
		        return (words) ? words.length : null;
		    },
	
		    'float': function(val, def) {
		        var res = parseFloat(val);
		        return isNaN(res) ? def : res;
		    },
	
		    'int': function(val, def) {
		        var res = parseInt(val, 10);
		        return isNaN(res) ? def : res;
		    }
		};
	
		// Aliases
		filters.d = filters['default'];
		filters.e = filters.escape;
	
		module.exports = filters;
	
	
	/***/ },
	/* 8 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var lib = __webpack_require__(1);
		var Obj = __webpack_require__(6);
	
		// Frames keep track of scoping both at compile-time and run-time so
		// we know how to access variables. Block tags can introduce special
		// variables, for example.
		var Frame = Obj.extend({
		    init: function(parent, isolateWrites) {
		        this.variables = {};
		        this.parent = parent;
		        this.topLevel = false;
		        // if this is true, writes (set) should never propagate upwards past
		        // this frame to its parent (though reads may).
		        this.isolateWrites = isolateWrites;
		    },
	
		    set: function(name, val, resolveUp) {
		        // Allow variables with dots by automatically creating the
		        // nested structure
		        var parts = name.split('.');
		        var obj = this.variables;
		        var frame = this;
	
		        if(resolveUp) {
		            if((frame = this.resolve(parts[0], true))) {
		                frame.set(name, val);
		                return;
		            }
		        }
	
		        for(var i=0; i<parts.length - 1; i++) {
		            var id = parts[i];
	
		            if(!obj[id]) {
		                obj[id] = {};
		            }
		            obj = obj[id];
		        }
	
		        obj[parts[parts.length - 1]] = val;
		    },
	
		    get: function(name) {
		        var val = this.variables[name];
		        if(val !== undefined && val !== null) {
		            return val;
		        }
		        return null;
		    },
	
		    lookup: function(name) {
		        var p = this.parent;
		        var val = this.variables[name];
		        if(val !== undefined && val !== null) {
		            return val;
		        }
		        return p && p.lookup(name);
		    },
	
		    resolve: function(name, forWrite) {
		        var p = (forWrite && this.isolateWrites) ? undefined : this.parent;
		        var val = this.variables[name];
		        if(val !== undefined && val !== null) {
		            return this;
		        }
		        return p && p.resolve(name);
		    },
	
		    push: function(isolateWrites) {
		        return new Frame(this, isolateWrites);
		    },
	
		    pop: function() {
		        return this.parent;
		    }
		});
	
		function makeMacro(argNames, kwargNames, func) {
		    return function() {
		        var argCount = numArgs(arguments);
		        var args;
		        var kwargs = getKeywordArgs(arguments);
		        var i;
	
		        if(argCount > argNames.length) {
		            args = Array.prototype.slice.call(arguments, 0, argNames.length);
	
		            // Positional arguments that should be passed in as
		            // keyword arguments (essentially default values)
		            var vals = Array.prototype.slice.call(arguments, args.length, argCount);
		            for(i = 0; i < vals.length; i++) {
		                if(i < kwargNames.length) {
		                    kwargs[kwargNames[i]] = vals[i];
		                }
		            }
	
		            args.push(kwargs);
		        }
		        else if(argCount < argNames.length) {
		            args = Array.prototype.slice.call(arguments, 0, argCount);
	
		            for(i = argCount; i < argNames.length; i++) {
		                var arg = argNames[i];
	
		                // Keyword arguments that should be passed as
		                // positional arguments, i.e. the caller explicitly
		                // used the name of a positional arg
		                args.push(kwargs[arg]);
		                delete kwargs[arg];
		            }
	
		            args.push(kwargs);
		        }
		        else {
		            args = arguments;
		        }
	
		        return func.apply(this, args);
		    };
		}
	
		function makeKeywordArgs(obj) {
		    obj.__keywords = true;
		    return obj;
		}
	
		function getKeywordArgs(args) {
		    var len = args.length;
		    if(len) {
		        var lastArg = args[len - 1];
		        if(lastArg && lastArg.hasOwnProperty('__keywords')) {
		            return lastArg;
		        }
		    }
		    return {};
		}
	
		function numArgs(args) {
		    var len = args.length;
		    if(len === 0) {
		        return 0;
		    }
	
		    var lastArg = args[len - 1];
		    if(lastArg && lastArg.hasOwnProperty('__keywords')) {
		        return len - 1;
		    }
		    else {
		        return len;
		    }
		}
	
		// A SafeString object indicates that the string should not be
		// autoescaped. This happens magically because autoescaping only
		// occurs on primitive string objects.
		function SafeString(val) {
		    if(typeof val !== 'string') {
		        return val;
		    }
	
		    this.val = val;
		    this.length = val.length;
		}
	
		SafeString.prototype = Object.create(String.prototype, {
		    length: { writable: true, configurable: true, value: 0 }
		});
		SafeString.prototype.valueOf = function() {
		    return this.val;
		};
		SafeString.prototype.toString = function() {
		    return this.val;
		};
	
		function copySafeness(dest, target) {
		    if(dest instanceof SafeString) {
		        return new SafeString(target);
		    }
		    return target.toString();
		}
	
		function markSafe(val) {
		    var type = typeof val;
	
		    if(type === 'string') {
		        return new SafeString(val);
		    }
		    else if(type !== 'function') {
		        return val;
		    }
		    else {
		        return function() {
		            var ret = val.apply(this, arguments);
	
		            if(typeof ret === 'string') {
		                return new SafeString(ret);
		            }
	
		            return ret;
		        };
		    }
		}
	
		function suppressValue(val, autoescape) {
		    val = (val !== undefined && val !== null) ? val : '';
	
		    if(autoescape && typeof val === 'string') {
		        val = lib.escape(val);
		    }
	
		    return val;
		}
	
		function ensureDefined(val, lineno, colno) {
		    if(val === null || val === undefined) {
		        throw new lib.TemplateError(
		            'attempted to output null or undefined value',
		            lineno + 1,
		            colno + 1
		        );
		    }
		    return val;
		}
	
		function memberLookup(obj, val) {
		    obj = obj || {};
	
		    if(typeof obj[val] === 'function') {
		        return function() {
		            return obj[val].apply(obj, arguments);
		        };
		    }
	
		    return obj[val];
		}
	
		function callWrap(obj, name, context, args) {
		    if(!obj) {
		        throw new Error('Unable to call `' + name + '`, which is undefined or falsey');
		    }
		    else if(typeof obj !== 'function') {
		        throw new Error('Unable to call `' + name + '`, which is not a function');
		    }
	
		    // jshint validthis: true
		    return obj.apply(context, args);
		}
	
		function contextOrFrameLookup(context, frame, name) {
		    var val = frame.lookup(name);
		    return (val !== undefined && val !== null) ?
		        val :
		        context.lookup(name);
		}
	
		function handleError(error, lineno, colno) {
		    if(error.lineno) {
		        return error;
		    }
		    else {
		        return new lib.TemplateError(error, lineno, colno);
		    }
		}
	
		function asyncEach(arr, dimen, iter, cb) {
		    if(lib.isArray(arr)) {
		        var len = arr.length;
	
		        lib.asyncIter(arr, function(item, i, next) {
		            switch(dimen) {
		            case 1: iter(item, i, len, next); break;
		            case 2: iter(item[0], item[1], i, len, next); break;
		            case 3: iter(item[0], item[1], item[2], i, len, next); break;
		            default:
		                item.push(i, next);
		                iter.apply(this, item);
		            }
		        }, cb);
		    }
		    else {
		        lib.asyncFor(arr, function(key, val, i, len, next) {
		            iter(key, val, i, len, next);
		        }, cb);
		    }
		}
	
		function asyncAll(arr, dimen, func, cb) {
		    var finished = 0;
		    var len, i;
		    var outputArr;
	
		    function done(i, output) {
		        finished++;
		        outputArr[i] = output;
	
		        if(finished === len) {
		            cb(null, outputArr.join(''));
		        }
		    }
	
		    if(lib.isArray(arr)) {
		        len = arr.length;
		        outputArr = new Array(len);
	
		        if(len === 0) {
		            cb(null, '');
		        }
		        else {
		            for(i = 0; i < arr.length; i++) {
		                var item = arr[i];
	
		                switch(dimen) {
		                case 1: func(item, i, len, done); break;
		                case 2: func(item[0], item[1], i, len, done); break;
		                case 3: func(item[0], item[1], item[2], i, len, done); break;
		                default:
		                    item.push(i, done);
		                    // jshint validthis: true
		                    func.apply(this, item);
		                }
		            }
		        }
		    }
		    else {
		        var keys = lib.keys(arr);
		        len = keys.length;
		        outputArr = new Array(len);
	
		        if(len === 0) {
		            cb(null, '');
		        }
		        else {
		            for(i = 0; i < keys.length; i++) {
		                var k = keys[i];
		                func(k, arr[k], i, len, done);
		            }
		        }
		    }
		}
	
		module.exports = {
		    Frame: Frame,
		    makeMacro: makeMacro,
		    makeKeywordArgs: makeKeywordArgs,
		    numArgs: numArgs,
		    suppressValue: suppressValue,
		    ensureDefined: ensureDefined,
		    memberLookup: memberLookup,
		    contextOrFrameLookup: contextOrFrameLookup,
		    callWrap: callWrap,
		    handleError: handleError,
		    isArray: lib.isArray,
		    keys: lib.keys,
		    SafeString: SafeString,
		    copySafeness: copySafeness,
		    markSafe: markSafe,
		    asyncEach: asyncEach,
		    asyncAll: asyncAll,
		    inOperator: lib.inOperator
		};
	
	
	/***/ },
	/* 9 */
	/***/ function(module, exports) {
	
		'use strict';
	
		function cycler(items) {
		    var index = -1;
	
		    return {
		        current: null,
		        reset: function() {
		            index = -1;
		            this.current = null;
		        },
	
		        next: function() {
		            index++;
		            if(index >= items.length) {
		                index = 0;
		            }
	
		            this.current = items[index];
		            return this.current;
		        },
		    };
	
		}
	
		function joiner(sep) {
		    sep = sep || ',';
		    var first = true;
	
		    return function() {
		        var val = first ? '' : sep;
		        first = false;
		        return val;
		    };
		}
	
		// Making this a function instead so it returns a new object
		// each time it's called. That way, if something like an environment
		// uses it, they will each have their own copy.
		function globals() {
		    return {
		        range: function(start, stop, step) {
		            if(typeof stop === 'undefined') {
		                stop = start;
		                start = 0;
		                step = 1;
		            }
		            else if(!step) {
		                step = 1;
		            }
	
		            var arr = [];
		            var i;
		            if (step > 0) {
		                for (i=start; i<stop; i+=step) {
		                    arr.push(i);
		                }
		            } else {
		                for (i=start; i>stop; i+=step) {
		                    arr.push(i);
		                }
		            }
		            return arr;
		        },
	
		        // lipsum: function(n, html, min, max) {
		        // },
	
		        cycler: function() {
		            return cycler(Array.prototype.slice.call(arguments));
		        },
	
		        joiner: function(sep) {
		            return joiner(sep);
		        }
		    };
		}
	
		module.exports = globals;
	
	
	/***/ },
	/* 10 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var Loader = __webpack_require__(11);
	
		var PrecompiledLoader = Loader.extend({
		    init: function(compiledTemplates) {
		        this.precompiled = compiledTemplates || {};
		    },
	
		    getSource: function(name) {
		        if (this.precompiled[name]) {
		            return {
		                src: { type: 'code',
		                       obj: this.precompiled[name] },
		                path: name
		            };
		        }
		        return null;
		    }
		});
	
		module.exports = PrecompiledLoader;
	
	
	/***/ },
	/* 11 */
	/***/ function(module, exports, __webpack_require__) {
	
		'use strict';
	
		var path = __webpack_require__(3);
		var Obj = __webpack_require__(6);
		var lib = __webpack_require__(1);
	
		var Loader = Obj.extend({
		    on: function(name, func) {
		        this.listeners = this.listeners || {};
		        this.listeners[name] = this.listeners[name] || [];
		        this.listeners[name].push(func);
		    },
	
		    emit: function(name /*, arg1, arg2, ...*/) {
		        var args = Array.prototype.slice.call(arguments, 1);
	
		        if(this.listeners && this.listeners[name]) {
		            lib.each(this.listeners[name], function(listener) {
		                listener.apply(null, args);
		            });
		        }
		    },
	
		    resolve: function(from, to) {
		        return path.resolve(path.dirname(from), to);
		    },
	
		    isRelative: function(filename) {
		        return (filename.indexOf('./') === 0 || filename.indexOf('../') === 0);
		    }
		});
	
		module.exports = Loader;
	
	
	/***/ },
	/* 12 */
	/***/ function(module, exports) {
	
		function installCompat() {
		  'use strict';
	
		  // This must be called like `nunjucks.installCompat` so that `this`
		  // references the nunjucks instance
		  var runtime = this.runtime; // jshint ignore:line
		  var lib = this.lib; // jshint ignore:line
	
		  var orig_contextOrFrameLookup = runtime.contextOrFrameLookup;
		  runtime.contextOrFrameLookup = function(context, frame, key) {
		    var val = orig_contextOrFrameLookup.apply(this, arguments);
		    if (val === undefined) {
		      switch (key) {
		      case 'True':
		        return true;
		      case 'False':
		        return false;
		      case 'None':
		        return null;
		      }
		    }
	
		    return val;
		  };
	
		  var orig_memberLookup = runtime.memberLookup;
		  var ARRAY_MEMBERS = {
		    pop: function(index) {
		      if (index === undefined) {
		        return this.pop();
		      }
		      if (index >= this.length || index < 0) {
		        throw new Error('KeyError');
		      }
		      return this.splice(index, 1);
		    },
		    remove: function(element) {
		      for (var i = 0; i < this.length; i++) {
		        if (this[i] === element) {
		          return this.splice(i, 1);
		        }
		      }
		      throw new Error('ValueError');
		    },
		    count: function(element) {
		      var count = 0;
		      for (var i = 0; i < this.length; i++) {
		        if (this[i] === element) {
		          count++;
		        }
		      }
		      return count;
		    },
		    index: function(element) {
		      var i;
		      if ((i = this.indexOf(element)) === -1) {
		        throw new Error('ValueError');
		      }
		      return i;
		    },
		    find: function(element) {
		      return this.indexOf(element);
		    },
		    insert: function(index, elem) {
		      return this.splice(index, 0, elem);
		    }
		  };
		  var OBJECT_MEMBERS = {
		    items: function() {
		      var ret = [];
		      for(var k in this) {
		        ret.push([k, this[k]]);
		      }
		      return ret;
		    },
		    values: function() {
		      var ret = [];
		      for(var k in this) {
		        ret.push(this[k]);
		      }
		      return ret;
		    },
		    keys: function() {
		      var ret = [];
		      for(var k in this) {
		        ret.push(k);
		      }
		      return ret;
		    },
		    get: function(key, def) {
		      var output = this[key];
		      if (output === undefined) {
		        output = def;
		      }
		      return output;
		    },
		    has_key: function(key) {
		      return this.hasOwnProperty(key);
		    },
		    pop: function(key, def) {
		      var output = this[key];
		      if (output === undefined && def !== undefined) {
		        output = def;
		      } else if (output === undefined) {
		        throw new Error('KeyError');
		      } else {
		        delete this[key];
		      }
		      return output;
		    },
		    popitem: function() {
		      for (var k in this) {
		        // Return the first object pair.
		        var val = this[k];
		        delete this[k];
		        return [k, val];
		      }
		      throw new Error('KeyError');
		    },
		    setdefault: function(key, def) {
		      if (key in this) {
		        return this[key];
		      }
		      if (def === undefined) {
		        def = null;
		      }
		      return this[key] = def;
		    },
		    update: function(kwargs) {
		      for (var k in kwargs) {
		        this[k] = kwargs[k];
		      }
		      return null;  // Always returns None
		    }
		  };
		  OBJECT_MEMBERS.iteritems = OBJECT_MEMBERS.items;
		  OBJECT_MEMBERS.itervalues = OBJECT_MEMBERS.values;
		  OBJECT_MEMBERS.iterkeys = OBJECT_MEMBERS.keys;
		  runtime.memberLookup = function(obj, val, autoescape) { // jshint ignore:line
		    obj = obj || {};
	
		    // If the object is an object, return any of the methods that Python would
		    // otherwise provide.
		    if (lib.isArray(obj) && ARRAY_MEMBERS.hasOwnProperty(val)) {
		      return function() {return ARRAY_MEMBERS[val].apply(obj, arguments);};
		    }
	
		    if (lib.isObject(obj) && OBJECT_MEMBERS.hasOwnProperty(val)) {
		      return function() {return OBJECT_MEMBERS[val].apply(obj, arguments);};
		    }
	
		    return orig_memberLookup.apply(this, arguments);
		  };
		}
	
		module.exports = installCompat;
	
	
	/***/ }
	/******/ ]);
	
	/*** EXPORTS FROM exports-loader ***/
	module.exports = nunjucks;

/***/ },
/* 10 */
/***/ function(module, exports) {

	module.exports = function(env){
	    function parse (parser, nodes, lexer) {
	        var tok = parser.nextToken();
	        key = parser.parseSignature(null, true);
	        parser.advanceAfterBlockEnd(tok.value);
	        return new nodes.CallExtension(this, 'run', key);
	    }
	
	    function Translation () {
	        this.tags = ['trans'];
	        this.parse = parse;
	        this.run = function (ctx, key) {
	            return key;
	        };
	    }
	
	    function Ignore () {
	        this.tags = ['load'];
	        this.parse = parse;
	        this.run = function () {
	            return '';
	        };
	    }
	
	    env.addExtension('translation', new Translation());
	    env.addExtension('passThrough', new Ignore());
	}


/***/ },
/* 11 */
/***/ function(module, exports) {

	module.exports = function (nunjucks, env, obj, dependencies){
	
	    var oldRoot = obj.root;
	
	    obj.root = function( env, context, frame, runtime, ignoreMissing, cb ) {
	        var oldGetTemplate = env.getTemplate;
	        env.getTemplate = function (name, ec, parentName, ignoreMissing, cb) {
	            if( typeof ec === "function" ) {
	                cb = ec = false;
	            }
	            var _require = function (name) {
	                try {
	                    // add a reference to the already resolved dependency here
	                    return dependencies[name];
	                }
	                catch (e) {
	                    if (frame.get("_require")) {
	                        return frame.get("_require")(name);
	                    }
	                    else {
	                        console.warn('Could not load template "%s"', name);
	                    }
	                }
	            };
	
	            var tmpl = _require(name);
	            frame.set("_require", _require);
	
	            if( ec ) tmpl.compile();
	            cb( null, tmpl );
	        };
	
	        oldRoot(env, context, frame, runtime, ignoreMissing, function (err, res) {
	            env.getTemplate = oldGetTemplate;
	            cb( err, res );
	        });
	    };
	
	    var src = {
	        obj: obj,
	        type: 'code'
	    };
	
	    return new nunjucks.Template(src, env);
	
	};

/***/ },
/* 12 */
/***/ function(module, exports, __webpack_require__) {

	var nunjucks = __webpack_require__(9);
	var env;
	if (!nunjucks.currentEnv){
		env = nunjucks.currentEnv = new nunjucks.Environment([], { autoescape: true });
	} else {
		env = nunjucks.currentEnv;
	}
	var configure = __webpack_require__(10)(env);
	var dependencies = nunjucks.webpackDependencies || (nunjucks.webpackDependencies = {});
	
	
	
	
	var shim = __webpack_require__(11);
	
	
	(function() {(nunjucks.nunjucksPrecompiled = nunjucks.nunjucksPrecompiled || {})["cosinnus/templates/cosinnus/universal/map/map-controls.html"] = (function() {
	function root(env, context, frame, runtime, cb) {
	var lineno = null;
	var colno = null;
	var output = "";
	try {
	var parentTemplate = null;
	output += runtime.suppressValue(env.getExtension("passThrough")["run"](context,runtime.contextOrFrameLookup(context, frame, "i18n")), true && env.opts.autoescape);
	output += "\n<form id=\"map-search\">\n    <div class=\"line\">\n        <div class=\"result-filter check people\" data-result-type=\"people\">\n            <div class=\"box\">\n                ";
	if(runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"people")) {
	output += "\n                    <i class=\"fa fa-check\"></i>\n                ";
	;
	}
	output += "\n            </div>\n            <div class=\"check__label\">";
	output += runtime.suppressValue(env.getExtension("translation")["run"](context,"People"), true && env.opts.autoescape);
	output += "</div>\n        </div>\n    </div>\n\n    <div class=\"line\">\n        <div class=\"result-filter check events\" data-result-type=\"events\">\n            <div class=\"box\">\n                ";
	if(runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"events")) {
	output += "\n                    <i class=\"fa fa-check\"></i>\n                ";
	;
	}
	output += "\n            </div>\n            <div class=\"check__label\">";
	output += runtime.suppressValue(env.getExtension("translation")["run"](context,"Events"), true && env.opts.autoescape);
	output += "</div>\n        </div>\n    </div>\n\n    <div class=\"line\">\n        <div class=\"result-filter check projects\" data-result-type=\"projects\">\n            <div class=\"box\">\n                ";
	if(runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"projects")) {
	output += "\n                    <i class=\"fa fa-check\"></i>\n                ";
	;
	}
	output += "\n            </div>\n            <div class=\"check__label\">";
	output += runtime.suppressValue(env.getExtension("translation")["run"](context,"Projects"), true && env.opts.autoescape);
	output += "</div>\n        </div>\n    </div>\n\n    <div class=\"line\">\n        <div class=\"result-filter check groups\" data-result-type=\"groups\">\n            <div class=\"box\">\n                ";
	if(runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"groups")) {
	output += "\n                    <i class=\"fa fa-check\"></i>\n                ";
	;
	}
	output += "\n            </div>\n            <div class=\"check__label\">";
	output += runtime.suppressValue(env.getExtension("translation")["run"](context,"Groups"), true && env.opts.autoescape);
	output += "</div>\n        </div>\n    </div>\n\n    <div class=\"line link\">\n        ";
	if(!runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"people") || !runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"events") || !runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"projects") || !runtime.memberLookup((runtime.contextOrFrameLookup(context, frame, "filters")),"groups")) {
	output += "\n            <a href=\"#\" class=\"reset-filters\">\n                Alle anzeigen\n            </a>\n        ";
	;
	}
	else {
	output += "\n            &nbsp;\n        ";
	;
	}
	output += "\n    </div>\n\n    <div class=\"line text-field\">\n        <input type=\"text\" class=\"q\" name=\"q\" placeholder=\"Suche\" value=\"";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "q"), env.opts.autoescape);
	output += "\" />\n        <i class=\"fa fa-search icon-search\"></i>\n        <div class=\"icon-loading sk-double-bounce\">\n            <div class=\"sk-child sk-double-bounce1\"></div>\n            <div class=\"sk-child sk-double-bounce2\"></div>\n        </div>\n    </div>\n\n    <div class=\"message\"></div>\n</form>\n\n<div class=\"line button\">\n    <div data-layer=\"street\"\n        class=\"btn layer-button ";
	if(runtime.contextOrFrameLookup(context, frame, "layer") == "street") {
	output += " active ";
	;
	}
	output += "\">\n        Street\n    </div>\n\n    <div data-layer=\"satellite\"\n        class=\"btn layer-button ";
	if(runtime.contextOrFrameLookup(context, frame, "layer") == "satellite") {
	output += " active ";
	;
	}
	output += "\">\n        Satellite\n    </div>\n\n    <div data-layer=\"terrain\"\n        class=\"btn layer-button ";
	if(runtime.contextOrFrameLookup(context, frame, "layer") == "terrain") {
	output += " active ";
	;
	}
	output += "\">\n        Terrain\n    </div>\n</div>\n";
	if(parentTemplate) {
	parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
	} else {
	cb(null, output);
	}
	;
	} catch (e) {
	  cb(runtime.handleError(e, lineno, colno));
	}
	}
	return {
	root: root
	};
	
	})();
	})();
	
	
	
	module.exports = shim(nunjucks, env, nunjucks.nunjucksPrecompiled["cosinnus/templates/cosinnus/universal/map/map-controls.html"] , dependencies)

/***/ },
/* 13 */
/***/ function(module, exports, __webpack_require__) {

	var nunjucks = __webpack_require__(9);
	var env;
	if (!nunjucks.currentEnv){
		env = nunjucks.currentEnv = new nunjucks.Environment([], { autoescape: true });
	} else {
		env = nunjucks.currentEnv;
	}
	var configure = __webpack_require__(10)(env);
	var dependencies = nunjucks.webpackDependencies || (nunjucks.webpackDependencies = {});
	
	
	
	
	var shim = __webpack_require__(11);
	
	
	(function() {(nunjucks.nunjucksPrecompiled = nunjucks.nunjucksPrecompiled || {})["cosinnus/templates/cosinnus/universal/map/popup.html"] = (function() {
	function root(env, context, frame, runtime, cb) {
	var lineno = null;
	var colno = null;
	var output = "";
	try {
	var parentTemplate = null;
	output += "<div class=\"popup\">\n    <img src=\"";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "imageURL"), env.opts.autoescape);
	output += "\" />\n    <div class=\"details\">\n        <div class=\"link\">\n            <a href=\"";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "url"), env.opts.autoescape);
	output += "\">";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "title"), env.opts.autoescape);
	output += "</a>\n        </div>\n        <div class=\"address\">";
	output += runtime.suppressValue(runtime.contextOrFrameLookup(context, frame, "address"), env.opts.autoescape);
	output += "</div>\n    </div>\n</div>\n";
	if(parentTemplate) {
	parentTemplate.rootRenderFunc(env, context, frame, runtime, cb);
	} else {
	cb(null, output);
	}
	;
	} catch (e) {
	  cb(runtime.handleError(e, lineno, colno));
	}
	}
	return {
	root: root
	};
	
	})();
	})();
	
	
	
	module.exports = shim(nunjucks, env, nunjucks.nunjucksPrecompiled["cosinnus/templates/cosinnus/universal/map/popup.html"] , dependencies)

/***/ },
/* 14 */
/***/ function(module, exports) {

	'use strict';
	
	module.exports = {
	    protocol: function () {
	        return window.location.protocol;
	    }
	};


/***/ },
/* 15 */
/***/ function(module, exports) {

	'use strict';
	
	// Pub-sub event mediator and  data store.
	module.exports = {
	    publish: function (eventName, data) {
	        $('html').trigger(eventName, data);
	    },
	
	    subscribe: function (events, data, handler) {
	        $('html').on(events, data, handler);
	    }
	};


/***/ }
/******/ ]);
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly8vd2VicGFjay9ib290c3RyYXAgMDJiYzFkOTBhNmQwMjQ1NzAyN2MiLCJ3ZWJwYWNrOi8vLy4vY29zaW5udXMvY2xpZW50L2luZGV4LmpzIiwid2VicGFjazovLy8uL2Nvc2lubnVzL2NsaWVudC9hcHBsaWNhdGlvbi5qcyIsIndlYnBhY2s6Ly8vLi9jb3Npbm51cy9jbGllbnQvcm91dGVyLmpzIiwid2VicGFjazovLy8uL2Nvc2lubnVzL2NsaWVudC9tb2RlbHMvbWFwLmpzIiwid2VicGFjazovLy8uL2Nvc2lubnVzL2NsaWVudC92aWV3cy9tYXAtdmlldy5qcyIsIndlYnBhY2s6Ly8vLi9jb3Npbm51cy9jbGllbnQvdmlld3MvYmFzZS92aWV3LmpzIiwid2VicGFjazovLy8uL2Nvc2lubnVzL2NsaWVudC92aWV3cy9tYXAtY29udHJvbHMtdmlldy5qcyIsIndlYnBhY2s6Ly8vLi9jb3Npbm51cy9jbGllbnQvdmlld3MvZXJyb3Itdmlldy5qcyIsIndlYnBhY2s6Ly8vLi9jb3Npbm51cy90ZW1wbGF0ZXMvY29zaW5udXMvdW5pdmVyc2FsL3hoci1lcnJvci5odG1sIiwid2VicGFjazovLy8uL34vbnVuanVja3MvYnJvd3Nlci9udW5qdWNrcy1zbGltLmpzIiwid2VicGFjazovLy8uL251bmp1Y2tzLmNvbmZpZy5qcyIsIndlYnBhY2s6Ly8vLi9+L251bmp1Y2tzLWxvYWRlci9ydW50aW1lLXNoaW0uanMiLCJ3ZWJwYWNrOi8vLy4vY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC9tYXAvbWFwLWNvbnRyb2xzLmh0bWwiLCJ3ZWJwYWNrOi8vLy4vY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC9tYXAvcG9wdXAuaHRtbCIsIndlYnBhY2s6Ly8vLi9jb3Npbm51cy9jbGllbnQvbGliL3V0aWwuanMiLCJ3ZWJwYWNrOi8vLy4vY29zaW5udXMvY2xpZW50L21lZGlhdG9yLmpzIl0sIm5hbWVzIjpbXSwi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QUs7O0FBRUw7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxVQUFTO0FBQ1QsTUFBSzs7QUFFTDtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBLFVBQVM7QUFDVDtBQUNBO0FBQ0E7QUFDQSxjQUFhO0FBQ2I7QUFDQTtBQUNBLGNBQWE7QUFDYjtBQUNBLE1BQUs7O0FBRUw7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxNQUFLOztBQUVMO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxVQUFTO0FBQ1Q7QUFDQTtBQUNBLE1BQUs7O0FBRUw7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxVQUFTO0FBQ1QsTUFBSzs7QUFFTDtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLFVBQVM7O0FBRVQ7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLDBCQUF5QjtBQUN6QixzQkFBcUI7QUFDckI7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLHNCQUFxQjtBQUNyQixjQUFhO0FBQ2IsVUFBUztBQUNUO0FBQ0EsTUFBSzs7QUFFTDtBQUNBO0FBQ0E7QUFDQSxNQUFLOztBQUVMO0FBQ0E7QUFDQTtBQUNBLE1BQUs7O0FBRUw7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsTUFBSztBQUNMLEVBQUM7Ozs7Ozs7QUN6S0Q7O0FBRUE7QUFDQTtBQUNBO0FBQ0EsTUFBSzs7QUFFTDtBQUNBO0FBQ0EsNENBQTJDO0FBQzNDO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsVUFBUztBQUNUO0FBQ0EsTUFBSzs7QUFFTDtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsRUFBQzs7Ozs7OztBQ2hDRDs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE1BQUs7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Q0EsT0FBTTtBQUNOO0FBQ0EsT0FBTTtBQUNOO0FBQ0EsT0FBTTtBQUNOO0FBQ0E7QUFDQTtBQUNBOzs7QUFHQSxRQUFPO0FBQ1A7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSx1QkFBc0IsY0FBYyxFQUFFO0FBQ3RDOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0EsbUJBQWtCO0FBQ2xCO0FBQ0EsV0FBVTtBQUNWLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSw2QkFBNEIseUJBQXlCO0FBQ3JEO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsV0FBVTtBQUNWO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLGVBQWM7O0FBRWQ7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxXQUFVOztBQUVWO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0EsR0FBRTs7QUFFRjtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLHNCQUFxQix3QkFBd0I7QUFDN0M7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLEdBQUU7O0FBRUY7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQSxvREFBbUQ7QUFDbkQsb0RBQW1EO0FBQ25EO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsV0FBVTtBQUNWO0FBQ0E7QUFDQTtBQUNBOztBQUVBLDZDQUE0QztBQUM1QztBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLCtCQUE4QixXQUFXO0FBQ3pDO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0EsT0FBTTs7O0FBR047QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxXQUFVO0FBQ1Y7QUFDQTtBQUNBOztBQUVBO0FBQ0E7O0FBRUE7QUFDQSw2Q0FBNEM7QUFDNUM7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxxQkFBb0I7QUFDcEI7QUFDQTtBQUNBLCtCQUE4QjtBQUM5QixPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0EsR0FBRTs7QUFFRjtBQUNBO0FBQ0E7QUFDQTs7O0FBR0EsUUFBTztBQUNQO0FBQ0E7Ozs7QUFJQSxRQUFPO0FBQ1A7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLGNBQWEsTUFBTTtBQUNuQjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07QUFDTjtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07QUFDTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsV0FBVTtBQUNWO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07QUFDTjtBQUNBO0FBQ0E7QUFDQTs7O0FBR0EsUUFBTztBQUNQO0FBQ0E7O0FBRUEsZ0RBQStDOztBQUUvQztBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxrRUFBaUUsa0JBQWtCO0FBQ25GO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxHQUFFO0FBQ0Y7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsOEJBQTZCLG9CQUFvQjtBQUNqRDtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUEsOEJBQTZCLDRCQUE0QixhQUFhLEVBQUU7O0FBRXhFLFFBQU87QUFDUDtBQUNBOztBQUVBOztBQUVBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQSx5Q0FBd0MsS0FBSyxFQUFFO0FBQy9DOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQSxlQUFjO0FBQ2Q7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTs7QUFFQSw4Q0FBNkM7OztBQUc3QyxRQUFPO0FBQ1A7QUFDQTs7QUFFQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBOztBQUVBLG9CQUFtQixnQkFBZ0I7QUFDbkM7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTs7QUFFQTtBQUNBO0FBQ0EscUNBQW9DLGVBQWU7QUFDbkQ7QUFDQTtBQUNBOztBQUVBO0FBQ0E7O0FBRUE7QUFDQSxPQUFNOztBQUVOO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQSxXQUFVO0FBQ1Y7QUFDQSxXQUFVO0FBQ1Y7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0EsV0FBVTs7QUFFVjtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTs7QUFFQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQSxzQkFBcUIsZ0JBQWdCO0FBQ3JDO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBLGVBQWM7QUFDZDs7QUFFQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBLDBCQUF5QjtBQUN6QjtBQUNBLGVBQWM7QUFDZDtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE9BQU07O0FBRU47QUFDQTtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0EsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQSxTQUFRO0FBQ1IsT0FBTTs7QUFFTjtBQUNBO0FBQ0E7QUFDQSxTQUFRO0FBQ1IsT0FBTTs7QUFFTjtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUEsdUJBQXNCOztBQUV0QjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0Esd0JBQXVCOztBQUV2QjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNB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TTs7QUFFTjtBQUNBO0FBQ0E7QUFDQSxHQUFFOztBQUVGO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBLHdCQUF1QixpQkFBaUI7QUFDeEM7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUEsK0JBQThCLHFCQUFxQjtBQUNuRDs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBLGVBQWM7QUFDZCxHQUFFO0FBQ0Y7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBOztBQUVB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QTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLGdDQUErQjtBQUMvQjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLEVBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQSxFQUFDO0FBQ0Q7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBLEVBQUM7QUFDRCxFQUFDOzs7O0FBSUQsaUo7Ozs7OztBQ2xHQTtBQUNBO0FBQ0E7QUFDQSw0REFBMkQsbUJBQW1CO0FBQzlFLEVBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQSxzRkFBcUY7Ozs7O0FBS3JGOzs7QUFHQSxjQUFhLGtFQUFrRTtBQUMvRTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsRUFBQztBQUNEO0FBQ0E7QUFDQTtBQUNBLEVBQUM7QUFDRDtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUEsRUFBQztBQUNELEVBQUM7Ozs7QUFJRCwwSTs7Ozs7O0FDbkRBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7Ozs7Ozs7QUNOQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLE1BQUs7O0FBRUw7QUFDQTtBQUNBO0FBQ0EiLCJmaWxlIjoiY2xpZW50LmpzIiwic291cmNlc0NvbnRlbnQiOlsiIFx0Ly8gVGhlIG1vZHVsZSBjYWNoZVxuIFx0dmFyIGluc3RhbGxlZE1vZHVsZXMgPSB7fTtcblxuIFx0Ly8gVGhlIHJlcXVpcmUgZnVuY3Rpb25cbiBcdGZ1bmN0aW9uIF9fd2VicGFja19yZXF1aXJlX18obW9kdWxlSWQpIHtcblxuIFx0XHQvLyBDaGVjayBpZiBtb2R1bGUgaXMgaW4gY2FjaGVcbiBcdFx0aWYoaW5zdGFsbGVkTW9kdWxlc1ttb2R1bGVJZF0pXG4gXHRcdFx0cmV0dXJuIGluc3RhbGxlZE1vZHVsZXNbbW9kdWxlSWRdLmV4cG9ydHM7XG5cbiBcdFx0Ly8gQ3JlYXRlIGEgbmV3IG1vZHVsZSAoYW5kIHB1dCBpdCBpbnRvIHRoZSBjYWNoZSlcbiBcdFx0dmFyIG1vZHVsZSA9IGluc3RhbGxlZE1vZHVsZXNbbW9kdWxlSWRdID0ge1xuIFx0XHRcdGV4cG9ydHM6IHt9LFxuIFx0XHRcdGlkOiBtb2R1bGVJZCxcbiBcdFx0XHRsb2FkZWQ6IGZhbHNlXG4gXHRcdH07XG5cbiBcdFx0Ly8gRXhlY3V0ZSB0aGUgbW9kdWxlIGZ1bmN0aW9uXG4gXHRcdG1vZHVsZXNbbW9kdWxlSWRdLmNhbGwobW9kdWxlLmV4cG9ydHMsIG1vZHVsZSwgbW9kdWxlLmV4cG9ydHMsIF9fd2VicGFja19yZXF1aXJlX18pO1xuXG4gXHRcdC8vIEZsYWcgdGhlIG1vZHVsZSBhcyBsb2FkZWRcbiBcdFx0bW9kdWxlLmxvYWRlZCA9IHRydWU7XG5cbiBcdFx0Ly8gUmV0dXJuIHRoZSBleHBvcnRzIG9mIHRoZSBtb2R1bGVcbiBcdFx0cmV0dXJuIG1vZHVsZS5leHBvcnRzO1xuIFx0fVxuXG5cbiBcdC8vIGV4cG9zZSB0aGUgbW9kdWxlcyBvYmplY3QgKF9fd2VicGFja19tb2R1bGVzX18pXG4gXHRfX3dlYnBhY2tfcmVxdWlyZV9fLm0gPSBtb2R1bGVzO1xuXG4gXHQvLyBleHBvc2UgdGhlIG1vZHVsZSBjYWNoZVxuIFx0X193ZWJwYWNrX3JlcXVpcmVfXy5jID0gaW5zdGFsbGVkTW9kdWxlcztcblxuIFx0Ly8gX193ZWJwYWNrX3B1YmxpY19wYXRoX19cbiBcdF9fd2VicGFja19yZXF1aXJlX18ucCA9IFwiXCI7XG5cbiBcdC8vIExvYWQgZW50cnkgbW9kdWxlIGFuZCByZXR1cm4gZXhwb3J0c1xuIFx0cmV0dXJuIF9fd2VicGFja19yZXF1aXJlX18oMCk7XG5cblxuXG4vKiogV0VCUEFDSyBGT09URVIgKipcbiAqKiB3ZWJwYWNrL2Jvb3RzdHJhcCAwMmJjMWQ5MGE2ZDAyNDU3MDI3Y1xuICoqLyIsIi8vIE1haW4gSmF2YVNjcmlwdCBmaWxlIOKAlCBtYWluIGVudHJ5IGZvciB3ZWJwYWNrXG5cbid1c2Ugc3RyaWN0JztcblxudmFyIEFwcGxpY2F0aW9uID0gcmVxdWlyZSgnYXBwbGljYXRpb24nKTtcblxuJChmdW5jdGlvbiAoKSB7XG4gICAgbmV3IEFwcGxpY2F0aW9uKCkuc3RhcnQoKTtcbn0pO1xuXG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL2Nvc2lubnVzL2NsaWVudC9pbmRleC5qc1xuICoqIG1vZHVsZSBpZCA9IDBcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIid1c2Ugc3RyaWN0JztcblxuLy8gTWFpbiBhcHBsaWNhdGlvbiBjbGFzc1xuXG52YXIgUm91dGVyID0gcmVxdWlyZSgncm91dGVyJyk7XG52YXIgbWVkaWF0b3IgPSByZXF1aXJlKCdtZWRpYXRvcicpO1xuXG5tb2R1bGUuZXhwb3J0cyA9IGZ1bmN0aW9uIEFwcGxpY2F0aW9uICgpIHtcbiAgICBzZWxmID0gdGhpcztcblxuICAgIHNlbGYucm91dGVyID0gbmV3IFJvdXRlcigpO1xuXG4gICAgc2VsZi5zdGFydCA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgc2VsZi5pbml0TWVkaWF0b3IoKTtcbiAgICAgICAgLy8gU3RhcnQgcm91dGluZy4uLlxuICAgICAgICBCYWNrYm9uZS5oaXN0b3J5LnN0YXJ0KHtcbiAgICAgICAgICAgIHB1c2hTdGF0ZTogdHJ1ZVxuICAgICAgICB9KTtcbiAgICAgICAgLy8gQSBnbG9iYWwgcmVzaXplIGV2ZW50XG4gICAgICAgICQod2luZG93KS5vbigncmVzaXplJywgZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgQmFja2JvbmUubWVkaWF0b3IucHVibGlzaCgncmVzaXplOndpbmRvdycpO1xuICAgICAgICB9KTtcbiAgICB9O1xuXG4gICAgc2VsZi5pbml0TWVkaWF0b3IgPSBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHNlbGYubWVkaWF0b3IgPSBCYWNrYm9uZS5tZWRpYXRvciA9IG1lZGlhdG9yO1xuICAgICAgICBzZWxmLm1lZGlhdG9yLnNldHRpbmdzID0gd2luZG93LnNldHRpbmdzIHx8IHt9O1xuICAgICAgICBzZWxmLm1lZGlhdG9yLnN1YnNjcmliZSgnbmF2aWdhdGU6cm91dGVyJywgZnVuY3Rpb24gKGV2ZW50LCB1cmwpIHtcbiAgICAgICAgICAgIGlmICh1cmwpIHtcbiAgICAgICAgICAgICAgICBzZWxmLnJvdXRlci5uYXZpZ2F0ZSh1cmwsIHtcbiAgICAgICAgICAgICAgICAgICAgdHJpZ2dlcjogZmFsc2VcbiAgICAgICAgICAgICAgICB9KTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSk7XG4gICAgfTtcbn07XG5cblxuXG4vKioqKioqKioqKioqKioqKipcbiAqKiBXRUJQQUNLIEZPT1RFUlxuICoqIC4vY29zaW5udXMvY2xpZW50L2FwcGxpY2F0aW9uLmpzXG4gKiogbW9kdWxlIGlkID0gMVxuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIiwiJ3VzZSBzdHJpY3QnXG5cbnZhciBNYXAgPSByZXF1aXJlKCdtb2RlbHMvbWFwJyk7XG52YXIgTWFwVmlldyA9IHJlcXVpcmUoJ3ZpZXdzL21hcC12aWV3Jyk7XG5cbm1vZHVsZS5leHBvcnRzID0gQmFja2JvbmUuUm91dGVyLmV4dGVuZCh7XG4gICAgcm91dGVzOiB7XG4gICAgICAgICdtYXAvJzogJ21hcCdcbiAgICB9LFxuXG4gICAgbWFwOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIC8vIElmIHRoZSBtYXAgdmlldyBoYXNuJ3QgYmVlbiBpbnN0YW50aWF0ZWQsIGNyZWF0ZSBhbmQgcmVuZGVyIGl0LlxuICAgICAgICBpZiAoIXRoaXMubWFwRnVsbHNjcmVlbikge1xuICAgICAgICAgICAgdGhpcy5tYXBGdWxsc2NyZWVuID0gbmV3IE1hcCgpO1xuICAgICAgICAgICAgdmFyIHZpZXcgPSBuZXcgTWFwVmlldyh7XG4gICAgICAgICAgICAgICAgZWw6ICcjbWFwLWZ1bGxzY3JlZW4nLFxuICAgICAgICAgICAgICAgIG1vZGVsOiB0aGlzLm1hcEZ1bGxzY3JlZW5cbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgdmlldy5yZW5kZXIoKTtcbiAgICAgICAgLy8gT3RoZXJ3aXNlIG5hdmlnYXRpb24gaGFzIG9jY3VycmVkIGJldHdlZW4gbWFwIHN0YXRlcy5cbiAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgIEJhY2tib25lLm1lZGlhdG9yLnB1Ymxpc2goJ25hdmlnYXRlOm1hcCcpO1xuICAgICAgICB9XG4gICAgfVxufSk7XG5cblxuXG4vKioqKioqKioqKioqKioqKipcbiAqKiBXRUJQQUNLIEZPT1RFUlxuICoqIC4vY29zaW5udXMvY2xpZW50L3JvdXRlci5qc1xuICoqIG1vZHVsZSBpZCA9IDJcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIid1c2Ugc3RyaWN0JztcblxubW9kdWxlLmV4cG9ydHMgPSBCYWNrYm9uZS5Nb2RlbC5leHRlbmQoe1xuICAgIGRlZmF1bHQ6IHtcbiAgICAgICAgZmlsdGVyczoge1xuICAgICAgICAgICAgcGVvcGxlOiB0cnVlLFxuICAgICAgICAgICAgZXZlbnRzOiB0cnVlLFxuICAgICAgICAgICAgcHJvamVjdHM6IHRydWUsXG4gICAgICAgICAgICBncm91cHM6IHRydWVcbiAgICAgICAgfSxcbiAgICAgICAgbGF5ZXI6ICdzdHJlZXQnXG4gICAgfSxcblxuICAgIGluaXRpYWxpemU6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNlbGYgPSB0aGlzO1xuICAgICAgICBzZWxmLnNldCgnZmlsdGVycycsIF8oc2VsZi5kZWZhdWx0LmZpbHRlcnMpLmNsb25lKCkpO1xuICAgICAgICBzZWxmLnNldCgnbGF5ZXInLCBzZWxmLmRlZmF1bHQubGF5ZXIpO1xuICAgICAgICBzZWxmLnNlYXJjaERlbGF5ID0gMTAwMCxcbiAgICAgICAgc2VsZi53aGlsZVNlYXJjaGluZ0RlbGF5ID0gNTAwMDtcbiAgICAgICAgQmFja2JvbmUubWVkaWF0b3Iuc3Vic2NyaWJlKCduYXZpZ2F0ZTptYXAnLCBmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICBzZWxmLmluaXRpYWxTZWFyY2goKTtcbiAgICAgICAgfSk7XG4gICAgfSxcblxuICAgIHNlYXJjaDogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgc2VsZiA9IHRoaXM7XG4gICAgICAgIHZhciB1cmwgPSB0aGlzLmJ1aWxkVVJMKCk7XG4gICAgICAgIHNlbGYuc2V0KCdzZWFyY2hpbmcnLCB0cnVlKTtcbiAgICAgICAgJC5nZXQodXJsLCBmdW5jdGlvbiAocmVzKSB7XG4gICAgICAgICAgICBzZWxmLnNldCgnc2VhcmNoaW5nJywgZmFsc2UpO1xuICAgICAgICAgICAgc2VsZi50cmlnZ2VyKCdlbmQ6c2VhcmNoJyk7XG4gICAgICAgICAgICAvLyAoVGhlIHNlYXJjaCBlbmRwb2ludCBpcyBzaW5nbGUtdGhyZWFkKS5cbiAgICAgICAgICAgIC8vIElmIHRoZXJlIGlzIGEgcXVldWVkIHNlYXJjaCwgcmVxdWV1ZSBpdC5cbiAgICAgICAgICAgIGlmIChzZWxmLmdldCgnd2FudHNUb1NlYXJjaCcpKSB7XG4gICAgICAgICAgICAgICAgc2VsZi5hdHRlbXB0U2VhcmNoKCk7XG4gICAgICAgICAgICAvLyBVcGRhdGUgdGhlIHJlc3VsdHMgaWYgdGhlcmUgaXNuJ3QgYSBxdWV1ZWQgc2VhcmNoLlxuICAgICAgICAgICAgfSBlbHNlIHtcbiAgICAgICAgICAgICAgICBzZWxmLnNldCgncmVzdWx0cycsIHJlcyk7XG4gICAgICAgICAgICAgICAgc2VsZi50cmlnZ2VyKCdjaGFuZ2U6cmVzdWx0cycpO1xuICAgICAgICAgICAgICAgIC8vIFNhdmUgdGhlIHNlYXJjaCBzdGF0ZSBpbiB0aGUgdXJsLlxuICAgICAgICAgICAgICAgIEJhY2tib25lLm1lZGlhdG9yLnB1Ymxpc2goJ25hdmlnYXRlOnJvdXRlcicsIHVybC5yZXBsYWNlKCcvbWFwcy9zZWFyY2gnLCAnL21hcC8nKSlcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSkuZmFpbChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICBzZWxmLnNldCgnc2VhcmNoaW5nJywgZmFsc2UpO1xuICAgICAgICAgICAgc2VsZi50cmlnZ2VyKCdlbmQ6c2VhcmNoJyk7XG4gICAgICAgICAgICBzZWxmLnRyaWdnZXIoJ2Vycm9yOnNlYXJjaCcpO1xuICAgICAgICB9KTtcbiAgICB9LFxuXG4gICAgaW5pdGlhbFNlYXJjaDogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIganNvbiA9IHRoaXMucGFyc2VVcmwod2luZG93LmxvY2F0aW9uLmhyZWYucmVwbGFjZSh3aW5kb3cubG9jYXRpb24ub3JpZ2luLCAnJykpO1xuICAgICAgICBpZiAoXyhqc29uKS5rZXlzKCkubGVuZ3RoKSB7XG4gICAgICAgICAgICB0aGlzLnNldCh7XG4gICAgICAgICAgICAgICAgZmlsdGVyczoge1xuICAgICAgICAgICAgICAgICAgICBwZW9wbGU6IGpzb24ucGVvcGxlLFxuICAgICAgICAgICAgICAgICAgICBldmVudHM6IGpzb24uZXZlbnRzLFxuICAgICAgICAgICAgICAgICAgICBwcm9qZWN0czoganNvbi5wcm9qZWN0cyxcbiAgICAgICAgICAgICAgICAgICAgZ3JvdXBzOiBqc29uLmdyb3Vwc1xuICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgcToganNvbi5xLFxuICAgICAgICAgICAgICAgIG5vcnRoOiBqc29uLm5lX2xhdCxcbiAgICAgICAgICAgICAgICBlYXN0OiBqc29uLm5lX2xvbixcbiAgICAgICAgICAgICAgICBzb3V0aDoganNvbi5zd19sYXQsXG4gICAgICAgICAgICAgICAgd2VzdDoganNvbi5zd19sb25cbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgdGhpcy50cmlnZ2VyKCdjaGFuZ2U6Ym91bmRzJyk7XG4gICAgICAgICAgICB0aGlzLnRyaWdnZXIoJ2NoYW5nZTpjb250cm9scycpO1xuICAgICAgICB9XG4gICAgICAgIHRoaXMuc2VhcmNoKCk7XG4gICAgfSxcblxuICAgIGJ1aWxkVVJMOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBzZWFyY2hQYXJhbXMgPSB7XG4gICAgICAgICAgICBxOiB0aGlzLmdldCgncScpLFxuICAgICAgICAgICAgbmVfbGF0OiB0aGlzLmdldCgnbm9ydGgnKSxcbiAgICAgICAgICAgIG5lX2xvbjogdGhpcy5nZXQoJ2Vhc3QnKSxcbiAgICAgICAgICAgIHN3X2xhdDogdGhpcy5nZXQoJ3NvdXRoJyksXG4gICAgICAgICAgICBzd19sb246IHRoaXMuZ2V0KCd3ZXN0JyksXG4gICAgICAgICAgICBwZW9wbGU6IHRoaXMuZ2V0KCdmaWx0ZXJzJykucGVvcGxlLFxuICAgICAgICAgICAgZXZlbnRzOiB0aGlzLmdldCgnZmlsdGVycycpLmV2ZW50cyxcbiAgICAgICAgICAgIHByb2plY3RzOiB0aGlzLmdldCgnZmlsdGVycycpLnByb2plY3RzLFxuICAgICAgICAgICAgZ3JvdXBzOiB0aGlzLmdldCgnZmlsdGVycycpLmdyb3Vwc1xuICAgICAgICB9O1xuICAgICAgICB2YXIgcXVlcnkgPSAkLnBhcmFtKHNlYXJjaFBhcmFtcyk7XG4gICAgICAgIHJldHVybiAnL21hcHMvc2VhcmNoPycgKyBxdWVyeTtcbiAgICB9LFxuXG4gICAgdG9nZ2xlRmlsdGVyIChyZXN1bHRUeXBlKSB7XG4gICAgICAgIHZhciBmaWx0ZXJzID0gdGhpcy5nZXQoJ2ZpbHRlcnMnKTtcbiAgICAgICAgZmlsdGVyc1tyZXN1bHRUeXBlXSA9ICFmaWx0ZXJzW3Jlc3VsdFR5cGVdO1xuICAgICAgICB0aGlzLnNldCgnZmlsdGVycycsIGZpbHRlcnMpO1xuICAgICAgICB0aGlzLmF0dGVtcHRTZWFyY2goKTtcbiAgICB9LFxuXG4gICAgcmVzZXRGaWx0ZXJzOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHRoaXMuc2V0KCdmaWx0ZXJzJywgXyh0aGlzLmRlZmF1bHQuZmlsdGVycykuY2xvbmUoKSk7XG4gICAgICAgIHRoaXMuYXR0ZW1wdFNlYXJjaCgpO1xuICAgIH0sXG5cbiAgICAvLyBSZWdpc3RlciBhIGNoYW5nZSBpbiB0aGUgY29udHJvbHMgb3IgdGhlIG1hcCBVSSB3aGljaCBzaG91bGQgcXVldWVcbiAgICAvLyBhIHNlYXJjaCBhdHRlbXB0LlxuICAgIGF0dGVtcHRTZWFyY2g6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNlbGYgPSB0aGlzLFxuICAgICAgICAgICAgLy8gSW5jcmVhc2UgdGhlIHNlYXJjaCBkZWxheSB3aGVuIGEgc2VhcmNoIGlzIGluIHByb2dyZXNzLlxuICAgICAgICAgICAgZGVsYXkgPSBzZWxmLmdldCgnc2VhcmNoaW5nJykgP1xuICAgICAgICAgICAgICAgIHNlbGYud2hpbGVTZWFyY2hpbmdEZWxheSA6IHNlbGYuc2VhcmNoRGVsYXk7XG4gICAgICAgIGNsZWFyVGltZW91dCh0aGlzLnNlYXJjaFRpbWVvdXQpO1xuICAgICAgICBzZWxmLnNldCgnd2FudHNUb1NlYXJjaCcsIHRydWUpO1xuICAgICAgICBzZWxmLnRyaWdnZXIoJ3dhbnQ6c2VhcmNoJyk7XG4gICAgICAgIHNlbGYuc2VhcmNoVGltZW91dCA9IHNldFRpbWVvdXQoZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgc2VsZi5zZWFyY2goKTtcbiAgICAgICAgICAgIHNlbGYuc2V0KCd3YW50c1RvU2VhcmNoJywgZmFsc2UpO1xuICAgICAgICB9LCBkZWxheSk7XG4gICAgfSxcblxuICAgIHBhcnNlVXJsOiBmdW5jdGlvbiAodXJsKSB7XG4gICAgICAgIGlmICh1cmwuaW5kZXhPZignPycpID49IDApIHtcbiAgICAgICAgICAgIHZhciBqc29uID0gSlNPTi5wYXJzZSgne1wiJyArIGRlY29kZVVSSSh1cmwucmVwbGFjZSgvW14/XSpcXD8vLCAnJykucmVwbGFjZSgvJi9nLCBcIlxcXCIsXFxcIlwiKS5yZXBsYWNlKC89L2csXCJcXFwiOlxcXCJcIikpICsgJ1wifScpXG4gICAgICAgIH0gZWxzZSB7XG4gICAgICAgICAgICB2YXIganNvbiA9IHt9O1xuICAgICAgICB9XG4gICAgICAgIF8oXyhqc29uKS5rZXlzKCkpLmVhY2goZnVuY3Rpb24gKGtleSkge1xuICAgICAgICAgICAgaWYgKGpzb25ba2V5XSAhPT0gJycpIHtcbiAgICAgICAgICAgICAgICB0cnkge1xuICAgICAgICAgICAgICAgICAgICBqc29uW2tleV0gPSBKU09OLnBhcnNlKGpzb25ba2V5XSk7XG4gICAgICAgICAgICAgICAgfSBjYXRjaCAoZXJyKSB7fVxuICAgICAgICAgICAgfVxuICAgICAgICB9KTtcbiAgICAgICAgcmV0dXJuIGpzb247XG4gICAgfSxcblxuICAgIGFjdGl2ZUZpbHRlcnM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIF8oXyh0aGlzLmdldCgnZmlsdGVycycpKS5rZXlzKCkpLnNlbGVjdChmdW5jdGlvbiAoZmlsdGVyKSB7XG4gICAgICAgICAgICByZXR1cm4gISFmaWx0ZXI7XG4gICAgICAgIH0pO1xuICAgIH1cbn0pO1xuXG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL2Nvc2lubnVzL2NsaWVudC9tb2RlbHMvbWFwLmpzXG4gKiogbW9kdWxlIGlkID0gM1xuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIiwiJ3VzZSBzdHJpY3QnO1xuXG52YXIgVmlldyA9IHJlcXVpcmUoJ3ZpZXdzL2Jhc2UvdmlldycpO1xudmFyIE1hcENvbnRyb2xzVmlldyA9IHJlcXVpcmUoJ3ZpZXdzL21hcC1jb250cm9scy12aWV3Jyk7XG52YXIgcG9wdXBUZW1wbGF0ZSA9IHJlcXVpcmUoJ21hcC9wb3B1cCcpO1xudmFyIHV0aWwgPSByZXF1aXJlKCdsaWIvdXRpbCcpO1xuXG5tb2R1bGUuZXhwb3J0cyA9IFZpZXcuZXh0ZW5kKHtcbiAgICBsYXllcnM6IHtcbiAgICAgICAgc3RyZWV0OiB7XG4gICAgICAgICAgICB1cmw6ICh1dGlsLnByb3RvY29sKCkgPT09ICdodHRwOicgP1xuICAgICAgICAgICAgICAgICdodHRwOi8ve3N9LmJhc2VtYXBzLmNhcnRvY2RuLmNvbS9saWdodF9hbGwve3p9L3t4fS97eX1AMngucG5nJyA6XG4gICAgICAgICAgICAgICAgJ2h0dHBzOi8vY2FydG9kYi1iYXNlbWFwcy17c30uZ2xvYmFsLnNzbC5mYXN0bHkubmV0L2xpZ2h0X2FsbC97en0ve3h9L3t5fS5wbmcnKSxcbiAgICAgICAgICAgIG9wdGlvbnM6IHtcbiAgICAgICAgICAgICAgICBhdHRyaWJ1dGlvbjogJ0NhcnRvREIgfCBPcGVuIFN0cmVldG1hcCdcbiAgICAgICAgICAgIH1cbiAgICAgICAgfSxcbiAgICAgICAgc2F0ZWxsaXRlOiB7XG4gICAgICAgICAgICB1cmw6IHV0aWwucHJvdG9jb2woKSArICcvL3tzfS5nb29nbGUuY29tL3Z0L2x5cnM9cyZ4PXt4fSZ5PXt5fSZ6PXt6fScsXG4gICAgICAgICAgICBvcHRpb25zOiB7XG4gICAgICAgICAgICAgICAgYXR0cmlidXRpb246ICdHb29nbGUgTWFwcycsXG4gICAgICAgICAgICAgICAgc3ViZG9tYWluczpbJ210MCcsJ210MScsJ210MicsJ210MyddXG4gICAgICAgICAgICB9XG4gICAgICAgIH0sXG4gICAgICAgIHRlcnJhaW46IHtcbiAgICAgICAgICAgIHVybDogdXRpbC5wcm90b2NvbCgpICsgJy8ve3N9Lmdvb2dsZS5jb20vdnQvbHlycz1wJng9e3h9Jnk9e3l9Jno9e3p9JyxcbiAgICAgICAgICAgIG9wdGlvbnM6IHtcbiAgICAgICAgICAgICAgICBhdHRyaWJ1dGlvbjogJ0dvb2dsZSBNYXBzJyxcbiAgICAgICAgICAgICAgICBzdWJkb21haW5zOlsnbXQwJywnbXQxJywnbXQyJywnbXQzJ11cbiAgICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgIH0sXG5cbiAgICByZXN1bHRDb2xvdXJzOiB7XG4gICAgICAgIHBlb3BsZTogJ3JlZCcsXG4gICAgICAgIGV2ZW50czogJ3llbGxvdycsXG4gICAgICAgIHByb2plY3RzOiAnZ3JlZW4nLFxuICAgICAgICBncm91cHM6ICdibHVlJ1xuICAgIH0sXG5cbiAgICBpbml0aWFsaXplOiBmdW5jdGlvbiAoKSB7XG4gICAgICAgIHZhciBzZWxmID0gdGhpcztcbiAgICAgICAgc2VsZi5jb250cm9sc1ZpZXcgPSBuZXcgTWFwQ29udHJvbHNWaWV3KHtcbiAgICAgICAgICAgIGVsOiAkKCcjbWFwLWNvbnRyb2xzJyksXG4gICAgICAgICAgICBtb2RlbDogc2VsZi5tb2RlbFxuICAgICAgICB9KTtcbiAgICAgICAgc2VsZi5jb250cm9sc1ZpZXcub24oJ2NoYW5nZTpsYXllcicsIHNlbGYuaGFuZGxlU3dpdGNoTGF5ZXIsIHNlbGYpO1xuICAgICAgICBzZWxmLm1vZGVsLm9uKCdjaGFuZ2U6cmVzdWx0cycsIHNlbGYudXBkYXRlTWFya2Vycywgc2VsZik7XG4gICAgICAgIHNlbGYubW9kZWwub24oJ2NoYW5nZTpib3VuZHMnLCBzZWxmLmZpdEJvdW5kcywgc2VsZik7XG4gICAgICAgIEJhY2tib25lLm1lZGlhdG9yLnN1YnNjcmliZSgncmVzaXplOndpbmRvdycsIGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHNlbGYubGVhZmxldC5pbnZhbGlkYXRlU2l6ZSgpO1xuICAgICAgICAgICAgc2VsZi5oYW5kbGVWaWV3cG9ydENoYW5nZSgpO1xuICAgICAgICB9KTtcbiAgICAgICAgVmlldy5wcm90b3R5cGUuaW5pdGlhbGl6ZS5jYWxsKHRoaXMpO1xuICAgIH0sXG5cbiAgICByZW5kZXI6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNlbGYgPSB0aGlzO1xuXG4gICAgICAgIHNlbGYuc2V0U3RhcnRQb3MoZnVuY3Rpb24gKCkge1xuICAgICAgICAgICAgc2VsZi5yZW5kZXJNYXAoKTtcbiAgICAgICAgICAgIHNlbGYubW9kZWwuaW5pdGlhbFNlYXJjaCgpO1xuICAgICAgICB9KTtcbiAgICB9LFxuXG4gICAgc2V0U3RhcnRQb3M6IGZ1bmN0aW9uIChjYikge1xuICAgICAgICB2YXIgc2VsZiA9IHRoaXM7XG5cbiAgICAgICAgaWYgKEJhY2tib25lLm1lZGlhdG9yLnNldHRpbmdzLm1hcFN0YXJ0UG9zKSB7XG4gICAgICAgICAgICBzZWxmLm1hcFN0YXJ0UG9zID0gQmFja2JvbmUubWVkaWF0b3Iuc2V0dGluZ3MubWFwU3RhcnRQb3M7XG4gICAgICAgICAgICBjYigpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgJC5nZXQoJ2h0dHA6Ly9pcC1hcGkuY29tL2pzb24nLCBmdW5jdGlvbiAocmVzKSB7XG4gICAgICAgICAgICAgICAgc2VsZi5tYXBTdGFydFBvcyA9IFtyZXMubGF0LCByZXMubG9uXTtcbiAgICAgICAgICAgICAgICBjYigpO1xuICAgICAgICAgICAgfSkuZmFpbChmdW5jdGlvbigpIHtcbiAgICAgICAgICAgICAgICBzZWxmLm1hcFN0YXJ0UG9zID0gWzAsIDBdO1xuICAgICAgICAgICAgICAgIGNiKCk7XG4gICAgICAgICAgICB9KTtcbiAgICAgICAgfVxuICAgIH0sXG5cbiAgICByZW5kZXJNYXA6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy5sZWFmbGV0ID0gTC5tYXAoJ21hcC1mdWxsc2NyZWVuLXN1cmZhY2UnKS5zZXRWaWV3KHRoaXMubWFwU3RhcnRQb3MsIDEzKTtcblxuICAgICAgICB0aGlzLnNldExheWVyKHRoaXMubW9kZWwuZ2V0KCdsYXllcicpKTtcblxuICAgICAgICB0aGlzLmxlYWZsZXQub24oJ3pvb21lbmQnLCB0aGlzLmhhbmRsZVZpZXdwb3J0Q2hhbmdlLCB0aGlzKTtcbiAgICAgICAgdGhpcy5sZWFmbGV0Lm9uKCdkcmFnZW5kJywgdGhpcy5oYW5kbGVWaWV3cG9ydENoYW5nZSwgdGhpcyk7XG4gICAgICAgIHRoaXMudXBkYXRlQm91bmRzKCk7XG4gICAgfSxcblxuICAgIHNldExheWVyOiBmdW5jdGlvbiAobGF5ZXIpIHtcbiAgICAgICAgdGhpcy5jdXJyZW50TGF5ZXIgJiYgdGhpcy5sZWFmbGV0LnJlbW92ZUxheWVyKHRoaXMuY3VycmVudExheWVyKTtcbiAgICAgICAgdmFyIG9wdGlvbnMgPSBfKHRoaXMubGF5ZXJzW2xheWVyXS5vcHRpb25zKS5leHRlbmQoe1xuICAgICAgICAgICAgbWF4Wm9vbTogMTUsXG4gICAgICAgICAgICBtaW5ab29tOjNcbiAgICAgICAgfSk7XG4gICAgICAgIHRoaXMuY3VycmVudExheWVyID0gTC50aWxlTGF5ZXIodGhpcy5sYXllcnNbbGF5ZXJdLnVybCwgb3B0aW9ucylcbiAgICAgICAgICAgIC5hZGRUbyh0aGlzLmxlYWZsZXQpO1xuICAgIH0sXG5cbiAgICB1cGRhdGVCb3VuZHM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIGJvdW5kcyA9IHRoaXMubGVhZmxldC5nZXRCb3VuZHMoKTtcbiAgICAgICAgdGhpcy5tb2RlbC5zZXQoe1xuICAgICAgICAgICAgc291dGg6IGJvdW5kcy5nZXRTb3V0aCgpLFxuICAgICAgICAgICAgd2VzdDogYm91bmRzLmdldFdlc3QoKSxcbiAgICAgICAgICAgIG5vcnRoOiBib3VuZHMuZ2V0Tm9ydGgoKSxcbiAgICAgICAgICAgIGVhc3Q6IGJvdW5kcy5nZXRFYXN0KClcbiAgICAgICAgfSk7XG4gICAgfSxcblxuICAgIC8vIEV2ZW50IEhhbmRsZXJzXG4gICAgLy8gLS0tLS0tLS0tLS0tLS1cblxuICAgIHVwZGF0ZU1hcmtlcnM6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIHNlbGYgPSB0aGlzLFxuICAgICAgICAgICAgY29udHJvbHMgPSB0aGlzLmNvbnRyb2xzVmlldy5tb2RlbCxcbiAgICAgICAgICAgIHJlc3VsdHMgPSBzZWxmLm1vZGVsLmdldCgncmVzdWx0cycpO1xuXG4gICAgICAgIC8vIFJlbW92ZSBwcmV2aW91cyBtYXJrZXJzIGZyb20gbWFwLlxuICAgICAgICBpZiAoc2VsZi5tYXJrZXJzKSB7XG4gICAgICAgICAgICBzZWxmLmxlYWZsZXQucmVtb3ZlTGF5ZXIoc2VsZi5tYXJrZXJzKTtcbiAgICAgICAgfVxuICAgICAgICBzZWxmLm1hcmtlcnMgPSBMLm1hcmtlckNsdXN0ZXJHcm91cCh7XG4gICAgICAgICAgICBtYXhDbHVzdGVyUmFkaXVzOiAzMFxuICAgICAgICB9KTtcblxuICAgICAgICBfKHRoaXMubW9kZWwuYWN0aXZlRmlsdGVycygpKS5lYWNoKGZ1bmN0aW9uIChyZXN1bHRUeXBlKSB7XG4gICAgICAgICAgICBfKHJlc3VsdHNbcmVzdWx0VHlwZV0pLmVhY2goZnVuY3Rpb24gKHJlc3VsdCkge1xuICAgICAgICAgICAgICAgIHNlbGYubWFya2Vycy5hZGRMYXllcihMXG4gICAgICAgICAgICAgICAgICAgIC5tYXJrZXIoW3Jlc3VsdC5sYXQsIHJlc3VsdC5sb25dLCB7XG4gICAgICAgICAgICAgICAgICAgICAgICBpY29uOiBMLmljb24oe1xuICAgICAgICAgICAgICAgICAgICAgICAgICAgIGljb25Vcmw6ICcvc3RhdGljL2pzL3ZlbmRvci9pbWFnZXMvbWFya2VyLWljb24tMngtJyArXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNlbGYucmVzdWx0Q29sb3Vyc1tyZXN1bHRUeXBlXSArICcucG5nJyxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpY29uU2l6ZTogWzE3LCAyOF0sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgaWNvbkFuY2hvcjogWzgsIDI4XSxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBwb3B1cEFuY2hvcjogWzEsIC0yN10sXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgc2hhZG93U2l6ZTogWzI4LCAyOF1cbiAgICAgICAgICAgICAgICAgICAgICAgIH0pXG4gICAgICAgICAgICAgICAgICAgIH0pXG4gICAgICAgICAgICAgICAgICAgIC5iaW5kUG9wdXAocG9wdXBUZW1wbGF0ZS5yZW5kZXIoe1xuICAgICAgICAgICAgICAgICAgICAgICAgaW1hZ2VVUkw6IHJlc3VsdC5pbWFnZVVybCxcbiAgICAgICAgICAgICAgICAgICAgICAgIHRpdGxlOiByZXN1bHQudGl0bGUsXG4gICAgICAgICAgICAgICAgICAgICAgICB1cmw6IHJlc3VsdC51cmwsXG4gICAgICAgICAgICAgICAgICAgICAgICBhZGRyZXNzOiByZXN1bHQuYWRkcmVzc1xuICAgICAgICAgICAgICAgICAgICB9KSkpO1xuICAgICAgICAgICAgfSk7XG4gICAgICAgIH0pO1xuICAgICAgICBzZWxmLmxlYWZsZXQuYWRkTGF5ZXIodGhpcy5tYXJrZXJzKTtcbiAgICB9LFxuXG4gICAgaGFuZGxlVmlld3BvcnRDaGFuZ2U6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdGhpcy51cGRhdGVCb3VuZHMoKTtcbiAgICAgICAgdGhpcy5tb2RlbC5hdHRlbXB0U2VhcmNoKCk7XG4gICAgfSxcblxuICAgIC8vIENoYW5nZSBiZXR3ZWVuIGxheWVycy5cbiAgICBoYW5kbGVTd2l0Y2hMYXllcjogZnVuY3Rpb24gKGxheWVyKSB7XG4gICAgICAgIHRoaXMuc2V0TGF5ZXIobGF5ZXIpO1xuICAgIH0sXG5cbiAgICAvLyBIYW5kbGUgY2hhbmdlIGJvdW5kcyAoZnJvbSBVUkwpLlxuICAgIGZpdEJvdW5kczogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLmxlYWZsZXQuZml0Qm91bmRzKEwubGF0TG5nQm91bmRzKFxuICAgICAgICAgICAgTC5sYXRMbmcodGhpcy5tb2RlbC5nZXQoJ3NvdXRoJyksIHRoaXMubW9kZWwuZ2V0KCd3ZXN0JykpLFxuICAgICAgICAgICAgTC5sYXRMbmcodGhpcy5tb2RlbC5nZXQoJ25vcnRoJyksIHRoaXMubW9kZWwuZ2V0KCdlYXN0JykpXG4gICAgICAgICkpO1xuICAgIH0sXG59KTtcblxuXG5cbi8qKioqKioqKioqKioqKioqKlxuICoqIFdFQlBBQ0sgRk9PVEVSXG4gKiogLi9jb3Npbm51cy9jbGllbnQvdmlld3MvbWFwLXZpZXcuanNcbiAqKiBtb2R1bGUgaWQgPSA0XG4gKiogbW9kdWxlIGNodW5rcyA9IDBcbiAqKi8iLCIndXNlIHN0cmljdCc7XG5cbm1vZHVsZS5leHBvcnRzID0gQmFja2JvbmUuVmlldy5leHRlbmQoe1xuICAgIGluaXRpYWxpemU6IGZ1bmN0aW9uIChvcHRpb25zKSB7XG4gICAgICAgIHRoaXMuc3RhdGUgPSBvcHRpb25zICYmIG9wdGlvbnMuc3RhdGUgfHwge307XG4gICAgfSxcblxuICAgIHJlbmRlcjogZnVuY3Rpb24gKCkge1xuICAgICAgICB2YXIgc2VsZiA9IHRoaXM7XG4gICAgICAgIC8vIENvbGxlY3QgdGhlIGRhdGEgdG8gYmUgcmVuZGVyZWQ7IGNhbiBiZSBvdmVycmlkZGVuIGluIGNoaWxkIHZpZXcuXG4gICAgICAgIHZhciBkYXRhID0gdGhpcy5nZXRUZW1wbGF0ZURhdGEoKTtcbiAgICAgICAgLy8gVXNlIG51bmp1Y2tzIHRvIHJlbmRlciB0aGUgdGVtcGxhdGUgKHNwZWNpZmllZCBpbiBjaGlsZCB2aWV3KS5cbiAgICAgICAgaWYgKHRoaXMudGVtcGxhdGUgJiYgdGhpcy50ZW1wbGF0ZS5yZW5kZXIgJiZcbiAgICAgICAgICAgIHR5cGVvZiB0aGlzLnRlbXBsYXRlLnJlbmRlciA9PT0gJ2Z1bmN0aW9uJykge1xuICAgICAgICAgICAgdGhpcy4kZWwuaHRtbCh0aGlzLnRlbXBsYXRlLnJlbmRlcihkYXRhKSk7XG4gICAgICAgIH1cbiAgICAgICAgLy8gQWZ0ZXIgYSByZXBhaW50ICh0byBhbGxvdyBmdXJ0aGVyIHJlbmRlcmluZyBpbiAjYWZ0ZXJSZW5kZXIpLFxuICAgICAgICAvLyBjYWxsIHRoZSBhZnRlciByZW5kZXIgbWV0aG9kIGlmIGl0IGV4aXN0cy5cbiAgICAgICAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICBzZWxmLmFmdGVyUmVuZGVyICYmIHNlbGYuYWZ0ZXJSZW5kZXIoKTtcbiAgICAgICAgfSwgMCk7XG4gICAgICAgIHJldHVybiB0aGlzO1xuICAgIH0sXG5cbiAgICAvLyBEZWZhdWx0IGltcGxlbWVudGF0aW9uIHRvIHJldHJpZXZlIGRhdGEgdG8gYmUgcmVuZGVyZWQuXG4gICAgLy8gSWYgYSBtb2RlbCBpcyBzZXQsIHJldHVybiBpdHMgYXR0cmlidXRlcyBhcyBKU09OLCBvdGhlcndpc2VcbiAgICAvLyBhbiBlbXB0eSBvYmplY3Qgd2l0aCBhbnkgc3RhdGUgYXR0cmlidXRlcyBvbiB0aGUgdmlldyBtaXhlZCBpbi5cbiAgICBnZXRUZW1wbGF0ZURhdGE6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgdmFyIG1vZGVsRGF0YSA9IHRoaXMubW9kZWwgJiYgdGhpcy5tb2RlbC50b0pTT04oKSB8fCB7fTtcbiAgICAgICAgdmFyIGRhdGEgPSBfKG1vZGVsRGF0YSkuZXh0ZW5kKHRoaXMuc3RhdGUpO1xuICAgICAgICByZXR1cm4gZGF0YTtcbiAgICB9XG59KTtcblxuXG5cbi8qKioqKioqKioqKioqKioqKlxuICoqIFdFQlBBQ0sgRk9PVEVSXG4gKiogLi9jb3Npbm51cy9jbGllbnQvdmlld3MvYmFzZS92aWV3LmpzXG4gKiogbW9kdWxlIGlkID0gNVxuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIiwiJ3VzZSBzdHJpY3QnO1xuXG52YXIgVmlldyA9IHJlcXVpcmUoJ3ZpZXdzL2Jhc2UvdmlldycpO1xudmFyIEVycm9yVmlldyA9IHJlcXVpcmUoJ3ZpZXdzL2Vycm9yLXZpZXcnKTtcbnZhciB0ZW1wbGF0ZSA9IHJlcXVpcmUoJ21hcC9tYXAtY29udHJvbHMnKTtcblxubW9kdWxlLmV4cG9ydHMgPSBWaWV3LmV4dGVuZCh7XG4gICAgaW5pdGlhbGl6ZTogZnVuY3Rpb24gKCkge1xuICAgICAgICB0aGlzLnRlbXBsYXRlID0gdGVtcGxhdGU7XG4gICAgICAgIHRoaXMubW9kZWwub24oJ3dhbnQ6c2VhcmNoJywgdGhpcy5oYW5kbGVTdGFydFNlYXJjaCwgdGhpcyk7XG4gICAgICAgIHRoaXMubW9kZWwub24oJ2VuZDpzZWFyY2gnLCB0aGlzLmhhbmRsZUVuZFNlYXJjaCwgdGhpcyk7XG4gICAgICAgIHRoaXMubW9kZWwub24oJ2NoYW5nZTpjb250cm9scycsIHRoaXMucmVuZGVyLCB0aGlzKTtcbiAgICAgICAgdGhpcy5tb2RlbC5vbignZXJyb3I6c2VhcmNoJywgdGhpcy5oYW5kbGVYaHJFcnJvciwgdGhpcyk7XG4gICAgICAgIFZpZXcucHJvdG90eXBlLmluaXRpYWxpemUuY2FsbCh0aGlzKTtcbiAgICB9LFxuXG4gICAgZXZlbnRzOiB7XG4gICAgICAgICdjbGljayAucmVzdWx0LWZpbHRlcic6ICd0b2dnbGVGaWx0ZXInLFxuICAgICAgICAnY2xpY2sgLnJlc2V0LWZpbHRlcnMnOiAncmVzZXRGaWx0ZXJzJyxcbiAgICAgICAgJ2NsaWNrIC5sYXllci1idXR0b24nOiAnc3dpdGNoTGF5ZXInLFxuICAgICAgICAnZm9jdXNpbiAucSc6ICd0b2dnbGVUeXBpbmcnLFxuICAgICAgICAnZm9jdXNvdXQgLnEnOiAndG9nZ2xlVHlwaW5nJyxcbiAgICAgICAgJ2tleXVwIC5xJzogJ2hhbmRsZVR5cGluZydcbiAgICB9LFxuXG4gICAgLy8gRXZlbnQgSGFuZGxlcnNcbiAgICAvLyAtLS0tLS0tLS0tLS0tLVxuXG4gICAgdG9nZ2xlRmlsdGVyOiBmdW5jdGlvbiAoZXZlbnQpIHtcbiAgICAgICAgdmFyIHJlc3VsdFR5cGUgPSAkKGV2ZW50LmN1cnJlbnRUYXJnZXQpLmRhdGEoJ3Jlc3VsdC10eXBlJyk7XG4gICAgICAgIHRoaXMubW9kZWwudG9nZ2xlRmlsdGVyKHJlc3VsdFR5cGUpO1xuICAgICAgICB0aGlzLnJlbmRlcigpO1xuICAgIH0sXG5cbiAgICByZXNldEZpbHRlcnM6IGZ1bmN0aW9uIChldmVudCkge1xuICAgICAgICBldmVudC5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICB0aGlzLm1vZGVsLnJlc2V0RmlsdGVycygpO1xuICAgICAgICB0aGlzLnJlbmRlcigpO1xuICAgIH0sXG5cbiAgICAvLyBTd2l0Y2ggbGF5ZXJzIGlmIGNsaWNrZWQgbGF5ZXIgaXNuJ3QgdGhlIGFjdGl2ZSBsYXllci5cbiAgICBzd2l0Y2hMYXllcjogZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgIHZhciBsYXllciA9ICQoZXZlbnQuY3VycmVudFRhcmdldCkuZGF0YSgnbGF5ZXInKTtcbiAgICAgICAgaWYgKHRoaXMubW9kZWwuZ2V0KCdsYXllcicpICE9PSBsYXllcikge1xuICAgICAgICAgICAgdGhpcy5tb2RlbC5zZXQoJ2xheWVyJywgbGF5ZXIpO1xuICAgICAgICAgICAgdGhpcy5yZW5kZXIoKTtcbiAgICAgICAgICAgIHRoaXMudHJpZ2dlcignY2hhbmdlOmxheWVyJywgbGF5ZXIpO1xuICAgICAgICB9XG4gICAgfSxcblxuICAgIHRvZ2dsZVR5cGluZzogZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgIHRoaXMuc3RhdGUudHlwaW5nID0gIXRoaXMuc3RhdGUudHlwaW5nO1xuICAgICAgICB0aGlzLiRlbC5maW5kKCcuaWNvbi1zZWFyY2gnKS50b2dnbGUoKTtcbiAgICB9LFxuXG4gICAgaGFuZGxlVHlwaW5nOiBmdW5jdGlvbiAoZXZlbnQpIHtcbiAgICAgICAgdmFyIHF1ZXJ5ID0gJChldmVudC5jdXJyZW50VGFyZ2V0KS52YWwoKTtcbiAgICAgICAgaWYgKHF1ZXJ5Lmxlbmd0aCA+IDIgfHwgcXVlcnkubGVuZ3RoID09PSAwKSB7XG4gICAgICAgICAgICB0aGlzLm1vZGVsLnNldCh7XG4gICAgICAgICAgICAgICAgcTogcXVlcnlcbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgdGhpcy5tb2RlbC5hdHRlbXB0U2VhcmNoKCk7XG4gICAgICAgIH1cbiAgICB9LFxuXG4gICAgaGFuZGxlU3RhcnRTZWFyY2g6IGZ1bmN0aW9uIChldmVudCkge1xuICAgICAgICB0aGlzLiRlbC5maW5kKCcuaWNvbi1zZWFyY2gnKS5oaWRlKCk7XG4gICAgICAgIHRoaXMuJGVsLmZpbmQoJy5pY29uLWxvYWRpbmcnKS5zaG93KCk7XG4gICAgfSxcblxuICAgIGhhbmRsZUVuZFNlYXJjaDogZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgIGlmICghdGhpcy5zdGF0ZS50eXBpbmcpIHtcbiAgICAgICAgICAgIHRoaXMuJGVsLmZpbmQoJy5pY29uLXNlYXJjaCcpLnNob3coKTtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLiRlbC5maW5kKCcuaWNvbi1sb2FkaW5nJykuaGlkZSgpO1xuICAgIH0sXG5cbiAgICBoYW5kbGVYaHJFcnJvcjogZnVuY3Rpb24gKGV2ZW50KSB7XG4gICAgICAgIGNvbnNvbGUubG9nKCcjaGFuZGxlWGhyRXJyb3InKTtcbiAgICAgICAgdmFyICRtZXNzYWdlID0gdGhpcy4kZWwuZmluZCgnZm9ybSAubWVzc2FnZScpO1xuICAgICAgICB2YXIgZXJyb3JWaWV3ID0gbmV3IEVycm9yVmlldyh7XG4gICAgICAgICAgICBtZXNzYWdlOiAnRWluIEZlaGxlciBpc3QgYmVpIGRlciBTdWNoZSBhdWZnZXRyZXRlbi4nLFxuICAgICAgICAgICAgZWw6ICRtZXNzYWdlXG4gICAgICAgIH0pLnJlbmRlcigpO1xuICAgIH1cbn0pO1xuXG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL2Nvc2lubnVzL2NsaWVudC92aWV3cy9tYXAtY29udHJvbHMtdmlldy5qc1xuICoqIG1vZHVsZSBpZCA9IDZcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIid1c2Ugc3RyaWN0JztcblxudmFyIFZpZXcgPSByZXF1aXJlKCd2aWV3cy9iYXNlL3ZpZXcnKTtcbnZhciB0ZW1wbGF0ZSA9IHJlcXVpcmUoJ3hoci1lcnJvcicpO1xuXG5tb2R1bGUuZXhwb3J0cyA9IFZpZXcuZXh0ZW5kKHtcbiAgICBpbml0aWFsaXplOiBmdW5jdGlvbiAob3B0aW9ucykge1xuICAgICAgICB0aGlzLnRlbXBsYXRlID0gdGVtcGxhdGU7XG4gICAgICAgIFZpZXcucHJvdG90eXBlLmluaXRpYWxpemUuY2FsbCh0aGlzKTtcbiAgICAgICAgdGhpcy5zdGF0ZSA9IHtcbiAgICAgICAgICAgIG1lc3NhZ2U6IG9wdGlvbnMubWVzc2FnZVxuICAgICAgICB9O1xuICAgIH1cbn0pO1xuXG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL2Nvc2lubnVzL2NsaWVudC92aWV3cy9lcnJvci12aWV3LmpzXG4gKiogbW9kdWxlIGlkID0gN1xuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIiwidmFyIG51bmp1Y2tzID0gcmVxdWlyZShcImV4cG9ydHM/bnVuanVja3MhbnVuanVja3MvYnJvd3Nlci9udW5qdWNrcy1zbGltXCIpO1xudmFyIGVudjtcbmlmICghbnVuanVja3MuY3VycmVudEVudil7XG5cdGVudiA9IG51bmp1Y2tzLmN1cnJlbnRFbnYgPSBuZXcgbnVuanVja3MuRW52aXJvbm1lbnQoW10sIHsgYXV0b2VzY2FwZTogdHJ1ZSB9KTtcbn0gZWxzZSB7XG5cdGVudiA9IG51bmp1Y2tzLmN1cnJlbnRFbnY7XG59XG52YXIgY29uZmlndXJlID0gcmVxdWlyZShcIi4uLy4uLy4uLy4uL251bmp1Y2tzLmNvbmZpZy5qc1wiKShlbnYpO1xudmFyIGRlcGVuZGVuY2llcyA9IG51bmp1Y2tzLndlYnBhY2tEZXBlbmRlbmNpZXMgfHwgKG51bmp1Y2tzLndlYnBhY2tEZXBlbmRlbmNpZXMgPSB7fSk7XG5cblxuXG5cbnZhciBzaGltID0gcmVxdWlyZShcIi9Vc2Vycy9kYW4vc2xhdGUvY29zaW5udXMtY29yZS9ub2RlX21vZHVsZXMvbnVuanVja3MtbG9hZGVyL3J1bnRpbWUtc2hpbVwiKTtcblxuXG4oZnVuY3Rpb24oKSB7KG51bmp1Y2tzLm51bmp1Y2tzUHJlY29tcGlsZWQgPSBudW5qdWNrcy5udW5qdWNrc1ByZWNvbXBpbGVkIHx8IHt9KVtcImNvc2lubnVzL3RlbXBsYXRlcy9jb3Npbm51cy91bml2ZXJzYWwveGhyLWVycm9yLmh0bWxcIl0gPSAoZnVuY3Rpb24oKSB7XG5mdW5jdGlvbiByb290KGVudiwgY29udGV4dCwgZnJhbWUsIHJ1bnRpbWUsIGNiKSB7XG52YXIgbGluZW5vID0gbnVsbDtcbnZhciBjb2xubyA9IG51bGw7XG52YXIgb3V0cHV0ID0gXCJcIjtcbnRyeSB7XG52YXIgcGFyZW50VGVtcGxhdGUgPSBudWxsO1xub3V0cHV0ICs9IFwiPGRpdiBjbGFzcz1cXFwiZXJyb3JcXFwiPlxcbiAgICBcIjtcbm91dHB1dCArPSBydW50aW1lLnN1cHByZXNzVmFsdWUocnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgXCJtZXNzYWdlXCIpLCBlbnYub3B0cy5hdXRvZXNjYXBlKTtcbm91dHB1dCArPSBcIlxcbjwvZGl2PlxcblwiO1xuaWYocGFyZW50VGVtcGxhdGUpIHtcbnBhcmVudFRlbXBsYXRlLnJvb3RSZW5kZXJGdW5jKGVudiwgY29udGV4dCwgZnJhbWUsIHJ1bnRpbWUsIGNiKTtcbn0gZWxzZSB7XG5jYihudWxsLCBvdXRwdXQpO1xufVxuO1xufSBjYXRjaCAoZSkge1xuICBjYihydW50aW1lLmhhbmRsZUVycm9yKGUsIGxpbmVubywgY29sbm8pKTtcbn1cbn1cbnJldHVybiB7XG5yb290OiByb290XG59O1xuXG59KSgpO1xufSkoKTtcblxuXG5cbm1vZHVsZS5leHBvcnRzID0gc2hpbShudW5qdWNrcywgZW52LCBudW5qdWNrcy5udW5qdWNrc1ByZWNvbXBpbGVkW1wiY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC94aHItZXJyb3IuaHRtbFwiXSAsIGRlcGVuZGVuY2llcylcblxuXG4vKioqKioqKioqKioqKioqKipcbiAqKiBXRUJQQUNLIEZPT1RFUlxuICoqIC4vY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC94aHItZXJyb3IuaHRtbFxuICoqIG1vZHVsZSBpZCA9IDhcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIi8qISBCcm93c2VyIGJ1bmRsZSBvZiBudW5qdWNrcyAyLjQuMiAoc2xpbSwgb25seSB3b3JrcyB3aXRoIHByZWNvbXBpbGVkIHRlbXBsYXRlcykgKi9cbnZhciBudW5qdWNrcyA9XG4vKioqKioqLyAoZnVuY3Rpb24obW9kdWxlcykgeyAvLyB3ZWJwYWNrQm9vdHN0cmFwXG4vKioqKioqLyBcdC8vIFRoZSBtb2R1bGUgY2FjaGVcbi8qKioqKiovIFx0dmFyIGluc3RhbGxlZE1vZHVsZXMgPSB7fTtcblxuLyoqKioqKi8gXHQvLyBUaGUgcmVxdWlyZSBmdW5jdGlvblxuLyoqKioqKi8gXHRmdW5jdGlvbiBfX3dlYnBhY2tfcmVxdWlyZV9fKG1vZHVsZUlkKSB7XG5cbi8qKioqKiovIFx0XHQvLyBDaGVjayBpZiBtb2R1bGUgaXMgaW4gY2FjaGVcbi8qKioqKiovIFx0XHRpZihpbnN0YWxsZWRNb2R1bGVzW21vZHVsZUlkXSlcbi8qKioqKiovIFx0XHRcdHJldHVybiBpbnN0YWxsZWRNb2R1bGVzW21vZHVsZUlkXS5leHBvcnRzO1xuXG4vKioqKioqLyBcdFx0Ly8gQ3JlYXRlIGEgbmV3IG1vZHVsZSAoYW5kIHB1dCBpdCBpbnRvIHRoZSBjYWNoZSlcbi8qKioqKiovIFx0XHR2YXIgbW9kdWxlID0gaW5zdGFsbGVkTW9kdWxlc1ttb2R1bGVJZF0gPSB7XG4vKioqKioqLyBcdFx0XHRleHBvcnRzOiB7fSxcbi8qKioqKiovIFx0XHRcdGlkOiBtb2R1bGVJZCxcbi8qKioqKiovIFx0XHRcdGxvYWRlZDogZmFsc2Vcbi8qKioqKiovIFx0XHR9O1xuXG4vKioqKioqLyBcdFx0Ly8gRXhlY3V0ZSB0aGUgbW9kdWxlIGZ1bmN0aW9uXG4vKioqKioqLyBcdFx0bW9kdWxlc1ttb2R1bGVJZF0uY2FsbChtb2R1bGUuZXhwb3J0cywgbW9kdWxlLCBtb2R1bGUuZXhwb3J0cywgX193ZWJwYWNrX3JlcXVpcmVfXyk7XG5cbi8qKioqKiovIFx0XHQvLyBGbGFnIHRoZSBtb2R1bGUgYXMgbG9hZGVkXG4vKioqKioqLyBcdFx0bW9kdWxlLmxvYWRlZCA9IHRydWU7XG5cbi8qKioqKiovIFx0XHQvLyBSZXR1cm4gdGhlIGV4cG9ydHMgb2YgdGhlIG1vZHVsZVxuLyoqKioqKi8gXHRcdHJldHVybiBtb2R1bGUuZXhwb3J0cztcbi8qKioqKiovIFx0fVxuXG5cbi8qKioqKiovIFx0Ly8gZXhwb3NlIHRoZSBtb2R1bGVzIG9iamVjdCAoX193ZWJwYWNrX21vZHVsZXNfXylcbi8qKioqKiovIFx0X193ZWJwYWNrX3JlcXVpcmVfXy5tID0gbW9kdWxlcztcblxuLyoqKioqKi8gXHQvLyBleHBvc2UgdGhlIG1vZHVsZSBjYWNoZVxuLyoqKioqKi8gXHRfX3dlYnBhY2tfcmVxdWlyZV9fLmMgPSBpbnN0YWxsZWRNb2R1bGVzO1xuXG4vKioqKioqLyBcdC8vIF9fd2VicGFja19wdWJsaWNfcGF0aF9fXG4vKioqKioqLyBcdF9fd2VicGFja19yZXF1aXJlX18ucCA9IFwiXCI7XG5cbi8qKioqKiovIFx0Ly8gTG9hZCBlbnRyeSBtb2R1bGUgYW5kIHJldHVybiBleHBvcnRzXG4vKioqKioqLyBcdHJldHVybiBfX3dlYnBhY2tfcmVxdWlyZV9fKDApO1xuLyoqKioqKi8gfSlcbi8qKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKiovXG4vKioqKioqLyAoW1xuLyogMCAqL1xuLyoqKi8gZnVuY3Rpb24obW9kdWxlLCBleHBvcnRzLCBfX3dlYnBhY2tfcmVxdWlyZV9fKSB7XG5cblx0J3VzZSBzdHJpY3QnO1xuXG5cdHZhciBsaWIgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDEpO1xuXHR2YXIgZW52ID0gX193ZWJwYWNrX3JlcXVpcmVfXygyKTtcblx0dmFyIExvYWRlciA9IF9fd2VicGFja19yZXF1aXJlX18oMTEpO1xuXHR2YXIgbG9hZGVycyA9IF9fd2VicGFja19yZXF1aXJlX18oMyk7XG5cdHZhciBwcmVjb21waWxlID0gX193ZWJwYWNrX3JlcXVpcmVfXygzKTtcblxuXHRtb2R1bGUuZXhwb3J0cyA9IHt9O1xuXHRtb2R1bGUuZXhwb3J0cy5FbnZpcm9ubWVudCA9IGVudi5FbnZpcm9ubWVudDtcblx0bW9kdWxlLmV4cG9ydHMuVGVtcGxhdGUgPSBlbnYuVGVtcGxhdGU7XG5cblx0bW9kdWxlLmV4cG9ydHMuTG9hZGVyID0gTG9hZGVyO1xuXHRtb2R1bGUuZXhwb3J0cy5GaWxlU3lzdGVtTG9hZGVyID0gbG9hZGVycy5GaWxlU3lzdGVtTG9hZGVyO1xuXHRtb2R1bGUuZXhwb3J0cy5QcmVjb21waWxlZExvYWRlciA9IGxvYWRlcnMuUHJlY29tcGlsZWRMb2FkZXI7XG5cdG1vZHVsZS5leHBvcnRzLldlYkxvYWRlciA9IGxvYWRlcnMuV2ViTG9hZGVyO1xuXG5cdG1vZHVsZS5leHBvcnRzLmNvbXBpbGVyID0gX193ZWJwYWNrX3JlcXVpcmVfXygzKTtcblx0bW9kdWxlLmV4cG9ydHMucGFyc2VyID0gX193ZWJwYWNrX3JlcXVpcmVfXygzKTtcblx0bW9kdWxlLmV4cG9ydHMubGV4ZXIgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDMpO1xuXHRtb2R1bGUuZXhwb3J0cy5ydW50aW1lID0gX193ZWJwYWNrX3JlcXVpcmVfXyg4KTtcblx0bW9kdWxlLmV4cG9ydHMubGliID0gbGliO1xuXHRtb2R1bGUuZXhwb3J0cy5ub2RlcyA9IF9fd2VicGFja19yZXF1aXJlX18oMyk7XG5cblx0bW9kdWxlLmV4cG9ydHMuaW5zdGFsbEppbmphQ29tcGF0ID0gX193ZWJwYWNrX3JlcXVpcmVfXygxMik7XG5cblx0Ly8gQSBzaW5nbGUgaW5zdGFuY2Ugb2YgYW4gZW52aXJvbm1lbnQsIHNpbmNlIHRoaXMgaXMgc28gY29tbW9ubHkgdXNlZFxuXG5cdHZhciBlO1xuXHRtb2R1bGUuZXhwb3J0cy5jb25maWd1cmUgPSBmdW5jdGlvbih0ZW1wbGF0ZXNQYXRoLCBvcHRzKSB7XG5cdCAgICBvcHRzID0gb3B0cyB8fCB7fTtcblx0ICAgIGlmKGxpYi5pc09iamVjdCh0ZW1wbGF0ZXNQYXRoKSkge1xuXHQgICAgICAgIG9wdHMgPSB0ZW1wbGF0ZXNQYXRoO1xuXHQgICAgICAgIHRlbXBsYXRlc1BhdGggPSBudWxsO1xuXHQgICAgfVxuXG5cdCAgICB2YXIgVGVtcGxhdGVMb2FkZXI7XG5cdCAgICBpZihsb2FkZXJzLkZpbGVTeXN0ZW1Mb2FkZXIpIHtcblx0ICAgICAgICBUZW1wbGF0ZUxvYWRlciA9IG5ldyBsb2FkZXJzLkZpbGVTeXN0ZW1Mb2FkZXIodGVtcGxhdGVzUGF0aCwge1xuXHQgICAgICAgICAgICB3YXRjaDogb3B0cy53YXRjaCxcblx0ICAgICAgICAgICAgbm9DYWNoZTogb3B0cy5ub0NhY2hlXG5cdCAgICAgICAgfSk7XG5cdCAgICB9XG5cdCAgICBlbHNlIGlmKGxvYWRlcnMuV2ViTG9hZGVyKSB7XG5cdCAgICAgICAgVGVtcGxhdGVMb2FkZXIgPSBuZXcgbG9hZGVycy5XZWJMb2FkZXIodGVtcGxhdGVzUGF0aCwge1xuXHQgICAgICAgICAgICB1c2VDYWNoZTogb3B0cy53ZWIgJiYgb3B0cy53ZWIudXNlQ2FjaGUsXG5cdCAgICAgICAgICAgIGFzeW5jOiBvcHRzLndlYiAmJiBvcHRzLndlYi5hc3luY1xuXHQgICAgICAgIH0pO1xuXHQgICAgfVxuXG5cdCAgICBlID0gbmV3IGVudi5FbnZpcm9ubWVudChUZW1wbGF0ZUxvYWRlciwgb3B0cyk7XG5cblx0ICAgIGlmKG9wdHMgJiYgb3B0cy5leHByZXNzKSB7XG5cdCAgICAgICAgZS5leHByZXNzKG9wdHMuZXhwcmVzcyk7XG5cdCAgICB9XG5cblx0ICAgIHJldHVybiBlO1xuXHR9O1xuXG5cdG1vZHVsZS5leHBvcnRzLmNvbXBpbGUgPSBmdW5jdGlvbihzcmMsIGVudiwgcGF0aCwgZWFnZXJDb21waWxlKSB7XG5cdCAgICBpZighZSkge1xuXHQgICAgICAgIG1vZHVsZS5leHBvcnRzLmNvbmZpZ3VyZSgpO1xuXHQgICAgfVxuXHQgICAgcmV0dXJuIG5ldyBtb2R1bGUuZXhwb3J0cy5UZW1wbGF0ZShzcmMsIGVudiwgcGF0aCwgZWFnZXJDb21waWxlKTtcblx0fTtcblxuXHRtb2R1bGUuZXhwb3J0cy5yZW5kZXIgPSBmdW5jdGlvbihuYW1lLCBjdHgsIGNiKSB7XG5cdCAgICBpZighZSkge1xuXHQgICAgICAgIG1vZHVsZS5leHBvcnRzLmNvbmZpZ3VyZSgpO1xuXHQgICAgfVxuXG5cdCAgICByZXR1cm4gZS5yZW5kZXIobmFtZSwgY3R4LCBjYik7XG5cdH07XG5cblx0bW9kdWxlLmV4cG9ydHMucmVuZGVyU3RyaW5nID0gZnVuY3Rpb24oc3JjLCBjdHgsIGNiKSB7XG5cdCAgICBpZighZSkge1xuXHQgICAgICAgIG1vZHVsZS5leHBvcnRzLmNvbmZpZ3VyZSgpO1xuXHQgICAgfVxuXG5cdCAgICByZXR1cm4gZS5yZW5kZXJTdHJpbmcoc3JjLCBjdHgsIGNiKTtcblx0fTtcblxuXHRpZihwcmVjb21waWxlKSB7XG5cdCAgICBtb2R1bGUuZXhwb3J0cy5wcmVjb21waWxlID0gcHJlY29tcGlsZS5wcmVjb21waWxlO1xuXHQgICAgbW9kdWxlLmV4cG9ydHMucHJlY29tcGlsZVN0cmluZyA9IHByZWNvbXBpbGUucHJlY29tcGlsZVN0cmluZztcblx0fVxuXG5cbi8qKiovIH0sXG4vKiAxICovXG4vKioqLyBmdW5jdGlvbihtb2R1bGUsIGV4cG9ydHMpIHtcblxuXHQndXNlIHN0cmljdCc7XG5cblx0dmFyIEFycmF5UHJvdG8gPSBBcnJheS5wcm90b3R5cGU7XG5cdHZhciBPYmpQcm90byA9IE9iamVjdC5wcm90b3R5cGU7XG5cblx0dmFyIGVzY2FwZU1hcCA9IHtcblx0ICAgICcmJzogJyZhbXA7Jyxcblx0ICAgICdcIic6ICcmcXVvdDsnLFxuXHQgICAgJ1xcJyc6ICcmIzM5OycsXG5cdCAgICAnPCc6ICcmbHQ7Jyxcblx0ICAgICc+JzogJyZndDsnXG5cdH07XG5cblx0dmFyIGVzY2FwZVJlZ2V4ID0gL1smXCInPD5dL2c7XG5cblx0dmFyIGxvb2t1cEVzY2FwZSA9IGZ1bmN0aW9uKGNoKSB7XG5cdCAgICByZXR1cm4gZXNjYXBlTWFwW2NoXTtcblx0fTtcblxuXHR2YXIgZXhwb3J0cyA9IG1vZHVsZS5leHBvcnRzID0ge307XG5cblx0ZXhwb3J0cy5wcmV0dGlmeUVycm9yID0gZnVuY3Rpb24ocGF0aCwgd2l0aEludGVybmFscywgZXJyKSB7XG5cdCAgICAvLyBqc2hpbnQgLVcwMjJcblx0ICAgIC8vIGh0dHA6Ly9qc2xpbnRlcnJvcnMuY29tL2RvLW5vdC1hc3NpZ24tdG8tdGhlLWV4Y2VwdGlvbi1wYXJhbWV0ZXJcblx0ICAgIGlmICghZXJyLlVwZGF0ZSkge1xuXHQgICAgICAgIC8vIG5vdCBvbmUgb2Ygb3VycywgY2FzdCBpdFxuXHQgICAgICAgIGVyciA9IG5ldyBleHBvcnRzLlRlbXBsYXRlRXJyb3IoZXJyKTtcblx0ICAgIH1cblx0ICAgIGVyci5VcGRhdGUocGF0aCk7XG5cblx0ICAgIC8vIFVubGVzcyB0aGV5IG1hcmtlZCB0aGUgZGV2IGZsYWcsIHNob3cgdGhlbSBhIHRyYWNlIGZyb20gaGVyZVxuXHQgICAgaWYgKCF3aXRoSW50ZXJuYWxzKSB7XG5cdCAgICAgICAgdmFyIG9sZCA9IGVycjtcblx0ICAgICAgICBlcnIgPSBuZXcgRXJyb3Iob2xkLm1lc3NhZ2UpO1xuXHQgICAgICAgIGVyci5uYW1lID0gb2xkLm5hbWU7XG5cdCAgICB9XG5cblx0ICAgIHJldHVybiBlcnI7XG5cdH07XG5cblx0ZXhwb3J0cy5UZW1wbGF0ZUVycm9yID0gZnVuY3Rpb24obWVzc2FnZSwgbGluZW5vLCBjb2xubykge1xuXHQgICAgdmFyIGVyciA9IHRoaXM7XG5cblx0ICAgIGlmIChtZXNzYWdlIGluc3RhbmNlb2YgRXJyb3IpIHsgLy8gZm9yIGNhc3RpbmcgcmVndWxhciBqcyBlcnJvcnNcblx0ICAgICAgICBlcnIgPSBtZXNzYWdlO1xuXHQgICAgICAgIG1lc3NhZ2UgPSBtZXNzYWdlLm5hbWUgKyAnOiAnICsgbWVzc2FnZS5tZXNzYWdlO1xuXG5cdCAgICAgICAgdHJ5IHtcblx0ICAgICAgICAgICAgaWYoZXJyLm5hbWUgPSAnJykge31cblx0ICAgICAgICB9XG5cdCAgICAgICAgY2F0Y2goZSkge1xuXHQgICAgICAgICAgICAvLyBJZiB3ZSBjYW4ndCBzZXQgdGhlIG5hbWUgb2YgdGhlIGVycm9yIG9iamVjdCBpbiB0aGlzXG5cdCAgICAgICAgICAgIC8vIGVudmlyb25tZW50LCBkb24ndCB1c2UgaXRcblx0ICAgICAgICAgICAgZXJyID0gdGhpcztcblx0ICAgICAgICB9XG5cdCAgICB9IGVsc2Uge1xuXHQgICAgICAgIGlmKEVycm9yLmNhcHR1cmVTdGFja1RyYWNlKSB7XG5cdCAgICAgICAgICAgIEVycm9yLmNhcHR1cmVTdGFja1RyYWNlKGVycik7XG5cdCAgICAgICAgfVxuXHQgICAgfVxuXG5cdCAgICBlcnIubmFtZSA9ICdUZW1wbGF0ZSByZW5kZXIgZXJyb3InO1xuXHQgICAgZXJyLm1lc3NhZ2UgPSBtZXNzYWdlO1xuXHQgICAgZXJyLmxpbmVubyA9IGxpbmVubztcblx0ICAgIGVyci5jb2xubyA9IGNvbG5vO1xuXHQgICAgZXJyLmZpcnN0VXBkYXRlID0gdHJ1ZTtcblxuXHQgICAgZXJyLlVwZGF0ZSA9IGZ1bmN0aW9uKHBhdGgpIHtcblx0ICAgICAgICB2YXIgbWVzc2FnZSA9ICcoJyArIChwYXRoIHx8ICd1bmtub3duIHBhdGgnKSArICcpJztcblxuXHQgICAgICAgIC8vIG9ubHkgc2hvdyBsaW5lbm8gKyBjb2xubyBuZXh0IHRvIHBhdGggb2YgdGVtcGxhdGVcblx0ICAgICAgICAvLyB3aGVyZSBlcnJvciBvY2N1cnJlZFxuXHQgICAgICAgIGlmICh0aGlzLmZpcnN0VXBkYXRlKSB7XG5cdCAgICAgICAgICAgIGlmKHRoaXMubGluZW5vICYmIHRoaXMuY29sbm8pIHtcblx0ICAgICAgICAgICAgICAgIG1lc3NhZ2UgKz0gJyBbTGluZSAnICsgdGhpcy5saW5lbm8gKyAnLCBDb2x1bW4gJyArIHRoaXMuY29sbm8gKyAnXSc7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSBpZih0aGlzLmxpbmVubykge1xuXHQgICAgICAgICAgICAgICAgbWVzc2FnZSArPSAnIFtMaW5lICcgKyB0aGlzLmxpbmVubyArICddJztcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblxuXHQgICAgICAgIG1lc3NhZ2UgKz0gJ1xcbiAnO1xuXHQgICAgICAgIGlmICh0aGlzLmZpcnN0VXBkYXRlKSB7XG5cdCAgICAgICAgICAgIG1lc3NhZ2UgKz0gJyAnO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHRoaXMubWVzc2FnZSA9IG1lc3NhZ2UgKyAodGhpcy5tZXNzYWdlIHx8ICcnKTtcblx0ICAgICAgICB0aGlzLmZpcnN0VXBkYXRlID0gZmFsc2U7XG5cdCAgICAgICAgcmV0dXJuIHRoaXM7XG5cdCAgICB9O1xuXG5cdCAgICByZXR1cm4gZXJyO1xuXHR9O1xuXG5cdGV4cG9ydHMuVGVtcGxhdGVFcnJvci5wcm90b3R5cGUgPSBFcnJvci5wcm90b3R5cGU7XG5cblx0ZXhwb3J0cy5lc2NhcGUgPSBmdW5jdGlvbih2YWwpIHtcblx0ICByZXR1cm4gdmFsLnJlcGxhY2UoZXNjYXBlUmVnZXgsIGxvb2t1cEVzY2FwZSk7XG5cdH07XG5cblx0ZXhwb3J0cy5pc0Z1bmN0aW9uID0gZnVuY3Rpb24ob2JqKSB7XG5cdCAgICByZXR1cm4gT2JqUHJvdG8udG9TdHJpbmcuY2FsbChvYmopID09PSAnW29iamVjdCBGdW5jdGlvbl0nO1xuXHR9O1xuXG5cdGV4cG9ydHMuaXNBcnJheSA9IEFycmF5LmlzQXJyYXkgfHwgZnVuY3Rpb24ob2JqKSB7XG5cdCAgICByZXR1cm4gT2JqUHJvdG8udG9TdHJpbmcuY2FsbChvYmopID09PSAnW29iamVjdCBBcnJheV0nO1xuXHR9O1xuXG5cdGV4cG9ydHMuaXNTdHJpbmcgPSBmdW5jdGlvbihvYmopIHtcblx0ICAgIHJldHVybiBPYmpQcm90by50b1N0cmluZy5jYWxsKG9iaikgPT09ICdbb2JqZWN0IFN0cmluZ10nO1xuXHR9O1xuXG5cdGV4cG9ydHMuaXNPYmplY3QgPSBmdW5jdGlvbihvYmopIHtcblx0ICAgIHJldHVybiBPYmpQcm90by50b1N0cmluZy5jYWxsKG9iaikgPT09ICdbb2JqZWN0IE9iamVjdF0nO1xuXHR9O1xuXG5cdGV4cG9ydHMuZ3JvdXBCeSA9IGZ1bmN0aW9uKG9iaiwgdmFsKSB7XG5cdCAgICB2YXIgcmVzdWx0ID0ge307XG5cdCAgICB2YXIgaXRlcmF0b3IgPSBleHBvcnRzLmlzRnVuY3Rpb24odmFsKSA/IHZhbCA6IGZ1bmN0aW9uKG9iaikgeyByZXR1cm4gb2JqW3ZhbF07IH07XG5cdCAgICBmb3IodmFyIGk9MDsgaTxvYmoubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICB2YXIgdmFsdWUgPSBvYmpbaV07XG5cdCAgICAgICAgdmFyIGtleSA9IGl0ZXJhdG9yKHZhbHVlLCBpKTtcblx0ICAgICAgICAocmVzdWx0W2tleV0gfHwgKHJlc3VsdFtrZXldID0gW10pKS5wdXNoKHZhbHVlKTtcblx0ICAgIH1cblx0ICAgIHJldHVybiByZXN1bHQ7XG5cdH07XG5cblx0ZXhwb3J0cy50b0FycmF5ID0gZnVuY3Rpb24ob2JqKSB7XG5cdCAgICByZXR1cm4gQXJyYXkucHJvdG90eXBlLnNsaWNlLmNhbGwob2JqKTtcblx0fTtcblxuXHRleHBvcnRzLndpdGhvdXQgPSBmdW5jdGlvbihhcnJheSkge1xuXHQgICAgdmFyIHJlc3VsdCA9IFtdO1xuXHQgICAgaWYgKCFhcnJheSkge1xuXHQgICAgICAgIHJldHVybiByZXN1bHQ7XG5cdCAgICB9XG5cdCAgICB2YXIgaW5kZXggPSAtMSxcblx0ICAgIGxlbmd0aCA9IGFycmF5Lmxlbmd0aCxcblx0ICAgIGNvbnRhaW5zID0gZXhwb3J0cy50b0FycmF5KGFyZ3VtZW50cykuc2xpY2UoMSk7XG5cblx0ICAgIHdoaWxlKCsraW5kZXggPCBsZW5ndGgpIHtcblx0ICAgICAgICBpZihleHBvcnRzLmluZGV4T2YoY29udGFpbnMsIGFycmF5W2luZGV4XSkgPT09IC0xKSB7XG5cdCAgICAgICAgICAgIHJlc3VsdC5wdXNoKGFycmF5W2luZGV4XSk7XG5cdCAgICAgICAgfVxuXHQgICAgfVxuXHQgICAgcmV0dXJuIHJlc3VsdDtcblx0fTtcblxuXHRleHBvcnRzLmV4dGVuZCA9IGZ1bmN0aW9uKG9iaiwgb2JqMikge1xuXHQgICAgZm9yKHZhciBrIGluIG9iajIpIHtcblx0ICAgICAgICBvYmpba10gPSBvYmoyW2tdO1xuXHQgICAgfVxuXHQgICAgcmV0dXJuIG9iajtcblx0fTtcblxuXHRleHBvcnRzLnJlcGVhdCA9IGZ1bmN0aW9uKGNoYXJfLCBuKSB7XG5cdCAgICB2YXIgc3RyID0gJyc7XG5cdCAgICBmb3IodmFyIGk9MDsgaTxuOyBpKyspIHtcblx0ICAgICAgICBzdHIgKz0gY2hhcl87XG5cdCAgICB9XG5cdCAgICByZXR1cm4gc3RyO1xuXHR9O1xuXG5cdGV4cG9ydHMuZWFjaCA9IGZ1bmN0aW9uKG9iaiwgZnVuYywgY29udGV4dCkge1xuXHQgICAgaWYob2JqID09IG51bGwpIHtcblx0ICAgICAgICByZXR1cm47XG5cdCAgICB9XG5cblx0ICAgIGlmKEFycmF5UHJvdG8uZWFjaCAmJiBvYmouZWFjaCA9PT0gQXJyYXlQcm90by5lYWNoKSB7XG5cdCAgICAgICAgb2JqLmZvckVhY2goZnVuYywgY29udGV4dCk7XG5cdCAgICB9XG5cdCAgICBlbHNlIGlmKG9iai5sZW5ndGggPT09ICtvYmoubGVuZ3RoKSB7XG5cdCAgICAgICAgZm9yKHZhciBpPTAsIGw9b2JqLmxlbmd0aDsgaTxsOyBpKyspIHtcblx0ICAgICAgICAgICAgZnVuYy5jYWxsKGNvbnRleHQsIG9ialtpXSwgaSwgb2JqKTtcblx0ICAgICAgICB9XG5cdCAgICB9XG5cdH07XG5cblx0ZXhwb3J0cy5tYXAgPSBmdW5jdGlvbihvYmosIGZ1bmMpIHtcblx0ICAgIHZhciByZXN1bHRzID0gW107XG5cdCAgICBpZihvYmogPT0gbnVsbCkge1xuXHQgICAgICAgIHJldHVybiByZXN1bHRzO1xuXHQgICAgfVxuXG5cdCAgICBpZihBcnJheVByb3RvLm1hcCAmJiBvYmoubWFwID09PSBBcnJheVByb3RvLm1hcCkge1xuXHQgICAgICAgIHJldHVybiBvYmoubWFwKGZ1bmMpO1xuXHQgICAgfVxuXG5cdCAgICBmb3IodmFyIGk9MDsgaTxvYmoubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICByZXN1bHRzW3Jlc3VsdHMubGVuZ3RoXSA9IGZ1bmMob2JqW2ldLCBpKTtcblx0ICAgIH1cblxuXHQgICAgaWYob2JqLmxlbmd0aCA9PT0gK29iai5sZW5ndGgpIHtcblx0ICAgICAgICByZXN1bHRzLmxlbmd0aCA9IG9iai5sZW5ndGg7XG5cdCAgICB9XG5cblx0ICAgIHJldHVybiByZXN1bHRzO1xuXHR9O1xuXG5cdGV4cG9ydHMuYXN5bmNJdGVyID0gZnVuY3Rpb24oYXJyLCBpdGVyLCBjYikge1xuXHQgICAgdmFyIGkgPSAtMTtcblxuXHQgICAgZnVuY3Rpb24gbmV4dCgpIHtcblx0ICAgICAgICBpKys7XG5cblx0ICAgICAgICBpZihpIDwgYXJyLmxlbmd0aCkge1xuXHQgICAgICAgICAgICBpdGVyKGFycltpXSwgaSwgbmV4dCwgY2IpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgY2IoKTtcblx0ICAgICAgICB9XG5cdCAgICB9XG5cblx0ICAgIG5leHQoKTtcblx0fTtcblxuXHRleHBvcnRzLmFzeW5jRm9yID0gZnVuY3Rpb24ob2JqLCBpdGVyLCBjYikge1xuXHQgICAgdmFyIGtleXMgPSBleHBvcnRzLmtleXMob2JqKTtcblx0ICAgIHZhciBsZW4gPSBrZXlzLmxlbmd0aDtcblx0ICAgIHZhciBpID0gLTE7XG5cblx0ICAgIGZ1bmN0aW9uIG5leHQoKSB7XG5cdCAgICAgICAgaSsrO1xuXHQgICAgICAgIHZhciBrID0ga2V5c1tpXTtcblxuXHQgICAgICAgIGlmKGkgPCBsZW4pIHtcblx0ICAgICAgICAgICAgaXRlcihrLCBvYmpba10sIGksIGxlbiwgbmV4dCk7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIGVsc2Uge1xuXHQgICAgICAgICAgICBjYigpO1xuXHQgICAgICAgIH1cblx0ICAgIH1cblxuXHQgICAgbmV4dCgpO1xuXHR9O1xuXG5cdC8vIGh0dHBzOi8vZGV2ZWxvcGVyLm1vemlsbGEub3JnL2VuLVVTL2RvY3MvV2ViL0phdmFTY3JpcHQvUmVmZXJlbmNlL0dsb2JhbF9PYmplY3RzL0FycmF5L2luZGV4T2YjUG9seWZpbGxcblx0ZXhwb3J0cy5pbmRleE9mID0gQXJyYXkucHJvdG90eXBlLmluZGV4T2YgP1xuXHQgICAgZnVuY3Rpb24gKGFyciwgc2VhcmNoRWxlbWVudCwgZnJvbUluZGV4KSB7XG5cdCAgICAgICAgcmV0dXJuIEFycmF5LnByb3RvdHlwZS5pbmRleE9mLmNhbGwoYXJyLCBzZWFyY2hFbGVtZW50LCBmcm9tSW5kZXgpO1xuXHQgICAgfSA6XG5cdCAgICBmdW5jdGlvbiAoYXJyLCBzZWFyY2hFbGVtZW50LCBmcm9tSW5kZXgpIHtcblx0ICAgICAgICB2YXIgbGVuZ3RoID0gdGhpcy5sZW5ndGggPj4+IDA7IC8vIEhhY2sgdG8gY29udmVydCBvYmplY3QubGVuZ3RoIHRvIGEgVUludDMyXG5cblx0ICAgICAgICBmcm9tSW5kZXggPSArZnJvbUluZGV4IHx8IDA7XG5cblx0ICAgICAgICBpZihNYXRoLmFicyhmcm9tSW5kZXgpID09PSBJbmZpbml0eSkge1xuXHQgICAgICAgICAgICBmcm9tSW5kZXggPSAwO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGlmKGZyb21JbmRleCA8IDApIHtcblx0ICAgICAgICAgICAgZnJvbUluZGV4ICs9IGxlbmd0aDtcblx0ICAgICAgICAgICAgaWYgKGZyb21JbmRleCA8IDApIHtcblx0ICAgICAgICAgICAgICAgIGZyb21JbmRleCA9IDA7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICB9XG5cblx0ICAgICAgICBmb3IoO2Zyb21JbmRleCA8IGxlbmd0aDsgZnJvbUluZGV4KyspIHtcblx0ICAgICAgICAgICAgaWYgKGFycltmcm9tSW5kZXhdID09PSBzZWFyY2hFbGVtZW50KSB7XG5cdCAgICAgICAgICAgICAgICByZXR1cm4gZnJvbUluZGV4O1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgcmV0dXJuIC0xO1xuXHQgICAgfTtcblxuXHRpZighQXJyYXkucHJvdG90eXBlLm1hcCkge1xuXHQgICAgQXJyYXkucHJvdG90eXBlLm1hcCA9IGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIHRocm93IG5ldyBFcnJvcignbWFwIGlzIHVuaW1wbGVtZW50ZWQgZm9yIHRoaXMganMgZW5naW5lJyk7XG5cdCAgICB9O1xuXHR9XG5cblx0ZXhwb3J0cy5rZXlzID0gZnVuY3Rpb24ob2JqKSB7XG5cdCAgICBpZihPYmplY3QucHJvdG90eXBlLmtleXMpIHtcblx0ICAgICAgICByZXR1cm4gb2JqLmtleXMoKTtcblx0ICAgIH1cblx0ICAgIGVsc2Uge1xuXHQgICAgICAgIHZhciBrZXlzID0gW107XG5cdCAgICAgICAgZm9yKHZhciBrIGluIG9iaikge1xuXHQgICAgICAgICAgICBpZihvYmouaGFzT3duUHJvcGVydHkoaykpIHtcblx0ICAgICAgICAgICAgICAgIGtleXMucHVzaChrKTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblx0ICAgICAgICByZXR1cm4ga2V5cztcblx0ICAgIH1cblx0fTtcblxuXHRleHBvcnRzLmluT3BlcmF0b3IgPSBmdW5jdGlvbiAoa2V5LCB2YWwpIHtcblx0ICAgIGlmIChleHBvcnRzLmlzQXJyYXkodmFsKSkge1xuXHQgICAgICAgIHJldHVybiBleHBvcnRzLmluZGV4T2YodmFsLCBrZXkpICE9PSAtMTtcblx0ICAgIH0gZWxzZSBpZiAoZXhwb3J0cy5pc09iamVjdCh2YWwpKSB7XG5cdCAgICAgICAgcmV0dXJuIGtleSBpbiB2YWw7XG5cdCAgICB9IGVsc2UgaWYgKGV4cG9ydHMuaXNTdHJpbmcodmFsKSkge1xuXHQgICAgICAgIHJldHVybiB2YWwuaW5kZXhPZihrZXkpICE9PSAtMTtcblx0ICAgIH0gZWxzZSB7XG5cdCAgICAgICAgdGhyb3cgbmV3IEVycm9yKCdDYW5ub3QgdXNlIFwiaW5cIiBvcGVyYXRvciB0byBzZWFyY2ggZm9yIFwiJ1xuXHQgICAgICAgICAgICArIGtleSArICdcIiBpbiB1bmV4cGVjdGVkIHR5cGVzLicpO1xuXHQgICAgfVxuXHR9O1xuXG5cbi8qKiovIH0sXG4vKiAyICovXG4vKioqLyBmdW5jdGlvbihtb2R1bGUsIGV4cG9ydHMsIF9fd2VicGFja19yZXF1aXJlX18pIHtcblxuXHQndXNlIHN0cmljdCc7XG5cblx0dmFyIHBhdGggPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDMpO1xuXHR2YXIgYXNhcCA9IF9fd2VicGFja19yZXF1aXJlX18oNCk7XG5cdHZhciBsaWIgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDEpO1xuXHR2YXIgT2JqID0gX193ZWJwYWNrX3JlcXVpcmVfXyg2KTtcblx0dmFyIGNvbXBpbGVyID0gX193ZWJwYWNrX3JlcXVpcmVfXygzKTtcblx0dmFyIGJ1aWx0aW5fZmlsdGVycyA9IF9fd2VicGFja19yZXF1aXJlX18oNyk7XG5cdHZhciBidWlsdGluX2xvYWRlcnMgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDMpO1xuXHR2YXIgcnVudGltZSA9IF9fd2VicGFja19yZXF1aXJlX18oOCk7XG5cdHZhciBnbG9iYWxzID0gX193ZWJwYWNrX3JlcXVpcmVfXyg5KTtcblx0dmFyIEZyYW1lID0gcnVudGltZS5GcmFtZTtcblx0dmFyIFRlbXBsYXRlO1xuXG5cdC8vIFVuY29uZGl0aW9uYWxseSBsb2FkIGluIHRoaXMgbG9hZGVyLCBldmVuIGlmIG5vIG90aGVyIG9uZXMgYXJlXG5cdC8vIGluY2x1ZGVkIChwb3NzaWJsZSBpbiB0aGUgc2xpbSBicm93c2VyIGJ1aWxkKVxuXHRidWlsdGluX2xvYWRlcnMuUHJlY29tcGlsZWRMb2FkZXIgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDEwKTtcblxuXHQvLyBJZiB0aGUgdXNlciBpcyB1c2luZyB0aGUgYXN5bmMgQVBJLCAqYWx3YXlzKiBjYWxsIGl0XG5cdC8vIGFzeW5jaHJvbm91c2x5IGV2ZW4gaWYgdGhlIHRlbXBsYXRlIHdhcyBzeW5jaHJvbm91cy5cblx0ZnVuY3Rpb24gY2FsbGJhY2tBc2FwKGNiLCBlcnIsIHJlcykge1xuXHQgICAgYXNhcChmdW5jdGlvbigpIHsgY2IoZXJyLCByZXMpOyB9KTtcblx0fVxuXG5cdHZhciBFbnZpcm9ubWVudCA9IE9iai5leHRlbmQoe1xuXHQgICAgaW5pdDogZnVuY3Rpb24obG9hZGVycywgb3B0cykge1xuXHQgICAgICAgIC8vIFRoZSBkZXYgZmxhZyBkZXRlcm1pbmVzIHRoZSB0cmFjZSB0aGF0J2xsIGJlIHNob3duIG9uIGVycm9ycy5cblx0ICAgICAgICAvLyBJZiBzZXQgdG8gdHJ1ZSwgcmV0dXJucyB0aGUgZnVsbCB0cmFjZSBmcm9tIHRoZSBlcnJvciBwb2ludCxcblx0ICAgICAgICAvLyBvdGhlcndpc2Ugd2lsbCByZXR1cm4gdHJhY2Ugc3RhcnRpbmcgZnJvbSBUZW1wbGF0ZS5yZW5kZXJcblx0ICAgICAgICAvLyAodGhlIGZ1bGwgdHJhY2UgZnJvbSB3aXRoaW4gbnVuanVja3MgbWF5IGNvbmZ1c2UgZGV2ZWxvcGVycyB1c2luZ1xuXHQgICAgICAgIC8vICB0aGUgbGlicmFyeSlcblx0ICAgICAgICAvLyBkZWZhdWx0cyB0byBmYWxzZVxuXHQgICAgICAgIG9wdHMgPSB0aGlzLm9wdHMgPSBvcHRzIHx8IHt9O1xuXHQgICAgICAgIHRoaXMub3B0cy5kZXYgPSAhIW9wdHMuZGV2O1xuXG5cdCAgICAgICAgLy8gVGhlIGF1dG9lc2NhcGUgZmxhZyBzZXRzIGdsb2JhbCBhdXRvZXNjYXBpbmcuIElmIHRydWUsXG5cdCAgICAgICAgLy8gZXZlcnkgc3RyaW5nIHZhcmlhYmxlIHdpbGwgYmUgZXNjYXBlZCBieSBkZWZhdWx0LlxuXHQgICAgICAgIC8vIElmIGZhbHNlLCBzdHJpbmdzIGNhbiBiZSBtYW51YWxseSBlc2NhcGVkIHVzaW5nIHRoZSBgZXNjYXBlYCBmaWx0ZXIuXG5cdCAgICAgICAgLy8gZGVmYXVsdHMgdG8gdHJ1ZVxuXHQgICAgICAgIHRoaXMub3B0cy5hdXRvZXNjYXBlID0gb3B0cy5hdXRvZXNjYXBlICE9IG51bGwgPyBvcHRzLmF1dG9lc2NhcGUgOiB0cnVlO1xuXG5cdCAgICAgICAgLy8gSWYgdHJ1ZSwgdGhpcyB3aWxsIG1ha2UgdGhlIHN5c3RlbSB0aHJvdyBlcnJvcnMgaWYgdHJ5aW5nXG5cdCAgICAgICAgLy8gdG8gb3V0cHV0IGEgbnVsbCBvciB1bmRlZmluZWQgdmFsdWVcblx0ICAgICAgICB0aGlzLm9wdHMudGhyb3dPblVuZGVmaW5lZCA9ICEhb3B0cy50aHJvd09uVW5kZWZpbmVkO1xuXHQgICAgICAgIHRoaXMub3B0cy50cmltQmxvY2tzID0gISFvcHRzLnRyaW1CbG9ja3M7XG5cdCAgICAgICAgdGhpcy5vcHRzLmxzdHJpcEJsb2NrcyA9ICEhb3B0cy5sc3RyaXBCbG9ja3M7XG5cblx0ICAgICAgICB0aGlzLmxvYWRlcnMgPSBbXTtcblxuXHQgICAgICAgIGlmKCFsb2FkZXJzKSB7XG5cdCAgICAgICAgICAgIC8vIFRoZSBmaWxlc3lzdGVtIGxvYWRlciBpcyBvbmx5IGF2YWlsYWJsZSBzZXJ2ZXItc2lkZVxuXHQgICAgICAgICAgICBpZihidWlsdGluX2xvYWRlcnMuRmlsZVN5c3RlbUxvYWRlcikge1xuXHQgICAgICAgICAgICAgICAgdGhpcy5sb2FkZXJzID0gW25ldyBidWlsdGluX2xvYWRlcnMuRmlsZVN5c3RlbUxvYWRlcigndmlld3MnKV07XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSBpZihidWlsdGluX2xvYWRlcnMuV2ViTG9hZGVyKSB7XG5cdCAgICAgICAgICAgICAgICB0aGlzLmxvYWRlcnMgPSBbbmV3IGJ1aWx0aW5fbG9hZGVycy5XZWJMb2FkZXIoJy92aWV3cycpXTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgdGhpcy5sb2FkZXJzID0gbGliLmlzQXJyYXkobG9hZGVycykgPyBsb2FkZXJzIDogW2xvYWRlcnNdO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIC8vIEl0J3MgZWFzeSB0byB1c2UgcHJlY29tcGlsZWQgdGVtcGxhdGVzOiBqdXN0IGluY2x1ZGUgdGhlbVxuXHQgICAgICAgIC8vIGJlZm9yZSB5b3UgY29uZmlndXJlIG51bmp1Y2tzIGFuZCB0aGlzIHdpbGwgYXV0b21hdGljYWxseVxuXHQgICAgICAgIC8vIHBpY2sgaXQgdXAgYW5kIHVzZSBpdFxuXHQgICAgICAgIGlmKCh0cnVlKSAmJiB3aW5kb3cubnVuanVja3NQcmVjb21waWxlZCkge1xuXHQgICAgICAgICAgICB0aGlzLmxvYWRlcnMudW5zaGlmdChcblx0ICAgICAgICAgICAgICAgIG5ldyBidWlsdGluX2xvYWRlcnMuUHJlY29tcGlsZWRMb2FkZXIod2luZG93Lm51bmp1Y2tzUHJlY29tcGlsZWQpXG5cdCAgICAgICAgICAgICk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgdGhpcy5pbml0Q2FjaGUoKTtcblxuXHQgICAgICAgIHRoaXMuZ2xvYmFscyA9IGdsb2JhbHMoKTtcblx0ICAgICAgICB0aGlzLmZpbHRlcnMgPSB7fTtcblx0ICAgICAgICB0aGlzLmFzeW5jRmlsdGVycyA9IFtdO1xuXHQgICAgICAgIHRoaXMuZXh0ZW5zaW9ucyA9IHt9O1xuXHQgICAgICAgIHRoaXMuZXh0ZW5zaW9uc0xpc3QgPSBbXTtcblxuXHQgICAgICAgIGZvcih2YXIgbmFtZSBpbiBidWlsdGluX2ZpbHRlcnMpIHtcblx0ICAgICAgICAgICAgdGhpcy5hZGRGaWx0ZXIobmFtZSwgYnVpbHRpbl9maWx0ZXJzW25hbWVdKTtcblx0ICAgICAgICB9XG5cdCAgICB9LFxuXG5cdCAgICBpbml0Q2FjaGU6IGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIC8vIENhY2hpbmcgYW5kIGNhY2hlIGJ1c3Rpbmdcblx0ICAgICAgICBsaWIuZWFjaCh0aGlzLmxvYWRlcnMsIGZ1bmN0aW9uKGxvYWRlcikge1xuXHQgICAgICAgICAgICBsb2FkZXIuY2FjaGUgPSB7fTtcblxuXHQgICAgICAgICAgICBpZih0eXBlb2YgbG9hZGVyLm9uID09PSAnZnVuY3Rpb24nKSB7XG5cdCAgICAgICAgICAgICAgICBsb2FkZXIub24oJ3VwZGF0ZScsIGZ1bmN0aW9uKHRlbXBsYXRlKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgbG9hZGVyLmNhY2hlW3RlbXBsYXRlXSA9IG51bGw7XG5cdCAgICAgICAgICAgICAgICB9KTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH0pO1xuXHQgICAgfSxcblxuXHQgICAgYWRkRXh0ZW5zaW9uOiBmdW5jdGlvbihuYW1lLCBleHRlbnNpb24pIHtcblx0ICAgICAgICBleHRlbnNpb24uX25hbWUgPSBuYW1lO1xuXHQgICAgICAgIHRoaXMuZXh0ZW5zaW9uc1tuYW1lXSA9IGV4dGVuc2lvbjtcblx0ICAgICAgICB0aGlzLmV4dGVuc2lvbnNMaXN0LnB1c2goZXh0ZW5zaW9uKTtcblx0ICAgICAgICByZXR1cm4gdGhpcztcblx0ICAgIH0sXG5cblx0ICAgIHJlbW92ZUV4dGVuc2lvbjogZnVuY3Rpb24obmFtZSkge1xuXHQgICAgICAgIHZhciBleHRlbnNpb24gPSB0aGlzLmdldEV4dGVuc2lvbihuYW1lKTtcblx0ICAgICAgICBpZiAoIWV4dGVuc2lvbikgcmV0dXJuO1xuXG5cdCAgICAgICAgdGhpcy5leHRlbnNpb25zTGlzdCA9IGxpYi53aXRob3V0KHRoaXMuZXh0ZW5zaW9uc0xpc3QsIGV4dGVuc2lvbik7XG5cdCAgICAgICAgZGVsZXRlIHRoaXMuZXh0ZW5zaW9uc1tuYW1lXTtcblx0ICAgIH0sXG5cblx0ICAgIGdldEV4dGVuc2lvbjogZnVuY3Rpb24obmFtZSkge1xuXHQgICAgICAgIHJldHVybiB0aGlzLmV4dGVuc2lvbnNbbmFtZV07XG5cdCAgICB9LFxuXG5cdCAgICBoYXNFeHRlbnNpb246IGZ1bmN0aW9uKG5hbWUpIHtcblx0ICAgICAgICByZXR1cm4gISF0aGlzLmV4dGVuc2lvbnNbbmFtZV07XG5cdCAgICB9LFxuXG5cdCAgICBhZGRHbG9iYWw6IGZ1bmN0aW9uKG5hbWUsIHZhbHVlKSB7XG5cdCAgICAgICAgdGhpcy5nbG9iYWxzW25hbWVdID0gdmFsdWU7XG5cdCAgICAgICAgcmV0dXJuIHRoaXM7XG5cdCAgICB9LFxuXG5cdCAgICBnZXRHbG9iYWw6IGZ1bmN0aW9uKG5hbWUpIHtcblx0ICAgICAgICBpZih0eXBlb2YgdGhpcy5nbG9iYWxzW25hbWVdID09PSAndW5kZWZpbmVkJykge1xuXHQgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoJ2dsb2JhbCBub3QgZm91bmQ6ICcgKyBuYW1lKTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIHRoaXMuZ2xvYmFsc1tuYW1lXTtcblx0ICAgIH0sXG5cblx0ICAgIGFkZEZpbHRlcjogZnVuY3Rpb24obmFtZSwgZnVuYywgYXN5bmMpIHtcblx0ICAgICAgICB2YXIgd3JhcHBlZCA9IGZ1bmM7XG5cblx0ICAgICAgICBpZihhc3luYykge1xuXHQgICAgICAgICAgICB0aGlzLmFzeW5jRmlsdGVycy5wdXNoKG5hbWUpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICB0aGlzLmZpbHRlcnNbbmFtZV0gPSB3cmFwcGVkO1xuXHQgICAgICAgIHJldHVybiB0aGlzO1xuXHQgICAgfSxcblxuXHQgICAgZ2V0RmlsdGVyOiBmdW5jdGlvbihuYW1lKSB7XG5cdCAgICAgICAgaWYoIXRoaXMuZmlsdGVyc1tuYW1lXSkge1xuXHQgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoJ2ZpbHRlciBub3QgZm91bmQ6ICcgKyBuYW1lKTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIHRoaXMuZmlsdGVyc1tuYW1lXTtcblx0ICAgIH0sXG5cblx0ICAgIHJlc29sdmVUZW1wbGF0ZTogZnVuY3Rpb24obG9hZGVyLCBwYXJlbnROYW1lLCBmaWxlbmFtZSkge1xuXHQgICAgICAgIHZhciBpc1JlbGF0aXZlID0gKGxvYWRlci5pc1JlbGF0aXZlICYmIHBhcmVudE5hbWUpPyBsb2FkZXIuaXNSZWxhdGl2ZShmaWxlbmFtZSkgOiBmYWxzZTtcblx0ICAgICAgICByZXR1cm4gKGlzUmVsYXRpdmUgJiYgbG9hZGVyLnJlc29sdmUpPyBsb2FkZXIucmVzb2x2ZShwYXJlbnROYW1lLCBmaWxlbmFtZSkgOiBmaWxlbmFtZTtcblx0ICAgIH0sXG5cblx0ICAgIGdldFRlbXBsYXRlOiBmdW5jdGlvbihuYW1lLCBlYWdlckNvbXBpbGUsIHBhcmVudE5hbWUsIGlnbm9yZU1pc3NpbmcsIGNiKSB7XG5cdCAgICAgICAgdmFyIHRoYXQgPSB0aGlzO1xuXHQgICAgICAgIHZhciB0bXBsID0gbnVsbDtcblx0ICAgICAgICBpZihuYW1lICYmIG5hbWUucmF3KSB7XG5cdCAgICAgICAgICAgIC8vIHRoaXMgZml4ZXMgYXV0b2VzY2FwZSBmb3IgdGVtcGxhdGVzIHJlZmVyZW5jZWQgaW4gc3ltYm9sc1xuXHQgICAgICAgICAgICBuYW1lID0gbmFtZS5yYXc7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgaWYobGliLmlzRnVuY3Rpb24ocGFyZW50TmFtZSkpIHtcblx0ICAgICAgICAgICAgY2IgPSBwYXJlbnROYW1lO1xuXHQgICAgICAgICAgICBwYXJlbnROYW1lID0gbnVsbDtcblx0ICAgICAgICAgICAgZWFnZXJDb21waWxlID0gZWFnZXJDb21waWxlIHx8IGZhbHNlO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGlmKGxpYi5pc0Z1bmN0aW9uKGVhZ2VyQ29tcGlsZSkpIHtcblx0ICAgICAgICAgICAgY2IgPSBlYWdlckNvbXBpbGU7XG5cdCAgICAgICAgICAgIGVhZ2VyQ29tcGlsZSA9IGZhbHNlO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGlmIChuYW1lIGluc3RhbmNlb2YgVGVtcGxhdGUpIHtcblx0ICAgICAgICAgICAgIHRtcGwgPSBuYW1lO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIGlmKHR5cGVvZiBuYW1lICE9PSAnc3RyaW5nJykge1xuXHQgICAgICAgICAgICB0aHJvdyBuZXcgRXJyb3IoJ3RlbXBsYXRlIG5hbWVzIG11c3QgYmUgYSBzdHJpbmc6ICcgKyBuYW1lKTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIGZvciAodmFyIGkgPSAwOyBpIDwgdGhpcy5sb2FkZXJzLmxlbmd0aDsgaSsrKSB7XG5cdCAgICAgICAgICAgICAgICB2YXIgX25hbWUgPSB0aGlzLnJlc29sdmVUZW1wbGF0ZSh0aGlzLmxvYWRlcnNbaV0sIHBhcmVudE5hbWUsIG5hbWUpO1xuXHQgICAgICAgICAgICAgICAgdG1wbCA9IHRoaXMubG9hZGVyc1tpXS5jYWNoZVtfbmFtZV07XG5cdCAgICAgICAgICAgICAgICBpZiAodG1wbCkgYnJlYWs7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICB9XG5cblx0ICAgICAgICBpZih0bXBsKSB7XG5cdCAgICAgICAgICAgIGlmKGVhZ2VyQ29tcGlsZSkge1xuXHQgICAgICAgICAgICAgICAgdG1wbC5jb21waWxlKCk7XG5cdCAgICAgICAgICAgIH1cblxuXHQgICAgICAgICAgICBpZihjYikge1xuXHQgICAgICAgICAgICAgICAgY2IobnVsbCwgdG1wbCk7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICByZXR1cm4gdG1wbDtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH0gZWxzZSB7XG5cdCAgICAgICAgICAgIHZhciBzeW5jUmVzdWx0O1xuXHQgICAgICAgICAgICB2YXIgX3RoaXMgPSB0aGlzO1xuXG5cdCAgICAgICAgICAgIHZhciBjcmVhdGVUZW1wbGF0ZSA9IGZ1bmN0aW9uKGVyciwgaW5mbykge1xuXHQgICAgICAgICAgICAgICAgaWYoIWluZm8gJiYgIWVycikge1xuXHQgICAgICAgICAgICAgICAgICAgIGlmKCFpZ25vcmVNaXNzaW5nKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIGVyciA9IG5ldyBFcnJvcigndGVtcGxhdGUgbm90IGZvdW5kOiAnICsgbmFtZSk7XG5cdCAgICAgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICAgICAgfVxuXG5cdCAgICAgICAgICAgICAgICBpZiAoZXJyKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgaWYoY2IpIHtcblx0ICAgICAgICAgICAgICAgICAgICAgICAgY2IoZXJyKTtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIHRocm93IGVycjtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgICAgICAgICB2YXIgdG1wbDtcblx0ICAgICAgICAgICAgICAgICAgICBpZihpbmZvKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIHRtcGwgPSBuZXcgVGVtcGxhdGUoaW5mby5zcmMsIF90aGlzLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGluZm8ucGF0aCwgZWFnZXJDb21waWxlKTtcblxuXHQgICAgICAgICAgICAgICAgICAgICAgICBpZighaW5mby5ub0NhY2hlKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgICAgICBpbmZvLmxvYWRlci5jYWNoZVtuYW1lXSA9IHRtcGw7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIHRtcGwgPSBuZXcgVGVtcGxhdGUoJycsIF90aGlzLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICcnLCBlYWdlckNvbXBpbGUpO1xuXHQgICAgICAgICAgICAgICAgICAgIH1cblxuXHQgICAgICAgICAgICAgICAgICAgIGlmKGNiKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIGNiKG51bGwsIHRtcGwpO1xuXHQgICAgICAgICAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgICAgICAgICAgICAgc3luY1Jlc3VsdCA9IHRtcGw7XG5cdCAgICAgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9O1xuXG5cdCAgICAgICAgICAgIGxpYi5hc3luY0l0ZXIodGhpcy5sb2FkZXJzLCBmdW5jdGlvbihsb2FkZXIsIGksIG5leHQsIGRvbmUpIHtcblx0ICAgICAgICAgICAgICAgIGZ1bmN0aW9uIGhhbmRsZShlcnIsIHNyYykge1xuXHQgICAgICAgICAgICAgICAgICAgIGlmKGVycikge1xuXHQgICAgICAgICAgICAgICAgICAgICAgICBkb25lKGVycik7XG5cdCAgICAgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICAgICAgICAgIGVsc2UgaWYoc3JjKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIHNyYy5sb2FkZXIgPSBsb2FkZXI7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIGRvbmUobnVsbCwgc3JjKTtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIG5leHQoKTtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgICAgIC8vIFJlc29sdmUgbmFtZSByZWxhdGl2ZSB0byBwYXJlbnROYW1lXG5cdCAgICAgICAgICAgICAgICBuYW1lID0gdGhhdC5yZXNvbHZlVGVtcGxhdGUobG9hZGVyLCBwYXJlbnROYW1lLCBuYW1lKTtcblxuXHQgICAgICAgICAgICAgICAgaWYobG9hZGVyLmFzeW5jKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgbG9hZGVyLmdldFNvdXJjZShuYW1lLCBoYW5kbGUpO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICAgICAgaGFuZGxlKG51bGwsIGxvYWRlci5nZXRTb3VyY2UobmFtZSkpO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9LCBjcmVhdGVUZW1wbGF0ZSk7XG5cblx0ICAgICAgICAgICAgcmV0dXJuIHN5bmNSZXN1bHQ7XG5cdCAgICAgICAgfVxuXHQgICAgfSxcblxuXHQgICAgZXhwcmVzczogZnVuY3Rpb24oYXBwKSB7XG5cdCAgICAgICAgdmFyIGVudiA9IHRoaXM7XG5cblx0ICAgICAgICBmdW5jdGlvbiBOdW5qdWNrc1ZpZXcobmFtZSwgb3B0cykge1xuXHQgICAgICAgICAgICB0aGlzLm5hbWUgICAgICAgICAgPSBuYW1lO1xuXHQgICAgICAgICAgICB0aGlzLnBhdGggICAgICAgICAgPSBuYW1lO1xuXHQgICAgICAgICAgICB0aGlzLmRlZmF1bHRFbmdpbmUgPSBvcHRzLmRlZmF1bHRFbmdpbmU7XG5cdCAgICAgICAgICAgIHRoaXMuZXh0ICAgICAgICAgICA9IHBhdGguZXh0bmFtZShuYW1lKTtcblx0ICAgICAgICAgICAgaWYgKCF0aGlzLmV4dCAmJiAhdGhpcy5kZWZhdWx0RW5naW5lKSB0aHJvdyBuZXcgRXJyb3IoJ05vIGRlZmF1bHQgZW5naW5lIHdhcyBzcGVjaWZpZWQgYW5kIG5vIGV4dGVuc2lvbiB3YXMgcHJvdmlkZWQuJyk7XG5cdCAgICAgICAgICAgIGlmICghdGhpcy5leHQpIHRoaXMubmFtZSArPSAodGhpcy5leHQgPSAoJy4nICE9PSB0aGlzLmRlZmF1bHRFbmdpbmVbMF0gPyAnLicgOiAnJykgKyB0aGlzLmRlZmF1bHRFbmdpbmUpO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIE51bmp1Y2tzVmlldy5wcm90b3R5cGUucmVuZGVyID0gZnVuY3Rpb24ob3B0cywgY2IpIHtcblx0ICAgICAgICAgIGVudi5yZW5kZXIodGhpcy5uYW1lLCBvcHRzLCBjYik7XG5cdCAgICAgICAgfTtcblxuXHQgICAgICAgIGFwcC5zZXQoJ3ZpZXcnLCBOdW5qdWNrc1ZpZXcpO1xuXHQgICAgICAgIHJldHVybiB0aGlzO1xuXHQgICAgfSxcblxuXHQgICAgcmVuZGVyOiBmdW5jdGlvbihuYW1lLCBjdHgsIGNiKSB7XG5cdCAgICAgICAgaWYobGliLmlzRnVuY3Rpb24oY3R4KSkge1xuXHQgICAgICAgICAgICBjYiA9IGN0eDtcblx0ICAgICAgICAgICAgY3R4ID0gbnVsbDtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICAvLyBXZSBzdXBwb3J0IGEgc3luY2hyb25vdXMgQVBJIHRvIG1ha2UgaXQgZWFzaWVyIHRvIG1pZ3JhdGVcblx0ICAgICAgICAvLyBleGlzdGluZyBjb2RlIHRvIGFzeW5jLiBUaGlzIHdvcmtzIGJlY2F1c2UgaWYgeW91IGRvbid0IGRvXG5cdCAgICAgICAgLy8gYW55dGhpbmcgYXN5bmMgd29yaywgdGhlIHdob2xlIHRoaW5nIGlzIGFjdHVhbGx5IHJ1blxuXHQgICAgICAgIC8vIHN5bmNocm9ub3VzbHkuXG5cdCAgICAgICAgdmFyIHN5bmNSZXN1bHQgPSBudWxsO1xuXG5cdCAgICAgICAgdGhpcy5nZXRUZW1wbGF0ZShuYW1lLCBmdW5jdGlvbihlcnIsIHRtcGwpIHtcblx0ICAgICAgICAgICAgaWYoZXJyICYmIGNiKSB7XG5cdCAgICAgICAgICAgICAgICBjYWxsYmFja0FzYXAoY2IsIGVycik7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSBpZihlcnIpIHtcblx0ICAgICAgICAgICAgICAgIHRocm93IGVycjtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgICAgIHN5bmNSZXN1bHQgPSB0bXBsLnJlbmRlcihjdHgsIGNiKTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH0pO1xuXG5cdCAgICAgICAgcmV0dXJuIHN5bmNSZXN1bHQ7XG5cdCAgICB9LFxuXG5cdCAgICByZW5kZXJTdHJpbmc6IGZ1bmN0aW9uKHNyYywgY3R4LCBvcHRzLCBjYikge1xuXHQgICAgICAgIGlmKGxpYi5pc0Z1bmN0aW9uKG9wdHMpKSB7XG5cdCAgICAgICAgICAgIGNiID0gb3B0cztcblx0ICAgICAgICAgICAgb3B0cyA9IHt9O1xuXHQgICAgICAgIH1cblx0ICAgICAgICBvcHRzID0gb3B0cyB8fCB7fTtcblxuXHQgICAgICAgIHZhciB0bXBsID0gbmV3IFRlbXBsYXRlKHNyYywgdGhpcywgb3B0cy5wYXRoKTtcblx0ICAgICAgICByZXR1cm4gdG1wbC5yZW5kZXIoY3R4LCBjYik7XG5cdCAgICB9XG5cdH0pO1xuXG5cdHZhciBDb250ZXh0ID0gT2JqLmV4dGVuZCh7XG5cdCAgICBpbml0OiBmdW5jdGlvbihjdHgsIGJsb2NrcywgZW52KSB7XG5cdCAgICAgICAgLy8gSGFzIHRvIGJlIHRpZWQgdG8gYW4gZW52aXJvbm1lbnQgc28gd2UgY2FuIHRhcCBpbnRvIGl0cyBnbG9iYWxzLlxuXHQgICAgICAgIHRoaXMuZW52ID0gZW52IHx8IG5ldyBFbnZpcm9ubWVudCgpO1xuXG5cdCAgICAgICAgLy8gTWFrZSBhIGR1cGxpY2F0ZSBvZiBjdHhcblx0ICAgICAgICB0aGlzLmN0eCA9IHt9O1xuXHQgICAgICAgIGZvcih2YXIgayBpbiBjdHgpIHtcblx0ICAgICAgICAgICAgaWYoY3R4Lmhhc093blByb3BlcnR5KGspKSB7XG5cdCAgICAgICAgICAgICAgICB0aGlzLmN0eFtrXSA9IGN0eFtrXTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHRoaXMuYmxvY2tzID0ge307XG5cdCAgICAgICAgdGhpcy5leHBvcnRlZCA9IFtdO1xuXG5cdCAgICAgICAgZm9yKHZhciBuYW1lIGluIGJsb2Nrcykge1xuXHQgICAgICAgICAgICB0aGlzLmFkZEJsb2NrKG5hbWUsIGJsb2Nrc1tuYW1lXSk7XG5cdCAgICAgICAgfVxuXHQgICAgfSxcblxuXHQgICAgbG9va3VwOiBmdW5jdGlvbihuYW1lKSB7XG5cdCAgICAgICAgLy8gVGhpcyBpcyBvbmUgb2YgdGhlIG1vc3QgY2FsbGVkIGZ1bmN0aW9ucywgc28gb3B0aW1pemUgZm9yXG5cdCAgICAgICAgLy8gdGhlIHR5cGljYWwgY2FzZSB3aGVyZSB0aGUgbmFtZSBpc24ndCBpbiB0aGUgZ2xvYmFsc1xuXHQgICAgICAgIGlmKG5hbWUgaW4gdGhpcy5lbnYuZ2xvYmFscyAmJiAhKG5hbWUgaW4gdGhpcy5jdHgpKSB7XG5cdCAgICAgICAgICAgIHJldHVybiB0aGlzLmVudi5nbG9iYWxzW25hbWVdO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgcmV0dXJuIHRoaXMuY3R4W25hbWVdO1xuXHQgICAgICAgIH1cblx0ICAgIH0sXG5cblx0ICAgIHNldFZhcmlhYmxlOiBmdW5jdGlvbihuYW1lLCB2YWwpIHtcblx0ICAgICAgICB0aGlzLmN0eFtuYW1lXSA9IHZhbDtcblx0ICAgIH0sXG5cblx0ICAgIGdldFZhcmlhYmxlczogZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgcmV0dXJuIHRoaXMuY3R4O1xuXHQgICAgfSxcblxuXHQgICAgYWRkQmxvY2s6IGZ1bmN0aW9uKG5hbWUsIGJsb2NrKSB7XG5cdCAgICAgICAgdGhpcy5ibG9ja3NbbmFtZV0gPSB0aGlzLmJsb2Nrc1tuYW1lXSB8fCBbXTtcblx0ICAgICAgICB0aGlzLmJsb2Nrc1tuYW1lXS5wdXNoKGJsb2NrKTtcblx0ICAgICAgICByZXR1cm4gdGhpcztcblx0ICAgIH0sXG5cblx0ICAgIGdldEJsb2NrOiBmdW5jdGlvbihuYW1lKSB7XG5cdCAgICAgICAgaWYoIXRoaXMuYmxvY2tzW25hbWVdKSB7XG5cdCAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcigndW5rbm93biBibG9jayBcIicgKyBuYW1lICsgJ1wiJyk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgcmV0dXJuIHRoaXMuYmxvY2tzW25hbWVdWzBdO1xuXHQgICAgfSxcblxuXHQgICAgZ2V0U3VwZXI6IGZ1bmN0aW9uKGVudiwgbmFtZSwgYmxvY2ssIGZyYW1lLCBydW50aW1lLCBjYikge1xuXHQgICAgICAgIHZhciBpZHggPSBsaWIuaW5kZXhPZih0aGlzLmJsb2Nrc1tuYW1lXSB8fCBbXSwgYmxvY2spO1xuXHQgICAgICAgIHZhciBibGsgPSB0aGlzLmJsb2Nrc1tuYW1lXVtpZHggKyAxXTtcblx0ICAgICAgICB2YXIgY29udGV4dCA9IHRoaXM7XG5cblx0ICAgICAgICBpZihpZHggPT09IC0xIHx8ICFibGspIHtcblx0ICAgICAgICAgICAgdGhyb3cgbmV3IEVycm9yKCdubyBzdXBlciBibG9jayBhdmFpbGFibGUgZm9yIFwiJyArIG5hbWUgKyAnXCInKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICBibGsoZW52LCBjb250ZXh0LCBmcmFtZSwgcnVudGltZSwgY2IpO1xuXHQgICAgfSxcblxuXHQgICAgYWRkRXhwb3J0OiBmdW5jdGlvbihuYW1lKSB7XG5cdCAgICAgICAgdGhpcy5leHBvcnRlZC5wdXNoKG5hbWUpO1xuXHQgICAgfSxcblxuXHQgICAgZ2V0RXhwb3J0ZWQ6IGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIHZhciBleHBvcnRlZCA9IHt9O1xuXHQgICAgICAgIGZvcih2YXIgaT0wOyBpPHRoaXMuZXhwb3J0ZWQubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICAgICAgdmFyIG5hbWUgPSB0aGlzLmV4cG9ydGVkW2ldO1xuXHQgICAgICAgICAgICBleHBvcnRlZFtuYW1lXSA9IHRoaXMuY3R4W25hbWVdO1xuXHQgICAgICAgIH1cblx0ICAgICAgICByZXR1cm4gZXhwb3J0ZWQ7XG5cdCAgICB9XG5cdH0pO1xuXG5cdFRlbXBsYXRlID0gT2JqLmV4dGVuZCh7XG5cdCAgICBpbml0OiBmdW5jdGlvbiAoc3JjLCBlbnYsIHBhdGgsIGVhZ2VyQ29tcGlsZSkge1xuXHQgICAgICAgIHRoaXMuZW52ID0gZW52IHx8IG5ldyBFbnZpcm9ubWVudCgpO1xuXG5cdCAgICAgICAgaWYobGliLmlzT2JqZWN0KHNyYykpIHtcblx0ICAgICAgICAgICAgc3dpdGNoKHNyYy50eXBlKSB7XG5cdCAgICAgICAgICAgIGNhc2UgJ2NvZGUnOiB0aGlzLnRtcGxQcm9wcyA9IHNyYy5vYmo7IGJyZWFrO1xuXHQgICAgICAgICAgICBjYXNlICdzdHJpbmcnOiB0aGlzLnRtcGxTdHIgPSBzcmMub2JqOyBicmVhaztcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIGlmKGxpYi5pc1N0cmluZyhzcmMpKSB7XG5cdCAgICAgICAgICAgIHRoaXMudG1wbFN0ciA9IHNyYztcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcignc3JjIG11c3QgYmUgYSBzdHJpbmcgb3IgYW4gb2JqZWN0IGRlc2NyaWJpbmcgJyArXG5cdCAgICAgICAgICAgICAgICAgICAgICAgICAgICAndGhlIHNvdXJjZScpO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHRoaXMucGF0aCA9IHBhdGg7XG5cblx0ICAgICAgICBpZihlYWdlckNvbXBpbGUpIHtcblx0ICAgICAgICAgICAgdmFyIF90aGlzID0gdGhpcztcblx0ICAgICAgICAgICAgdHJ5IHtcblx0ICAgICAgICAgICAgICAgIF90aGlzLl9jb21waWxlKCk7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgY2F0Y2goZXJyKSB7XG5cdCAgICAgICAgICAgICAgICB0aHJvdyBsaWIucHJldHRpZnlFcnJvcih0aGlzLnBhdGgsIHRoaXMuZW52Lm9wdHMuZGV2LCBlcnIpO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgfVxuXHQgICAgICAgIGVsc2Uge1xuXHQgICAgICAgICAgICB0aGlzLmNvbXBpbGVkID0gZmFsc2U7XG5cdCAgICAgICAgfVxuXHQgICAgfSxcblxuXHQgICAgcmVuZGVyOiBmdW5jdGlvbihjdHgsIHBhcmVudEZyYW1lLCBjYikge1xuXHQgICAgICAgIGlmICh0eXBlb2YgY3R4ID09PSAnZnVuY3Rpb24nKSB7XG5cdCAgICAgICAgICAgIGNiID0gY3R4O1xuXHQgICAgICAgICAgICBjdHggPSB7fTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSBpZiAodHlwZW9mIHBhcmVudEZyYW1lID09PSAnZnVuY3Rpb24nKSB7XG5cdCAgICAgICAgICAgIGNiID0gcGFyZW50RnJhbWU7XG5cdCAgICAgICAgICAgIHBhcmVudEZyYW1lID0gbnVsbDtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICB2YXIgZm9yY2VBc3luYyA9IHRydWU7XG5cdCAgICAgICAgaWYocGFyZW50RnJhbWUpIHtcblx0ICAgICAgICAgICAgLy8gSWYgdGhlcmUgaXMgYSBmcmFtZSwgd2UgYXJlIGJlaW5nIGNhbGxlZCBmcm9tIGludGVybmFsXG5cdCAgICAgICAgICAgIC8vIGNvZGUgb2YgYW5vdGhlciB0ZW1wbGF0ZSwgYW5kIHRoZSBpbnRlcm5hbCBzeXN0ZW1cblx0ICAgICAgICAgICAgLy8gZGVwZW5kcyBvbiB0aGUgc3luYy9hc3luYyBuYXR1cmUgb2YgdGhlIHBhcmVudCB0ZW1wbGF0ZVxuXHQgICAgICAgICAgICAvLyB0byBiZSBpbmhlcml0ZWQsIHNvIGZvcmNlIGFuIGFzeW5jIGNhbGxiYWNrXG5cdCAgICAgICAgICAgIGZvcmNlQXN5bmMgPSBmYWxzZTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICB2YXIgX3RoaXMgPSB0aGlzO1xuXHQgICAgICAgIC8vIENhdGNoIGNvbXBpbGUgZXJyb3JzIGZvciBhc3luYyByZW5kZXJpbmdcblx0ICAgICAgICB0cnkge1xuXHQgICAgICAgICAgICBfdGhpcy5jb21waWxlKCk7XG5cdCAgICAgICAgfSBjYXRjaCAoX2Vycikge1xuXHQgICAgICAgICAgICB2YXIgZXJyID0gbGliLnByZXR0aWZ5RXJyb3IodGhpcy5wYXRoLCB0aGlzLmVudi5vcHRzLmRldiwgX2Vycik7XG5cdCAgICAgICAgICAgIGlmIChjYikgcmV0dXJuIGNhbGxiYWNrQXNhcChjYiwgZXJyKTtcblx0ICAgICAgICAgICAgZWxzZSB0aHJvdyBlcnI7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgdmFyIGNvbnRleHQgPSBuZXcgQ29udGV4dChjdHggfHwge30sIF90aGlzLmJsb2NrcywgX3RoaXMuZW52KTtcblx0ICAgICAgICB2YXIgZnJhbWUgPSBwYXJlbnRGcmFtZSA/IHBhcmVudEZyYW1lLnB1c2godHJ1ZSkgOiBuZXcgRnJhbWUoKTtcblx0ICAgICAgICBmcmFtZS50b3BMZXZlbCA9IHRydWU7XG5cdCAgICAgICAgdmFyIHN5bmNSZXN1bHQgPSBudWxsO1xuXG5cdCAgICAgICAgX3RoaXMucm9vdFJlbmRlckZ1bmMoXG5cdCAgICAgICAgICAgIF90aGlzLmVudixcblx0ICAgICAgICAgICAgY29udGV4dCxcblx0ICAgICAgICAgICAgZnJhbWUgfHwgbmV3IEZyYW1lKCksXG5cdCAgICAgICAgICAgIHJ1bnRpbWUsXG5cdCAgICAgICAgICAgIGZ1bmN0aW9uKGVyciwgcmVzKSB7XG5cdCAgICAgICAgICAgICAgICBpZihlcnIpIHtcblx0ICAgICAgICAgICAgICAgICAgICBlcnIgPSBsaWIucHJldHRpZnlFcnJvcihfdGhpcy5wYXRoLCBfdGhpcy5lbnYub3B0cy5kZXYsIGVycik7XG5cdCAgICAgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgICAgIGlmKGNiKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgaWYoZm9yY2VBc3luYykge1xuXHQgICAgICAgICAgICAgICAgICAgICAgICBjYWxsYmFja0FzYXAoY2IsIGVyciwgcmVzKTtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICAgICAgICAgIGNiKGVyciwgcmVzKTtcblx0ICAgICAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgICAgICAgICBpZihlcnIpIHsgdGhyb3cgZXJyOyB9XG5cdCAgICAgICAgICAgICAgICAgICAgc3luY1Jlc3VsdCA9IHJlcztcblx0ICAgICAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgICk7XG5cblx0ICAgICAgICByZXR1cm4gc3luY1Jlc3VsdDtcblx0ICAgIH0sXG5cblxuXHQgICAgZ2V0RXhwb3J0ZWQ6IGZ1bmN0aW9uKGN0eCwgcGFyZW50RnJhbWUsIGNiKSB7XG5cdCAgICAgICAgaWYgKHR5cGVvZiBjdHggPT09ICdmdW5jdGlvbicpIHtcblx0ICAgICAgICAgICAgY2IgPSBjdHg7XG5cdCAgICAgICAgICAgIGN0eCA9IHt9O1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGlmICh0eXBlb2YgcGFyZW50RnJhbWUgPT09ICdmdW5jdGlvbicpIHtcblx0ICAgICAgICAgICAgY2IgPSBwYXJlbnRGcmFtZTtcblx0ICAgICAgICAgICAgcGFyZW50RnJhbWUgPSBudWxsO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIC8vIENhdGNoIGNvbXBpbGUgZXJyb3JzIGZvciBhc3luYyByZW5kZXJpbmdcblx0ICAgICAgICB0cnkge1xuXHQgICAgICAgICAgICB0aGlzLmNvbXBpbGUoKTtcblx0ICAgICAgICB9IGNhdGNoIChlKSB7XG5cdCAgICAgICAgICAgIGlmIChjYikgcmV0dXJuIGNiKGUpO1xuXHQgICAgICAgICAgICBlbHNlIHRocm93IGU7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgdmFyIGZyYW1lID0gcGFyZW50RnJhbWUgPyBwYXJlbnRGcmFtZS5wdXNoKCkgOiBuZXcgRnJhbWUoKTtcblx0ICAgICAgICBmcmFtZS50b3BMZXZlbCA9IHRydWU7XG5cblx0ICAgICAgICAvLyBSdW4gdGhlIHJvb3RSZW5kZXJGdW5jIHRvIHBvcHVsYXRlIHRoZSBjb250ZXh0IHdpdGggZXhwb3J0ZWQgdmFyc1xuXHQgICAgICAgIHZhciBjb250ZXh0ID0gbmV3IENvbnRleHQoY3R4IHx8IHt9LCB0aGlzLmJsb2NrcywgdGhpcy5lbnYpO1xuXHQgICAgICAgIHRoaXMucm9vdFJlbmRlckZ1bmModGhpcy5lbnYsXG5cdCAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250ZXh0LFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgZnJhbWUsXG5cdCAgICAgICAgICAgICAgICAgICAgICAgICAgICBydW50aW1lLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgZnVuY3Rpb24oZXJyKSB7XG5cdCAgICAgICAgXHRcdCAgICAgICAgaWYgKCBlcnIgKSB7XG5cdCAgICAgICAgXHRcdFx0ICAgIGNiKGVyciwgbnVsbCk7XG5cdCAgICAgICAgXHRcdCAgICAgICAgfSBlbHNlIHtcblx0ICAgICAgICBcdFx0XHQgICAgY2IobnVsbCwgY29udGV4dC5nZXRFeHBvcnRlZCgpKTtcblx0ICAgICAgICBcdFx0ICAgICAgICB9XG5cdCAgICAgICAgICAgICAgICAgICAgICAgICAgICB9KTtcblx0ICAgIH0sXG5cblx0ICAgIGNvbXBpbGU6IGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIGlmKCF0aGlzLmNvbXBpbGVkKSB7XG5cdCAgICAgICAgICAgIHRoaXMuX2NvbXBpbGUoKTtcblx0ICAgICAgICB9XG5cdCAgICB9LFxuXG5cdCAgICBfY29tcGlsZTogZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgdmFyIHByb3BzO1xuXG5cdCAgICAgICAgaWYodGhpcy50bXBsUHJvcHMpIHtcblx0ICAgICAgICAgICAgcHJvcHMgPSB0aGlzLnRtcGxQcm9wcztcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIHZhciBzb3VyY2UgPSBjb21waWxlci5jb21waWxlKHRoaXMudG1wbFN0cixcblx0ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5lbnYuYXN5bmNGaWx0ZXJzLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmVudi5leHRlbnNpb25zTGlzdCxcblx0ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGhpcy5wYXRoLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aGlzLmVudi5vcHRzKTtcblxuXHQgICAgICAgICAgICAvKiBqc2xpbnQgZXZpbDogdHJ1ZSAqL1xuXHQgICAgICAgICAgICB2YXIgZnVuYyA9IG5ldyBGdW5jdGlvbihzb3VyY2UpO1xuXHQgICAgICAgICAgICBwcm9wcyA9IGZ1bmMoKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICB0aGlzLmJsb2NrcyA9IHRoaXMuX2dldEJsb2Nrcyhwcm9wcyk7XG5cdCAgICAgICAgdGhpcy5yb290UmVuZGVyRnVuYyA9IHByb3BzLnJvb3Q7XG5cdCAgICAgICAgdGhpcy5jb21waWxlZCA9IHRydWU7XG5cdCAgICB9LFxuXG5cdCAgICBfZ2V0QmxvY2tzOiBmdW5jdGlvbihwcm9wcykge1xuXHQgICAgICAgIHZhciBibG9ja3MgPSB7fTtcblxuXHQgICAgICAgIGZvcih2YXIgayBpbiBwcm9wcykge1xuXHQgICAgICAgICAgICBpZihrLnNsaWNlKDAsIDIpID09PSAnYl8nKSB7XG5cdCAgICAgICAgICAgICAgICBibG9ja3Nbay5zbGljZSgyKV0gPSBwcm9wc1trXTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHJldHVybiBibG9ja3M7XG5cdCAgICB9XG5cdH0pO1xuXG5cdG1vZHVsZS5leHBvcnRzID0ge1xuXHQgICAgRW52aXJvbm1lbnQ6IEVudmlyb25tZW50LFxuXHQgICAgVGVtcGxhdGU6IFRlbXBsYXRlXG5cdH07XG5cblxuLyoqKi8gfSxcbi8qIDMgKi9cbi8qKiovIGZ1bmN0aW9uKG1vZHVsZSwgZXhwb3J0cykge1xuXG5cdFxuXG4vKioqLyB9LFxuLyogNCAqL1xuLyoqKi8gZnVuY3Rpb24obW9kdWxlLCBleHBvcnRzLCBfX3dlYnBhY2tfcmVxdWlyZV9fKSB7XG5cblx0XCJ1c2Ugc3RyaWN0XCI7XG5cblx0Ly8gcmF3QXNhcCBwcm92aWRlcyBldmVyeXRoaW5nIHdlIG5lZWQgZXhjZXB0IGV4Y2VwdGlvbiBtYW5hZ2VtZW50LlxuXHR2YXIgcmF3QXNhcCA9IF9fd2VicGFja19yZXF1aXJlX18oNSk7XG5cdC8vIFJhd1Rhc2tzIGFyZSByZWN5Y2xlZCB0byByZWR1Y2UgR0MgY2h1cm4uXG5cdHZhciBmcmVlVGFza3MgPSBbXTtcblx0Ly8gV2UgcXVldWUgZXJyb3JzIHRvIGVuc3VyZSB0aGV5IGFyZSB0aHJvd24gaW4gcmlnaHQgb3JkZXIgKEZJRk8pLlxuXHQvLyBBcnJheS1hcy1xdWV1ZSBpcyBnb29kIGVub3VnaCBoZXJlLCBzaW5jZSB3ZSBhcmUganVzdCBkZWFsaW5nIHdpdGggZXhjZXB0aW9ucy5cblx0dmFyIHBlbmRpbmdFcnJvcnMgPSBbXTtcblx0dmFyIHJlcXVlc3RFcnJvclRocm93ID0gcmF3QXNhcC5tYWtlUmVxdWVzdENhbGxGcm9tVGltZXIodGhyb3dGaXJzdEVycm9yKTtcblxuXHRmdW5jdGlvbiB0aHJvd0ZpcnN0RXJyb3IoKSB7XG5cdCAgICBpZiAocGVuZGluZ0Vycm9ycy5sZW5ndGgpIHtcblx0ICAgICAgICB0aHJvdyBwZW5kaW5nRXJyb3JzLnNoaWZ0KCk7XG5cdCAgICB9XG5cdH1cblxuXHQvKipcblx0ICogQ2FsbHMgYSB0YXNrIGFzIHNvb24gYXMgcG9zc2libGUgYWZ0ZXIgcmV0dXJuaW5nLCBpbiBpdHMgb3duIGV2ZW50LCB3aXRoIHByaW9yaXR5XG5cdCAqIG92ZXIgb3RoZXIgZXZlbnRzIGxpa2UgYW5pbWF0aW9uLCByZWZsb3csIGFuZCByZXBhaW50LiBBbiBlcnJvciB0aHJvd24gZnJvbSBhblxuXHQgKiBldmVudCB3aWxsIG5vdCBpbnRlcnJ1cHQsIG5vciBldmVuIHN1YnN0YW50aWFsbHkgc2xvdyBkb3duIHRoZSBwcm9jZXNzaW5nIG9mXG5cdCAqIG90aGVyIGV2ZW50cywgYnV0IHdpbGwgYmUgcmF0aGVyIHBvc3Rwb25lZCB0byBhIGxvd2VyIHByaW9yaXR5IGV2ZW50LlxuXHQgKiBAcGFyYW0ge3tjYWxsfX0gdGFzayBBIGNhbGxhYmxlIG9iamVjdCwgdHlwaWNhbGx5IGEgZnVuY3Rpb24gdGhhdCB0YWtlcyBub1xuXHQgKiBhcmd1bWVudHMuXG5cdCAqL1xuXHRtb2R1bGUuZXhwb3J0cyA9IGFzYXA7XG5cdGZ1bmN0aW9uIGFzYXAodGFzaykge1xuXHQgICAgdmFyIHJhd1Rhc2s7XG5cdCAgICBpZiAoZnJlZVRhc2tzLmxlbmd0aCkge1xuXHQgICAgICAgIHJhd1Rhc2sgPSBmcmVlVGFza3MucG9wKCk7XG5cdCAgICB9IGVsc2Uge1xuXHQgICAgICAgIHJhd1Rhc2sgPSBuZXcgUmF3VGFzaygpO1xuXHQgICAgfVxuXHQgICAgcmF3VGFzay50YXNrID0gdGFzaztcblx0ICAgIHJhd0FzYXAocmF3VGFzayk7XG5cdH1cblxuXHQvLyBXZSB3cmFwIHRhc2tzIHdpdGggcmVjeWNsYWJsZSB0YXNrIG9iamVjdHMuICBBIHRhc2sgb2JqZWN0IGltcGxlbWVudHNcblx0Ly8gYGNhbGxgLCBqdXN0IGxpa2UgYSBmdW5jdGlvbi5cblx0ZnVuY3Rpb24gUmF3VGFzaygpIHtcblx0ICAgIHRoaXMudGFzayA9IG51bGw7XG5cdH1cblxuXHQvLyBUaGUgc29sZSBwdXJwb3NlIG9mIHdyYXBwaW5nIHRoZSB0YXNrIGlzIHRvIGNhdGNoIHRoZSBleGNlcHRpb24gYW5kIHJlY3ljbGVcblx0Ly8gdGhlIHRhc2sgb2JqZWN0IGFmdGVyIGl0cyBzaW5nbGUgdXNlLlxuXHRSYXdUYXNrLnByb3RvdHlwZS5jYWxsID0gZnVuY3Rpb24gKCkge1xuXHQgICAgdHJ5IHtcblx0ICAgICAgICB0aGlzLnRhc2suY2FsbCgpO1xuXHQgICAgfSBjYXRjaCAoZXJyb3IpIHtcblx0ICAgICAgICBpZiAoYXNhcC5vbmVycm9yKSB7XG5cdCAgICAgICAgICAgIC8vIFRoaXMgaG9vayBleGlzdHMgcHVyZWx5IGZvciB0ZXN0aW5nIHB1cnBvc2VzLlxuXHQgICAgICAgICAgICAvLyBJdHMgbmFtZSB3aWxsIGJlIHBlcmlvZGljYWxseSByYW5kb21pemVkIHRvIGJyZWFrIGFueSBjb2RlIHRoYXRcblx0ICAgICAgICAgICAgLy8gZGVwZW5kcyBvbiBpdHMgZXhpc3RlbmNlLlxuXHQgICAgICAgICAgICBhc2FwLm9uZXJyb3IoZXJyb3IpO1xuXHQgICAgICAgIH0gZWxzZSB7XG5cdCAgICAgICAgICAgIC8vIEluIGEgd2ViIGJyb3dzZXIsIGV4Y2VwdGlvbnMgYXJlIG5vdCBmYXRhbC4gSG93ZXZlciwgdG8gYXZvaWRcblx0ICAgICAgICAgICAgLy8gc2xvd2luZyBkb3duIHRoZSBxdWV1ZSBvZiBwZW5kaW5nIHRhc2tzLCB3ZSByZXRocm93IHRoZSBlcnJvciBpbiBhXG5cdCAgICAgICAgICAgIC8vIGxvd2VyIHByaW9yaXR5IHR1cm4uXG5cdCAgICAgICAgICAgIHBlbmRpbmdFcnJvcnMucHVzaChlcnJvcik7XG5cdCAgICAgICAgICAgIHJlcXVlc3RFcnJvclRocm93KCk7XG5cdCAgICAgICAgfVxuXHQgICAgfSBmaW5hbGx5IHtcblx0ICAgICAgICB0aGlzLnRhc2sgPSBudWxsO1xuXHQgICAgICAgIGZyZWVUYXNrc1tmcmVlVGFza3MubGVuZ3RoXSA9IHRoaXM7XG5cdCAgICB9XG5cdH07XG5cblxuLyoqKi8gfSxcbi8qIDUgKi9cbi8qKiovIGZ1bmN0aW9uKG1vZHVsZSwgZXhwb3J0cykge1xuXG5cdC8qIFdFQlBBQ0sgVkFSIElOSkVDVElPTiAqLyhmdW5jdGlvbihnbG9iYWwpIHtcInVzZSBzdHJpY3RcIjtcblxuXHQvLyBVc2UgdGhlIGZhc3Rlc3QgbWVhbnMgcG9zc2libGUgdG8gZXhlY3V0ZSBhIHRhc2sgaW4gaXRzIG93biB0dXJuLCB3aXRoXG5cdC8vIHByaW9yaXR5IG92ZXIgb3RoZXIgZXZlbnRzIGluY2x1ZGluZyBJTywgYW5pbWF0aW9uLCByZWZsb3csIGFuZCByZWRyYXdcblx0Ly8gZXZlbnRzIGluIGJyb3dzZXJzLlxuXHQvL1xuXHQvLyBBbiBleGNlcHRpb24gdGhyb3duIGJ5IGEgdGFzayB3aWxsIHBlcm1hbmVudGx5IGludGVycnVwdCB0aGUgcHJvY2Vzc2luZyBvZlxuXHQvLyBzdWJzZXF1ZW50IHRhc2tzLiBUaGUgaGlnaGVyIGxldmVsIGBhc2FwYCBmdW5jdGlvbiBlbnN1cmVzIHRoYXQgaWYgYW5cblx0Ly8gZXhjZXB0aW9uIGlzIHRocm93biBieSBhIHRhc2ssIHRoYXQgdGhlIHRhc2sgcXVldWUgd2lsbCBjb250aW51ZSBmbHVzaGluZyBhc1xuXHQvLyBzb29uIGFzIHBvc3NpYmxlLCBidXQgaWYgeW91IHVzZSBgcmF3QXNhcGAgZGlyZWN0bHksIHlvdSBhcmUgcmVzcG9uc2libGUgdG9cblx0Ly8gZWl0aGVyIGVuc3VyZSB0aGF0IG5vIGV4Y2VwdGlvbnMgYXJlIHRocm93biBmcm9tIHlvdXIgdGFzaywgb3IgdG8gbWFudWFsbHlcblx0Ly8gY2FsbCBgcmF3QXNhcC5yZXF1ZXN0Rmx1c2hgIGlmIGFuIGV4Y2VwdGlvbiBpcyB0aHJvd24uXG5cdG1vZHVsZS5leHBvcnRzID0gcmF3QXNhcDtcblx0ZnVuY3Rpb24gcmF3QXNhcCh0YXNrKSB7XG5cdCAgICBpZiAoIXF1ZXVlLmxlbmd0aCkge1xuXHQgICAgICAgIHJlcXVlc3RGbHVzaCgpO1xuXHQgICAgICAgIGZsdXNoaW5nID0gdHJ1ZTtcblx0ICAgIH1cblx0ICAgIC8vIEVxdWl2YWxlbnQgdG8gcHVzaCwgYnV0IGF2b2lkcyBhIGZ1bmN0aW9uIGNhbGwuXG5cdCAgICBxdWV1ZVtxdWV1ZS5sZW5ndGhdID0gdGFzaztcblx0fVxuXG5cdHZhciBxdWV1ZSA9IFtdO1xuXHQvLyBPbmNlIGEgZmx1c2ggaGFzIGJlZW4gcmVxdWVzdGVkLCBubyBmdXJ0aGVyIGNhbGxzIHRvIGByZXF1ZXN0Rmx1c2hgIGFyZVxuXHQvLyBuZWNlc3NhcnkgdW50aWwgdGhlIG5leHQgYGZsdXNoYCBjb21wbGV0ZXMuXG5cdHZhciBmbHVzaGluZyA9IGZhbHNlO1xuXHQvLyBgcmVxdWVzdEZsdXNoYCBpcyBhbiBpbXBsZW1lbnRhdGlvbi1zcGVjaWZpYyBtZXRob2QgdGhhdCBhdHRlbXB0cyB0byBraWNrXG5cdC8vIG9mZiBhIGBmbHVzaGAgZXZlbnQgYXMgcXVpY2tseSBhcyBwb3NzaWJsZS4gYGZsdXNoYCB3aWxsIGF0dGVtcHQgdG8gZXhoYXVzdFxuXHQvLyB0aGUgZXZlbnQgcXVldWUgYmVmb3JlIHlpZWxkaW5nIHRvIHRoZSBicm93c2VyJ3Mgb3duIGV2ZW50IGxvb3AuXG5cdHZhciByZXF1ZXN0Rmx1c2g7XG5cdC8vIFRoZSBwb3NpdGlvbiBvZiB0aGUgbmV4dCB0YXNrIHRvIGV4ZWN1dGUgaW4gdGhlIHRhc2sgcXVldWUuIFRoaXMgaXNcblx0Ly8gcHJlc2VydmVkIGJldHdlZW4gY2FsbHMgdG8gYGZsdXNoYCBzbyB0aGF0IGl0IGNhbiBiZSByZXN1bWVkIGlmXG5cdC8vIGEgdGFzayB0aHJvd3MgYW4gZXhjZXB0aW9uLlxuXHR2YXIgaW5kZXggPSAwO1xuXHQvLyBJZiBhIHRhc2sgc2NoZWR1bGVzIGFkZGl0aW9uYWwgdGFza3MgcmVjdXJzaXZlbHksIHRoZSB0YXNrIHF1ZXVlIGNhbiBncm93XG5cdC8vIHVuYm91bmRlZC4gVG8gcHJldmVudCBtZW1vcnkgZXhoYXVzdGlvbiwgdGhlIHRhc2sgcXVldWUgd2lsbCBwZXJpb2RpY2FsbHlcblx0Ly8gdHJ1bmNhdGUgYWxyZWFkeS1jb21wbGV0ZWQgdGFza3MuXG5cdHZhciBjYXBhY2l0eSA9IDEwMjQ7XG5cblx0Ly8gVGhlIGZsdXNoIGZ1bmN0aW9uIHByb2Nlc3NlcyBhbGwgdGFza3MgdGhhdCBoYXZlIGJlZW4gc2NoZWR1bGVkIHdpdGhcblx0Ly8gYHJhd0FzYXBgIHVubGVzcyBhbmQgdW50aWwgb25lIG9mIHRob3NlIHRhc2tzIHRocm93cyBhbiBleGNlcHRpb24uXG5cdC8vIElmIGEgdGFzayB0aHJvd3MgYW4gZXhjZXB0aW9uLCBgZmx1c2hgIGVuc3VyZXMgdGhhdCBpdHMgc3RhdGUgd2lsbCByZW1haW5cblx0Ly8gY29uc2lzdGVudCBhbmQgd2lsbCByZXN1bWUgd2hlcmUgaXQgbGVmdCBvZmYgd2hlbiBjYWxsZWQgYWdhaW4uXG5cdC8vIEhvd2V2ZXIsIGBmbHVzaGAgZG9lcyBub3QgbWFrZSBhbnkgYXJyYW5nZW1lbnRzIHRvIGJlIGNhbGxlZCBhZ2FpbiBpZiBhblxuXHQvLyBleGNlcHRpb24gaXMgdGhyb3duLlxuXHRmdW5jdGlvbiBmbHVzaCgpIHtcblx0ICAgIHdoaWxlIChpbmRleCA8IHF1ZXVlLmxlbmd0aCkge1xuXHQgICAgICAgIHZhciBjdXJyZW50SW5kZXggPSBpbmRleDtcblx0ICAgICAgICAvLyBBZHZhbmNlIHRoZSBpbmRleCBiZWZvcmUgY2FsbGluZyB0aGUgdGFzay4gVGhpcyBlbnN1cmVzIHRoYXQgd2Ugd2lsbFxuXHQgICAgICAgIC8vIGJlZ2luIGZsdXNoaW5nIG9uIHRoZSBuZXh0IHRhc2sgdGhlIHRhc2sgdGhyb3dzIGFuIGVycm9yLlxuXHQgICAgICAgIGluZGV4ID0gaW5kZXggKyAxO1xuXHQgICAgICAgIHF1ZXVlW2N1cnJlbnRJbmRleF0uY2FsbCgpO1xuXHQgICAgICAgIC8vIFByZXZlbnQgbGVha2luZyBtZW1vcnkgZm9yIGxvbmcgY2hhaW5zIG9mIHJlY3Vyc2l2ZSBjYWxscyB0byBgYXNhcGAuXG5cdCAgICAgICAgLy8gSWYgd2UgY2FsbCBgYXNhcGAgd2l0aGluIHRhc2tzIHNjaGVkdWxlZCBieSBgYXNhcGAsIHRoZSBxdWV1ZSB3aWxsXG5cdCAgICAgICAgLy8gZ3JvdywgYnV0IHRvIGF2b2lkIGFuIE8obikgd2FsayBmb3IgZXZlcnkgdGFzayB3ZSBleGVjdXRlLCB3ZSBkb24ndFxuXHQgICAgICAgIC8vIHNoaWZ0IHRhc2tzIG9mZiB0aGUgcXVldWUgYWZ0ZXIgdGhleSBoYXZlIGJlZW4gZXhlY3V0ZWQuXG5cdCAgICAgICAgLy8gSW5zdGVhZCwgd2UgcGVyaW9kaWNhbGx5IHNoaWZ0IDEwMjQgdGFza3Mgb2ZmIHRoZSBxdWV1ZS5cblx0ICAgICAgICBpZiAoaW5kZXggPiBjYXBhY2l0eSkge1xuXHQgICAgICAgICAgICAvLyBNYW51YWxseSBzaGlmdCBhbGwgdmFsdWVzIHN0YXJ0aW5nIGF0IHRoZSBpbmRleCBiYWNrIHRvIHRoZVxuXHQgICAgICAgICAgICAvLyBiZWdpbm5pbmcgb2YgdGhlIHF1ZXVlLlxuXHQgICAgICAgICAgICBmb3IgKHZhciBzY2FuID0gMCwgbmV3TGVuZ3RoID0gcXVldWUubGVuZ3RoIC0gaW5kZXg7IHNjYW4gPCBuZXdMZW5ndGg7IHNjYW4rKykge1xuXHQgICAgICAgICAgICAgICAgcXVldWVbc2Nhbl0gPSBxdWV1ZVtzY2FuICsgaW5kZXhdO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIHF1ZXVlLmxlbmd0aCAtPSBpbmRleDtcblx0ICAgICAgICAgICAgaW5kZXggPSAwO1xuXHQgICAgICAgIH1cblx0ICAgIH1cblx0ICAgIHF1ZXVlLmxlbmd0aCA9IDA7XG5cdCAgICBpbmRleCA9IDA7XG5cdCAgICBmbHVzaGluZyA9IGZhbHNlO1xuXHR9XG5cblx0Ly8gYHJlcXVlc3RGbHVzaGAgaXMgaW1wbGVtZW50ZWQgdXNpbmcgYSBzdHJhdGVneSBiYXNlZCBvbiBkYXRhIGNvbGxlY3RlZCBmcm9tXG5cdC8vIGV2ZXJ5IGF2YWlsYWJsZSBTYXVjZUxhYnMgU2VsZW5pdW0gd2ViIGRyaXZlciB3b3JrZXIgYXQgdGltZSBvZiB3cml0aW5nLlxuXHQvLyBodHRwczovL2RvY3MuZ29vZ2xlLmNvbS9zcHJlYWRzaGVldHMvZC8xbUctNVVZR3VwNXF4R2RFTVdraFA2QldDejA1M05VYjJFMVFvVVRVMTZ1QS9lZGl0I2dpZD03ODM3MjQ1OTNcblxuXHQvLyBTYWZhcmkgNiBhbmQgNi4xIGZvciBkZXNrdG9wLCBpUGFkLCBhbmQgaVBob25lIGFyZSB0aGUgb25seSBicm93c2VycyB0aGF0XG5cdC8vIGhhdmUgV2ViS2l0TXV0YXRpb25PYnNlcnZlciBidXQgbm90IHVuLXByZWZpeGVkIE11dGF0aW9uT2JzZXJ2ZXIuXG5cdC8vIE11c3QgdXNlIGBnbG9iYWxgIGluc3RlYWQgb2YgYHdpbmRvd2AgdG8gd29yayBpbiBib3RoIGZyYW1lcyBhbmQgd2ViXG5cdC8vIHdvcmtlcnMuIGBnbG9iYWxgIGlzIGEgcHJvdmlzaW9uIG9mIEJyb3dzZXJpZnksIE1yLCBNcnMsIG9yIE1vcC5cblx0dmFyIEJyb3dzZXJNdXRhdGlvbk9ic2VydmVyID0gZ2xvYmFsLk11dGF0aW9uT2JzZXJ2ZXIgfHwgZ2xvYmFsLldlYktpdE11dGF0aW9uT2JzZXJ2ZXI7XG5cblx0Ly8gTXV0YXRpb25PYnNlcnZlcnMgYXJlIGRlc2lyYWJsZSBiZWNhdXNlIHRoZXkgaGF2ZSBoaWdoIHByaW9yaXR5IGFuZCB3b3JrXG5cdC8vIHJlbGlhYmx5IGV2ZXJ5d2hlcmUgdGhleSBhcmUgaW1wbGVtZW50ZWQuXG5cdC8vIFRoZXkgYXJlIGltcGxlbWVudGVkIGluIGFsbCBtb2Rlcm4gYnJvd3NlcnMuXG5cdC8vXG5cdC8vIC0gQW5kcm9pZCA0LTQuM1xuXHQvLyAtIENocm9tZSAyNi0zNFxuXHQvLyAtIEZpcmVmb3ggMTQtMjlcblx0Ly8gLSBJbnRlcm5ldCBFeHBsb3JlciAxMVxuXHQvLyAtIGlQYWQgU2FmYXJpIDYtNy4xXG5cdC8vIC0gaVBob25lIFNhZmFyaSA3LTcuMVxuXHQvLyAtIFNhZmFyaSA2LTdcblx0aWYgKHR5cGVvZiBCcm93c2VyTXV0YXRpb25PYnNlcnZlciA9PT0gXCJmdW5jdGlvblwiKSB7XG5cdCAgICByZXF1ZXN0Rmx1c2ggPSBtYWtlUmVxdWVzdENhbGxGcm9tTXV0YXRpb25PYnNlcnZlcihmbHVzaCk7XG5cblx0Ly8gTWVzc2FnZUNoYW5uZWxzIGFyZSBkZXNpcmFibGUgYmVjYXVzZSB0aGV5IGdpdmUgZGlyZWN0IGFjY2VzcyB0byB0aGUgSFRNTFxuXHQvLyB0YXNrIHF1ZXVlLCBhcmUgaW1wbGVtZW50ZWQgaW4gSW50ZXJuZXQgRXhwbG9yZXIgMTAsIFNhZmFyaSA1LjAtMSwgYW5kIE9wZXJhXG5cdC8vIDExLTEyLCBhbmQgaW4gd2ViIHdvcmtlcnMgaW4gbWFueSBlbmdpbmVzLlxuXHQvLyBBbHRob3VnaCBtZXNzYWdlIGNoYW5uZWxzIHlpZWxkIHRvIGFueSBxdWV1ZWQgcmVuZGVyaW5nIGFuZCBJTyB0YXNrcywgdGhleVxuXHQvLyB3b3VsZCBiZSBiZXR0ZXIgdGhhbiBpbXBvc2luZyB0aGUgNG1zIGRlbGF5IG9mIHRpbWVycy5cblx0Ly8gSG93ZXZlciwgdGhleSBkbyBub3Qgd29yayByZWxpYWJseSBpbiBJbnRlcm5ldCBFeHBsb3JlciBvciBTYWZhcmkuXG5cblx0Ly8gSW50ZXJuZXQgRXhwbG9yZXIgMTAgaXMgdGhlIG9ubHkgYnJvd3NlciB0aGF0IGhhcyBzZXRJbW1lZGlhdGUgYnV0IGRvZXNcblx0Ly8gbm90IGhhdmUgTXV0YXRpb25PYnNlcnZlcnMuXG5cdC8vIEFsdGhvdWdoIHNldEltbWVkaWF0ZSB5aWVsZHMgdG8gdGhlIGJyb3dzZXIncyByZW5kZXJlciwgaXQgd291bGQgYmVcblx0Ly8gcHJlZmVycmFibGUgdG8gZmFsbGluZyBiYWNrIHRvIHNldFRpbWVvdXQgc2luY2UgaXQgZG9lcyBub3QgaGF2ZVxuXHQvLyB0aGUgbWluaW11bSA0bXMgcGVuYWx0eS5cblx0Ly8gVW5mb3J0dW5hdGVseSB0aGVyZSBhcHBlYXJzIHRvIGJlIGEgYnVnIGluIEludGVybmV0IEV4cGxvcmVyIDEwIE1vYmlsZSAoYW5kXG5cdC8vIERlc2t0b3AgdG8gYSBsZXNzZXIgZXh0ZW50KSB0aGF0IHJlbmRlcnMgYm90aCBzZXRJbW1lZGlhdGUgYW5kXG5cdC8vIE1lc3NhZ2VDaGFubmVsIHVzZWxlc3MgZm9yIHRoZSBwdXJwb3NlcyBvZiBBU0FQLlxuXHQvLyBodHRwczovL2dpdGh1Yi5jb20va3Jpc2tvd2FsL3EvaXNzdWVzLzM5NlxuXG5cdC8vIFRpbWVycyBhcmUgaW1wbGVtZW50ZWQgdW5pdmVyc2FsbHkuXG5cdC8vIFdlIGZhbGwgYmFjayB0byB0aW1lcnMgaW4gd29ya2VycyBpbiBtb3N0IGVuZ2luZXMsIGFuZCBpbiBmb3JlZ3JvdW5kXG5cdC8vIGNvbnRleHRzIGluIHRoZSBmb2xsb3dpbmcgYnJvd3NlcnMuXG5cdC8vIEhvd2V2ZXIsIG5vdGUgdGhhdCBldmVuIHRoaXMgc2ltcGxlIGNhc2UgcmVxdWlyZXMgbnVhbmNlcyB0byBvcGVyYXRlIGluIGFcblx0Ly8gYnJvYWQgc3BlY3RydW0gb2YgYnJvd3NlcnMuXG5cdC8vXG5cdC8vIC0gRmlyZWZveCAzLTEzXG5cdC8vIC0gSW50ZXJuZXQgRXhwbG9yZXIgNi05XG5cdC8vIC0gaVBhZCBTYWZhcmkgNC4zXG5cdC8vIC0gTHlueCAyLjguN1xuXHR9IGVsc2Uge1xuXHQgICAgcmVxdWVzdEZsdXNoID0gbWFrZVJlcXVlc3RDYWxsRnJvbVRpbWVyKGZsdXNoKTtcblx0fVxuXG5cdC8vIGByZXF1ZXN0Rmx1c2hgIHJlcXVlc3RzIHRoYXQgdGhlIGhpZ2ggcHJpb3JpdHkgZXZlbnQgcXVldWUgYmUgZmx1c2hlZCBhc1xuXHQvLyBzb29uIGFzIHBvc3NpYmxlLlxuXHQvLyBUaGlzIGlzIHVzZWZ1bCB0byBwcmV2ZW50IGFuIGVycm9yIHRocm93biBpbiBhIHRhc2sgZnJvbSBzdGFsbGluZyB0aGUgZXZlbnRcblx0Ly8gcXVldWUgaWYgdGhlIGV4Y2VwdGlvbiBoYW5kbGVkIGJ5IE5vZGUuanPigJlzXG5cdC8vIGBwcm9jZXNzLm9uKFwidW5jYXVnaHRFeGNlcHRpb25cIilgIG9yIGJ5IGEgZG9tYWluLlxuXHRyYXdBc2FwLnJlcXVlc3RGbHVzaCA9IHJlcXVlc3RGbHVzaDtcblxuXHQvLyBUbyByZXF1ZXN0IGEgaGlnaCBwcmlvcml0eSBldmVudCwgd2UgaW5kdWNlIGEgbXV0YXRpb24gb2JzZXJ2ZXIgYnkgdG9nZ2xpbmdcblx0Ly8gdGhlIHRleHQgb2YgYSB0ZXh0IG5vZGUgYmV0d2VlbiBcIjFcIiBhbmQgXCItMVwiLlxuXHRmdW5jdGlvbiBtYWtlUmVxdWVzdENhbGxGcm9tTXV0YXRpb25PYnNlcnZlcihjYWxsYmFjaykge1xuXHQgICAgdmFyIHRvZ2dsZSA9IDE7XG5cdCAgICB2YXIgb2JzZXJ2ZXIgPSBuZXcgQnJvd3Nlck11dGF0aW9uT2JzZXJ2ZXIoY2FsbGJhY2spO1xuXHQgICAgdmFyIG5vZGUgPSBkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShcIlwiKTtcblx0ICAgIG9ic2VydmVyLm9ic2VydmUobm9kZSwge2NoYXJhY3RlckRhdGE6IHRydWV9KTtcblx0ICAgIHJldHVybiBmdW5jdGlvbiByZXF1ZXN0Q2FsbCgpIHtcblx0ICAgICAgICB0b2dnbGUgPSAtdG9nZ2xlO1xuXHQgICAgICAgIG5vZGUuZGF0YSA9IHRvZ2dsZTtcblx0ICAgIH07XG5cdH1cblxuXHQvLyBUaGUgbWVzc2FnZSBjaGFubmVsIHRlY2huaXF1ZSB3YXMgZGlzY292ZXJlZCBieSBNYWx0ZSBVYmwgYW5kIHdhcyB0aGVcblx0Ly8gb3JpZ2luYWwgZm91bmRhdGlvbiBmb3IgdGhpcyBsaWJyYXJ5LlxuXHQvLyBodHRwOi8vd3d3Lm5vbmJsb2NraW5nLmlvLzIwMTEvMDYvd2luZG93bmV4dHRpY2suaHRtbFxuXG5cdC8vIFNhZmFyaSA2LjAuNSAoYXQgbGVhc3QpIGludGVybWl0dGVudGx5IGZhaWxzIHRvIGNyZWF0ZSBtZXNzYWdlIHBvcnRzIG9uIGFcblx0Ly8gcGFnZSdzIGZpcnN0IGxvYWQuIFRoYW5rZnVsbHksIHRoaXMgdmVyc2lvbiBvZiBTYWZhcmkgc3VwcG9ydHNcblx0Ly8gTXV0YXRpb25PYnNlcnZlcnMsIHNvIHdlIGRvbid0IG5lZWQgdG8gZmFsbCBiYWNrIGluIHRoYXQgY2FzZS5cblxuXHQvLyBmdW5jdGlvbiBtYWtlUmVxdWVzdENhbGxGcm9tTWVzc2FnZUNoYW5uZWwoY2FsbGJhY2spIHtcblx0Ly8gICAgIHZhciBjaGFubmVsID0gbmV3IE1lc3NhZ2VDaGFubmVsKCk7XG5cdC8vICAgICBjaGFubmVsLnBvcnQxLm9ubWVzc2FnZSA9IGNhbGxiYWNrO1xuXHQvLyAgICAgcmV0dXJuIGZ1bmN0aW9uIHJlcXVlc3RDYWxsKCkge1xuXHQvLyAgICAgICAgIGNoYW5uZWwucG9ydDIucG9zdE1lc3NhZ2UoMCk7XG5cdC8vICAgICB9O1xuXHQvLyB9XG5cblx0Ly8gRm9yIHJlYXNvbnMgZXhwbGFpbmVkIGFib3ZlLCB3ZSBhcmUgYWxzbyB1bmFibGUgdG8gdXNlIGBzZXRJbW1lZGlhdGVgXG5cdC8vIHVuZGVyIGFueSBjaXJjdW1zdGFuY2VzLlxuXHQvLyBFdmVuIGlmIHdlIHdlcmUsIHRoZXJlIGlzIGFub3RoZXIgYnVnIGluIEludGVybmV0IEV4cGxvcmVyIDEwLlxuXHQvLyBJdCBpcyBub3Qgc3VmZmljaWVudCB0byBhc3NpZ24gYHNldEltbWVkaWF0ZWAgdG8gYHJlcXVlc3RGbHVzaGAgYmVjYXVzZVxuXHQvLyBgc2V0SW1tZWRpYXRlYCBtdXN0IGJlIGNhbGxlZCAqYnkgbmFtZSogYW5kIHRoZXJlZm9yZSBtdXN0IGJlIHdyYXBwZWQgaW4gYVxuXHQvLyBjbG9zdXJlLlxuXHQvLyBOZXZlciBmb3JnZXQuXG5cblx0Ly8gZnVuY3Rpb24gbWFrZVJlcXVlc3RDYWxsRnJvbVNldEltbWVkaWF0ZShjYWxsYmFjaykge1xuXHQvLyAgICAgcmV0dXJuIGZ1bmN0aW9uIHJlcXVlc3RDYWxsKCkge1xuXHQvLyAgICAgICAgIHNldEltbWVkaWF0ZShjYWxsYmFjayk7XG5cdC8vICAgICB9O1xuXHQvLyB9XG5cblx0Ly8gU2FmYXJpIDYuMCBoYXMgYSBwcm9ibGVtIHdoZXJlIHRpbWVycyB3aWxsIGdldCBsb3N0IHdoaWxlIHRoZSB1c2VyIGlzXG5cdC8vIHNjcm9sbGluZy4gVGhpcyBwcm9ibGVtIGRvZXMgbm90IGltcGFjdCBBU0FQIGJlY2F1c2UgU2FmYXJpIDYuMCBzdXBwb3J0c1xuXHQvLyBtdXRhdGlvbiBvYnNlcnZlcnMsIHNvIHRoYXQgaW1wbGVtZW50YXRpb24gaXMgdXNlZCBpbnN0ZWFkLlxuXHQvLyBIb3dldmVyLCBpZiB3ZSBldmVyIGVsZWN0IHRvIHVzZSB0aW1lcnMgaW4gU2FmYXJpLCB0aGUgcHJldmFsZW50IHdvcmstYXJvdW5kXG5cdC8vIGlzIHRvIGFkZCBhIHNjcm9sbCBldmVudCBsaXN0ZW5lciB0aGF0IGNhbGxzIGZvciBhIGZsdXNoLlxuXG5cdC8vIGBzZXRUaW1lb3V0YCBkb2VzIG5vdCBjYWxsIHRoZSBwYXNzZWQgY2FsbGJhY2sgaWYgdGhlIGRlbGF5IGlzIGxlc3MgdGhhblxuXHQvLyBhcHByb3hpbWF0ZWx5IDcgaW4gd2ViIHdvcmtlcnMgaW4gRmlyZWZveCA4IHRocm91Z2ggMTgsIGFuZCBzb21ldGltZXMgbm90XG5cdC8vIGV2ZW4gdGhlbi5cblxuXHRmdW5jdGlvbiBtYWtlUmVxdWVzdENhbGxGcm9tVGltZXIoY2FsbGJhY2spIHtcblx0ICAgIHJldHVybiBmdW5jdGlvbiByZXF1ZXN0Q2FsbCgpIHtcblx0ICAgICAgICAvLyBXZSBkaXNwYXRjaCBhIHRpbWVvdXQgd2l0aCBhIHNwZWNpZmllZCBkZWxheSBvZiAwIGZvciBlbmdpbmVzIHRoYXRcblx0ICAgICAgICAvLyBjYW4gcmVsaWFibHkgYWNjb21tb2RhdGUgdGhhdCByZXF1ZXN0LiBUaGlzIHdpbGwgdXN1YWxseSBiZSBzbmFwcGVkXG5cdCAgICAgICAgLy8gdG8gYSA0IG1pbGlzZWNvbmQgZGVsYXksIGJ1dCBvbmNlIHdlJ3JlIGZsdXNoaW5nLCB0aGVyZSdzIG5vIGRlbGF5XG5cdCAgICAgICAgLy8gYmV0d2VlbiBldmVudHMuXG5cdCAgICAgICAgdmFyIHRpbWVvdXRIYW5kbGUgPSBzZXRUaW1lb3V0KGhhbmRsZVRpbWVyLCAwKTtcblx0ICAgICAgICAvLyBIb3dldmVyLCBzaW5jZSB0aGlzIHRpbWVyIGdldHMgZnJlcXVlbnRseSBkcm9wcGVkIGluIEZpcmVmb3hcblx0ICAgICAgICAvLyB3b3JrZXJzLCB3ZSBlbmxpc3QgYW4gaW50ZXJ2YWwgaGFuZGxlIHRoYXQgd2lsbCB0cnkgdG8gZmlyZVxuXHQgICAgICAgIC8vIGFuIGV2ZW50IDIwIHRpbWVzIHBlciBzZWNvbmQgdW50aWwgaXQgc3VjY2VlZHMuXG5cdCAgICAgICAgdmFyIGludGVydmFsSGFuZGxlID0gc2V0SW50ZXJ2YWwoaGFuZGxlVGltZXIsIDUwKTtcblxuXHQgICAgICAgIGZ1bmN0aW9uIGhhbmRsZVRpbWVyKCkge1xuXHQgICAgICAgICAgICAvLyBXaGljaGV2ZXIgdGltZXIgc3VjY2VlZHMgd2lsbCBjYW5jZWwgYm90aCB0aW1lcnMgYW5kXG5cdCAgICAgICAgICAgIC8vIGV4ZWN1dGUgdGhlIGNhbGxiYWNrLlxuXHQgICAgICAgICAgICBjbGVhclRpbWVvdXQodGltZW91dEhhbmRsZSk7XG5cdCAgICAgICAgICAgIGNsZWFySW50ZXJ2YWwoaW50ZXJ2YWxIYW5kbGUpO1xuXHQgICAgICAgICAgICBjYWxsYmFjaygpO1xuXHQgICAgICAgIH1cblx0ICAgIH07XG5cdH1cblxuXHQvLyBUaGlzIGlzIGZvciBgYXNhcC5qc2Agb25seS5cblx0Ly8gSXRzIG5hbWUgd2lsbCBiZSBwZXJpb2RpY2FsbHkgcmFuZG9taXplZCB0byBicmVhayBhbnkgY29kZSB0aGF0IGRlcGVuZHMgb25cblx0Ly8gaXRzIGV4aXN0ZW5jZS5cblx0cmF3QXNhcC5tYWtlUmVxdWVzdENhbGxGcm9tVGltZXIgPSBtYWtlUmVxdWVzdENhbGxGcm9tVGltZXI7XG5cblx0Ly8gQVNBUCB3YXMgb3JpZ2luYWxseSBhIG5leHRUaWNrIHNoaW0gaW5jbHVkZWQgaW4gUS4gVGhpcyB3YXMgZmFjdG9yZWQgb3V0XG5cdC8vIGludG8gdGhpcyBBU0FQIHBhY2thZ2UuIEl0IHdhcyBsYXRlciBhZGFwdGVkIHRvIFJTVlAgd2hpY2ggbWFkZSBmdXJ0aGVyXG5cdC8vIGFtZW5kbWVudHMuIFRoZXNlIGRlY2lzaW9ucywgcGFydGljdWxhcmx5IHRvIG1hcmdpbmFsaXplIE1lc3NhZ2VDaGFubmVsIGFuZFxuXHQvLyB0byBjYXB0dXJlIHRoZSBNdXRhdGlvbk9ic2VydmVyIGltcGxlbWVudGF0aW9uIGluIGEgY2xvc3VyZSwgd2VyZSBpbnRlZ3JhdGVkXG5cdC8vIGJhY2sgaW50byBBU0FQIHByb3Blci5cblx0Ly8gaHR0cHM6Ly9naXRodWIuY29tL3RpbGRlaW8vcnN2cC5qcy9ibG9iL2NkZGY3MjMyNTQ2YTljZjg1ODUyNGI3NWNkZTZmOWVkZjcyNjIwYTcvbGliL3JzdnAvYXNhcC5qc1xuXG5cdC8qIFdFQlBBQ0sgVkFSIElOSkVDVElPTiAqL30uY2FsbChleHBvcnRzLCAoZnVuY3Rpb24oKSB7IHJldHVybiB0aGlzOyB9KCkpKSlcblxuLyoqKi8gfSxcbi8qIDYgKi9cbi8qKiovIGZ1bmN0aW9uKG1vZHVsZSwgZXhwb3J0cykge1xuXG5cdCd1c2Ugc3RyaWN0JztcblxuXHQvLyBBIHNpbXBsZSBjbGFzcyBzeXN0ZW0sIG1vcmUgZG9jdW1lbnRhdGlvbiB0byBjb21lXG5cblx0ZnVuY3Rpb24gZXh0ZW5kKGNscywgbmFtZSwgcHJvcHMpIHtcblx0ICAgIC8vIFRoaXMgZG9lcyB0aGF0IHNhbWUgdGhpbmcgYXMgT2JqZWN0LmNyZWF0ZSwgYnV0IHdpdGggc3VwcG9ydCBmb3IgSUU4XG5cdCAgICB2YXIgRiA9IGZ1bmN0aW9uKCkge307XG5cdCAgICBGLnByb3RvdHlwZSA9IGNscy5wcm90b3R5cGU7XG5cdCAgICB2YXIgcHJvdG90eXBlID0gbmV3IEYoKTtcblxuXHQgICAgLy8ganNoaW50IHVuZGVmOiBmYWxzZVxuXHQgICAgdmFyIGZuVGVzdCA9IC94eXovLnRlc3QoZnVuY3Rpb24oKXsgeHl6OyB9KSA/IC9cXGJwYXJlbnRcXGIvIDogLy4qLztcblx0ICAgIHByb3BzID0gcHJvcHMgfHwge307XG5cblx0ICAgIGZvcih2YXIgayBpbiBwcm9wcykge1xuXHQgICAgICAgIHZhciBzcmMgPSBwcm9wc1trXTtcblx0ICAgICAgICB2YXIgcGFyZW50ID0gcHJvdG90eXBlW2tdO1xuXG5cdCAgICAgICAgaWYodHlwZW9mIHBhcmVudCA9PT0gJ2Z1bmN0aW9uJyAmJlxuXHQgICAgICAgICAgIHR5cGVvZiBzcmMgPT09ICdmdW5jdGlvbicgJiZcblx0ICAgICAgICAgICBmblRlc3QudGVzdChzcmMpKSB7XG5cdCAgICAgICAgICAgIC8qanNoaW50IC1XMDgzICovXG5cdCAgICAgICAgICAgIHByb3RvdHlwZVtrXSA9IChmdW5jdGlvbiAoc3JjLCBwYXJlbnQpIHtcblx0ICAgICAgICAgICAgICAgIHJldHVybiBmdW5jdGlvbigpIHtcblx0ICAgICAgICAgICAgICAgICAgICAvLyBTYXZlIHRoZSBjdXJyZW50IHBhcmVudCBtZXRob2Rcblx0ICAgICAgICAgICAgICAgICAgICB2YXIgdG1wID0gdGhpcy5wYXJlbnQ7XG5cblx0ICAgICAgICAgICAgICAgICAgICAvLyBTZXQgcGFyZW50IHRvIHRoZSBwcmV2aW91cyBtZXRob2QsIGNhbGwsIGFuZCByZXN0b3JlXG5cdCAgICAgICAgICAgICAgICAgICAgdGhpcy5wYXJlbnQgPSBwYXJlbnQ7XG5cdCAgICAgICAgICAgICAgICAgICAgdmFyIHJlcyA9IHNyYy5hcHBseSh0aGlzLCBhcmd1bWVudHMpO1xuXHQgICAgICAgICAgICAgICAgICAgIHRoaXMucGFyZW50ID0gdG1wO1xuXG5cdCAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHJlcztcblx0ICAgICAgICAgICAgICAgIH07XG5cdCAgICAgICAgICAgIH0pKHNyYywgcGFyZW50KTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIHByb3RvdHlwZVtrXSA9IHNyYztcblx0ICAgICAgICB9XG5cdCAgICB9XG5cblx0ICAgIHByb3RvdHlwZS50eXBlbmFtZSA9IG5hbWU7XG5cblx0ICAgIHZhciBuZXdfY2xzID0gZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgaWYocHJvdG90eXBlLmluaXQpIHtcblx0ICAgICAgICAgICAgcHJvdG90eXBlLmluaXQuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcblx0ICAgICAgICB9XG5cdCAgICB9O1xuXG5cdCAgICBuZXdfY2xzLnByb3RvdHlwZSA9IHByb3RvdHlwZTtcblx0ICAgIG5ld19jbHMucHJvdG90eXBlLmNvbnN0cnVjdG9yID0gbmV3X2NscztcblxuXHQgICAgbmV3X2Nscy5leHRlbmQgPSBmdW5jdGlvbihuYW1lLCBwcm9wcykge1xuXHQgICAgICAgIGlmKHR5cGVvZiBuYW1lID09PSAnb2JqZWN0Jykge1xuXHQgICAgICAgICAgICBwcm9wcyA9IG5hbWU7XG5cdCAgICAgICAgICAgIG5hbWUgPSAnYW5vbnltb3VzJztcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIGV4dGVuZChuZXdfY2xzLCBuYW1lLCBwcm9wcyk7XG5cdCAgICB9O1xuXG5cdCAgICByZXR1cm4gbmV3X2Nscztcblx0fVxuXG5cdG1vZHVsZS5leHBvcnRzID0gZXh0ZW5kKE9iamVjdCwgJ09iamVjdCcsIHt9KTtcblxuXG4vKioqLyB9LFxuLyogNyAqL1xuLyoqKi8gZnVuY3Rpb24obW9kdWxlLCBleHBvcnRzLCBfX3dlYnBhY2tfcmVxdWlyZV9fKSB7XG5cblx0J3VzZSBzdHJpY3QnO1xuXG5cdHZhciBsaWIgPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDEpO1xuXHR2YXIgciA9IF9fd2VicGFja19yZXF1aXJlX18oOCk7XG5cblx0ZnVuY3Rpb24gbm9ybWFsaXplKHZhbHVlLCBkZWZhdWx0VmFsdWUpIHtcblx0ICAgIGlmKHZhbHVlID09PSBudWxsIHx8IHZhbHVlID09PSB1bmRlZmluZWQgfHwgdmFsdWUgPT09IGZhbHNlKSB7XG5cdCAgICAgICAgcmV0dXJuIGRlZmF1bHRWYWx1ZTtcblx0ICAgIH1cblx0ICAgIHJldHVybiB2YWx1ZTtcblx0fVxuXG5cdHZhciBmaWx0ZXJzID0ge1xuXHQgICAgYWJzOiBmdW5jdGlvbihuKSB7XG5cdCAgICAgICAgcmV0dXJuIE1hdGguYWJzKG4pO1xuXHQgICAgfSxcblxuXHQgICAgYmF0Y2g6IGZ1bmN0aW9uKGFyciwgbGluZWNvdW50LCBmaWxsX3dpdGgpIHtcblx0ICAgICAgICB2YXIgaTtcblx0ICAgICAgICB2YXIgcmVzID0gW107XG5cdCAgICAgICAgdmFyIHRtcCA9IFtdO1xuXG5cdCAgICAgICAgZm9yKGkgPSAwOyBpIDwgYXJyLmxlbmd0aDsgaSsrKSB7XG5cdCAgICAgICAgICAgIGlmKGkgJSBsaW5lY291bnQgPT09IDAgJiYgdG1wLmxlbmd0aCkge1xuXHQgICAgICAgICAgICAgICAgcmVzLnB1c2godG1wKTtcblx0ICAgICAgICAgICAgICAgIHRtcCA9IFtdO1xuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgdG1wLnB1c2goYXJyW2ldKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICBpZih0bXAubGVuZ3RoKSB7XG5cdCAgICAgICAgICAgIGlmKGZpbGxfd2l0aCkge1xuXHQgICAgICAgICAgICAgICAgZm9yKGkgPSB0bXAubGVuZ3RoOyBpIDwgbGluZWNvdW50OyBpKyspIHtcblx0ICAgICAgICAgICAgICAgICAgICB0bXAucHVzaChmaWxsX3dpdGgpO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgcmVzLnB1c2godG1wKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICByZXR1cm4gcmVzO1xuXHQgICAgfSxcblxuXHQgICAgY2FwaXRhbGl6ZTogZnVuY3Rpb24oc3RyKSB7XG5cdCAgICAgICAgc3RyID0gbm9ybWFsaXplKHN0ciwgJycpO1xuXHQgICAgICAgIHZhciByZXQgPSBzdHIudG9Mb3dlckNhc2UoKTtcblx0ICAgICAgICByZXR1cm4gci5jb3B5U2FmZW5lc3Moc3RyLCByZXQuY2hhckF0KDApLnRvVXBwZXJDYXNlKCkgKyByZXQuc2xpY2UoMSkpO1xuXHQgICAgfSxcblxuXHQgICAgY2VudGVyOiBmdW5jdGlvbihzdHIsIHdpZHRoKSB7XG5cdCAgICAgICAgc3RyID0gbm9ybWFsaXplKHN0ciwgJycpO1xuXHQgICAgICAgIHdpZHRoID0gd2lkdGggfHwgODA7XG5cblx0ICAgICAgICBpZihzdHIubGVuZ3RoID49IHdpZHRoKSB7XG5cdCAgICAgICAgICAgIHJldHVybiBzdHI7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgdmFyIHNwYWNlcyA9IHdpZHRoIC0gc3RyLmxlbmd0aDtcblx0ICAgICAgICB2YXIgcHJlID0gbGliLnJlcGVhdCgnICcsIHNwYWNlcy8yIC0gc3BhY2VzICUgMik7XG5cdCAgICAgICAgdmFyIHBvc3QgPSBsaWIucmVwZWF0KCcgJywgc3BhY2VzLzIpO1xuXHQgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyhzdHIsIHByZSArIHN0ciArIHBvc3QpO1xuXHQgICAgfSxcblxuXHQgICAgJ2RlZmF1bHQnOiBmdW5jdGlvbih2YWwsIGRlZiwgYm9vbCkge1xuXHQgICAgICAgIGlmKGJvb2wpIHtcblx0ICAgICAgICAgICAgcmV0dXJuIHZhbCA/IHZhbCA6IGRlZjtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIHJldHVybiAodmFsICE9PSB1bmRlZmluZWQpID8gdmFsIDogZGVmO1xuXHQgICAgICAgIH1cblx0ICAgIH0sXG5cblx0ICAgIGRpY3Rzb3J0OiBmdW5jdGlvbih2YWwsIGNhc2Vfc2Vuc2l0aXZlLCBieSkge1xuXHQgICAgICAgIGlmICghbGliLmlzT2JqZWN0KHZhbCkpIHtcblx0ICAgICAgICAgICAgdGhyb3cgbmV3IGxpYi5UZW1wbGF0ZUVycm9yKCdkaWN0c29ydCBmaWx0ZXI6IHZhbCBtdXN0IGJlIGFuIG9iamVjdCcpO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHZhciBhcnJheSA9IFtdO1xuXHQgICAgICAgIGZvciAodmFyIGsgaW4gdmFsKSB7XG5cdCAgICAgICAgICAgIC8vIGRlbGliZXJhdGVseSBpbmNsdWRlIHByb3BlcnRpZXMgZnJvbSB0aGUgb2JqZWN0J3MgcHJvdG90eXBlXG5cdCAgICAgICAgICAgIGFycmF5LnB1c2goW2ssdmFsW2tdXSk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgdmFyIHNpO1xuXHQgICAgICAgIGlmIChieSA9PT0gdW5kZWZpbmVkIHx8IGJ5ID09PSAna2V5Jykge1xuXHQgICAgICAgICAgICBzaSA9IDA7XG5cdCAgICAgICAgfSBlbHNlIGlmIChieSA9PT0gJ3ZhbHVlJykge1xuXHQgICAgICAgICAgICBzaSA9IDE7XG5cdCAgICAgICAgfSBlbHNlIHtcblx0ICAgICAgICAgICAgdGhyb3cgbmV3IGxpYi5UZW1wbGF0ZUVycm9yKFxuXHQgICAgICAgICAgICAgICAgJ2RpY3Rzb3J0IGZpbHRlcjogWW91IGNhbiBvbmx5IHNvcnQgYnkgZWl0aGVyIGtleSBvciB2YWx1ZScpO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGFycmF5LnNvcnQoZnVuY3Rpb24odDEsIHQyKSB7XG5cdCAgICAgICAgICAgIHZhciBhID0gdDFbc2ldO1xuXHQgICAgICAgICAgICB2YXIgYiA9IHQyW3NpXTtcblxuXHQgICAgICAgICAgICBpZiAoIWNhc2Vfc2Vuc2l0aXZlKSB7XG5cdCAgICAgICAgICAgICAgICBpZiAobGliLmlzU3RyaW5nKGEpKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgYSA9IGEudG9VcHBlckNhc2UoKTtcblx0ICAgICAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgICAgIGlmIChsaWIuaXNTdHJpbmcoYikpIHtcblx0ICAgICAgICAgICAgICAgICAgICBiID0gYi50b1VwcGVyQ2FzZSgpO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgcmV0dXJuIGEgPiBiID8gMSA6IChhID09PSBiID8gMCA6IC0xKTtcblx0ICAgICAgICB9KTtcblxuXHQgICAgICAgIHJldHVybiBhcnJheTtcblx0ICAgIH0sXG5cblx0ICAgIGR1bXA6IGZ1bmN0aW9uKG9iaikge1xuXHQgICAgICAgIHJldHVybiBKU09OLnN0cmluZ2lmeShvYmopO1xuXHQgICAgfSxcblxuXHQgICAgZXNjYXBlOiBmdW5jdGlvbihzdHIpIHtcblx0ICAgICAgICBpZih0eXBlb2Ygc3RyID09PSAnc3RyaW5nJykge1xuXHQgICAgICAgICAgICByZXR1cm4gci5tYXJrU2FmZShsaWIuZXNjYXBlKHN0cikpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICByZXR1cm4gc3RyO1xuXHQgICAgfSxcblxuXHQgICAgc2FmZTogZnVuY3Rpb24oc3RyKSB7XG5cdCAgICAgICAgcmV0dXJuIHIubWFya1NhZmUoc3RyKTtcblx0ICAgIH0sXG5cblx0ICAgIGZpcnN0OiBmdW5jdGlvbihhcnIpIHtcblx0ICAgICAgICByZXR1cm4gYXJyWzBdO1xuXHQgICAgfSxcblxuXHQgICAgZ3JvdXBieTogZnVuY3Rpb24oYXJyLCBhdHRyKSB7XG5cdCAgICAgICAgcmV0dXJuIGxpYi5ncm91cEJ5KGFyciwgYXR0cik7XG5cdCAgICB9LFxuXG5cdCAgICBpbmRlbnQ6IGZ1bmN0aW9uKHN0ciwgd2lkdGgsIGluZGVudGZpcnN0KSB7XG5cdCAgICAgICAgc3RyID0gbm9ybWFsaXplKHN0ciwgJycpO1xuXG5cdCAgICAgICAgaWYgKHN0ciA9PT0gJycpIHJldHVybiAnJztcblxuXHQgICAgICAgIHdpZHRoID0gd2lkdGggfHwgNDtcblx0ICAgICAgICB2YXIgcmVzID0gJyc7XG5cdCAgICAgICAgdmFyIGxpbmVzID0gc3RyLnNwbGl0KCdcXG4nKTtcblx0ICAgICAgICB2YXIgc3AgPSBsaWIucmVwZWF0KCcgJywgd2lkdGgpO1xuXG5cdCAgICAgICAgZm9yKHZhciBpPTA7IGk8bGluZXMubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICAgICAgaWYoaSA9PT0gMCAmJiAhaW5kZW50Zmlyc3QpIHtcblx0ICAgICAgICAgICAgICAgIHJlcyArPSBsaW5lc1tpXSArICdcXG4nO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIGVsc2Uge1xuXHQgICAgICAgICAgICAgICAgcmVzICs9IHNwICsgbGluZXNbaV0gKyAnXFxuJztcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyhzdHIsIHJlcyk7XG5cdCAgICB9LFxuXG5cdCAgICBqb2luOiBmdW5jdGlvbihhcnIsIGRlbCwgYXR0cikge1xuXHQgICAgICAgIGRlbCA9IGRlbCB8fCAnJztcblxuXHQgICAgICAgIGlmKGF0dHIpIHtcblx0ICAgICAgICAgICAgYXJyID0gbGliLm1hcChhcnIsIGZ1bmN0aW9uKHYpIHtcblx0ICAgICAgICAgICAgICAgIHJldHVybiB2W2F0dHJdO1xuXHQgICAgICAgICAgICB9KTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICByZXR1cm4gYXJyLmpvaW4oZGVsKTtcblx0ICAgIH0sXG5cblx0ICAgIGxhc3Q6IGZ1bmN0aW9uKGFycikge1xuXHQgICAgICAgIHJldHVybiBhcnJbYXJyLmxlbmd0aC0xXTtcblx0ICAgIH0sXG5cblx0ICAgIGxlbmd0aDogZnVuY3Rpb24odmFsKSB7XG5cdCAgICAgICAgdmFyIHZhbHVlID0gbm9ybWFsaXplKHZhbCwgJycpO1xuXG5cdCAgICAgICAgaWYodmFsdWUgIT09IHVuZGVmaW5lZCkge1xuXHQgICAgICAgICAgICBpZihcblx0ICAgICAgICAgICAgICAgICh0eXBlb2YgTWFwID09PSAnZnVuY3Rpb24nICYmIHZhbHVlIGluc3RhbmNlb2YgTWFwKSB8fFxuXHQgICAgICAgICAgICAgICAgKHR5cGVvZiBTZXQgPT09ICdmdW5jdGlvbicgJiYgdmFsdWUgaW5zdGFuY2VvZiBTZXQpXG5cdCAgICAgICAgICAgICkge1xuXHQgICAgICAgICAgICAgICAgLy8gRUNNQVNjcmlwdCAyMDE1IE1hcHMgYW5kIFNldHNcblx0ICAgICAgICAgICAgICAgIHJldHVybiB2YWx1ZS5zaXplO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIHJldHVybiB2YWx1ZS5sZW5ndGg7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIHJldHVybiAwO1xuXHQgICAgfSxcblxuXHQgICAgbGlzdDogZnVuY3Rpb24odmFsKSB7XG5cdCAgICAgICAgaWYobGliLmlzU3RyaW5nKHZhbCkpIHtcblx0ICAgICAgICAgICAgcmV0dXJuIHZhbC5zcGxpdCgnJyk7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIGVsc2UgaWYobGliLmlzT2JqZWN0KHZhbCkpIHtcblx0ICAgICAgICAgICAgdmFyIGtleXMgPSBbXTtcblxuXHQgICAgICAgICAgICBpZihPYmplY3Qua2V5cykge1xuXHQgICAgICAgICAgICAgICAga2V5cyA9IE9iamVjdC5rZXlzKHZhbCk7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICBmb3IodmFyIGsgaW4gdmFsKSB7XG5cdCAgICAgICAgICAgICAgICAgICAga2V5cy5wdXNoKGspO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgcmV0dXJuIGxpYi5tYXAoa2V5cywgZnVuY3Rpb24oaykge1xuXHQgICAgICAgICAgICAgICAgcmV0dXJuIHsga2V5OiBrLFxuXHQgICAgICAgICAgICAgICAgICAgICAgICAgdmFsdWU6IHZhbFtrXSB9O1xuXHQgICAgICAgICAgICB9KTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSBpZihsaWIuaXNBcnJheSh2YWwpKSB7XG5cdCAgICAgICAgICByZXR1cm4gdmFsO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgdGhyb3cgbmV3IGxpYi5UZW1wbGF0ZUVycm9yKCdsaXN0IGZpbHRlcjogdHlwZSBub3QgaXRlcmFibGUnKTtcblx0ICAgICAgICB9XG5cdCAgICB9LFxuXG5cdCAgICBsb3dlcjogZnVuY3Rpb24oc3RyKSB7XG5cdCAgICAgICAgc3RyID0gbm9ybWFsaXplKHN0ciwgJycpO1xuXHQgICAgICAgIHJldHVybiBzdHIudG9Mb3dlckNhc2UoKTtcblx0ICAgIH0sXG5cblx0ICAgIHJhbmRvbTogZnVuY3Rpb24oYXJyKSB7XG5cdCAgICAgICAgcmV0dXJuIGFycltNYXRoLmZsb29yKE1hdGgucmFuZG9tKCkgKiBhcnIubGVuZ3RoKV07XG5cdCAgICB9LFxuXG5cdCAgICByZWplY3RhdHRyOiBmdW5jdGlvbihhcnIsIGF0dHIpIHtcblx0ICAgICAgcmV0dXJuIGFyci5maWx0ZXIoZnVuY3Rpb24gKGl0ZW0pIHtcblx0ICAgICAgICByZXR1cm4gIWl0ZW1bYXR0cl07XG5cdCAgICAgIH0pO1xuXHQgICAgfSxcblxuXHQgICAgc2VsZWN0YXR0cjogZnVuY3Rpb24oYXJyLCBhdHRyKSB7XG5cdCAgICAgIHJldHVybiBhcnIuZmlsdGVyKGZ1bmN0aW9uIChpdGVtKSB7XG5cdCAgICAgICAgcmV0dXJuICEhaXRlbVthdHRyXTtcblx0ICAgICAgfSk7XG5cdCAgICB9LFxuXG5cdCAgICByZXBsYWNlOiBmdW5jdGlvbihzdHIsIG9sZCwgbmV3XywgbWF4Q291bnQpIHtcblx0ICAgICAgICB2YXIgb3JpZ2luYWxTdHIgPSBzdHI7XG5cblx0ICAgICAgICBpZiAob2xkIGluc3RhbmNlb2YgUmVnRXhwKSB7XG5cdCAgICAgICAgICAgIHJldHVybiBzdHIucmVwbGFjZShvbGQsIG5ld18pO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIGlmKHR5cGVvZiBtYXhDb3VudCA9PT0gJ3VuZGVmaW5lZCcpe1xuXHQgICAgICAgICAgICBtYXhDb3VudCA9IC0xO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHZhciByZXMgPSAnJzsgIC8vIE91dHB1dFxuXG5cdCAgICAgICAgLy8gQ2FzdCBOdW1iZXJzIGluIHRoZSBzZWFyY2ggdGVybSB0byBzdHJpbmdcblx0ICAgICAgICBpZih0eXBlb2Ygb2xkID09PSAnbnVtYmVyJyl7XG5cdCAgICAgICAgICAgIG9sZCA9IG9sZCArICcnO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIGlmKHR5cGVvZiBvbGQgIT09ICdzdHJpbmcnKSB7XG5cdCAgICAgICAgICAgIC8vIElmIGl0IGlzIHNvbWV0aGluZyBvdGhlciB0aGFuIG51bWJlciBvciBzdHJpbmcsXG5cdCAgICAgICAgICAgIC8vIHJldHVybiB0aGUgb3JpZ2luYWwgc3RyaW5nXG5cdCAgICAgICAgICAgIHJldHVybiBzdHI7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgLy8gQ2FzdCBudW1iZXJzIGluIHRoZSByZXBsYWNlbWVudCB0byBzdHJpbmdcblx0ICAgICAgICBpZih0eXBlb2Ygc3RyID09PSAnbnVtYmVyJyl7XG5cdCAgICAgICAgICAgIHN0ciA9IHN0ciArICcnO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIC8vIElmIGJ5IG5vdywgd2UgZG9uJ3QgaGF2ZSBhIHN0cmluZywgdGhyb3cgaXQgYmFja1xuXHQgICAgICAgIGlmKHR5cGVvZiBzdHIgIT09ICdzdHJpbmcnICYmICEoc3RyIGluc3RhbmNlb2Ygci5TYWZlU3RyaW5nKSl7XG5cdCAgICAgICAgICAgIHJldHVybiBzdHI7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgLy8gU2hvcnRDaXJjdWl0c1xuXHQgICAgICAgIGlmKG9sZCA9PT0gJycpe1xuXHQgICAgICAgICAgICAvLyBNaW1pYyB0aGUgcHl0aG9uIGJlaGF2aW91cjogZW1wdHkgc3RyaW5nIGlzIHJlcGxhY2VkXG5cdCAgICAgICAgICAgIC8vIGJ5IHJlcGxhY2VtZW50IGUuZy4gXCJhYmNcInxyZXBsYWNlKFwiXCIsIFwiLlwiKSAtPiAuYS5iLmMuXG5cdCAgICAgICAgICAgIHJlcyA9IG5ld18gKyBzdHIuc3BsaXQoJycpLmpvaW4obmV3XykgKyBuZXdfO1xuXHQgICAgICAgICAgICByZXR1cm4gci5jb3B5U2FmZW5lc3Moc3RyLCByZXMpO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHZhciBuZXh0SW5kZXggPSBzdHIuaW5kZXhPZihvbGQpO1xuXHQgICAgICAgIC8vIGlmICMgb2YgcmVwbGFjZW1lbnRzIHRvIHBlcmZvcm0gaXMgMCwgb3IgdGhlIHN0cmluZyB0byBkb2VzXG5cdCAgICAgICAgLy8gbm90IGNvbnRhaW4gdGhlIG9sZCB2YWx1ZSwgcmV0dXJuIHRoZSBzdHJpbmdcblx0ICAgICAgICBpZihtYXhDb3VudCA9PT0gMCB8fCBuZXh0SW5kZXggPT09IC0xKXtcblx0ICAgICAgICAgICAgcmV0dXJuIHN0cjtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICB2YXIgcG9zID0gMDtcblx0ICAgICAgICB2YXIgY291bnQgPSAwOyAvLyAjIG9mIHJlcGxhY2VtZW50cyBtYWRlXG5cblx0ICAgICAgICB3aGlsZShuZXh0SW5kZXggID4gLTEgJiYgKG1heENvdW50ID09PSAtMSB8fCBjb3VudCA8IG1heENvdW50KSl7XG5cdCAgICAgICAgICAgIC8vIEdyYWIgdGhlIG5leHQgY2h1bmsgb2Ygc3JjIHN0cmluZyBhbmQgYWRkIGl0IHdpdGggdGhlXG5cdCAgICAgICAgICAgIC8vIHJlcGxhY2VtZW50LCB0byB0aGUgcmVzdWx0XG5cdCAgICAgICAgICAgIHJlcyArPSBzdHIuc3Vic3RyaW5nKHBvcywgbmV4dEluZGV4KSArIG5ld187XG5cdCAgICAgICAgICAgIC8vIEluY3JlbWVudCBvdXIgcG9pbnRlciBpbiB0aGUgc3JjIHN0cmluZ1xuXHQgICAgICAgICAgICBwb3MgPSBuZXh0SW5kZXggKyBvbGQubGVuZ3RoO1xuXHQgICAgICAgICAgICBjb3VudCsrO1xuXHQgICAgICAgICAgICAvLyBTZWUgaWYgdGhlcmUgYXJlIGFueSBtb3JlIHJlcGxhY2VtZW50cyB0byBiZSBtYWRlXG5cdCAgICAgICAgICAgIG5leHRJbmRleCA9IHN0ci5pbmRleE9mKG9sZCwgcG9zKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICAvLyBXZSd2ZSBlaXRoZXIgcmVhY2hlZCB0aGUgZW5kLCBvciBkb25lIHRoZSBtYXggIyBvZlxuXHQgICAgICAgIC8vIHJlcGxhY2VtZW50cywgdGFjayBvbiBhbnkgcmVtYWluaW5nIHN0cmluZ1xuXHQgICAgICAgIGlmKHBvcyA8IHN0ci5sZW5ndGgpIHtcblx0ICAgICAgICAgICAgcmVzICs9IHN0ci5zdWJzdHJpbmcocG9zKTtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICByZXR1cm4gci5jb3B5U2FmZW5lc3Mob3JpZ2luYWxTdHIsIHJlcyk7XG5cdCAgICB9LFxuXG5cdCAgICByZXZlcnNlOiBmdW5jdGlvbih2YWwpIHtcblx0ICAgICAgICB2YXIgYXJyO1xuXHQgICAgICAgIGlmKGxpYi5pc1N0cmluZyh2YWwpKSB7XG5cdCAgICAgICAgICAgIGFyciA9IGZpbHRlcnMubGlzdCh2YWwpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgLy8gQ29weSBpdFxuXHQgICAgICAgICAgICBhcnIgPSBsaWIubWFwKHZhbCwgZnVuY3Rpb24odikgeyByZXR1cm4gdjsgfSk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgYXJyLnJldmVyc2UoKTtcblxuXHQgICAgICAgIGlmKGxpYi5pc1N0cmluZyh2YWwpKSB7XG5cdCAgICAgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyh2YWwsIGFyci5qb2luKCcnKSk7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIHJldHVybiBhcnI7XG5cdCAgICB9LFxuXG5cdCAgICByb3VuZDogZnVuY3Rpb24odmFsLCBwcmVjaXNpb24sIG1ldGhvZCkge1xuXHQgICAgICAgIHByZWNpc2lvbiA9IHByZWNpc2lvbiB8fCAwO1xuXHQgICAgICAgIHZhciBmYWN0b3IgPSBNYXRoLnBvdygxMCwgcHJlY2lzaW9uKTtcblx0ICAgICAgICB2YXIgcm91bmRlcjtcblxuXHQgICAgICAgIGlmKG1ldGhvZCA9PT0gJ2NlaWwnKSB7XG5cdCAgICAgICAgICAgIHJvdW5kZXIgPSBNYXRoLmNlaWw7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIGVsc2UgaWYobWV0aG9kID09PSAnZmxvb3InKSB7XG5cdCAgICAgICAgICAgIHJvdW5kZXIgPSBNYXRoLmZsb29yO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgcm91bmRlciA9IE1hdGgucm91bmQ7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgcmV0dXJuIHJvdW5kZXIodmFsICogZmFjdG9yKSAvIGZhY3Rvcjtcblx0ICAgIH0sXG5cblx0ICAgIHNsaWNlOiBmdW5jdGlvbihhcnIsIHNsaWNlcywgZmlsbFdpdGgpIHtcblx0ICAgICAgICB2YXIgc2xpY2VMZW5ndGggPSBNYXRoLmZsb29yKGFyci5sZW5ndGggLyBzbGljZXMpO1xuXHQgICAgICAgIHZhciBleHRyYSA9IGFyci5sZW5ndGggJSBzbGljZXM7XG5cdCAgICAgICAgdmFyIG9mZnNldCA9IDA7XG5cdCAgICAgICAgdmFyIHJlcyA9IFtdO1xuXG5cdCAgICAgICAgZm9yKHZhciBpPTA7IGk8c2xpY2VzOyBpKyspIHtcblx0ICAgICAgICAgICAgdmFyIHN0YXJ0ID0gb2Zmc2V0ICsgaSAqIHNsaWNlTGVuZ3RoO1xuXHQgICAgICAgICAgICBpZihpIDwgZXh0cmEpIHtcblx0ICAgICAgICAgICAgICAgIG9mZnNldCsrO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIHZhciBlbmQgPSBvZmZzZXQgKyAoaSArIDEpICogc2xpY2VMZW5ndGg7XG5cblx0ICAgICAgICAgICAgdmFyIHNsaWNlID0gYXJyLnNsaWNlKHN0YXJ0LCBlbmQpO1xuXHQgICAgICAgICAgICBpZihmaWxsV2l0aCAmJiBpID49IGV4dHJhKSB7XG5cdCAgICAgICAgICAgICAgICBzbGljZS5wdXNoKGZpbGxXaXRoKTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICByZXMucHVzaChzbGljZSk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgcmV0dXJuIHJlcztcblx0ICAgIH0sXG5cblx0ICAgIHN1bTogZnVuY3Rpb24oYXJyLCBhdHRyLCBzdGFydCkge1xuXHQgICAgICAgIHZhciBzdW0gPSAwO1xuXG5cdCAgICAgICAgaWYodHlwZW9mIHN0YXJ0ID09PSAnbnVtYmVyJyl7XG5cdCAgICAgICAgICAgIHN1bSArPSBzdGFydDtcblx0ICAgICAgICB9XG5cblx0ICAgICAgICBpZihhdHRyKSB7XG5cdCAgICAgICAgICAgIGFyciA9IGxpYi5tYXAoYXJyLCBmdW5jdGlvbih2KSB7XG5cdCAgICAgICAgICAgICAgICByZXR1cm4gdlthdHRyXTtcblx0ICAgICAgICAgICAgfSk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgZm9yKHZhciBpID0gMDsgaSA8IGFyci5sZW5ndGg7IGkrKykge1xuXHQgICAgICAgICAgICBzdW0gKz0gYXJyW2ldO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIHJldHVybiBzdW07XG5cdCAgICB9LFxuXG5cdCAgICBzb3J0OiByLm1ha2VNYWNybyhbJ3ZhbHVlJywgJ3JldmVyc2UnLCAnY2FzZV9zZW5zaXRpdmUnLCAnYXR0cmlidXRlJ10sIFtdLCBmdW5jdGlvbihhcnIsIHJldmVyc2UsIGNhc2VTZW5zLCBhdHRyKSB7XG5cdCAgICAgICAgIC8vIENvcHkgaXRcblx0ICAgICAgICBhcnIgPSBsaWIubWFwKGFyciwgZnVuY3Rpb24odikgeyByZXR1cm4gdjsgfSk7XG5cblx0ICAgICAgICBhcnIuc29ydChmdW5jdGlvbihhLCBiKSB7XG5cdCAgICAgICAgICAgIHZhciB4LCB5O1xuXG5cdCAgICAgICAgICAgIGlmKGF0dHIpIHtcblx0ICAgICAgICAgICAgICAgIHggPSBhW2F0dHJdO1xuXHQgICAgICAgICAgICAgICAgeSA9IGJbYXR0cl07XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICB4ID0gYTtcblx0ICAgICAgICAgICAgICAgIHkgPSBiO1xuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgaWYoIWNhc2VTZW5zICYmIGxpYi5pc1N0cmluZyh4KSAmJiBsaWIuaXNTdHJpbmcoeSkpIHtcblx0ICAgICAgICAgICAgICAgIHggPSB4LnRvTG93ZXJDYXNlKCk7XG5cdCAgICAgICAgICAgICAgICB5ID0geS50b0xvd2VyQ2FzZSgpO1xuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgaWYoeCA8IHkpIHtcblx0ICAgICAgICAgICAgICAgIHJldHVybiByZXZlcnNlID8gMSA6IC0xO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIGVsc2UgaWYoeCA+IHkpIHtcblx0ICAgICAgICAgICAgICAgIHJldHVybiByZXZlcnNlID8gLTE6IDE7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgICAgICByZXR1cm4gMDtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgIH0pO1xuXG5cdCAgICAgICAgcmV0dXJuIGFycjtcblx0ICAgIH0pLFxuXG5cdCAgICBzdHJpbmc6IGZ1bmN0aW9uKG9iaikge1xuXHQgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyhvYmosIG9iaik7XG5cdCAgICB9LFxuXG5cdCAgICBzdHJpcHRhZ3M6IGZ1bmN0aW9uKGlucHV0LCBwcmVzZXJ2ZV9saW5lYnJlYWtzKSB7XG5cdCAgICAgICAgaW5wdXQgPSBub3JtYWxpemUoaW5wdXQsICcnKTtcblx0ICAgICAgICBwcmVzZXJ2ZV9saW5lYnJlYWtzID0gcHJlc2VydmVfbGluZWJyZWFrcyB8fCBmYWxzZTtcblx0ICAgICAgICB2YXIgdGFncyA9IC88XFwvPyhbYS16XVthLXowLTldKilcXGJbXj5dKj58PCEtLVtcXHNcXFNdKj8tLT4vZ2k7XG5cdCAgICAgICAgdmFyIHRyaW1tZWRJbnB1dCA9IGZpbHRlcnMudHJpbShpbnB1dC5yZXBsYWNlKHRhZ3MsICcnKSk7XG5cdCAgICAgICAgdmFyIHJlcyA9ICcnO1xuXHQgICAgICAgIGlmIChwcmVzZXJ2ZV9saW5lYnJlYWtzKSB7XG5cdCAgICAgICAgICAgIHJlcyA9IHRyaW1tZWRJbnB1dFxuXHQgICAgICAgICAgICAgICAgLnJlcGxhY2UoL14gK3wgKyQvZ20sICcnKSAgICAgLy8gcmVtb3ZlIGxlYWRpbmcgYW5kIHRyYWlsaW5nIHNwYWNlc1xuXHQgICAgICAgICAgICAgICAgLnJlcGxhY2UoLyArL2csICcgJykgICAgICAgICAgLy8gc3F1YXNoIGFkamFjZW50IHNwYWNlc1xuXHQgICAgICAgICAgICAgICAgLnJlcGxhY2UoLyhcXHJcXG4pL2csICdcXG4nKSAgICAgLy8gbm9ybWFsaXplIGxpbmVicmVha3MgKENSTEYgLT4gTEYpXG5cdCAgICAgICAgICAgICAgICAucmVwbGFjZSgvXFxuXFxuXFxuKy9nLCAnXFxuXFxuJyk7IC8vIHNxdWFzaCBhYm5vcm1hbCBhZGphY2VudCBsaW5lYnJlYWtzXG5cdCAgICAgICAgfSBlbHNlIHtcblx0ICAgICAgICAgICAgcmVzID0gdHJpbW1lZElucHV0LnJlcGxhY2UoL1xccysvZ2ksICcgJyk7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyhpbnB1dCwgcmVzKTtcblx0ICAgIH0sXG5cblx0ICAgIHRpdGxlOiBmdW5jdGlvbihzdHIpIHtcblx0ICAgICAgICBzdHIgPSBub3JtYWxpemUoc3RyLCAnJyk7XG5cdCAgICAgICAgdmFyIHdvcmRzID0gc3RyLnNwbGl0KCcgJyk7XG5cdCAgICAgICAgZm9yKHZhciBpID0gMDsgaSA8IHdvcmRzLmxlbmd0aDsgaSsrKSB7XG5cdCAgICAgICAgICAgIHdvcmRzW2ldID0gZmlsdGVycy5jYXBpdGFsaXplKHdvcmRzW2ldKTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIHIuY29weVNhZmVuZXNzKHN0ciwgd29yZHMuam9pbignICcpKTtcblx0ICAgIH0sXG5cblx0ICAgIHRyaW06IGZ1bmN0aW9uKHN0cikge1xuXHQgICAgICAgIHJldHVybiByLmNvcHlTYWZlbmVzcyhzdHIsIHN0ci5yZXBsYWNlKC9eXFxzKnxcXHMqJC9nLCAnJykpO1xuXHQgICAgfSxcblxuXHQgICAgdHJ1bmNhdGU6IGZ1bmN0aW9uKGlucHV0LCBsZW5ndGgsIGtpbGx3b3JkcywgZW5kKSB7XG5cdCAgICAgICAgdmFyIG9yaWcgPSBpbnB1dDtcblx0ICAgICAgICBpbnB1dCA9IG5vcm1hbGl6ZShpbnB1dCwgJycpO1xuXHQgICAgICAgIGxlbmd0aCA9IGxlbmd0aCB8fCAyNTU7XG5cblx0ICAgICAgICBpZiAoaW5wdXQubGVuZ3RoIDw9IGxlbmd0aClcblx0ICAgICAgICAgICAgcmV0dXJuIGlucHV0O1xuXG5cdCAgICAgICAgaWYgKGtpbGx3b3Jkcykge1xuXHQgICAgICAgICAgICBpbnB1dCA9IGlucHV0LnN1YnN0cmluZygwLCBsZW5ndGgpO1xuXHQgICAgICAgIH0gZWxzZSB7XG5cdCAgICAgICAgICAgIHZhciBpZHggPSBpbnB1dC5sYXN0SW5kZXhPZignICcsIGxlbmd0aCk7XG5cdCAgICAgICAgICAgIGlmKGlkeCA9PT0gLTEpIHtcblx0ICAgICAgICAgICAgICAgIGlkeCA9IGxlbmd0aDtcblx0ICAgICAgICAgICAgfVxuXG5cdCAgICAgICAgICAgIGlucHV0ID0gaW5wdXQuc3Vic3RyaW5nKDAsIGlkeCk7XG5cdCAgICAgICAgfVxuXG5cdCAgICAgICAgaW5wdXQgKz0gKGVuZCAhPT0gdW5kZWZpbmVkICYmIGVuZCAhPT0gbnVsbCkgPyBlbmQgOiAnLi4uJztcblx0ICAgICAgICByZXR1cm4gci5jb3B5U2FmZW5lc3Mob3JpZywgaW5wdXQpO1xuXHQgICAgfSxcblxuXHQgICAgdXBwZXI6IGZ1bmN0aW9uKHN0cikge1xuXHQgICAgICAgIHN0ciA9IG5vcm1hbGl6ZShzdHIsICcnKTtcblx0ICAgICAgICByZXR1cm4gc3RyLnRvVXBwZXJDYXNlKCk7XG5cdCAgICB9LFxuXG5cdCAgICB1cmxlbmNvZGU6IGZ1bmN0aW9uKG9iaikge1xuXHQgICAgICAgIHZhciBlbmMgPSBlbmNvZGVVUklDb21wb25lbnQ7XG5cdCAgICAgICAgaWYgKGxpYi5pc1N0cmluZyhvYmopKSB7XG5cdCAgICAgICAgICAgIHJldHVybiBlbmMob2JqKTtcblx0ICAgICAgICB9IGVsc2Uge1xuXHQgICAgICAgICAgICB2YXIgcGFydHM7XG5cdCAgICAgICAgICAgIGlmIChsaWIuaXNBcnJheShvYmopKSB7XG5cdCAgICAgICAgICAgICAgICBwYXJ0cyA9IG9iai5tYXAoZnVuY3Rpb24oaXRlbSkge1xuXHQgICAgICAgICAgICAgICAgICAgIHJldHVybiBlbmMoaXRlbVswXSkgKyAnPScgKyBlbmMoaXRlbVsxXSk7XG5cdCAgICAgICAgICAgICAgICB9KTtcblx0ICAgICAgICAgICAgfSBlbHNlIHtcblx0ICAgICAgICAgICAgICAgIHBhcnRzID0gW107XG5cdCAgICAgICAgICAgICAgICBmb3IgKHZhciBrIGluIG9iaikge1xuXHQgICAgICAgICAgICAgICAgICAgIGlmIChvYmouaGFzT3duUHJvcGVydHkoaykpIHtcblx0ICAgICAgICAgICAgICAgICAgICAgICAgcGFydHMucHVzaChlbmMoaykgKyAnPScgKyBlbmMob2JqW2tdKSk7XG5cdCAgICAgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIHJldHVybiBwYXJ0cy5qb2luKCcmJyk7XG5cdCAgICAgICAgfVxuXHQgICAgfSxcblxuXHQgICAgdXJsaXplOiBmdW5jdGlvbihzdHIsIGxlbmd0aCwgbm9mb2xsb3cpIHtcblx0ICAgICAgICBpZiAoaXNOYU4obGVuZ3RoKSkgbGVuZ3RoID0gSW5maW5pdHk7XG5cblx0ICAgICAgICB2YXIgbm9Gb2xsb3dBdHRyID0gKG5vZm9sbG93ID09PSB0cnVlID8gJyByZWw9XCJub2ZvbGxvd1wiJyA6ICcnKTtcblxuXHQgICAgICAgIC8vIEZvciB0aGUgamluamEgcmVnZXhwLCBzZWVcblx0ICAgICAgICAvLyBodHRwczovL2dpdGh1Yi5jb20vbWl0c3VoaWtvL2ppbmphMi9ibG9iL2YxNWI4MTRkY2JhNmFhMTJiYzc0ZDFmN2QwYzg4MWQ1NWY3MTI2YmUvamluamEyL3V0aWxzLnB5I0wyMC1MMjNcblx0ICAgICAgICB2YXIgcHVuY1JFID0gL14oPzpcXCh8PHwmbHQ7KT8oLio/KSg/OlxcLnwsfFxcKXxcXG58Jmd0Oyk/JC87XG5cdCAgICAgICAgLy8gZnJvbSBodHRwOi8vYmxvZy5nZXJ2Lm5ldC8yMDExLzA1L2h0bWw1X2VtYWlsX2FkZHJlc3NfcmVnZXhwL1xuXHQgICAgICAgIHZhciBlbWFpbFJFID0gL15bXFx3LiEjJCUmJyorXFwtXFwvPT9cXF5ge3x9fl0rQFthLXpcXGRcXC1dKyhcXC5bYS16XFxkXFwtXSspKyQvaTtcblx0ICAgICAgICB2YXIgaHR0cEh0dHBzUkUgPSAvXmh0dHBzPzpcXC9cXC8uKiQvO1xuXHQgICAgICAgIHZhciB3d3dSRSA9IC9ed3d3XFwuLztcblx0ICAgICAgICB2YXIgdGxkUkUgPSAvXFwuKD86b3JnfG5ldHxjb20pKD86XFw6fFxcL3wkKS87XG5cblx0ICAgICAgICB2YXIgd29yZHMgPSBzdHIuc3BsaXQoLyhcXHMrKS8pLmZpbHRlcihmdW5jdGlvbih3b3JkKSB7XG5cdCAgICAgICAgICAvLyBJZiB0aGUgd29yZCBoYXMgbm8gbGVuZ3RoLCBiYWlsLiBUaGlzIGNhbiBoYXBwZW4gZm9yIHN0ciB3aXRoXG5cdCAgICAgICAgICAvLyB0cmFpbGluZyB3aGl0ZXNwYWNlLlxuXHQgICAgICAgICAgcmV0dXJuIHdvcmQgJiYgd29yZC5sZW5ndGg7XG5cdCAgICAgICAgfSkubWFwKGZ1bmN0aW9uKHdvcmQpIHtcblx0ICAgICAgICAgIHZhciBtYXRjaGVzID0gd29yZC5tYXRjaChwdW5jUkUpO1xuXHQgICAgICAgICAgdmFyIHBvc3NpYmxlVXJsID0gbWF0Y2hlcyAmJiBtYXRjaGVzWzFdIHx8IHdvcmQ7XG5cblx0ICAgICAgICAgIC8vIHVybCB0aGF0IHN0YXJ0cyB3aXRoIGh0dHAgb3IgaHR0cHNcblx0ICAgICAgICAgIGlmIChodHRwSHR0cHNSRS50ZXN0KHBvc3NpYmxlVXJsKSlcblx0ICAgICAgICAgICAgcmV0dXJuICc8YSBocmVmPVwiJyArIHBvc3NpYmxlVXJsICsgJ1wiJyArIG5vRm9sbG93QXR0ciArICc+JyArIHBvc3NpYmxlVXJsLnN1YnN0cigwLCBsZW5ndGgpICsgJzwvYT4nO1xuXG5cdCAgICAgICAgICAvLyB1cmwgdGhhdCBzdGFydHMgd2l0aCB3d3cuXG5cdCAgICAgICAgICBpZiAod3d3UkUudGVzdChwb3NzaWJsZVVybCkpXG5cdCAgICAgICAgICAgIHJldHVybiAnPGEgaHJlZj1cImh0dHA6Ly8nICsgcG9zc2libGVVcmwgKyAnXCInICsgbm9Gb2xsb3dBdHRyICsgJz4nICsgcG9zc2libGVVcmwuc3Vic3RyKDAsIGxlbmd0aCkgKyAnPC9hPic7XG5cblx0ICAgICAgICAgIC8vIGFuIGVtYWlsIGFkZHJlc3Mgb2YgdGhlIGZvcm0gdXNlcm5hbWVAZG9tYWluLnRsZFxuXHQgICAgICAgICAgaWYgKGVtYWlsUkUudGVzdChwb3NzaWJsZVVybCkpXG5cdCAgICAgICAgICAgIHJldHVybiAnPGEgaHJlZj1cIm1haWx0bzonICsgcG9zc2libGVVcmwgKyAnXCI+JyArIHBvc3NpYmxlVXJsICsgJzwvYT4nO1xuXG5cdCAgICAgICAgICAvLyB1cmwgdGhhdCBlbmRzIGluIC5jb20sIC5vcmcgb3IgLm5ldCB0aGF0IGlzIG5vdCBhbiBlbWFpbCBhZGRyZXNzXG5cdCAgICAgICAgICBpZiAodGxkUkUudGVzdChwb3NzaWJsZVVybCkpXG5cdCAgICAgICAgICAgIHJldHVybiAnPGEgaHJlZj1cImh0dHA6Ly8nICsgcG9zc2libGVVcmwgKyAnXCInICsgbm9Gb2xsb3dBdHRyICsgJz4nICsgcG9zc2libGVVcmwuc3Vic3RyKDAsIGxlbmd0aCkgKyAnPC9hPic7XG5cblx0ICAgICAgICAgIHJldHVybiB3b3JkO1xuXG5cdCAgICAgICAgfSk7XG5cblx0ICAgICAgICByZXR1cm4gd29yZHMuam9pbignJyk7XG5cdCAgICB9LFxuXG5cdCAgICB3b3JkY291bnQ6IGZ1bmN0aW9uKHN0cikge1xuXHQgICAgICAgIHN0ciA9IG5vcm1hbGl6ZShzdHIsICcnKTtcblx0ICAgICAgICB2YXIgd29yZHMgPSAoc3RyKSA/IHN0ci5tYXRjaCgvXFx3Ky9nKSA6IG51bGw7XG5cdCAgICAgICAgcmV0dXJuICh3b3JkcykgPyB3b3Jkcy5sZW5ndGggOiBudWxsO1xuXHQgICAgfSxcblxuXHQgICAgJ2Zsb2F0JzogZnVuY3Rpb24odmFsLCBkZWYpIHtcblx0ICAgICAgICB2YXIgcmVzID0gcGFyc2VGbG9hdCh2YWwpO1xuXHQgICAgICAgIHJldHVybiBpc05hTihyZXMpID8gZGVmIDogcmVzO1xuXHQgICAgfSxcblxuXHQgICAgJ2ludCc6IGZ1bmN0aW9uKHZhbCwgZGVmKSB7XG5cdCAgICAgICAgdmFyIHJlcyA9IHBhcnNlSW50KHZhbCwgMTApO1xuXHQgICAgICAgIHJldHVybiBpc05hTihyZXMpID8gZGVmIDogcmVzO1xuXHQgICAgfVxuXHR9O1xuXG5cdC8vIEFsaWFzZXNcblx0ZmlsdGVycy5kID0gZmlsdGVyc1snZGVmYXVsdCddO1xuXHRmaWx0ZXJzLmUgPSBmaWx0ZXJzLmVzY2FwZTtcblxuXHRtb2R1bGUuZXhwb3J0cyA9IGZpbHRlcnM7XG5cblxuLyoqKi8gfSxcbi8qIDggKi9cbi8qKiovIGZ1bmN0aW9uKG1vZHVsZSwgZXhwb3J0cywgX193ZWJwYWNrX3JlcXVpcmVfXykge1xuXG5cdCd1c2Ugc3RyaWN0JztcblxuXHR2YXIgbGliID0gX193ZWJwYWNrX3JlcXVpcmVfXygxKTtcblx0dmFyIE9iaiA9IF9fd2VicGFja19yZXF1aXJlX18oNik7XG5cblx0Ly8gRnJhbWVzIGtlZXAgdHJhY2sgb2Ygc2NvcGluZyBib3RoIGF0IGNvbXBpbGUtdGltZSBhbmQgcnVuLXRpbWUgc29cblx0Ly8gd2Uga25vdyBob3cgdG8gYWNjZXNzIHZhcmlhYmxlcy4gQmxvY2sgdGFncyBjYW4gaW50cm9kdWNlIHNwZWNpYWxcblx0Ly8gdmFyaWFibGVzLCBmb3IgZXhhbXBsZS5cblx0dmFyIEZyYW1lID0gT2JqLmV4dGVuZCh7XG5cdCAgICBpbml0OiBmdW5jdGlvbihwYXJlbnQsIGlzb2xhdGVXcml0ZXMpIHtcblx0ICAgICAgICB0aGlzLnZhcmlhYmxlcyA9IHt9O1xuXHQgICAgICAgIHRoaXMucGFyZW50ID0gcGFyZW50O1xuXHQgICAgICAgIHRoaXMudG9wTGV2ZWwgPSBmYWxzZTtcblx0ICAgICAgICAvLyBpZiB0aGlzIGlzIHRydWUsIHdyaXRlcyAoc2V0KSBzaG91bGQgbmV2ZXIgcHJvcGFnYXRlIHVwd2FyZHMgcGFzdFxuXHQgICAgICAgIC8vIHRoaXMgZnJhbWUgdG8gaXRzIHBhcmVudCAodGhvdWdoIHJlYWRzIG1heSkuXG5cdCAgICAgICAgdGhpcy5pc29sYXRlV3JpdGVzID0gaXNvbGF0ZVdyaXRlcztcblx0ICAgIH0sXG5cblx0ICAgIHNldDogZnVuY3Rpb24obmFtZSwgdmFsLCByZXNvbHZlVXApIHtcblx0ICAgICAgICAvLyBBbGxvdyB2YXJpYWJsZXMgd2l0aCBkb3RzIGJ5IGF1dG9tYXRpY2FsbHkgY3JlYXRpbmcgdGhlXG5cdCAgICAgICAgLy8gbmVzdGVkIHN0cnVjdHVyZVxuXHQgICAgICAgIHZhciBwYXJ0cyA9IG5hbWUuc3BsaXQoJy4nKTtcblx0ICAgICAgICB2YXIgb2JqID0gdGhpcy52YXJpYWJsZXM7XG5cdCAgICAgICAgdmFyIGZyYW1lID0gdGhpcztcblxuXHQgICAgICAgIGlmKHJlc29sdmVVcCkge1xuXHQgICAgICAgICAgICBpZigoZnJhbWUgPSB0aGlzLnJlc29sdmUocGFydHNbMF0sIHRydWUpKSkge1xuXHQgICAgICAgICAgICAgICAgZnJhbWUuc2V0KG5hbWUsIHZhbCk7XG5cdCAgICAgICAgICAgICAgICByZXR1cm47XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICB9XG5cblx0ICAgICAgICBmb3IodmFyIGk9MDsgaTxwYXJ0cy5sZW5ndGggLSAxOyBpKyspIHtcblx0ICAgICAgICAgICAgdmFyIGlkID0gcGFydHNbaV07XG5cblx0ICAgICAgICAgICAgaWYoIW9ialtpZF0pIHtcblx0ICAgICAgICAgICAgICAgIG9ialtpZF0gPSB7fTtcblx0ICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICBvYmogPSBvYmpbaWRdO1xuXHQgICAgICAgIH1cblxuXHQgICAgICAgIG9ialtwYXJ0c1twYXJ0cy5sZW5ndGggLSAxXV0gPSB2YWw7XG5cdCAgICB9LFxuXG5cdCAgICBnZXQ6IGZ1bmN0aW9uKG5hbWUpIHtcblx0ICAgICAgICB2YXIgdmFsID0gdGhpcy52YXJpYWJsZXNbbmFtZV07XG5cdCAgICAgICAgaWYodmFsICE9PSB1bmRlZmluZWQgJiYgdmFsICE9PSBudWxsKSB7XG5cdCAgICAgICAgICAgIHJldHVybiB2YWw7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIHJldHVybiBudWxsO1xuXHQgICAgfSxcblxuXHQgICAgbG9va3VwOiBmdW5jdGlvbihuYW1lKSB7XG5cdCAgICAgICAgdmFyIHAgPSB0aGlzLnBhcmVudDtcblx0ICAgICAgICB2YXIgdmFsID0gdGhpcy52YXJpYWJsZXNbbmFtZV07XG5cdCAgICAgICAgaWYodmFsICE9PSB1bmRlZmluZWQgJiYgdmFsICE9PSBudWxsKSB7XG5cdCAgICAgICAgICAgIHJldHVybiB2YWw7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIHJldHVybiBwICYmIHAubG9va3VwKG5hbWUpO1xuXHQgICAgfSxcblxuXHQgICAgcmVzb2x2ZTogZnVuY3Rpb24obmFtZSwgZm9yV3JpdGUpIHtcblx0ICAgICAgICB2YXIgcCA9IChmb3JXcml0ZSAmJiB0aGlzLmlzb2xhdGVXcml0ZXMpID8gdW5kZWZpbmVkIDogdGhpcy5wYXJlbnQ7XG5cdCAgICAgICAgdmFyIHZhbCA9IHRoaXMudmFyaWFibGVzW25hbWVdO1xuXHQgICAgICAgIGlmKHZhbCAhPT0gdW5kZWZpbmVkICYmIHZhbCAhPT0gbnVsbCkge1xuXHQgICAgICAgICAgICByZXR1cm4gdGhpcztcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIHAgJiYgcC5yZXNvbHZlKG5hbWUpO1xuXHQgICAgfSxcblxuXHQgICAgcHVzaDogZnVuY3Rpb24oaXNvbGF0ZVdyaXRlcykge1xuXHQgICAgICAgIHJldHVybiBuZXcgRnJhbWUodGhpcywgaXNvbGF0ZVdyaXRlcyk7XG5cdCAgICB9LFxuXG5cdCAgICBwb3A6IGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIHJldHVybiB0aGlzLnBhcmVudDtcblx0ICAgIH1cblx0fSk7XG5cblx0ZnVuY3Rpb24gbWFrZU1hY3JvKGFyZ05hbWVzLCBrd2FyZ05hbWVzLCBmdW5jKSB7XG5cdCAgICByZXR1cm4gZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgdmFyIGFyZ0NvdW50ID0gbnVtQXJncyhhcmd1bWVudHMpO1xuXHQgICAgICAgIHZhciBhcmdzO1xuXHQgICAgICAgIHZhciBrd2FyZ3MgPSBnZXRLZXl3b3JkQXJncyhhcmd1bWVudHMpO1xuXHQgICAgICAgIHZhciBpO1xuXG5cdCAgICAgICAgaWYoYXJnQ291bnQgPiBhcmdOYW1lcy5sZW5ndGgpIHtcblx0ICAgICAgICAgICAgYXJncyA9IEFycmF5LnByb3RvdHlwZS5zbGljZS5jYWxsKGFyZ3VtZW50cywgMCwgYXJnTmFtZXMubGVuZ3RoKTtcblxuXHQgICAgICAgICAgICAvLyBQb3NpdGlvbmFsIGFyZ3VtZW50cyB0aGF0IHNob3VsZCBiZSBwYXNzZWQgaW4gYXNcblx0ICAgICAgICAgICAgLy8ga2V5d29yZCBhcmd1bWVudHMgKGVzc2VudGlhbGx5IGRlZmF1bHQgdmFsdWVzKVxuXHQgICAgICAgICAgICB2YXIgdmFscyA9IEFycmF5LnByb3RvdHlwZS5zbGljZS5jYWxsKGFyZ3VtZW50cywgYXJncy5sZW5ndGgsIGFyZ0NvdW50KTtcblx0ICAgICAgICAgICAgZm9yKGkgPSAwOyBpIDwgdmFscy5sZW5ndGg7IGkrKykge1xuXHQgICAgICAgICAgICAgICAgaWYoaSA8IGt3YXJnTmFtZXMubGVuZ3RoKSB7XG5cdCAgICAgICAgICAgICAgICAgICAga3dhcmdzW2t3YXJnTmFtZXNbaV1dID0gdmFsc1tpXTtcblx0ICAgICAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgfVxuXG5cdCAgICAgICAgICAgIGFyZ3MucHVzaChrd2FyZ3MpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIGlmKGFyZ0NvdW50IDwgYXJnTmFtZXMubGVuZ3RoKSB7XG5cdCAgICAgICAgICAgIGFyZ3MgPSBBcnJheS5wcm90b3R5cGUuc2xpY2UuY2FsbChhcmd1bWVudHMsIDAsIGFyZ0NvdW50KTtcblxuXHQgICAgICAgICAgICBmb3IoaSA9IGFyZ0NvdW50OyBpIDwgYXJnTmFtZXMubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICAgICAgICAgIHZhciBhcmcgPSBhcmdOYW1lc1tpXTtcblxuXHQgICAgICAgICAgICAgICAgLy8gS2V5d29yZCBhcmd1bWVudHMgdGhhdCBzaG91bGQgYmUgcGFzc2VkIGFzXG5cdCAgICAgICAgICAgICAgICAvLyBwb3NpdGlvbmFsIGFyZ3VtZW50cywgaS5lLiB0aGUgY2FsbGVyIGV4cGxpY2l0bHlcblx0ICAgICAgICAgICAgICAgIC8vIHVzZWQgdGhlIG5hbWUgb2YgYSBwb3NpdGlvbmFsIGFyZ1xuXHQgICAgICAgICAgICAgICAgYXJncy5wdXNoKGt3YXJnc1thcmddKTtcblx0ICAgICAgICAgICAgICAgIGRlbGV0ZSBrd2FyZ3NbYXJnXTtcblx0ICAgICAgICAgICAgfVxuXG5cdCAgICAgICAgICAgIGFyZ3MucHVzaChrd2FyZ3MpO1xuXHQgICAgICAgIH1cblx0ICAgICAgICBlbHNlIHtcblx0ICAgICAgICAgICAgYXJncyA9IGFyZ3VtZW50cztcblx0ICAgICAgICB9XG5cblx0ICAgICAgICByZXR1cm4gZnVuYy5hcHBseSh0aGlzLCBhcmdzKTtcblx0ICAgIH07XG5cdH1cblxuXHRmdW5jdGlvbiBtYWtlS2V5d29yZEFyZ3Mob2JqKSB7XG5cdCAgICBvYmouX19rZXl3b3JkcyA9IHRydWU7XG5cdCAgICByZXR1cm4gb2JqO1xuXHR9XG5cblx0ZnVuY3Rpb24gZ2V0S2V5d29yZEFyZ3MoYXJncykge1xuXHQgICAgdmFyIGxlbiA9IGFyZ3MubGVuZ3RoO1xuXHQgICAgaWYobGVuKSB7XG5cdCAgICAgICAgdmFyIGxhc3RBcmcgPSBhcmdzW2xlbiAtIDFdO1xuXHQgICAgICAgIGlmKGxhc3RBcmcgJiYgbGFzdEFyZy5oYXNPd25Qcm9wZXJ0eSgnX19rZXl3b3JkcycpKSB7XG5cdCAgICAgICAgICAgIHJldHVybiBsYXN0QXJnO1xuXHQgICAgICAgIH1cblx0ICAgIH1cblx0ICAgIHJldHVybiB7fTtcblx0fVxuXG5cdGZ1bmN0aW9uIG51bUFyZ3MoYXJncykge1xuXHQgICAgdmFyIGxlbiA9IGFyZ3MubGVuZ3RoO1xuXHQgICAgaWYobGVuID09PSAwKSB7XG5cdCAgICAgICAgcmV0dXJuIDA7XG5cdCAgICB9XG5cblx0ICAgIHZhciBsYXN0QXJnID0gYXJnc1tsZW4gLSAxXTtcblx0ICAgIGlmKGxhc3RBcmcgJiYgbGFzdEFyZy5oYXNPd25Qcm9wZXJ0eSgnX19rZXl3b3JkcycpKSB7XG5cdCAgICAgICAgcmV0dXJuIGxlbiAtIDE7XG5cdCAgICB9XG5cdCAgICBlbHNlIHtcblx0ICAgICAgICByZXR1cm4gbGVuO1xuXHQgICAgfVxuXHR9XG5cblx0Ly8gQSBTYWZlU3RyaW5nIG9iamVjdCBpbmRpY2F0ZXMgdGhhdCB0aGUgc3RyaW5nIHNob3VsZCBub3QgYmVcblx0Ly8gYXV0b2VzY2FwZWQuIFRoaXMgaGFwcGVucyBtYWdpY2FsbHkgYmVjYXVzZSBhdXRvZXNjYXBpbmcgb25seVxuXHQvLyBvY2N1cnMgb24gcHJpbWl0aXZlIHN0cmluZyBvYmplY3RzLlxuXHRmdW5jdGlvbiBTYWZlU3RyaW5nKHZhbCkge1xuXHQgICAgaWYodHlwZW9mIHZhbCAhPT0gJ3N0cmluZycpIHtcblx0ICAgICAgICByZXR1cm4gdmFsO1xuXHQgICAgfVxuXG5cdCAgICB0aGlzLnZhbCA9IHZhbDtcblx0ICAgIHRoaXMubGVuZ3RoID0gdmFsLmxlbmd0aDtcblx0fVxuXG5cdFNhZmVTdHJpbmcucHJvdG90eXBlID0gT2JqZWN0LmNyZWF0ZShTdHJpbmcucHJvdG90eXBlLCB7XG5cdCAgICBsZW5ndGg6IHsgd3JpdGFibGU6IHRydWUsIGNvbmZpZ3VyYWJsZTogdHJ1ZSwgdmFsdWU6IDAgfVxuXHR9KTtcblx0U2FmZVN0cmluZy5wcm90b3R5cGUudmFsdWVPZiA9IGZ1bmN0aW9uKCkge1xuXHQgICAgcmV0dXJuIHRoaXMudmFsO1xuXHR9O1xuXHRTYWZlU3RyaW5nLnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uKCkge1xuXHQgICAgcmV0dXJuIHRoaXMudmFsO1xuXHR9O1xuXG5cdGZ1bmN0aW9uIGNvcHlTYWZlbmVzcyhkZXN0LCB0YXJnZXQpIHtcblx0ICAgIGlmKGRlc3QgaW5zdGFuY2VvZiBTYWZlU3RyaW5nKSB7XG5cdCAgICAgICAgcmV0dXJuIG5ldyBTYWZlU3RyaW5nKHRhcmdldCk7XG5cdCAgICB9XG5cdCAgICByZXR1cm4gdGFyZ2V0LnRvU3RyaW5nKCk7XG5cdH1cblxuXHRmdW5jdGlvbiBtYXJrU2FmZSh2YWwpIHtcblx0ICAgIHZhciB0eXBlID0gdHlwZW9mIHZhbDtcblxuXHQgICAgaWYodHlwZSA9PT0gJ3N0cmluZycpIHtcblx0ICAgICAgICByZXR1cm4gbmV3IFNhZmVTdHJpbmcodmFsKTtcblx0ICAgIH1cblx0ICAgIGVsc2UgaWYodHlwZSAhPT0gJ2Z1bmN0aW9uJykge1xuXHQgICAgICAgIHJldHVybiB2YWw7XG5cdCAgICB9XG5cdCAgICBlbHNlIHtcblx0ICAgICAgICByZXR1cm4gZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgICAgIHZhciByZXQgPSB2YWwuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcblxuXHQgICAgICAgICAgICBpZih0eXBlb2YgcmV0ID09PSAnc3RyaW5nJykge1xuXHQgICAgICAgICAgICAgICAgcmV0dXJuIG5ldyBTYWZlU3RyaW5nKHJldCk7XG5cdCAgICAgICAgICAgIH1cblxuXHQgICAgICAgICAgICByZXR1cm4gcmV0O1xuXHQgICAgICAgIH07XG5cdCAgICB9XG5cdH1cblxuXHRmdW5jdGlvbiBzdXBwcmVzc1ZhbHVlKHZhbCwgYXV0b2VzY2FwZSkge1xuXHQgICAgdmFsID0gKHZhbCAhPT0gdW5kZWZpbmVkICYmIHZhbCAhPT0gbnVsbCkgPyB2YWwgOiAnJztcblxuXHQgICAgaWYoYXV0b2VzY2FwZSAmJiB0eXBlb2YgdmFsID09PSAnc3RyaW5nJykge1xuXHQgICAgICAgIHZhbCA9IGxpYi5lc2NhcGUodmFsKTtcblx0ICAgIH1cblxuXHQgICAgcmV0dXJuIHZhbDtcblx0fVxuXG5cdGZ1bmN0aW9uIGVuc3VyZURlZmluZWQodmFsLCBsaW5lbm8sIGNvbG5vKSB7XG5cdCAgICBpZih2YWwgPT09IG51bGwgfHwgdmFsID09PSB1bmRlZmluZWQpIHtcblx0ICAgICAgICB0aHJvdyBuZXcgbGliLlRlbXBsYXRlRXJyb3IoXG5cdCAgICAgICAgICAgICdhdHRlbXB0ZWQgdG8gb3V0cHV0IG51bGwgb3IgdW5kZWZpbmVkIHZhbHVlJyxcblx0ICAgICAgICAgICAgbGluZW5vICsgMSxcblx0ICAgICAgICAgICAgY29sbm8gKyAxXG5cdCAgICAgICAgKTtcblx0ICAgIH1cblx0ICAgIHJldHVybiB2YWw7XG5cdH1cblxuXHRmdW5jdGlvbiBtZW1iZXJMb29rdXAob2JqLCB2YWwpIHtcblx0ICAgIG9iaiA9IG9iaiB8fCB7fTtcblxuXHQgICAgaWYodHlwZW9mIG9ialt2YWxdID09PSAnZnVuY3Rpb24nKSB7XG5cdCAgICAgICAgcmV0dXJuIGZ1bmN0aW9uKCkge1xuXHQgICAgICAgICAgICByZXR1cm4gb2JqW3ZhbF0uYXBwbHkob2JqLCBhcmd1bWVudHMpO1xuXHQgICAgICAgIH07XG5cdCAgICB9XG5cblx0ICAgIHJldHVybiBvYmpbdmFsXTtcblx0fVxuXG5cdGZ1bmN0aW9uIGNhbGxXcmFwKG9iaiwgbmFtZSwgY29udGV4dCwgYXJncykge1xuXHQgICAgaWYoIW9iaikge1xuXHQgICAgICAgIHRocm93IG5ldyBFcnJvcignVW5hYmxlIHRvIGNhbGwgYCcgKyBuYW1lICsgJ2AsIHdoaWNoIGlzIHVuZGVmaW5lZCBvciBmYWxzZXknKTtcblx0ICAgIH1cblx0ICAgIGVsc2UgaWYodHlwZW9mIG9iaiAhPT0gJ2Z1bmN0aW9uJykge1xuXHQgICAgICAgIHRocm93IG5ldyBFcnJvcignVW5hYmxlIHRvIGNhbGwgYCcgKyBuYW1lICsgJ2AsIHdoaWNoIGlzIG5vdCBhIGZ1bmN0aW9uJyk7XG5cdCAgICB9XG5cblx0ICAgIC8vIGpzaGludCB2YWxpZHRoaXM6IHRydWVcblx0ICAgIHJldHVybiBvYmouYXBwbHkoY29udGV4dCwgYXJncyk7XG5cdH1cblxuXHRmdW5jdGlvbiBjb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgbmFtZSkge1xuXHQgICAgdmFyIHZhbCA9IGZyYW1lLmxvb2t1cChuYW1lKTtcblx0ICAgIHJldHVybiAodmFsICE9PSB1bmRlZmluZWQgJiYgdmFsICE9PSBudWxsKSA/XG5cdCAgICAgICAgdmFsIDpcblx0ICAgICAgICBjb250ZXh0Lmxvb2t1cChuYW1lKTtcblx0fVxuXG5cdGZ1bmN0aW9uIGhhbmRsZUVycm9yKGVycm9yLCBsaW5lbm8sIGNvbG5vKSB7XG5cdCAgICBpZihlcnJvci5saW5lbm8pIHtcblx0ICAgICAgICByZXR1cm4gZXJyb3I7XG5cdCAgICB9XG5cdCAgICBlbHNlIHtcblx0ICAgICAgICByZXR1cm4gbmV3IGxpYi5UZW1wbGF0ZUVycm9yKGVycm9yLCBsaW5lbm8sIGNvbG5vKTtcblx0ICAgIH1cblx0fVxuXG5cdGZ1bmN0aW9uIGFzeW5jRWFjaChhcnIsIGRpbWVuLCBpdGVyLCBjYikge1xuXHQgICAgaWYobGliLmlzQXJyYXkoYXJyKSkge1xuXHQgICAgICAgIHZhciBsZW4gPSBhcnIubGVuZ3RoO1xuXG5cdCAgICAgICAgbGliLmFzeW5jSXRlcihhcnIsIGZ1bmN0aW9uKGl0ZW0sIGksIG5leHQpIHtcblx0ICAgICAgICAgICAgc3dpdGNoKGRpbWVuKSB7XG5cdCAgICAgICAgICAgIGNhc2UgMTogaXRlcihpdGVtLCBpLCBsZW4sIG5leHQpOyBicmVhaztcblx0ICAgICAgICAgICAgY2FzZSAyOiBpdGVyKGl0ZW1bMF0sIGl0ZW1bMV0sIGksIGxlbiwgbmV4dCk7IGJyZWFrO1xuXHQgICAgICAgICAgICBjYXNlIDM6IGl0ZXIoaXRlbVswXSwgaXRlbVsxXSwgaXRlbVsyXSwgaSwgbGVuLCBuZXh0KTsgYnJlYWs7XG5cdCAgICAgICAgICAgIGRlZmF1bHQ6XG5cdCAgICAgICAgICAgICAgICBpdGVtLnB1c2goaSwgbmV4dCk7XG5cdCAgICAgICAgICAgICAgICBpdGVyLmFwcGx5KHRoaXMsIGl0ZW0pO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgfSwgY2IpO1xuXHQgICAgfVxuXHQgICAgZWxzZSB7XG5cdCAgICAgICAgbGliLmFzeW5jRm9yKGFyciwgZnVuY3Rpb24oa2V5LCB2YWwsIGksIGxlbiwgbmV4dCkge1xuXHQgICAgICAgICAgICBpdGVyKGtleSwgdmFsLCBpLCBsZW4sIG5leHQpO1xuXHQgICAgICAgIH0sIGNiKTtcblx0ICAgIH1cblx0fVxuXG5cdGZ1bmN0aW9uIGFzeW5jQWxsKGFyciwgZGltZW4sIGZ1bmMsIGNiKSB7XG5cdCAgICB2YXIgZmluaXNoZWQgPSAwO1xuXHQgICAgdmFyIGxlbiwgaTtcblx0ICAgIHZhciBvdXRwdXRBcnI7XG5cblx0ICAgIGZ1bmN0aW9uIGRvbmUoaSwgb3V0cHV0KSB7XG5cdCAgICAgICAgZmluaXNoZWQrKztcblx0ICAgICAgICBvdXRwdXRBcnJbaV0gPSBvdXRwdXQ7XG5cblx0ICAgICAgICBpZihmaW5pc2hlZCA9PT0gbGVuKSB7XG5cdCAgICAgICAgICAgIGNiKG51bGwsIG91dHB1dEFyci5qb2luKCcnKSk7XG5cdCAgICAgICAgfVxuXHQgICAgfVxuXG5cdCAgICBpZihsaWIuaXNBcnJheShhcnIpKSB7XG5cdCAgICAgICAgbGVuID0gYXJyLmxlbmd0aDtcblx0ICAgICAgICBvdXRwdXRBcnIgPSBuZXcgQXJyYXkobGVuKTtcblxuXHQgICAgICAgIGlmKGxlbiA9PT0gMCkge1xuXHQgICAgICAgICAgICBjYihudWxsLCAnJyk7XG5cdCAgICAgICAgfVxuXHQgICAgICAgIGVsc2Uge1xuXHQgICAgICAgICAgICBmb3IoaSA9IDA7IGkgPCBhcnIubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICAgICAgICAgIHZhciBpdGVtID0gYXJyW2ldO1xuXG5cdCAgICAgICAgICAgICAgICBzd2l0Y2goZGltZW4pIHtcblx0ICAgICAgICAgICAgICAgIGNhc2UgMTogZnVuYyhpdGVtLCBpLCBsZW4sIGRvbmUpOyBicmVhaztcblx0ICAgICAgICAgICAgICAgIGNhc2UgMjogZnVuYyhpdGVtWzBdLCBpdGVtWzFdLCBpLCBsZW4sIGRvbmUpOyBicmVhaztcblx0ICAgICAgICAgICAgICAgIGNhc2UgMzogZnVuYyhpdGVtWzBdLCBpdGVtWzFdLCBpdGVtWzJdLCBpLCBsZW4sIGRvbmUpOyBicmVhaztcblx0ICAgICAgICAgICAgICAgIGRlZmF1bHQ6XG5cdCAgICAgICAgICAgICAgICAgICAgaXRlbS5wdXNoKGksIGRvbmUpO1xuXHQgICAgICAgICAgICAgICAgICAgIC8vIGpzaGludCB2YWxpZHRoaXM6IHRydWVcblx0ICAgICAgICAgICAgICAgICAgICBmdW5jLmFwcGx5KHRoaXMsIGl0ZW0pO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgfVxuXHQgICAgfVxuXHQgICAgZWxzZSB7XG5cdCAgICAgICAgdmFyIGtleXMgPSBsaWIua2V5cyhhcnIpO1xuXHQgICAgICAgIGxlbiA9IGtleXMubGVuZ3RoO1xuXHQgICAgICAgIG91dHB1dEFyciA9IG5ldyBBcnJheShsZW4pO1xuXG5cdCAgICAgICAgaWYobGVuID09PSAwKSB7XG5cdCAgICAgICAgICAgIGNiKG51bGwsICcnKTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgZWxzZSB7XG5cdCAgICAgICAgICAgIGZvcihpID0gMDsgaSA8IGtleXMubGVuZ3RoOyBpKyspIHtcblx0ICAgICAgICAgICAgICAgIHZhciBrID0ga2V5c1tpXTtcblx0ICAgICAgICAgICAgICAgIGZ1bmMoaywgYXJyW2tdLCBpLCBsZW4sIGRvbmUpO1xuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgfVxuXHQgICAgfVxuXHR9XG5cblx0bW9kdWxlLmV4cG9ydHMgPSB7XG5cdCAgICBGcmFtZTogRnJhbWUsXG5cdCAgICBtYWtlTWFjcm86IG1ha2VNYWNybyxcblx0ICAgIG1ha2VLZXl3b3JkQXJnczogbWFrZUtleXdvcmRBcmdzLFxuXHQgICAgbnVtQXJnczogbnVtQXJncyxcblx0ICAgIHN1cHByZXNzVmFsdWU6IHN1cHByZXNzVmFsdWUsXG5cdCAgICBlbnN1cmVEZWZpbmVkOiBlbnN1cmVEZWZpbmVkLFxuXHQgICAgbWVtYmVyTG9va3VwOiBtZW1iZXJMb29rdXAsXG5cdCAgICBjb250ZXh0T3JGcmFtZUxvb2t1cDogY29udGV4dE9yRnJhbWVMb29rdXAsXG5cdCAgICBjYWxsV3JhcDogY2FsbFdyYXAsXG5cdCAgICBoYW5kbGVFcnJvcjogaGFuZGxlRXJyb3IsXG5cdCAgICBpc0FycmF5OiBsaWIuaXNBcnJheSxcblx0ICAgIGtleXM6IGxpYi5rZXlzLFxuXHQgICAgU2FmZVN0cmluZzogU2FmZVN0cmluZyxcblx0ICAgIGNvcHlTYWZlbmVzczogY29weVNhZmVuZXNzLFxuXHQgICAgbWFya1NhZmU6IG1hcmtTYWZlLFxuXHQgICAgYXN5bmNFYWNoOiBhc3luY0VhY2gsXG5cdCAgICBhc3luY0FsbDogYXN5bmNBbGwsXG5cdCAgICBpbk9wZXJhdG9yOiBsaWIuaW5PcGVyYXRvclxuXHR9O1xuXG5cbi8qKiovIH0sXG4vKiA5ICovXG4vKioqLyBmdW5jdGlvbihtb2R1bGUsIGV4cG9ydHMpIHtcblxuXHQndXNlIHN0cmljdCc7XG5cblx0ZnVuY3Rpb24gY3ljbGVyKGl0ZW1zKSB7XG5cdCAgICB2YXIgaW5kZXggPSAtMTtcblxuXHQgICAgcmV0dXJuIHtcblx0ICAgICAgICBjdXJyZW50OiBudWxsLFxuXHQgICAgICAgIHJlc2V0OiBmdW5jdGlvbigpIHtcblx0ICAgICAgICAgICAgaW5kZXggPSAtMTtcblx0ICAgICAgICAgICAgdGhpcy5jdXJyZW50ID0gbnVsbDtcblx0ICAgICAgICB9LFxuXG5cdCAgICAgICAgbmV4dDogZnVuY3Rpb24oKSB7XG5cdCAgICAgICAgICAgIGluZGV4Kys7XG5cdCAgICAgICAgICAgIGlmKGluZGV4ID49IGl0ZW1zLmxlbmd0aCkge1xuXHQgICAgICAgICAgICAgICAgaW5kZXggPSAwO1xuXHQgICAgICAgICAgICB9XG5cblx0ICAgICAgICAgICAgdGhpcy5jdXJyZW50ID0gaXRlbXNbaW5kZXhdO1xuXHQgICAgICAgICAgICByZXR1cm4gdGhpcy5jdXJyZW50O1xuXHQgICAgICAgIH0sXG5cdCAgICB9O1xuXG5cdH1cblxuXHRmdW5jdGlvbiBqb2luZXIoc2VwKSB7XG5cdCAgICBzZXAgPSBzZXAgfHwgJywnO1xuXHQgICAgdmFyIGZpcnN0ID0gdHJ1ZTtcblxuXHQgICAgcmV0dXJuIGZ1bmN0aW9uKCkge1xuXHQgICAgICAgIHZhciB2YWwgPSBmaXJzdCA/ICcnIDogc2VwO1xuXHQgICAgICAgIGZpcnN0ID0gZmFsc2U7XG5cdCAgICAgICAgcmV0dXJuIHZhbDtcblx0ICAgIH07XG5cdH1cblxuXHQvLyBNYWtpbmcgdGhpcyBhIGZ1bmN0aW9uIGluc3RlYWQgc28gaXQgcmV0dXJucyBhIG5ldyBvYmplY3Rcblx0Ly8gZWFjaCB0aW1lIGl0J3MgY2FsbGVkLiBUaGF0IHdheSwgaWYgc29tZXRoaW5nIGxpa2UgYW4gZW52aXJvbm1lbnRcblx0Ly8gdXNlcyBpdCwgdGhleSB3aWxsIGVhY2ggaGF2ZSB0aGVpciBvd24gY29weS5cblx0ZnVuY3Rpb24gZ2xvYmFscygpIHtcblx0ICAgIHJldHVybiB7XG5cdCAgICAgICAgcmFuZ2U6IGZ1bmN0aW9uKHN0YXJ0LCBzdG9wLCBzdGVwKSB7XG5cdCAgICAgICAgICAgIGlmKHR5cGVvZiBzdG9wID09PSAndW5kZWZpbmVkJykge1xuXHQgICAgICAgICAgICAgICAgc3RvcCA9IHN0YXJ0O1xuXHQgICAgICAgICAgICAgICAgc3RhcnQgPSAwO1xuXHQgICAgICAgICAgICAgICAgc3RlcCA9IDE7XG5cdCAgICAgICAgICAgIH1cblx0ICAgICAgICAgICAgZWxzZSBpZighc3RlcCkge1xuXHQgICAgICAgICAgICAgICAgc3RlcCA9IDE7XG5cdCAgICAgICAgICAgIH1cblxuXHQgICAgICAgICAgICB2YXIgYXJyID0gW107XG5cdCAgICAgICAgICAgIHZhciBpO1xuXHQgICAgICAgICAgICBpZiAoc3RlcCA+IDApIHtcblx0ICAgICAgICAgICAgICAgIGZvciAoaT1zdGFydDsgaTxzdG9wOyBpKz1zdGVwKSB7XG5cdCAgICAgICAgICAgICAgICAgICAgYXJyLnB1c2goaSk7XG5cdCAgICAgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIH0gZWxzZSB7XG5cdCAgICAgICAgICAgICAgICBmb3IgKGk9c3RhcnQ7IGk+c3RvcDsgaSs9c3RlcCkge1xuXHQgICAgICAgICAgICAgICAgICAgIGFyci5wdXNoKGkpO1xuXHQgICAgICAgICAgICAgICAgfVxuXHQgICAgICAgICAgICB9XG5cdCAgICAgICAgICAgIHJldHVybiBhcnI7XG5cdCAgICAgICAgfSxcblxuXHQgICAgICAgIC8vIGxpcHN1bTogZnVuY3Rpb24obiwgaHRtbCwgbWluLCBtYXgpIHtcblx0ICAgICAgICAvLyB9LFxuXG5cdCAgICAgICAgY3ljbGVyOiBmdW5jdGlvbigpIHtcblx0ICAgICAgICAgICAgcmV0dXJuIGN5Y2xlcihBcnJheS5wcm90b3R5cGUuc2xpY2UuY2FsbChhcmd1bWVudHMpKTtcblx0ICAgICAgICB9LFxuXG5cdCAgICAgICAgam9pbmVyOiBmdW5jdGlvbihzZXApIHtcblx0ICAgICAgICAgICAgcmV0dXJuIGpvaW5lcihzZXApO1xuXHQgICAgICAgIH1cblx0ICAgIH07XG5cdH1cblxuXHRtb2R1bGUuZXhwb3J0cyA9IGdsb2JhbHM7XG5cblxuLyoqKi8gfSxcbi8qIDEwICovXG4vKioqLyBmdW5jdGlvbihtb2R1bGUsIGV4cG9ydHMsIF9fd2VicGFja19yZXF1aXJlX18pIHtcblxuXHQndXNlIHN0cmljdCc7XG5cblx0dmFyIExvYWRlciA9IF9fd2VicGFja19yZXF1aXJlX18oMTEpO1xuXG5cdHZhciBQcmVjb21waWxlZExvYWRlciA9IExvYWRlci5leHRlbmQoe1xuXHQgICAgaW5pdDogZnVuY3Rpb24oY29tcGlsZWRUZW1wbGF0ZXMpIHtcblx0ICAgICAgICB0aGlzLnByZWNvbXBpbGVkID0gY29tcGlsZWRUZW1wbGF0ZXMgfHwge307XG5cdCAgICB9LFxuXG5cdCAgICBnZXRTb3VyY2U6IGZ1bmN0aW9uKG5hbWUpIHtcblx0ICAgICAgICBpZiAodGhpcy5wcmVjb21waWxlZFtuYW1lXSkge1xuXHQgICAgICAgICAgICByZXR1cm4ge1xuXHQgICAgICAgICAgICAgICAgc3JjOiB7IHR5cGU6ICdjb2RlJyxcblx0ICAgICAgICAgICAgICAgICAgICAgICBvYmo6IHRoaXMucHJlY29tcGlsZWRbbmFtZV0gfSxcblx0ICAgICAgICAgICAgICAgIHBhdGg6IG5hbWVcblx0ICAgICAgICAgICAgfTtcblx0ICAgICAgICB9XG5cdCAgICAgICAgcmV0dXJuIG51bGw7XG5cdCAgICB9XG5cdH0pO1xuXG5cdG1vZHVsZS5leHBvcnRzID0gUHJlY29tcGlsZWRMb2FkZXI7XG5cblxuLyoqKi8gfSxcbi8qIDExICovXG4vKioqLyBmdW5jdGlvbihtb2R1bGUsIGV4cG9ydHMsIF9fd2VicGFja19yZXF1aXJlX18pIHtcblxuXHQndXNlIHN0cmljdCc7XG5cblx0dmFyIHBhdGggPSBfX3dlYnBhY2tfcmVxdWlyZV9fKDMpO1xuXHR2YXIgT2JqID0gX193ZWJwYWNrX3JlcXVpcmVfXyg2KTtcblx0dmFyIGxpYiA9IF9fd2VicGFja19yZXF1aXJlX18oMSk7XG5cblx0dmFyIExvYWRlciA9IE9iai5leHRlbmQoe1xuXHQgICAgb246IGZ1bmN0aW9uKG5hbWUsIGZ1bmMpIHtcblx0ICAgICAgICB0aGlzLmxpc3RlbmVycyA9IHRoaXMubGlzdGVuZXJzIHx8IHt9O1xuXHQgICAgICAgIHRoaXMubGlzdGVuZXJzW25hbWVdID0gdGhpcy5saXN0ZW5lcnNbbmFtZV0gfHwgW107XG5cdCAgICAgICAgdGhpcy5saXN0ZW5lcnNbbmFtZV0ucHVzaChmdW5jKTtcblx0ICAgIH0sXG5cblx0ICAgIGVtaXQ6IGZ1bmN0aW9uKG5hbWUgLyosIGFyZzEsIGFyZzIsIC4uLiovKSB7XG5cdCAgICAgICAgdmFyIGFyZ3MgPSBBcnJheS5wcm90b3R5cGUuc2xpY2UuY2FsbChhcmd1bWVudHMsIDEpO1xuXG5cdCAgICAgICAgaWYodGhpcy5saXN0ZW5lcnMgJiYgdGhpcy5saXN0ZW5lcnNbbmFtZV0pIHtcblx0ICAgICAgICAgICAgbGliLmVhY2godGhpcy5saXN0ZW5lcnNbbmFtZV0sIGZ1bmN0aW9uKGxpc3RlbmVyKSB7XG5cdCAgICAgICAgICAgICAgICBsaXN0ZW5lci5hcHBseShudWxsLCBhcmdzKTtcblx0ICAgICAgICAgICAgfSk7XG5cdCAgICAgICAgfVxuXHQgICAgfSxcblxuXHQgICAgcmVzb2x2ZTogZnVuY3Rpb24oZnJvbSwgdG8pIHtcblx0ICAgICAgICByZXR1cm4gcGF0aC5yZXNvbHZlKHBhdGguZGlybmFtZShmcm9tKSwgdG8pO1xuXHQgICAgfSxcblxuXHQgICAgaXNSZWxhdGl2ZTogZnVuY3Rpb24oZmlsZW5hbWUpIHtcblx0ICAgICAgICByZXR1cm4gKGZpbGVuYW1lLmluZGV4T2YoJy4vJykgPT09IDAgfHwgZmlsZW5hbWUuaW5kZXhPZignLi4vJykgPT09IDApO1xuXHQgICAgfVxuXHR9KTtcblxuXHRtb2R1bGUuZXhwb3J0cyA9IExvYWRlcjtcblxuXG4vKioqLyB9LFxuLyogMTIgKi9cbi8qKiovIGZ1bmN0aW9uKG1vZHVsZSwgZXhwb3J0cykge1xuXG5cdGZ1bmN0aW9uIGluc3RhbGxDb21wYXQoKSB7XG5cdCAgJ3VzZSBzdHJpY3QnO1xuXG5cdCAgLy8gVGhpcyBtdXN0IGJlIGNhbGxlZCBsaWtlIGBudW5qdWNrcy5pbnN0YWxsQ29tcGF0YCBzbyB0aGF0IGB0aGlzYFxuXHQgIC8vIHJlZmVyZW5jZXMgdGhlIG51bmp1Y2tzIGluc3RhbmNlXG5cdCAgdmFyIHJ1bnRpbWUgPSB0aGlzLnJ1bnRpbWU7IC8vIGpzaGludCBpZ25vcmU6bGluZVxuXHQgIHZhciBsaWIgPSB0aGlzLmxpYjsgLy8ganNoaW50IGlnbm9yZTpsaW5lXG5cblx0ICB2YXIgb3JpZ19jb250ZXh0T3JGcmFtZUxvb2t1cCA9IHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXA7XG5cdCAgcnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cCA9IGZ1bmN0aW9uKGNvbnRleHQsIGZyYW1lLCBrZXkpIHtcblx0ICAgIHZhciB2YWwgPSBvcmlnX2NvbnRleHRPckZyYW1lTG9va3VwLmFwcGx5KHRoaXMsIGFyZ3VtZW50cyk7XG5cdCAgICBpZiAodmFsID09PSB1bmRlZmluZWQpIHtcblx0ICAgICAgc3dpdGNoIChrZXkpIHtcblx0ICAgICAgY2FzZSAnVHJ1ZSc6XG5cdCAgICAgICAgcmV0dXJuIHRydWU7XG5cdCAgICAgIGNhc2UgJ0ZhbHNlJzpcblx0ICAgICAgICByZXR1cm4gZmFsc2U7XG5cdCAgICAgIGNhc2UgJ05vbmUnOlxuXHQgICAgICAgIHJldHVybiBudWxsO1xuXHQgICAgICB9XG5cdCAgICB9XG5cblx0ICAgIHJldHVybiB2YWw7XG5cdCAgfTtcblxuXHQgIHZhciBvcmlnX21lbWJlckxvb2t1cCA9IHJ1bnRpbWUubWVtYmVyTG9va3VwO1xuXHQgIHZhciBBUlJBWV9NRU1CRVJTID0ge1xuXHQgICAgcG9wOiBmdW5jdGlvbihpbmRleCkge1xuXHQgICAgICBpZiAoaW5kZXggPT09IHVuZGVmaW5lZCkge1xuXHQgICAgICAgIHJldHVybiB0aGlzLnBvcCgpO1xuXHQgICAgICB9XG5cdCAgICAgIGlmIChpbmRleCA+PSB0aGlzLmxlbmd0aCB8fCBpbmRleCA8IDApIHtcblx0ICAgICAgICB0aHJvdyBuZXcgRXJyb3IoJ0tleUVycm9yJyk7XG5cdCAgICAgIH1cblx0ICAgICAgcmV0dXJuIHRoaXMuc3BsaWNlKGluZGV4LCAxKTtcblx0ICAgIH0sXG5cdCAgICByZW1vdmU6IGZ1bmN0aW9uKGVsZW1lbnQpIHtcblx0ICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmxlbmd0aDsgaSsrKSB7XG5cdCAgICAgICAgaWYgKHRoaXNbaV0gPT09IGVsZW1lbnQpIHtcblx0ICAgICAgICAgIHJldHVybiB0aGlzLnNwbGljZShpLCAxKTtcblx0ICAgICAgICB9XG5cdCAgICAgIH1cblx0ICAgICAgdGhyb3cgbmV3IEVycm9yKCdWYWx1ZUVycm9yJyk7XG5cdCAgICB9LFxuXHQgICAgY291bnQ6IGZ1bmN0aW9uKGVsZW1lbnQpIHtcblx0ICAgICAgdmFyIGNvdW50ID0gMDtcblx0ICAgICAgZm9yICh2YXIgaSA9IDA7IGkgPCB0aGlzLmxlbmd0aDsgaSsrKSB7XG5cdCAgICAgICAgaWYgKHRoaXNbaV0gPT09IGVsZW1lbnQpIHtcblx0ICAgICAgICAgIGNvdW50Kys7XG5cdCAgICAgICAgfVxuXHQgICAgICB9XG5cdCAgICAgIHJldHVybiBjb3VudDtcblx0ICAgIH0sXG5cdCAgICBpbmRleDogZnVuY3Rpb24oZWxlbWVudCkge1xuXHQgICAgICB2YXIgaTtcblx0ICAgICAgaWYgKChpID0gdGhpcy5pbmRleE9mKGVsZW1lbnQpKSA9PT0gLTEpIHtcblx0ICAgICAgICB0aHJvdyBuZXcgRXJyb3IoJ1ZhbHVlRXJyb3InKTtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gaTtcblx0ICAgIH0sXG5cdCAgICBmaW5kOiBmdW5jdGlvbihlbGVtZW50KSB7XG5cdCAgICAgIHJldHVybiB0aGlzLmluZGV4T2YoZWxlbWVudCk7XG5cdCAgICB9LFxuXHQgICAgaW5zZXJ0OiBmdW5jdGlvbihpbmRleCwgZWxlbSkge1xuXHQgICAgICByZXR1cm4gdGhpcy5zcGxpY2UoaW5kZXgsIDAsIGVsZW0pO1xuXHQgICAgfVxuXHQgIH07XG5cdCAgdmFyIE9CSkVDVF9NRU1CRVJTID0ge1xuXHQgICAgaXRlbXM6IGZ1bmN0aW9uKCkge1xuXHQgICAgICB2YXIgcmV0ID0gW107XG5cdCAgICAgIGZvcih2YXIgayBpbiB0aGlzKSB7XG5cdCAgICAgICAgcmV0LnB1c2goW2ssIHRoaXNba11dKTtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gcmV0O1xuXHQgICAgfSxcblx0ICAgIHZhbHVlczogZnVuY3Rpb24oKSB7XG5cdCAgICAgIHZhciByZXQgPSBbXTtcblx0ICAgICAgZm9yKHZhciBrIGluIHRoaXMpIHtcblx0ICAgICAgICByZXQucHVzaCh0aGlzW2tdKTtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gcmV0O1xuXHQgICAgfSxcblx0ICAgIGtleXM6IGZ1bmN0aW9uKCkge1xuXHQgICAgICB2YXIgcmV0ID0gW107XG5cdCAgICAgIGZvcih2YXIgayBpbiB0aGlzKSB7XG5cdCAgICAgICAgcmV0LnB1c2goayk7XG5cdCAgICAgIH1cblx0ICAgICAgcmV0dXJuIHJldDtcblx0ICAgIH0sXG5cdCAgICBnZXQ6IGZ1bmN0aW9uKGtleSwgZGVmKSB7XG5cdCAgICAgIHZhciBvdXRwdXQgPSB0aGlzW2tleV07XG5cdCAgICAgIGlmIChvdXRwdXQgPT09IHVuZGVmaW5lZCkge1xuXHQgICAgICAgIG91dHB1dCA9IGRlZjtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gb3V0cHV0O1xuXHQgICAgfSxcblx0ICAgIGhhc19rZXk6IGZ1bmN0aW9uKGtleSkge1xuXHQgICAgICByZXR1cm4gdGhpcy5oYXNPd25Qcm9wZXJ0eShrZXkpO1xuXHQgICAgfSxcblx0ICAgIHBvcDogZnVuY3Rpb24oa2V5LCBkZWYpIHtcblx0ICAgICAgdmFyIG91dHB1dCA9IHRoaXNba2V5XTtcblx0ICAgICAgaWYgKG91dHB1dCA9PT0gdW5kZWZpbmVkICYmIGRlZiAhPT0gdW5kZWZpbmVkKSB7XG5cdCAgICAgICAgb3V0cHV0ID0gZGVmO1xuXHQgICAgICB9IGVsc2UgaWYgKG91dHB1dCA9PT0gdW5kZWZpbmVkKSB7XG5cdCAgICAgICAgdGhyb3cgbmV3IEVycm9yKCdLZXlFcnJvcicpO1xuXHQgICAgICB9IGVsc2Uge1xuXHQgICAgICAgIGRlbGV0ZSB0aGlzW2tleV07XG5cdCAgICAgIH1cblx0ICAgICAgcmV0dXJuIG91dHB1dDtcblx0ICAgIH0sXG5cdCAgICBwb3BpdGVtOiBmdW5jdGlvbigpIHtcblx0ICAgICAgZm9yICh2YXIgayBpbiB0aGlzKSB7XG5cdCAgICAgICAgLy8gUmV0dXJuIHRoZSBmaXJzdCBvYmplY3QgcGFpci5cblx0ICAgICAgICB2YXIgdmFsID0gdGhpc1trXTtcblx0ICAgICAgICBkZWxldGUgdGhpc1trXTtcblx0ICAgICAgICByZXR1cm4gW2ssIHZhbF07XG5cdCAgICAgIH1cblx0ICAgICAgdGhyb3cgbmV3IEVycm9yKCdLZXlFcnJvcicpO1xuXHQgICAgfSxcblx0ICAgIHNldGRlZmF1bHQ6IGZ1bmN0aW9uKGtleSwgZGVmKSB7XG5cdCAgICAgIGlmIChrZXkgaW4gdGhpcykge1xuXHQgICAgICAgIHJldHVybiB0aGlzW2tleV07XG5cdCAgICAgIH1cblx0ICAgICAgaWYgKGRlZiA9PT0gdW5kZWZpbmVkKSB7XG5cdCAgICAgICAgZGVmID0gbnVsbDtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gdGhpc1trZXldID0gZGVmO1xuXHQgICAgfSxcblx0ICAgIHVwZGF0ZTogZnVuY3Rpb24oa3dhcmdzKSB7XG5cdCAgICAgIGZvciAodmFyIGsgaW4ga3dhcmdzKSB7XG5cdCAgICAgICAgdGhpc1trXSA9IGt3YXJnc1trXTtcblx0ICAgICAgfVxuXHQgICAgICByZXR1cm4gbnVsbDsgIC8vIEFsd2F5cyByZXR1cm5zIE5vbmVcblx0ICAgIH1cblx0ICB9O1xuXHQgIE9CSkVDVF9NRU1CRVJTLml0ZXJpdGVtcyA9IE9CSkVDVF9NRU1CRVJTLml0ZW1zO1xuXHQgIE9CSkVDVF9NRU1CRVJTLml0ZXJ2YWx1ZXMgPSBPQkpFQ1RfTUVNQkVSUy52YWx1ZXM7XG5cdCAgT0JKRUNUX01FTUJFUlMuaXRlcmtleXMgPSBPQkpFQ1RfTUVNQkVSUy5rZXlzO1xuXHQgIHJ1bnRpbWUubWVtYmVyTG9va3VwID0gZnVuY3Rpb24ob2JqLCB2YWwsIGF1dG9lc2NhcGUpIHsgLy8ganNoaW50IGlnbm9yZTpsaW5lXG5cdCAgICBvYmogPSBvYmogfHwge307XG5cblx0ICAgIC8vIElmIHRoZSBvYmplY3QgaXMgYW4gb2JqZWN0LCByZXR1cm4gYW55IG9mIHRoZSBtZXRob2RzIHRoYXQgUHl0aG9uIHdvdWxkXG5cdCAgICAvLyBvdGhlcndpc2UgcHJvdmlkZS5cblx0ICAgIGlmIChsaWIuaXNBcnJheShvYmopICYmIEFSUkFZX01FTUJFUlMuaGFzT3duUHJvcGVydHkodmFsKSkge1xuXHQgICAgICByZXR1cm4gZnVuY3Rpb24oKSB7cmV0dXJuIEFSUkFZX01FTUJFUlNbdmFsXS5hcHBseShvYmosIGFyZ3VtZW50cyk7fTtcblx0ICAgIH1cblxuXHQgICAgaWYgKGxpYi5pc09iamVjdChvYmopICYmIE9CSkVDVF9NRU1CRVJTLmhhc093blByb3BlcnR5KHZhbCkpIHtcblx0ICAgICAgcmV0dXJuIGZ1bmN0aW9uKCkge3JldHVybiBPQkpFQ1RfTUVNQkVSU1t2YWxdLmFwcGx5KG9iaiwgYXJndW1lbnRzKTt9O1xuXHQgICAgfVxuXG5cdCAgICByZXR1cm4gb3JpZ19tZW1iZXJMb29rdXAuYXBwbHkodGhpcywgYXJndW1lbnRzKTtcblx0ICB9O1xuXHR9XG5cblx0bW9kdWxlLmV4cG9ydHMgPSBpbnN0YWxsQ29tcGF0O1xuXG5cbi8qKiovIH1cbi8qKioqKiovIF0pO1xuXG4vKioqIEVYUE9SVFMgRlJPTSBleHBvcnRzLWxvYWRlciAqKiovXG5tb2R1bGUuZXhwb3J0cyA9IG51bmp1Y2tzO1xuXG5cbi8qKioqKioqKioqKioqKioqKlxuICoqIFdFQlBBQ0sgRk9PVEVSXG4gKiogLi9+L2V4cG9ydHMtbG9hZGVyP251bmp1Y2tzIS4vfi9udW5qdWNrcy9icm93c2VyL251bmp1Y2tzLXNsaW0uanNcbiAqKiBtb2R1bGUgaWQgPSA5XG4gKiogbW9kdWxlIGNodW5rcyA9IDBcbiAqKi8iLCJtb2R1bGUuZXhwb3J0cyA9IGZ1bmN0aW9uKGVudil7XG4gICAgZnVuY3Rpb24gcGFyc2UgKHBhcnNlciwgbm9kZXMsIGxleGVyKSB7XG4gICAgICAgIHZhciB0b2sgPSBwYXJzZXIubmV4dFRva2VuKCk7XG4gICAgICAgIGtleSA9IHBhcnNlci5wYXJzZVNpZ25hdHVyZShudWxsLCB0cnVlKTtcbiAgICAgICAgcGFyc2VyLmFkdmFuY2VBZnRlckJsb2NrRW5kKHRvay52YWx1ZSk7XG4gICAgICAgIHJldHVybiBuZXcgbm9kZXMuQ2FsbEV4dGVuc2lvbih0aGlzLCAncnVuJywga2V5KTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBUcmFuc2xhdGlvbiAoKSB7XG4gICAgICAgIHRoaXMudGFncyA9IFsndHJhbnMnXTtcbiAgICAgICAgdGhpcy5wYXJzZSA9IHBhcnNlO1xuICAgICAgICB0aGlzLnJ1biA9IGZ1bmN0aW9uIChjdHgsIGtleSkge1xuICAgICAgICAgICAgcmV0dXJuIGtleTtcbiAgICAgICAgfTtcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBJZ25vcmUgKCkge1xuICAgICAgICB0aGlzLnRhZ3MgPSBbJ2xvYWQnXTtcbiAgICAgICAgdGhpcy5wYXJzZSA9IHBhcnNlO1xuICAgICAgICB0aGlzLnJ1biA9IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAgIHJldHVybiAnJztcbiAgICAgICAgfTtcbiAgICB9XG5cbiAgICBlbnYuYWRkRXh0ZW5zaW9uKCd0cmFuc2xhdGlvbicsIG5ldyBUcmFuc2xhdGlvbigpKTtcbiAgICBlbnYuYWRkRXh0ZW5zaW9uKCdwYXNzVGhyb3VnaCcsIG5ldyBJZ25vcmUoKSk7XG59XG5cblxuXG4vKioqKioqKioqKioqKioqKipcbiAqKiBXRUJQQUNLIEZPT1RFUlxuICoqIC4vbnVuanVja3MuY29uZmlnLmpzXG4gKiogbW9kdWxlIGlkID0gMTBcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIm1vZHVsZS5leHBvcnRzID0gZnVuY3Rpb24gKG51bmp1Y2tzLCBlbnYsIG9iaiwgZGVwZW5kZW5jaWVzKXtcblxuICAgIHZhciBvbGRSb290ID0gb2JqLnJvb3Q7XG5cbiAgICBvYmoucm9vdCA9IGZ1bmN0aW9uKCBlbnYsIGNvbnRleHQsIGZyYW1lLCBydW50aW1lLCBpZ25vcmVNaXNzaW5nLCBjYiApIHtcbiAgICAgICAgdmFyIG9sZEdldFRlbXBsYXRlID0gZW52LmdldFRlbXBsYXRlO1xuICAgICAgICBlbnYuZ2V0VGVtcGxhdGUgPSBmdW5jdGlvbiAobmFtZSwgZWMsIHBhcmVudE5hbWUsIGlnbm9yZU1pc3NpbmcsIGNiKSB7XG4gICAgICAgICAgICBpZiggdHlwZW9mIGVjID09PSBcImZ1bmN0aW9uXCIgKSB7XG4gICAgICAgICAgICAgICAgY2IgPSBlYyA9IGZhbHNlO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgdmFyIF9yZXF1aXJlID0gZnVuY3Rpb24gKG5hbWUpIHtcbiAgICAgICAgICAgICAgICB0cnkge1xuICAgICAgICAgICAgICAgICAgICAvLyBhZGQgYSByZWZlcmVuY2UgdG8gdGhlIGFscmVhZHkgcmVzb2x2ZWQgZGVwZW5kZW5jeSBoZXJlXG4gICAgICAgICAgICAgICAgICAgIHJldHVybiBkZXBlbmRlbmNpZXNbbmFtZV07XG4gICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIGNhdGNoIChlKSB7XG4gICAgICAgICAgICAgICAgICAgIGlmIChmcmFtZS5nZXQoXCJfcmVxdWlyZVwiKSkge1xuICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIGZyYW1lLmdldChcIl9yZXF1aXJlXCIpKG5hbWUpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGVsc2Uge1xuICAgICAgICAgICAgICAgICAgICAgICAgY29uc29sZS53YXJuKCdDb3VsZCBub3QgbG9hZCB0ZW1wbGF0ZSBcIiVzXCInLCBuYW1lKTtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgIH07XG5cbiAgICAgICAgICAgIHZhciB0bXBsID0gX3JlcXVpcmUobmFtZSk7XG4gICAgICAgICAgICBmcmFtZS5zZXQoXCJfcmVxdWlyZVwiLCBfcmVxdWlyZSk7XG5cbiAgICAgICAgICAgIGlmKCBlYyApIHRtcGwuY29tcGlsZSgpO1xuICAgICAgICAgICAgY2IoIG51bGwsIHRtcGwgKTtcbiAgICAgICAgfTtcblxuICAgICAgICBvbGRSb290KGVudiwgY29udGV4dCwgZnJhbWUsIHJ1bnRpbWUsIGlnbm9yZU1pc3NpbmcsIGZ1bmN0aW9uIChlcnIsIHJlcykge1xuICAgICAgICAgICAgZW52LmdldFRlbXBsYXRlID0gb2xkR2V0VGVtcGxhdGU7XG4gICAgICAgICAgICBjYiggZXJyLCByZXMgKTtcbiAgICAgICAgfSk7XG4gICAgfTtcblxuICAgIHZhciBzcmMgPSB7XG4gICAgICAgIG9iajogb2JqLFxuICAgICAgICB0eXBlOiAnY29kZSdcbiAgICB9O1xuXG4gICAgcmV0dXJuIG5ldyBudW5qdWNrcy5UZW1wbGF0ZShzcmMsIGVudik7XG5cbn07XG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL34vbnVuanVja3MtbG9hZGVyL3J1bnRpbWUtc2hpbS5qc1xuICoqIG1vZHVsZSBpZCA9IDExXG4gKiogbW9kdWxlIGNodW5rcyA9IDBcbiAqKi8iLCJ2YXIgbnVuanVja3MgPSByZXF1aXJlKFwiZXhwb3J0cz9udW5qdWNrcyFudW5qdWNrcy9icm93c2VyL251bmp1Y2tzLXNsaW1cIik7XG52YXIgZW52O1xuaWYgKCFudW5qdWNrcy5jdXJyZW50RW52KXtcblx0ZW52ID0gbnVuanVja3MuY3VycmVudEVudiA9IG5ldyBudW5qdWNrcy5FbnZpcm9ubWVudChbXSwgeyBhdXRvZXNjYXBlOiB0cnVlIH0pO1xufSBlbHNlIHtcblx0ZW52ID0gbnVuanVja3MuY3VycmVudEVudjtcbn1cbnZhciBjb25maWd1cmUgPSByZXF1aXJlKFwiLi4vLi4vLi4vLi4vLi4vbnVuanVja3MuY29uZmlnLmpzXCIpKGVudik7XG52YXIgZGVwZW5kZW5jaWVzID0gbnVuanVja3Mud2VicGFja0RlcGVuZGVuY2llcyB8fCAobnVuanVja3Mud2VicGFja0RlcGVuZGVuY2llcyA9IHt9KTtcblxuXG5cblxudmFyIHNoaW0gPSByZXF1aXJlKFwiL1VzZXJzL2Rhbi9zbGF0ZS9jb3Npbm51cy1jb3JlL25vZGVfbW9kdWxlcy9udW5qdWNrcy1sb2FkZXIvcnVudGltZS1zaGltXCIpO1xuXG5cbihmdW5jdGlvbigpIHsobnVuanVja3MubnVuanVja3NQcmVjb21waWxlZCA9IG51bmp1Y2tzLm51bmp1Y2tzUHJlY29tcGlsZWQgfHwge30pW1wiY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC9tYXAvbWFwLWNvbnRyb2xzLmh0bWxcIl0gPSAoZnVuY3Rpb24oKSB7XG5mdW5jdGlvbiByb290KGVudiwgY29udGV4dCwgZnJhbWUsIHJ1bnRpbWUsIGNiKSB7XG52YXIgbGluZW5vID0gbnVsbDtcbnZhciBjb2xubyA9IG51bGw7XG52YXIgb3V0cHV0ID0gXCJcIjtcbnRyeSB7XG52YXIgcGFyZW50VGVtcGxhdGUgPSBudWxsO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShlbnYuZ2V0RXh0ZW5zaW9uKFwicGFzc1Rocm91Z2hcIilbXCJydW5cIl0oY29udGV4dCxydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcImkxOG5cIikpLCB0cnVlICYmIGVudi5vcHRzLmF1dG9lc2NhcGUpO1xub3V0cHV0ICs9IFwiXFxuPGZvcm0gaWQ9XFxcIm1hcC1zZWFyY2hcXFwiPlxcbiAgICA8ZGl2IGNsYXNzPVxcXCJsaW5lXFxcIj5cXG4gICAgICAgIDxkaXYgY2xhc3M9XFxcInJlc3VsdC1maWx0ZXIgY2hlY2sgcGVvcGxlXFxcIiBkYXRhLXJlc3VsdC10eXBlPVxcXCJwZW9wbGVcXFwiPlxcbiAgICAgICAgICAgIDxkaXYgY2xhc3M9XFxcImJveFxcXCI+XFxuICAgICAgICAgICAgICAgIFwiO1xuaWYocnVudGltZS5tZW1iZXJMb29rdXAoKHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXAoY29udGV4dCwgZnJhbWUsIFwiZmlsdGVyc1wiKSksXCJwZW9wbGVcIikpIHtcbm91dHB1dCArPSBcIlxcbiAgICAgICAgICAgICAgICAgICAgPGkgY2xhc3M9XFxcImZhIGZhLWNoZWNrXFxcIj48L2k+XFxuICAgICAgICAgICAgICAgIFwiO1xuO1xufVxub3V0cHV0ICs9IFwiXFxuICAgICAgICAgICAgPC9kaXY+XFxuICAgICAgICAgICAgPGRpdiBjbGFzcz1cXFwiY2hlY2tfX2xhYmVsXFxcIj5cIjtcbm91dHB1dCArPSBydW50aW1lLnN1cHByZXNzVmFsdWUoZW52LmdldEV4dGVuc2lvbihcInRyYW5zbGF0aW9uXCIpW1wicnVuXCJdKGNvbnRleHQsXCJQZW9wbGVcIiksIHRydWUgJiYgZW52Lm9wdHMuYXV0b2VzY2FwZSk7XG5vdXRwdXQgKz0gXCI8L2Rpdj5cXG4gICAgICAgIDwvZGl2PlxcbiAgICA8L2Rpdj5cXG5cXG4gICAgPGRpdiBjbGFzcz1cXFwibGluZVxcXCI+XFxuICAgICAgICA8ZGl2IGNsYXNzPVxcXCJyZXN1bHQtZmlsdGVyIGNoZWNrIGV2ZW50c1xcXCIgZGF0YS1yZXN1bHQtdHlwZT1cXFwiZXZlbnRzXFxcIj5cXG4gICAgICAgICAgICA8ZGl2IGNsYXNzPVxcXCJib3hcXFwiPlxcbiAgICAgICAgICAgICAgICBcIjtcbmlmKHJ1bnRpbWUubWVtYmVyTG9va3VwKChydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcImZpbHRlcnNcIikpLFwiZXZlbnRzXCIpKSB7XG5vdXRwdXQgKz0gXCJcXG4gICAgICAgICAgICAgICAgICAgIDxpIGNsYXNzPVxcXCJmYSBmYS1jaGVja1xcXCI+PC9pPlxcbiAgICAgICAgICAgICAgICBcIjtcbjtcbn1cbm91dHB1dCArPSBcIlxcbiAgICAgICAgICAgIDwvZGl2PlxcbiAgICAgICAgICAgIDxkaXYgY2xhc3M9XFxcImNoZWNrX19sYWJlbFxcXCI+XCI7XG5vdXRwdXQgKz0gcnVudGltZS5zdXBwcmVzc1ZhbHVlKGVudi5nZXRFeHRlbnNpb24oXCJ0cmFuc2xhdGlvblwiKVtcInJ1blwiXShjb250ZXh0LFwiRXZlbnRzXCIpLCB0cnVlICYmIGVudi5vcHRzLmF1dG9lc2NhcGUpO1xub3V0cHV0ICs9IFwiPC9kaXY+XFxuICAgICAgICA8L2Rpdj5cXG4gICAgPC9kaXY+XFxuXFxuICAgIDxkaXYgY2xhc3M9XFxcImxpbmVcXFwiPlxcbiAgICAgICAgPGRpdiBjbGFzcz1cXFwicmVzdWx0LWZpbHRlciBjaGVjayBwcm9qZWN0c1xcXCIgZGF0YS1yZXN1bHQtdHlwZT1cXFwicHJvamVjdHNcXFwiPlxcbiAgICAgICAgICAgIDxkaXYgY2xhc3M9XFxcImJveFxcXCI+XFxuICAgICAgICAgICAgICAgIFwiO1xuaWYocnVudGltZS5tZW1iZXJMb29rdXAoKHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXAoY29udGV4dCwgZnJhbWUsIFwiZmlsdGVyc1wiKSksXCJwcm9qZWN0c1wiKSkge1xub3V0cHV0ICs9IFwiXFxuICAgICAgICAgICAgICAgICAgICA8aSBjbGFzcz1cXFwiZmEgZmEtY2hlY2tcXFwiPjwvaT5cXG4gICAgICAgICAgICAgICAgXCI7XG47XG59XG5vdXRwdXQgKz0gXCJcXG4gICAgICAgICAgICA8L2Rpdj5cXG4gICAgICAgICAgICA8ZGl2IGNsYXNzPVxcXCJjaGVja19fbGFiZWxcXFwiPlwiO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShlbnYuZ2V0RXh0ZW5zaW9uKFwidHJhbnNsYXRpb25cIilbXCJydW5cIl0oY29udGV4dCxcIlByb2plY3RzXCIpLCB0cnVlICYmIGVudi5vcHRzLmF1dG9lc2NhcGUpO1xub3V0cHV0ICs9IFwiPC9kaXY+XFxuICAgICAgICA8L2Rpdj5cXG4gICAgPC9kaXY+XFxuXFxuICAgIDxkaXYgY2xhc3M9XFxcImxpbmVcXFwiPlxcbiAgICAgICAgPGRpdiBjbGFzcz1cXFwicmVzdWx0LWZpbHRlciBjaGVjayBncm91cHNcXFwiIGRhdGEtcmVzdWx0LXR5cGU9XFxcImdyb3Vwc1xcXCI+XFxuICAgICAgICAgICAgPGRpdiBjbGFzcz1cXFwiYm94XFxcIj5cXG4gICAgICAgICAgICAgICAgXCI7XG5pZihydW50aW1lLm1lbWJlckxvb2t1cCgocnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgXCJmaWx0ZXJzXCIpKSxcImdyb3Vwc1wiKSkge1xub3V0cHV0ICs9IFwiXFxuICAgICAgICAgICAgICAgICAgICA8aSBjbGFzcz1cXFwiZmEgZmEtY2hlY2tcXFwiPjwvaT5cXG4gICAgICAgICAgICAgICAgXCI7XG47XG59XG5vdXRwdXQgKz0gXCJcXG4gICAgICAgICAgICA8L2Rpdj5cXG4gICAgICAgICAgICA8ZGl2IGNsYXNzPVxcXCJjaGVja19fbGFiZWxcXFwiPlwiO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShlbnYuZ2V0RXh0ZW5zaW9uKFwidHJhbnNsYXRpb25cIilbXCJydW5cIl0oY29udGV4dCxcIkdyb3Vwc1wiKSwgdHJ1ZSAmJiBlbnYub3B0cy5hdXRvZXNjYXBlKTtcbm91dHB1dCArPSBcIjwvZGl2PlxcbiAgICAgICAgPC9kaXY+XFxuICAgIDwvZGl2PlxcblxcbiAgICA8ZGl2IGNsYXNzPVxcXCJsaW5lIGxpbmtcXFwiPlxcbiAgICAgICAgXCI7XG5pZighcnVudGltZS5tZW1iZXJMb29rdXAoKHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXAoY29udGV4dCwgZnJhbWUsIFwiZmlsdGVyc1wiKSksXCJwZW9wbGVcIikgfHwgIXJ1bnRpbWUubWVtYmVyTG9va3VwKChydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcImZpbHRlcnNcIikpLFwiZXZlbnRzXCIpIHx8ICFydW50aW1lLm1lbWJlckxvb2t1cCgocnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgXCJmaWx0ZXJzXCIpKSxcInByb2plY3RzXCIpIHx8ICFydW50aW1lLm1lbWJlckxvb2t1cCgocnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgXCJmaWx0ZXJzXCIpKSxcImdyb3Vwc1wiKSkge1xub3V0cHV0ICs9IFwiXFxuICAgICAgICAgICAgPGEgaHJlZj1cXFwiI1xcXCIgY2xhc3M9XFxcInJlc2V0LWZpbHRlcnNcXFwiPlxcbiAgICAgICAgICAgICAgICBBbGxlIGFuemVpZ2VuXFxuICAgICAgICAgICAgPC9hPlxcbiAgICAgICAgXCI7XG47XG59XG5lbHNlIHtcbm91dHB1dCArPSBcIlxcbiAgICAgICAgICAgICZuYnNwO1xcbiAgICAgICAgXCI7XG47XG59XG5vdXRwdXQgKz0gXCJcXG4gICAgPC9kaXY+XFxuXFxuICAgIDxkaXYgY2xhc3M9XFxcImxpbmUgdGV4dC1maWVsZFxcXCI+XFxuICAgICAgICA8aW5wdXQgdHlwZT1cXFwidGV4dFxcXCIgY2xhc3M9XFxcInFcXFwiIG5hbWU9XFxcInFcXFwiIHBsYWNlaG9sZGVyPVxcXCJTdWNoZVxcXCIgdmFsdWU9XFxcIlwiO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcInFcIiksIGVudi5vcHRzLmF1dG9lc2NhcGUpO1xub3V0cHV0ICs9IFwiXFxcIiAvPlxcbiAgICAgICAgPGkgY2xhc3M9XFxcImZhIGZhLXNlYXJjaCBpY29uLXNlYXJjaFxcXCI+PC9pPlxcbiAgICAgICAgPGRpdiBjbGFzcz1cXFwiaWNvbi1sb2FkaW5nIHNrLWRvdWJsZS1ib3VuY2VcXFwiPlxcbiAgICAgICAgICAgIDxkaXYgY2xhc3M9XFxcInNrLWNoaWxkIHNrLWRvdWJsZS1ib3VuY2UxXFxcIj48L2Rpdj5cXG4gICAgICAgICAgICA8ZGl2IGNsYXNzPVxcXCJzay1jaGlsZCBzay1kb3VibGUtYm91bmNlMlxcXCI+PC9kaXY+XFxuICAgICAgICA8L2Rpdj5cXG4gICAgPC9kaXY+XFxuXFxuICAgIDxkaXYgY2xhc3M9XFxcIm1lc3NhZ2VcXFwiPjwvZGl2PlxcbjwvZm9ybT5cXG5cXG48ZGl2IGNsYXNzPVxcXCJsaW5lIGJ1dHRvblxcXCI+XFxuICAgIDxkaXYgZGF0YS1sYXllcj1cXFwic3RyZWV0XFxcIlxcbiAgICAgICAgY2xhc3M9XFxcImJ0biBsYXllci1idXR0b24gXCI7XG5pZihydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcImxheWVyXCIpID09IFwic3RyZWV0XCIpIHtcbm91dHB1dCArPSBcIiBhY3RpdmUgXCI7XG47XG59XG5vdXRwdXQgKz0gXCJcXFwiPlxcbiAgICAgICAgU3RyZWV0XFxuICAgIDwvZGl2PlxcblxcbiAgICA8ZGl2IGRhdGEtbGF5ZXI9XFxcInNhdGVsbGl0ZVxcXCJcXG4gICAgICAgIGNsYXNzPVxcXCJidG4gbGF5ZXItYnV0dG9uIFwiO1xuaWYocnVudGltZS5jb250ZXh0T3JGcmFtZUxvb2t1cChjb250ZXh0LCBmcmFtZSwgXCJsYXllclwiKSA9PSBcInNhdGVsbGl0ZVwiKSB7XG5vdXRwdXQgKz0gXCIgYWN0aXZlIFwiO1xuO1xufVxub3V0cHV0ICs9IFwiXFxcIj5cXG4gICAgICAgIFNhdGVsbGl0ZVxcbiAgICA8L2Rpdj5cXG5cXG4gICAgPGRpdiBkYXRhLWxheWVyPVxcXCJ0ZXJyYWluXFxcIlxcbiAgICAgICAgY2xhc3M9XFxcImJ0biBsYXllci1idXR0b24gXCI7XG5pZihydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcImxheWVyXCIpID09IFwidGVycmFpblwiKSB7XG5vdXRwdXQgKz0gXCIgYWN0aXZlIFwiO1xuO1xufVxub3V0cHV0ICs9IFwiXFxcIj5cXG4gICAgICAgIFRlcnJhaW5cXG4gICAgPC9kaXY+XFxuPC9kaXY+XFxuXCI7XG5pZihwYXJlbnRUZW1wbGF0ZSkge1xucGFyZW50VGVtcGxhdGUucm9vdFJlbmRlckZ1bmMoZW52LCBjb250ZXh0LCBmcmFtZSwgcnVudGltZSwgY2IpO1xufSBlbHNlIHtcbmNiKG51bGwsIG91dHB1dCk7XG59XG47XG59IGNhdGNoIChlKSB7XG4gIGNiKHJ1bnRpbWUuaGFuZGxlRXJyb3IoZSwgbGluZW5vLCBjb2xubykpO1xufVxufVxucmV0dXJuIHtcbnJvb3Q6IHJvb3Rcbn07XG5cbn0pKCk7XG59KSgpO1xuXG5cblxubW9kdWxlLmV4cG9ydHMgPSBzaGltKG51bmp1Y2tzLCBlbnYsIG51bmp1Y2tzLm51bmp1Y2tzUHJlY29tcGlsZWRbXCJjb3Npbm51cy90ZW1wbGF0ZXMvY29zaW5udXMvdW5pdmVyc2FsL21hcC9tYXAtY29udHJvbHMuaHRtbFwiXSAsIGRlcGVuZGVuY2llcylcblxuXG4vKioqKioqKioqKioqKioqKipcbiAqKiBXRUJQQUNLIEZPT1RFUlxuICoqIC4vY29zaW5udXMvdGVtcGxhdGVzL2Nvc2lubnVzL3VuaXZlcnNhbC9tYXAvbWFwLWNvbnRyb2xzLmh0bWxcbiAqKiBtb2R1bGUgaWQgPSAxMlxuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIiwidmFyIG51bmp1Y2tzID0gcmVxdWlyZShcImV4cG9ydHM/bnVuanVja3MhbnVuanVja3MvYnJvd3Nlci9udW5qdWNrcy1zbGltXCIpO1xudmFyIGVudjtcbmlmICghbnVuanVja3MuY3VycmVudEVudil7XG5cdGVudiA9IG51bmp1Y2tzLmN1cnJlbnRFbnYgPSBuZXcgbnVuanVja3MuRW52aXJvbm1lbnQoW10sIHsgYXV0b2VzY2FwZTogdHJ1ZSB9KTtcbn0gZWxzZSB7XG5cdGVudiA9IG51bmp1Y2tzLmN1cnJlbnRFbnY7XG59XG52YXIgY29uZmlndXJlID0gcmVxdWlyZShcIi4uLy4uLy4uLy4uLy4uL251bmp1Y2tzLmNvbmZpZy5qc1wiKShlbnYpO1xudmFyIGRlcGVuZGVuY2llcyA9IG51bmp1Y2tzLndlYnBhY2tEZXBlbmRlbmNpZXMgfHwgKG51bmp1Y2tzLndlYnBhY2tEZXBlbmRlbmNpZXMgPSB7fSk7XG5cblxuXG5cbnZhciBzaGltID0gcmVxdWlyZShcIi9Vc2Vycy9kYW4vc2xhdGUvY29zaW5udXMtY29yZS9ub2RlX21vZHVsZXMvbnVuanVja3MtbG9hZGVyL3J1bnRpbWUtc2hpbVwiKTtcblxuXG4oZnVuY3Rpb24oKSB7KG51bmp1Y2tzLm51bmp1Y2tzUHJlY29tcGlsZWQgPSBudW5qdWNrcy5udW5qdWNrc1ByZWNvbXBpbGVkIHx8IHt9KVtcImNvc2lubnVzL3RlbXBsYXRlcy9jb3Npbm51cy91bml2ZXJzYWwvbWFwL3BvcHVwLmh0bWxcIl0gPSAoZnVuY3Rpb24oKSB7XG5mdW5jdGlvbiByb290KGVudiwgY29udGV4dCwgZnJhbWUsIHJ1bnRpbWUsIGNiKSB7XG52YXIgbGluZW5vID0gbnVsbDtcbnZhciBjb2xubyA9IG51bGw7XG52YXIgb3V0cHV0ID0gXCJcIjtcbnRyeSB7XG52YXIgcGFyZW50VGVtcGxhdGUgPSBudWxsO1xub3V0cHV0ICs9IFwiPGRpdiBjbGFzcz1cXFwicG9wdXBcXFwiPlxcbiAgICA8aW1nIHNyYz1cXFwiXCI7XG5vdXRwdXQgKz0gcnVudGltZS5zdXBwcmVzc1ZhbHVlKHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXAoY29udGV4dCwgZnJhbWUsIFwiaW1hZ2VVUkxcIiksIGVudi5vcHRzLmF1dG9lc2NhcGUpO1xub3V0cHV0ICs9IFwiXFxcIiAvPlxcbiAgICA8ZGl2IGNsYXNzPVxcXCJkZXRhaWxzXFxcIj5cXG4gICAgICAgIDxkaXYgY2xhc3M9XFxcImxpbmtcXFwiPlxcbiAgICAgICAgICAgIDxhIGhyZWY9XFxcIlwiO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcInVybFwiKSwgZW52Lm9wdHMuYXV0b2VzY2FwZSk7XG5vdXRwdXQgKz0gXCJcXFwiPlwiO1xub3V0cHV0ICs9IHJ1bnRpbWUuc3VwcHJlc3NWYWx1ZShydW50aW1lLmNvbnRleHRPckZyYW1lTG9va3VwKGNvbnRleHQsIGZyYW1lLCBcInRpdGxlXCIpLCBlbnYub3B0cy5hdXRvZXNjYXBlKTtcbm91dHB1dCArPSBcIjwvYT5cXG4gICAgICAgIDwvZGl2PlxcbiAgICAgICAgPGRpdiBjbGFzcz1cXFwiYWRkcmVzc1xcXCI+XCI7XG5vdXRwdXQgKz0gcnVudGltZS5zdXBwcmVzc1ZhbHVlKHJ1bnRpbWUuY29udGV4dE9yRnJhbWVMb29rdXAoY29udGV4dCwgZnJhbWUsIFwiYWRkcmVzc1wiKSwgZW52Lm9wdHMuYXV0b2VzY2FwZSk7XG5vdXRwdXQgKz0gXCI8L2Rpdj5cXG4gICAgPC9kaXY+XFxuPC9kaXY+XFxuXCI7XG5pZihwYXJlbnRUZW1wbGF0ZSkge1xucGFyZW50VGVtcGxhdGUucm9vdFJlbmRlckZ1bmMoZW52LCBjb250ZXh0LCBmcmFtZSwgcnVudGltZSwgY2IpO1xufSBlbHNlIHtcbmNiKG51bGwsIG91dHB1dCk7XG59XG47XG59IGNhdGNoIChlKSB7XG4gIGNiKHJ1bnRpbWUuaGFuZGxlRXJyb3IoZSwgbGluZW5vLCBjb2xubykpO1xufVxufVxucmV0dXJuIHtcbnJvb3Q6IHJvb3Rcbn07XG5cbn0pKCk7XG59KSgpO1xuXG5cblxubW9kdWxlLmV4cG9ydHMgPSBzaGltKG51bmp1Y2tzLCBlbnYsIG51bmp1Y2tzLm51bmp1Y2tzUHJlY29tcGlsZWRbXCJjb3Npbm51cy90ZW1wbGF0ZXMvY29zaW5udXMvdW5pdmVyc2FsL21hcC9wb3B1cC5odG1sXCJdICwgZGVwZW5kZW5jaWVzKVxuXG5cbi8qKioqKioqKioqKioqKioqKlxuICoqIFdFQlBBQ0sgRk9PVEVSXG4gKiogLi9jb3Npbm51cy90ZW1wbGF0ZXMvY29zaW5udXMvdW5pdmVyc2FsL21hcC9wb3B1cC5odG1sXG4gKiogbW9kdWxlIGlkID0gMTNcbiAqKiBtb2R1bGUgY2h1bmtzID0gMFxuICoqLyIsIid1c2Ugc3RyaWN0JztcblxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgcHJvdG9jb2w6IGZ1bmN0aW9uICgpIHtcbiAgICAgICAgcmV0dXJuIHdpbmRvdy5sb2NhdGlvbi5wcm90b2NvbDtcbiAgICB9XG59O1xuXG5cblxuLyoqKioqKioqKioqKioqKioqXG4gKiogV0VCUEFDSyBGT09URVJcbiAqKiAuL2Nvc2lubnVzL2NsaWVudC9saWIvdXRpbC5qc1xuICoqIG1vZHVsZSBpZCA9IDE0XG4gKiogbW9kdWxlIGNodW5rcyA9IDBcbiAqKi8iLCIndXNlIHN0cmljdCc7XG5cbi8vIFB1Yi1zdWIgZXZlbnQgbWVkaWF0b3IgYW5kICBkYXRhIHN0b3JlLlxubW9kdWxlLmV4cG9ydHMgPSB7XG4gICAgcHVibGlzaDogZnVuY3Rpb24gKGV2ZW50TmFtZSwgZGF0YSkge1xuICAgICAgICAkKCdodG1sJykudHJpZ2dlcihldmVudE5hbWUsIGRhdGEpO1xuICAgIH0sXG5cbiAgICBzdWJzY3JpYmU6IGZ1bmN0aW9uIChldmVudHMsIGRhdGEsIGhhbmRsZXIpIHtcbiAgICAgICAgJCgnaHRtbCcpLm9uKGV2ZW50cywgZGF0YSwgaGFuZGxlcik7XG4gICAgfVxufTtcblxuXG5cbi8qKioqKioqKioqKioqKioqKlxuICoqIFdFQlBBQ0sgRk9PVEVSXG4gKiogLi9jb3Npbm51cy9jbGllbnQvbWVkaWF0b3IuanNcbiAqKiBtb2R1bGUgaWQgPSAxNVxuICoqIG1vZHVsZSBjaHVua3MgPSAwXG4gKiovIl0sInNvdXJjZVJvb3QiOiIifQ==