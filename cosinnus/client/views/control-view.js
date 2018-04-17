'use strict';

var ContentControlView = require('views/base/content-control-view');
var ErrorView = require('views/error-view');
var PaginationControlView = require('views/pagination-control-view');

var ResultCollection = require('collections/result-collection');
var Result = require('models/result');

var util = require('lib/util.js');

module.exports = ContentControlView.extend({
	
	template: require('map/map-controls'),
	
	activeFiltersTemplate: require('map/map-controls-active-filters'), 
	
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
        allTopics: {},  // the dict of all searchable topics
        controlsEnabled: true,
        filterGroup: null,
        
        // in fullscreen mode, this must always be the base URL we started at
        basePageURL: '/map/',
        
        // will be set to self.state during initialization
    	state: {
    		// current query
    		q: '',
			activeTopicIds: [],
			filtersActive: false, // if true, any filter is active and we display a reset-filter button
			typeFiltersActive: false, // a result type filter is active
			topicFiltersActive: false, // a topic filter is active
			ignoreLocation: false, // if true, search ignores all geo-loc and even shows results without tagged location
			searching: false,
			searchHadErrors: false,
			searchResultLimit: 20,
			page: null,
			pageIndex: 0,
			searchOnScroll: true,
			resultsStale: false,
			urlSelectedResultId: null,
			filterPanelVisible: false,
    	}
    },
    
    // the main ResultCollection of all displayed results
    collection: null,
    
    paginationControlView: null,
    
    // the currently hovered on and selected Result items
    selectedResult: null,
    hoveredResult: null,
    
    searchEndpointURL: '/maps/search/',
    searchDelay: 600,
    searchXHRTimeout: 15000,
    currentSearchHttpRequest: null, 
    
    initialize: function (options, app, collection) {
    	var self = this;
    	ContentControlView.prototype.initialize.call(self, options, app, collection);
    	
    	if (!self.collection) {
    		self.collection = new ResultCollection();
    	}
    	
    	Backbone.mediator.subscribe('want:search', self.handleStartSearch, self);
    	Backbone.mediator.subscribe('end:search', self.handleEndSearch, self);
    	Backbone.mediator.subscribe('app:ready', self.handleAppReady, self);
    	Backbone.mediator.subscribe('app:stale-results', self.handleStaleResults, self);
    	
    	util.log('control-view.js: initialized. with self.App=' + self.App)
    },

    events: {
    	'click .result-filter-button': 'toggleFilterButton',
    	'click .topic-button': 'toggleFilterButton',
        'click .reset-all': 'resetAllClicked',
        'click .query-search-button ': 'triggerQuerySearch',
        'click .icon-filters': 'toggleFilterPanel',
        'focus .q': 'showFilterPanel',
        'click .reset-type-filters': 'resetTypeFiltersClicked',
        'click .reset-topic-filters': 'resetTopicFiltersClicked',
        'click .reset-q': 'resetQClicked',
        'click .reset-type-and-topic-filters': 'resetAllClicked', // use this to only reset the filters box: 'resetTypeAndTopicFiltersClicked',
        'click .active-filters': 'showFilterPanel',
        'click .check-ignore-location': 'markSearchBoxSearchable',
        'click .onoffswitch-text-label': 'onOffSwitchLabelClicked',
        
        'keyup .q': 'handleTyping',
        'keydown .q': 'handleKeyDown',
    },

    // Event Handlers
    // --------------


    toggleFilterButton: function (event) {
        event.preventDefault();
        var $button = $(event.currentTarget);
        // check if all buttons of this type are selected.
        //  if so, make this click only select this button (deselect all others)
        if ($button.hasClass('result-filter-button') &&
    		this.$el.find('.result-filter-button').length == this.$el.find('.result-filter-button.selected').length) {
        	this.$el.find('.result-filter-button').removeClass('selected');
        } else if ($button.hasClass('topic-button') &&
    		this.$el.find('.topic-button').length == this.$el.find('.topic-button.selected').length) {
        	this.$el.find('.topic-button').removeClass('selected');
        }
        // toggle the button
    	$button.toggleClass('selected');
    	// mark search box as searchable
    	this.markSearchBoxSearchable();
    },
    
    /** Reset all types of input filters and trigger a new search */
    resetAllClicked: function (event) {
        event.preventDefault();
        this.state.q = '';
        this.resetTopics();
        this.resetTypeFilters();
        this.render();
    	this.triggerDelayedSearch(true);
    },
    
    /** Internal state reset of filtered topics */
    resetTopics: function () {
    	this.state.activeTopicIds = [];
    },
    
    /** Internal state reset of filtered result types */
    resetTypeFilters: function () {
    	this.state.activeFilters = _(this.options.availableFilters).clone();
    },

    resetTypeFiltersClicked: function (event) {
    	event.preventDefault();
    	event.stopPropagation();
        this.resetTypeFilters();
        this.render();
    	this.triggerDelayedSearch(true);
    },

    resetTopicFiltersClicked: function (event) {
    	event.preventDefault();
    	event.stopPropagation();
        this.resetTopics();
        this.render();
    	this.triggerDelayedSearch(true);
    },

    resetQClicked: function (event) {
    	event.preventDefault();
    	event.stopPropagation();
        this.state.q = '';
        this.render();
    	this.triggerDelayedSearch(true);
    },
    
    resetTypeAndTopicFiltersClicked: function (event) {
    	event.preventDefault();
    	event.stopPropagation();
        this.resetTypeFilters();
        this.resetTopics();
        this.render();
    	this.triggerDelayedSearch(true);
    },
    
    toggleSearchOnScrollClicked: function (event) {
    	event.preventDefault();
    	this.state.searchOnScroll = !this.state.searchOnScroll;
    	if (this.state.searchOnScroll == true && this.state.resultsStale) {
    		this.staleSearchButtonClicked(event);
    	} else {
    		this.paginationControlView.render();
    	}
    },
    
    staleSearchButtonClicked: function (event) {
    	event.preventDefault();
    	this.triggerDelayedSearch(true);
    	// we cheat this in because we know the search will do it anyways in a millisecond,
    	// but without this it won't be in time for the render() of the controls
    	this.state.resultsStale = false;
    	this.paginationControlView.render();
    },
    
    paginationForwardClicked: function (event) {
    	event.preventDefault();
    	if (this.state.page.has_next) {
    		this.state.pageIndex += 1;
    		this.triggerDelayedSearch(true, true);
    	}
    },
    
    paginationBackClicked: function (event) {
    	event.preventDefault();
    	if (this.state.page.has_previous && this.state.pageIndex > 0) {
    		this.state.pageIndex -= 1;
    		this.triggerDelayedSearch(true, true);
    	}
    },
    
    onOffSwitchLabelClicked: function (event) {
    	$(event.target).next().find('input[type="checkbox"]').click()
    },
    
    toggleFilterPanel: function (event) {
    	if (event) {
    		event.preventDefault();
    	}
    	if (this.filterPanelVisible) {
    		this.hideFilterPanel(event);
    	} else {
    		this.showFilterPanel(event);
    	}
    },
    
    showFilterPanel: function (event) {
    	if (event) {
    		event.preventDefault();
    	}
    	this.filterPanelVisible = true;
    	this.$el.find('.map-controls-filters').slideDown(250);
    	this.$el.find('.icon-filters').addClass('open');
    },
    
    hideFilterPanel: function (event) {
    	if (event) {
    		event.preventDefault();
    	}
    	this.filterPanelVisible = false;
    	this.$el.find('.map-controls-filters').slideUp(250);
    	this.$el.find('.icon-filters').removeClass('open');
    	
    },
    
    

    
    /**
     * Unused now, this used to be the search-while-typing feature.
     * TODO: Remove completely (also this.state.typing) once sure 
     * we don't want it
     
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
    
    */
    
    handleTyping: function (event) {
    	var self = this;
        if (util.isIgnorableKey(event)) {
            event.preventDefault();
            return false;
        }
        self.markSearchBoxSearchable();
    },
    
    handleKeyDown: function (event) {
        if (event.keyCode == 13) {
        	event.preventDefault();
        	this.triggerQuerySearch();
            return false;
        }
    },
    
    markSearchBoxSearchable: function () {
    	this.$el.find('.icon-search').addClass('active');
    	this.$el.find('.button-search').removeClass('disabled');
    },
    
    /**
     * Will start a fresh search with the current query of the search textbox.
     */
    triggerQuerySearch: function () {
        var query = this.$el.find('.q').val();
		this.state.q = query;
		this.applyFilters();
		this.state.ignoreLocation = !this.$el.find('.check-ignore-location').is(':checked');
		this.triggerDelayedSearch(true);
    },
    

    handleStartSearch: function (event) {
    	this.$el.find('.icon-loading').removeClass('hidden');
        this.$el.find('.q').blur();
        // disable input in content views during search (up to the views to decide what to disable)
        _.each(this.App.contentViews, function(view){
    		view.disableInput();
    	});
        
    },

    handleEndSearch: function (event) {
        this.$el.find('.icon-loading').addClass('hidden');
        // enable input in content views during search (up to the views to decide what to enable)
        _.each(this.App.contentViews, function(view){
    		view.enableInput();
    	});
    },

    /** Called when the App is fully loaded for the first time.
     * 	WARNING: Due to the threaded after_render() method, this may
     * 		currently actually happen before a full load.
     *  */
    handleAppReady: function (event) {
    	util.log('control-view.js: app is ready to search. starting search from URL!')
    	this.triggerSearchFromUrl();
    },
    
    /** Executed *every time* after render */
    afterRender: function () {
    	var self = this;
    	// Create the pagination control view if not exists
    	if (!self.paginationControlView && self.App.tileListView) {
    		self.paginationControlView = new PaginationControlView({
    			model: null,
    			el: self.App.tileListView.$el.find('.pagination-controls'),
    			fullscreen: self.App.displayOptions.fullscreen,
    			splitscreen: self.App.displayOptions.showMap && self.App.displayOptions.showTiles
    		}, 
    		self.App,
    		self
    		).render();
    	}
    },
    
    /**
     * Let all content views parse the URL parameters they are interested in, and then start 
     * a fresh search.
     */
    triggerSearchFromUrl: function (noNewNavigateEvent) {
    	var urlParams = this.parseUrl(window.location.href.replace(window.location.origin, ''));
    	_.each(this.App.contentViews, function(view){
    		view.applyUrlSearchParameters(urlParams);
    	});
    	this.render();
    	this.triggerDelayedSearch(true, true, noNewNavigateEvent);
    },
    
    /**
     * The context can contain `reason` for a signal for out-of-date result sets:
     * - viewport-changed: The map was scrolled or window was resized
     * - map-navigate: Router navigate on the map (not called during initial navigation)
     * - ...
     */
    handleStaleResults: function (context) {
    	if (context.reason == 'viewport-changed') {
    		util.log('*** control-view.js: Received signal for stale results bc of viewport change, and triggering a delayed search if nothing prevents it')
    	} else if (context.reason == 'map-navigate') {
    		util.log('*** control-view.js: Received signal for stale results bc of map-navigate, but doing nothing rn')
    	}
    	
    	var staleBefore = this.state.resultsStale;
    	this.state.resultsStale = true;
    	
    	if (context.reason == 'map-navigate') {
    		// on a navigate event we have to re-read the URL (but add no history state)
    		this.triggerSearchFromUrl(true);
    	} else {
    		// search or do nothing, depending on if we re-search on scroll
    		if (this.state.searchOnScroll) {
    			// check before auto-rerendering that the input-box is not focused!
    			// if so, on mobile this search would pull down the keyboard
    			if (!this.$el.find('.q').is(":focus")) {
    				this.triggerDelayedSearch();
    			} else {
    				util.log('control-view.js: Prevented a search while input is focused!')
    			}
    		} else {
    			// re-render controls so the manual search button will be enabled
    			if (!staleBefore) {
    				this.paginationControlView.render();
    			}
    		}
    	}
    },
    
    // called with a list of dicts of results freshly returned after a search
    processSearchResults: function (jsonResultList) {
    	var self = this;
    	
    	var resultModels = [];
    	_.each(jsonResultList, function(res){
    		var newmod = new Result(res);
    		resultModels.push(newmod);
    	});
    	// take the current selected model and check if it is in the new result list
    	// if so, set that to selected
    	// if not: add it to it
    	if (self.selectedResult) {
    		var position = resultModels.map(function(e){return e.id;}).indexOf(self.selectedResult.id);
    		if (position > -1) {
    			resultModels[position].set('selected', true);
    		} else {
    			resultModels.push(self.selectedResult);
    		}
    	}
    	// take the current hovered model and check if it is in the new result list
    	// if so, set that to hovered
    	// if not: add it to it
    	if (self.hoveredResult) {
    		var position = resultModels.map(function(e){return e.id;}).indexOf(self.hoveredResult.id);
    		if (position > -1) {
    			resultModels[position].set('hovered', true);
    		} else {
    			resultModels.push(self.hoveredResult);
    		}
    	}
    	
    	
    	util.log('control-view.js:processSearchResults: check that the currently selected object is kept in the collection!')
    	
    	
    	util.log('control-view.js: got the results back and updated the collection!')
    	util.log(self.collection.toJSON());
    	
    	
    	
    	self.collection.reset(resultModels);
    	
    	// if our URL points directly at an item, select it.
    	// the API should take care that it is *always* in the result set
    	if (!self.selectedResult && self.state.urlSelectedResultId) {
    		self.setSelectedResult(self.collection.get(self.state.urlSelectedResultId));
    		self.state.urlSelectedResultId = null;
    	}
    	

    	// TODO: clean up if not needed anymore
    	
    	// self.collection.set(resultModels);
    	/**
    	 * Merges existing models and updates them.
    	 * Calls 'add'/'change'/'remove'!
    	 * 
    	 * TodosCollection.set([
			    { id: 1, title: 'go to Jamaica.', completed: true },
			    { id: 2, title: 'go to China.', completed: false },
			    { id: 4, title: 'go to Disney World.', completed: false }
			]);
    	 * 
    	 */
    	
    	/**
    	 * Does NOT call add/change/remove!
    	 * Calls 'reset' signal!
    	 * options.previousModels is the removed set!
    	 * 
    	 * var todo = new Backbone.Model();
			var todos = new Backbone.Collection([todo])
			.on('reset', function(todos, options) {
			  console.log(options.previousModels);
			  console.log([todo]);
			  console.log(options.previousModels[0] === todo); // true
			});
			todos.reset([]);
    	 */
    },
    
    // public functions
    
    /**
     * Will set a new selected result and un-set the old one.
     * If result == null, will just un-set the current one.
     */
    setSelectedResult: function (result) {
    	if (this.selectedResult != null) {
    		// unselect previously selected result
    		this.selectedResult.set('selected', false);
    		if (result != null) {
    			// we're instantly selecting a new result
    			Backbone.mediator.publish('result:reselected', result);
    		} else {
    			// just unselecting, without selecting a new result
    			Backbone.mediator.publish('result:unselected', this.selectedResult);
    		}
    	} else if (result != null) {
    		// we select a new result without a previous one having been selected
    		Backbone.mediator.publish('result:selected', result);
    	}
    	this.selectedResult = result;
    	if (this.selectedResult != null) {
    		this.selectedResult.set('selected', true);
    	}
    	// selecting a result changes the URL so results can be directly linked
    	if (App.displayOptions.routeNavigation) {
    		var newUrl = this.buildSearchQueryURL(false).replace(this.searchEndpointURL, this.options.basePageURL);
    		App.router.replaceUrl(newUrl);
    	}
    },
    
    /**
     * Will set a new hovered result and un-set the old one.
     * If result == null, will just un-set the current one.
     */
    setHoveredResult: function (result) {
    	if (this.hoveredResult != null) {
    		this.hoveredResult.set('hovered', false);
    	}
    	this.hoveredResult = result;
    	if (this.hoveredResult != null) {
    		this.hoveredResult.set('hovered', true);
    	}
    },
    

    search: function (noNavigate) {
        var self = this;
        self.state.resultsStale = false;
        
        var url = self.buildSearchQueryURL(true);
        self.state.searching = true;
        
        // cancel the currently ongoing request
        if (self.currentSearchHttpRequest) {
        	util.log('control-view.js: New search! Aborting current search request.')
        	self.currentSearchHttpRequest.abort();
        }
        
        self.currentSearchHttpRequest = $.ajax(url, {
        	type: 'GET',
        	timeout: self.searchXHRTimeout,
        	success: function (data, textStatus) {
            	// Save the search state in the url.
            	if (App.displayOptions.routeNavigation && !noNavigate) {
            		util.log('control-view.js: +++++++++++++++++ since we are fullscreen, publishing router URL update!')
            		Backbone.mediator.publish('navigate:router', self.buildSearchQueryURL(false).replace(self.searchEndpointURL, self.options.basePageURL))
            	}
            	util.log('got resultssss')
            	util.log(data)
            	util.log(textStatus)
            	var results = data.results;
            	self.processSearchResults(results);
            	self.state.page = data.page;
            	self.state.pageIndex = data.page && data.page.index || 0;
            	self.state.searchHadErrors = false;
	        },
	        error: function (xhr, textStatus) {
	            util.log('control-view.js: Search XHR failed.')
	            if (textStatus === 'abort') {
	        		return;
	        	}
	            Backbone.mediator.publish('error:search');
	            self.state.searchHadErrors = true;
	        },
	        complete: function (xhr, textStatus) {
	        	util.log('control-view.js: Search complete: ' + textStatus)
	        	if (textStatus === 'abort') {
	        		return;
	        	}
	        	if (textStatus !== 'success') {
	        		self.state.searchHadErrors = true;
	        	}
	            self.state.searching = false;
	            
	            if (self.options.controlsEnabled) {
	            	// determine if any filtering method is active (topics or result types)
	            	self.state.filtersActive = false;
	            	self.state.topicFiltersActive = false;
	            	self.state.typeFiltersActive = false;
	            	
	            	if (self.state.ignoreLocation) {
	            		self.state.filtersActive = true;
	            	}
	            	if (self.state.activeTopicIds.length > 0) {
	            		self.state.filtersActive = true;
	            		self.state.topicFiltersActive = true;
	            	}
            		_.each(Object.keys(self.options.availableFilters), function(key) {
            			if (self.options.availableFilters[key] != self.state.activeFilters[key]) {
            				self.state.filtersActive = true;
            				self.state.typeFiltersActive = true;
            			}
            		});
	            	self.refreshSearchControls();
	            	self.hideFilterPanel();
	            	self.renderActiveFilters();
	            	// refresh pagination controls
	            	self.paginationControlView.render();
	            }
	            
	            Backbone.mediator.publish('end:search');
	        }
        });
    },
    
    refreshSearchControls: function () {
    	var self = this;
    	self.$el.find('.icon-filters').toggleClass('active', self.state.filtersActive);
    	self.$el.find('.icon-reset').toggleClass('hidden', (!self.state.filtersActive && !self.state.q));
    	self.$el.find('.icon-search').removeClass('active');
    	self.$el.find('.button-search').addClass('disabled');
    },
    
    renderActiveFilters: function () {
    	if (this.state.filtersActive || this.state.q) {
    		var data = this.getTemplateData();
    		var rendered = this.activeFiltersTemplate.render(data);
    		this.$el.find('.map-controls-active-filters').html(rendered).show();
    	} else {
    		this.$el.find('.map-controls-active-filters').hide().empty();
    	}
    },
    
    /** Unused, remove if not needed */
    /** Old version: we do not re-render the search controls any more because of loss
     *  of new search input for the user
    refreshSearchControls: function () {
    	// restore the search textbox after the render so we don't throw the user out
    	var qdata = util.saveInputStatus(self.$el.find('.q'));
    	self.render();
    	util.restoreInputStatus(self.$el.find('.q'), qdata);
    },
    */
    
    // extended from content-control-view.js
    applyUrlSearchParameters: function (urlParams) {
        _.extend(this.state, {
            activeFilters: {
                people: util.ifundef(urlParams.people, this.options.activeFilters.people),
                events: util.ifundef(urlParams.events, this.options.activeFilters.events),
                projects: util.ifundef(urlParams.projects, this.options.activeFilters.projects),
                groups: util.ifundef(urlParams.groups, this.options.activeFilters.groups)
            },
            q: util.ifundef(urlParams.q, this.state.q),
            ignoreLocation: util.ifundef(urlParams.ignore_location, this.state.ignoreLocation),
            searchResultLimit: util.ifundef(urlParams.limits, this.state.searchResultLimit),
            activeTopicIds: util.ifundef(urlParams.topics, this.state.activeTopicIds),
            pageIndex: util.ifundef(urlParams.page, this.state.pageIndex),
            urlSelectedResultId: util.ifundef(urlParams.item, this.state.urlSelectedResultId),
        });
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
        if (this.state.activeTopicIds.length > 0) {
        	_.extend(searchParams, {
        		topics: this.state.activeTopicIds.join(',')
        	});
        }
        if (this.state.pageIndex > 0) {
        	_.extend(searchParams, {
        		page: this.state.pageIndex
        	});
        }
        if (this.selectedResult) {
        	_.extend(searchParams, {
        		item: this.selectedResult.id
        	});
        } else if (this.state.urlSelectedResultId) {
        	_.extend(searchParams, {
        		item: this.state.urlSelectedResultId
        	});
        }
        if (this.state.ignoreLocation) {
        	_.extend(searchParams, {
        		ignore_location: 1
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
        
        util.log(' ************  BUILD SEARCH QUERY URL RETURNED (forAPI): ' + forAPI)
        util.log(url)
        return url;
    },
    
    /** Collects all toggled states of filter buttons and applies them onto the current control-view state */
    applyFilters: function () {
    	var self = this;

    	// Result types
    	var all_deselected = true;
    	self.$el.find('.result-filter-button').each(function(){
    		var $button = $(this);
    		var resultType = $button.attr('data-result-filter-type');
    		var selected = $button.hasClass('selected');
    		self.state.activeFilters[resultType] = selected;
    		if (selected) {
    			all_deselected = false;
    		}
    	});
    	// if we select all types, drop the filter (select all is default). 
    	if (all_deselected) {
    		self.resetResultFilters();
    	}
    	
    	// Topics
    	self.resetTopics();
    	self.$el.find('.topic-button.selected').each(function(){
        	var $button = $(this);
        	var bid = parseInt($button.attr('data-topic-id'));
        	self.state.activeTopicIds.push(bid);
        });
    	// if we select all topics, drop the filter (select all is default). 
    	// -1 because allTopics contains the empty choice
    	if (self.state.activeTopicIds.length >= Object.keys(self.options.allTopics).length-1) {
    		self.resetTopics();
    	}
        
    },

    // TODO REMOVE
    toggleFilter: function (resultType) {
        var activeFilters = this.state.activeFilters;
        activeFilters[resultType] = !activeFilters[resultType];
        this.state.activeFilters = activeFilters;
        this.triggerDelayedSearch(true);
    },

    // Register a change in the controls or the map UI which should queue
    // a search attempt after a delay.
    triggerDelayedSearch: function (fireImmediatelyIfPossible, noPageReset, noNavigate) {
        var self = this;
        
        var delay = self.searchDelay;
        if (fireImmediatelyIfPossible) {
        	delay = 0;
        	util.log('control-view.js: TODO: FireImmediately was passed true!')
        }
        if (!noPageReset) {
        	self.state.pageIndex = 0;
        }
        clearTimeout(this.searchTimeout);
        Backbone.mediator.publish('want:search');
        self.searchTimeout = setTimeout(function () {
            self.search(noNavigate);
        }, delay);
    },

    activeFilterList: function () {
        return _(_(this.state.activeFilters).keys()).select(function (filter) {
            return !!filter;
        });
    },
    
});
