'use strict';

var ContentControlView = require('views/base/content-control-view');
var ErrorView = require('views/error-view');
var util = require('lib/util.js');

module.exports = ContentControlView.extend({
	
	App: null,
	
	template: require('map/map-controls'),
	
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
    },
    
    searchEndpointURL: '/maps/search/',
    searchDelay: 400,
    whileSearchingDelay: 5000,
	
    options: {
    	state: {
    		// current query
    		q: '',
    		topicsVisible: false,
			activeTopicIds: null,
			wantsToSearch: false,
			searching: false
    	}
    },
    
    initialize: function (options, app) {
    	var self = this;
    	self.App = app;
    	self.options = $.extend(true, {}, self.defaults, options);
    	Backbone.mediator.subscribe('want:search', self.handleStartSearch, self);
    	Backbone.mediator.subscribe('end:search', self.handleEndSearch, self);
    	Backbone.mediator.subscribe('change:controls', self.render, self);
    	Backbone.mediator.subscribe('error:search', self.handleXhrError, self);
    	Backbone.mediator.subscribe('app:ready', self.fhandleAppReady, self);
    	
    	console.log('control-view.js: initialized. with self.App=' + self.App)
    	
    	// this calls self.initializeSearchParameters()
        ContentControlView.prototype.initialize.call(self, options);

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
            this.attemptSearch();
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
    
    handleAppReady: function (event) {
    	alert('control-view.js: app is ready to search!!! but not doing anything rn')
    	
    	return;

        this.search();
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
                self.attemptSearch();
            // Update the results if there isn't a queued search.
            } else {
            	alert('control-view.js: TODO: we got the results back! put them in a collection and implement all the "change:results" subscribers!')
                self.set('results', res);
                Backbone.mediator.publish('change:results');
                // Save the search state in the url.
                if (App.displayOptions.fullscreen) {
                    Backbone.mediator.publish('navigate:router', self.buildSearchQueryURL(false).replace(self.searchEndpointURL, self.options.basePageURL))
                }
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
                people: this.ifundef(urlParams.people, this.options.activeFilters.people),
                events: this.ifundef(urlParams.events, this.options.activeFilters.events),
                projects: this.ifundef(urlParams.projects, this.options.activeFilters.projects),
                groups: this.ifundef(urlParams.groups, this.options.activeFilters.groups)
            },
            q: this.ifundef(urlParams.q, this.state.q),
            //limit: this.ifundef(urlParams.limits, this.get('limit')),
            activeTopicIds: this.ifundef(urlParams.topics, this.state.activeTopicIds)
        });
        console.log('TODO: we removed the "limit" param. what to do with it?')
    },
    
    // extended from content-control-view.js
    contributeToSearchParameters: function() {
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
    	return searchParams
    },
    
    buildSearchQueryURL: function (padded) {
    	// collect all search parameters from content views that affect them
    	var searchParams = {};
    	_.each(this.App.contentViews, function(view){
    		_.extend(searchParams, view.contributeToSearchParameters());
    	});
        var query = $.param(searchParams);
        
        var url = this.searchEndpointURL;
        if (this.options.filterGroup) {
            url = url + this.options.filterGroup + '/';
        }
        return url + '?' + query;
    },

    toggleFilter: function (resultType) {
        var activeFilters = this.state.activeFilters;
        activeFilters[resultType] = !activeFilters[resultType];
        this.state.activeFilters = activeFilters;
        this.attemptSearch();
    },

    resetFilters: function () {
        this.state.activeFilters = _(this.options.availableFilters).clone();
        this.attemptSearch();
    },
    
    showTopics: function () {
        this.state.topicsVisible = true;
    },
    
    toggleTopicFilter: function (topic_ids) {
        this.state.activeTopicIds = topic_ids;
        this.attemptSearch();
    },

    // Register a change in the controls or the map UI which should queue
    // a search attempt.
    attemptSearch: function () {
        var self = this;
            // Increase the search delay when a search is in progress.
        var delay = self.get('searching') ?
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
