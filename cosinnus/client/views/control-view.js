'use strict';

var ContentControlView = require('views/base/content-control-view');
var ErrorView = require('views/error-view');
var util = require('lib/util.js');

module.exports = ContentControlView.extend({
	
	App: null,
	
	template: require('map/map-controls'),
	
	// will be set to self.options during initialization
	defaults: {
        availableFilters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        activeFilters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        topicsHtml: '',
        controlsEnabled: true,
        filterGroup: null,
        
        // in fullscreen mode, this must always be the base URL we started at
        basePageURL: '/map/',
        
        // will be set to self.state during initialization
    	state: {
    		// current query
    		q: '',
    		topicsVisible: false,
			activeTopicIds: null,
			wantsToSearch: false,
			searching: false,
			searchResultLimit: 400,
    	}
    },
    
    searchEndpointURL: '/maps/search/',
    searchDelay: 400,
    whileSearchingDelay: 5000,
	
    
    initialize: function (options, app) {
    	var self = this;
    	// this calls self.initializeSearchParameters()
    	ContentControlView.prototype.initialize.call(self, options);
    	
    	self.App = app;
    	Backbone.mediator.subscribe('want:search', self.handleStartSearch, self);
    	Backbone.mediator.subscribe('end:search', self.handleEndSearch, self);
    	Backbone.mediator.subscribe('change:controls', self.render, self);
    	Backbone.mediator.subscribe('error:search', self.handleXhrError, self);
    	Backbone.mediator.subscribe('app:ready', self.handleAppReady, self);
    	Backbone.mediator.subscribe('app:stale-results', self.handleStaleResults, self);
    	
    	util.log('control-view.js: initialized. with self.App=' + self.App)
    	

        if (self.state.activeTopicIds) {
            this.showTopics();
        }
    },

    events: {
        'click .result-filter': 'toggleFilterClicked',
        'click .reset-filters': 'resetFiltersClicked',
        'click .show-topics': 'showTopicsClicked',
        'change #id_topics': 'toggleTopicFilterClicked',
        'focusin .q': 'toggleTyping',
        'focusout .q': 'toggleTyping',
        'keyup .q': 'handleTyping',
        'keydown .q': 'handleKeyDown',
    },

    // Event Handlers
    // --------------

    toggleFilterClicked: function (event) {
        var resultType = $(event.currentTarget).data('result-type');
        this.toggleFilter(resultType);
        this.render();
    },

    resetFiltersClicked: function (event) {
        event.preventDefault();
        this.resetFilters();
        this.render();
    },
    
    showTopicsClicked: function (event) {
        event.preventDefault();
        this.showTopics();
        this.render();
    },

    toggleTopicFilterClicked: function (event) {
        var topic_ids = $(event.currentTarget).val();
        this.toggleTopicFilter(topic_ids);
    },

    toggleTyping: function (event) {
        this.state.typing = !this.state.typing;
        this.$el.find('.icon-search').toggle();
    },

    handleTyping: function (event) {
        if (util.isIgnorableKey(event)) {
            event.preventDefault();
            return false;
        }
        
        var query = $(event.currentTarget).val();
        if (query.length > 2 || query.length === 0) {
            this.state.q = query;
            this.triggerDelayedSearch();
        }
    },
    
    handleKeyDown: function (event) {
        if (event.keyCode == 13) {
            event.preventDefault();
            return false;
        }
    },

    handleStartSearch: function (event) {
        this.$el.find('.icon-search').addClass('hidden');
        this.$el.find('.icon-loading').removeClass('hidden');
    },

    handleEndSearch: function (event) {
        if (!this.state.typing) {
            this.$el.find('.icon-search').removeClass('hidden');
        }
        this.$el.find('.icon-loading').addClass('hidden');
        var $message = this.$el.find('form .message');
        $message.hide();
    },

    handleXhrError: function (event) {
        var $message = this.$el.find('form .message');
        new ErrorView({
            message: 'Ein Fehler ist bei der Suche aufgetreten.',
            el: $message
        }).render();
        $message.show();
    },
    
    /** Called when the App is fully loaded for the first time.
     * 	WARNING: Due to the threaded after_render() method, this may
     * 		currently actually happen before a full load.
     *  */
    handleAppReady: function (event) {
    	util.log('control-view.js: app is ready to search. starting this.search()!')
    	this.search();
    },
    
    /**
     * The context can contain `reason` for a signal for out-of-date result sets:
     * - viewport-changed: The map was scrolled or window was resized
     * - map-navigate: Router navigate on the map (not called during initial navigation)
     * - ...
     */
    handleStaleResults: function (context) {
    	if (context.reason == 'viewport-changed') {
    		util.log('control-view.js: Received signal for stale results bc of viewport change, but doing nothing rn')
    	} else if (context.reason == 'viewport-changed') {
    		util.log('control-view.js: Received signal for stale results bc of map-navigate, but doing nothing rn')
    	}
    	// this.triggerDelayedSearch();
    	// or
    	// this.search();
    },

    afterRender: function () {
        // update topics selector with current topics
        var topics_selector = this.$el.find('#id_topics');
        if (topics_selector.length > 0 && this.state.activeTopicIds) {
            topics_selector.val(this.state.activeTopicIds).select2();
        }
    },
    

    search: function () {
        var self = this;
        var url = self.buildSearchQueryURL(true);
        
        self.state.searching = true;
        $.get(url, function (res) {
            self.state.searching = false;
            Backbone.mediator.publish('end:search');
            // (The search endpoint is single-thread).
            // If there is a queued search, requeue it.
            if (self.state.wantsToSearch) {
                self.triggerDelayedSearch();
            // Update the results if there isn't a queued search.
            } else {
            	// Save the search state in the url.
            	if (App.displayOptions.fullscreen) {
            		util.log('control-view.js: +++++++++++++++++ since we are fullscreen, publishing router URL update!')
            		Backbone.mediator.publish('navigate:router', self.buildSearchQueryURL(false).replace(self.searchEndpointURL, self.options.basePageURL))
            	}
            	alert('control-view.js: TODO: we got the results back! put them in a collection and implement all the "change:results" subscribers!')
                self.set('results', res);
                Backbone.mediator.publish('change:results');
            }
        }).fail(function () {
            self.state.searching = false;
            Backbone.mediator.publish('end:search');
            Backbone.mediator.publish('error:search');
        });
    },
    
    // extended from content-control-view.js
    initializeSearchParameters: function (urlParams) {
        _.extend(this.state, {
            activeFilters: {
                people: util.ifundef(urlParams.people, this.options.activeFilters.people),
                events: util.ifundef(urlParams.events, this.options.activeFilters.events),
                projects: util.ifundef(urlParams.projects, this.options.activeFilters.projects),
                groups: util.ifundef(urlParams.groups, this.options.activeFilters.groups)
            },
            q: util.ifundef(urlParams.q, this.state.q),
            searchResultLimit: util.ifundef(urlParams.limits, this.state.searchResultLimit),
            activeTopicIds: util.ifundef(urlParams.topics, this.state.activeTopicIds)
        });
        util.log('TODO: we need to remove the "limit" param from the router URL, but not from the API call URL!')
    },
    
    // extended from content-control-view.js
    contributeToSearchParameters: function(forAPI) {
        var searchParams = {
            q: this.state.q,
            people: this.state.activeFilters.people,
            events: this.state.activeFilters.events,
            projects: this.state.activeFilters.projects,
            groups: this.state.activeFilters.groups,
        };
        if (this.state.activeTopicIds) {
        	_.extend(searchParams, {
        		topics: this.state.activeTopicIds.join(',')
        	});
        }
        if (forAPI) {
        	_.extend(searchParams, {
        		limit: this.state.searchResultLimit
        	});
        }
        
        util.log('control-view.js: returning search params:')
        util.log(searchParams)
    	return searchParams
    },
    
    /**
     * Build the URL containing all parameters for the current view
     * 
     * @param forAPI: if true, contains all search parameters.
     * 		if false, contains only these that should be visible in the browser URL 
     */
    buildSearchQueryURL: function (forAPI) {
    	// collect all search parameters from content views that affect them
    	var searchParams = {};
    	_.each(this.App.contentViews, function(view){
    		_.extend(searchParams, view.contributeToSearchParameters(forAPI));
    	});
        var query = $.param(searchParams);
        
        var url = this.searchEndpointURL;
        if (this.options.filterGroup) {
            url = url + this.options.filterGroup + '/';
        }
        url = url + '?' + query
        
        util.log(' ************  BUILD SEARCH QUERY URL RETURNED (*** ' + forAPI)
        util.log(url)
        return url;
    },

    toggleFilter: function (resultType) {
        var activeFilters = this.state.activeFilters;
        activeFilters[resultType] = !activeFilters[resultType];
        this.state.activeFilters = activeFilters;
        this.triggerDelayedSearch();
    },

    resetFilters: function () {
        this.state.activeFilters = _(this.options.availableFilters).clone();
        this.triggerDelayedSearch();
    },
    
    showTopics: function () {
        this.state.topicsVisible = true;
    },
    
    toggleTopicFilter: function (topic_ids) {
        this.state.activeTopicIds = topic_ids;
        this.triggerDelayedSearch();
    },

    // Register a change in the controls or the map UI which should queue
    // a search attempt after a delay.
    triggerDelayedSearch: function () {
        var self = this;
            // Increase the search delay when a search is in progress.
        var delay = self.state.searching ?
                self.whileSearchingDelay : self.searchDelay;
        clearTimeout(this.searchTimeout);
        self.state.wantsToSearch = true;
        Backbone.mediator.publish('want:search');
        self.searchTimeout = setTimeout(function () {
            self.search();
            self.state.wantsToSearch = false;
        }, delay);
    },

    activeFilterList: function () {
        return _(_(this.state.activeFilters).keys()).select(function (filter) {
            return !!filter;
        });
    },
    
});
