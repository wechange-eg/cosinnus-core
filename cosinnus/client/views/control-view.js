'use strict';

var ContentControlView = require('views/base/content-control-view');
var ErrorView = require('views/error-view');
var PaginationControlView = require('views/pagination-control-view');
var MobileControlView = require('views/mobile-control-view');
var CreateIdeaView = require('views/create-idea-view');

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
            projects: true,
            events: true,
            groups: true,
        },
        activeFilters: {
            people: true,
            projects: true,
            events: true,
            groups: true
        },
        availableFilterList: [], // contains availableFilters keys that are true, generated on initialize
        
        allTopics: {},  // the dict of all searchable topics
        allSDGS: {}, // the dict of all searchable SDGs
        allManagedTags: {}, // the dict of all searchable CosinnusManagedTags
        managedTagsLabels: {}, // the labels dict for CosinnusManagedTags
        portalInfo: {}, // portal info by portal-id, from `get_cosinnus_portal_info()`
        controlsEnabled: true,
        filterGroup: null,
        fullscreen: false,
        splitscreen: false,
        showMine: false, // URL param. if true, only the current user's own results will be shown. ignored away if user is not logged in.
        
        paginationControlsEnabled: true, 
        paginationControlsUseInfiniteScroll: false, // if true, the pagination controls will be hidden and infinite scroll will be used
        
        // in fullscreen mode, this must always be the base URL we started at
        basePageURL: '/map/',
        
        // will be set to self.state during initialization
        state: {
            // current query
            q: '', // URL param. 
            activeTopicIds: [],
            activeSDGIds: [],
            activeManagedTagsIds: [],
            filtersActive: false, // URL param.  if true, any filter is active and we display a reset-filter button
            typeFiltersActive: false, // URL param.  a result type filter is active
            topicFiltersActive: false, // URL param.  a topic filter is active
            sdgFiltersActive: false,
            managedTagsFiltersActive: false,
            ignoreLocation: false, // if true, search ignores all geo-loc and even shows results without tagged location
            searching: false,
            searchHadErrors: false,
            searchResultLimit: 20,
            page: null,  // URL param. 
            pageIndex: 0,
            searchOnScroll: true,
            resultsStale: false,
            urlSelectedResultId: null, // URL param. the currently selected result, given in the url
            filterPanelVisible: false,
            lastViewBeforeDetailWasListView: false, // a savestate so we know which view to return to after closing the detail view on mobile
        }
    },
    
    // the main ResultCollection of all displayed results
    collection: null,

    paginationControlView: null,
    mobileControlView: null,
    createIdeaView: null,
    
    // the currently hovered on and selected Result items
    selectedResult: null,
    hoveredResult: null,
    detailResult: null, // the Result displayed as DetailView result. not the same as `selectedResult`!
    detailResultCache: {},
    
    searchEndpointURL: '/map/search/',
    detailEndpointURL: '/map/detail/',
    searchDelay: 1, // since we are cancelling xhrs properly, we do not need to delay searches anymore. but leaving it in if we ever do again.
    searchXHRTimeout: 15000,
    currentSearchHttpRequest: null, 
    currentDetailHttpRequest: null,
    
    initialize: function (options, app, collection) {
        var self = this;
        // add idea models if active
        if (COSINNUS_IDEAS_ENABLED) {
        	self.defaults.availableFilters['ideas'] = true;
        	self.defaults.activeFilters['ideas'] = true;
        }
        // add organization models if active
        if (COSINNUS_ORGANIZATIONS_ENABLED) {
        	self.defaults.availableFilters['organizations'] = true;
        	self.defaults.activeFilters['organizations'] = true;
        }
        
        ContentControlView.prototype.initialize.call(self, options, app, collection);
        
        _.each(this.options.availableFilters, function(active, type){
            if (active) {
            	self.options.availableFilterList.push(type); 
            }
        });
        if (COSINNUS_MAP_OPTIONS['filter_panel_default_visible']) {
            self.state.filterPanelVisible = true;
        }
        
        if (!self.collection) {
            self.collection = new ResultCollection();
        }
        if (options.searchResultLimit && !isNaN(options.searchResultLimit)) {
        	var searchResultLimit = parseInt(options.searchResultLimit);
        	if (searchResultLimit > 0) {
        		self.state.searchResultLimit = options.searchResultLimit;
        	}
        }
        
        Backbone.mediator.subscribe('want:search', self.handleStartSearch, self);
        Backbone.mediator.subscribe('end:search', self.handleEndSearch, self);
        Backbone.mediator.subscribe('app:ready', self.handleAppReady, self);
        Backbone.mediator.subscribe('app:stale-results', self.handleStaleResults, self);
        
        self.triggerMobileDefaultView();
        
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
        'click .reset-sdg-filters': 'resetSDGFiltersClicked',
        'click .reset-managed-tag-filters': 'resetManagedTagsFiltersClicked',
        'click .reset-q': 'resetQClicked',
        'click .reset-type-and-topic-filters': 'resetAllClicked', // use this to only reset the filters box: 'resetTypeAndTopicFiltersClicked',
        'click .active-filters': 'showFilterPanel',
        'change .check-ignore-location': 'markSearchBoxSearchable',
        
        'keyup .q': 'handleTyping',
        'keydown .q': 'handleKeyDown',

        'click .sdg-button': 'toggleSDGFilterButton',
        'click .managed-tag-button': 'toggleManagedTagsFilterButton',
        'mouseenter .hover-image-button': 'showHoverIcon',
        'mouseleave .hover-image-button': 'hideHoverIcon',
        'mouseenter .hover-image-icon': 'hideHoverIcon'
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

    toggleSDGFilterButton: function (event) {
        event.preventDefault();
        var $button = $(event.currentTarget);
        // check if all buttons of this type are selected.
        //  if so, make this click only select this button (deselect all others)
        if ($button.hasClass('result-filter-button') &&
            this.$el.find('.result-filter-button').length == this.$el.find('.result-filter-button.selected').length) {
            this.$el.find('.result-filter-button').removeClass('selected');
        } else if ($button.hasClass('sdg-button') &&
            this.$el.find('.sdg-button').length == this.$el.find('.sdg-button.selected').length) {
            this.$el.find('.sdg-button').removeClass('selected');
        }
        // toggle the button
        $button.toggleClass('selected');
        // mark search box as searchable
        this.markSearchBoxSearchable();
    },
    
    toggleManagedTagsFilterButton: function (event) {
        event.preventDefault();
        var $button = $(event.currentTarget);
        // check if all buttons of this type are selected.
        //  if so, make this click only select this button (deselect all others)
        if ($button.hasClass('result-filter-button') &&
            this.$el.find('.result-filter-button').length == this.$el.find('.result-filter-button.selected').length) {
            this.$el.find('.result-filter-button').removeClass('selected');
        } else if ($button.hasClass('managedTags-button') &&
            this.$el.find('.managedTags-button').length == this.$el.find('.managedTags-button.selected').length) {
            this.$el.find('.managedTags-button').removeClass('selected');
        }
        // toggle the button
        $button.toggleClass('selected');
        // mark search box as searchable
        this.markSearchBoxSearchable();
    },
    
    /** Reset all types of input filters and trigger a new search */
    resetAllClicked: function (event) {
        event.preventDefault();
        this.resetAll();
        this.render();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },
    
    /** Resets all filter states */
    resetAll: function () {
        this.state.q = '';
        this.resetTopics();
        this.resetSDGS();
        this.resetManagedTags();
        this.resetTypeFilters();
        this.clearDetailResultCache();
    },
    
    /** Internal state reset of filtered topics */
    resetTopics: function () {
        this.state.activeTopicIds = [];
    },

    resetSDGS: function () {
        this.state.activeSDGIds = [];
    },
    
    resetManagedTags: function () {
        this.state.activeManagedTagsIds = [];
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
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },

    resetTopicFiltersClicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.resetTopics();
        this.render();
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },

    resetSDGFiltersClicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.resetSDGS();
        this.render();
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },
    
    resetManagedTagsFiltersClicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.resetManagedTags();
        this.render();
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },

    resetQClicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.state.q = '';
        this.render();
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },
    
    resetTypeAndTopicFiltersClicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this.resetTypeFilters();
        this.resetTopics();
        this.render();
        this.clearDetailResultCache();
        var searchReason = 'reset-filters-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },
    
    /** This doesn't listen to events in this view, but rather is the target for 
     *     delegated events from tile-view and tile-detail-view */
    onTopicLinkClicked: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var $link = $(event.target);
        var topicId = $link.attr('data-topic-id');
        this.resetAll();
        this.state.activeTopicIds = [parseInt(topicId)];
        this.clearDetailResultCache();
        this.triggerDelayedSearch(true);
    },
    
    /** This doesn't listen to events in this view, but rather is the target for 
     *     delegated events from tile-view and tile-detail-view */
    onManagedTagLinkClicked: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var $link = $(event.target);
        var managedTagId = $link.attr('data-managed-tag-id');
        this.resetAll();
        this.state.activeManagedTagsIds = [parseInt(managedTagId)];
        this.clearDetailResultCache();
        this.triggerDelayedSearch(true);
    },
    
    toggleSearchOnScrollClicked: function (event) {
        this.state.searchOnScroll = !this.state.searchOnScroll;
        if (this.state.searchOnScroll == true && this.state.resultsStale) {
            this.staleSearchButtonClicked(event);
        } 
    },
    
    staleSearchButtonClicked: function (event) {
        event.preventDefault();
        this.clearDetailResultCache();
        this.triggerDelayedSearch(true);
        // we cheat this in because we know the search will do it anyways in a millisecond,
        // but without this it won't be in time for the render() of the controls
        this.state.resultsStale = false;
        if (this.paginationControlView) {
        	this.paginationControlView.render();
        }
    },
    
    paginationForwardClicked: function (event) {
    	if (event) {
    		event.preventDefault();
    	}
        if (this.state.page.has_next) {
            this.state.pageIndex += 1;
            this.triggerDelayedSearch(true, true, false, 'paginate-search');
        }
    },
    
    paginationBackClicked: function (event) {
    	if (event) {
    		event.preventDefault();
    	}
        if (this.state.page.has_previous && this.state.pageIndex > 0) {
            this.state.pageIndex -= 1;
            this.triggerDelayedSearch(true, true, false, 'paginate-search');
        }
    },
    
    /* ---------------------  Display-related logic    ------------------------------- */
    
    
    /** Open the Create-Idea view */
    openCreateIdeaView: function (event) {
    	var self = this;
    	if (COSINNUS_IDEAS_ENABLED) {
    		if (!self.createIdeaView) {
    			self.createIdeaView = new CreateIdeaView({
    				elParent: self.App.el,
    			}, 
    			self.App,
    			self
    			).render();
    		} else {
    			self.createIdeaView.$el.removeClass('hidden');
    		}
            Backbone.mediator.publish('ideas:create-view-opened');
    	}
    },
    
    /** Open the Create-Idea view */
    closeCreateIdeaView: function (event) {
    	var self = this;
    	self.createIdeaView.$el.addClass('hidden');
    	self.untriggerMobileIdeaCreateView(event);
    	Backbone.mediator.publish('ideas:create-view-closed');
    },
    
    /** Mobile view switch buttons */
    _resetMobileView: function (event, dontResetDetailResult) {
        // unselect the detail view if one is open
        if (this.detailResult && !dontResetDetailResult) {
            this.displayDetailResult(null);
        }
        this.App.$el.removeClass('mobile-view-map mobile-view-search mobile-view-list mobile-view-detail mobile-view-idea-create-1 mobile-view-idea-create-2');
    },
    
    triggerMobileDefaultView: function (event) {
    	if (this.options.splitscreen) {
    		this.triggerMobileMapView(event);
        } else {
        	this.triggerMobileListView(event);
        }
    },
    
    triggerMobileListView: function (event) {
        this._resetMobileView();
        this.App.$el.addClass('mobile-view-list');
        if (this.App.tileListView) { // might not be loaded yet
        	this.App.tileListView.gridRefresh();
        }
    },

    triggerMobileSearchView: function (event) {
        this._resetMobileView();
        this.App.$el.addClass('mobile-view-search');
        this.$el.find('.q').focus();
    },

    triggerMobileMapView: function (event) {
        this._resetMobileView();
        this.App.$el.addClass('mobile-view-map');
    },

    triggerMobileDetailView: function (event) {
    	// save the current view 
    	// (if it was list view we want to return to that instead of map view when closing detail)
    	this.state.lastViewBeforeDetailWasListView = this.App.$el.hasClass('mobile-view-list');
    	this._resetMobileView(event, true);
    	this.App.$el.addClass('mobile-view-detail');
    },

    triggerMobileIdeaCreate1View: function (event) {
        this._resetMobileView();
        this.openCreateIdeaView(event);
        this.App.$el.addClass('mobile-view-idea-create-1');
    },

    triggerMobileIdeaCreate2View: function (event) {
        this._resetMobileView();
        this.App.$el.addClass('mobile-view-idea-create-2');
    },

    untriggerMobileIdeaCreateView: function (event) {
        this.triggerMobileDefaultView(event);
    },

    untriggerMobileDetailView: function (event) {
        if (this.state.lastViewBeforeDetailWasListView) {
        	this.triggerMobileListView(event);
        } else {
        	this.triggerMobileMapView(event);
        }
    },

    showHoverIcon: function (event) {
        var icon = $(event.target.querySelector('img'))
        icon.removeClass('hover-image-icon-hidden')
    },

    hideHoverIcon: function (event) {
        if (event.target.tagName == 'IMG') {
            $(event.target).addClass('hover-image-icon-hidden')
        } else {
            $(event.target.querySelector('img')).addClass('hover-image-icon-hidden')
        }
    },
    /**
     * Toggles the state of the views between splitview, map-fullscreen or tile-fullscreen.
     */
    switchDisplayState: function (showMap, showTiles) {
    	if (!showMap && !showTiles) {
            util.log('control-view.js: cant hide both tile and map views at the same time!');
            return;
    	}
    	this.App.displayOptions.showMap = showMap;
    	this.App.displayOptions.showTiles = showTiles;
    	this.options.splitscreen = showMap && showTiles;
    	this.App.loadTileView();
    	this.App.loadMapView();
    },

    
    /* ---------------------  Functional logic    ------------------------------- */
    
    
    /**
     * Will start a fresh search with the current query of the search textbox.
     */
    triggerQuerySearch: function () {
        var query = this.$el.find('.q').val();
        this.state.q = query;
        this.applyFilters();
        this.state.ignoreLocation = !this.$el.find('.check-ignore-location').is(':checked');
        this.clearDetailResultCache();
        var searchReason = 'manual-search';
        this.triggerDelayedSearch(true, false, false, searchReason);
    },
    
    /** Delete the detail result cache, should only happen on voluntary user "new search" actions! */
    clearDetailResultCache: function () {
        self.detailResultCache = {};
    },
    
    /** Triggers on click of a link that opens a result detail view.
     *  Can be triggered from multiple views. */
    onResultLinkClicked: function (event, directItemId, noNavigate) {
        var self = this;
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        // parse the target object from the link
        var data = null;
        if (!directItemId && event) {
            var $tar = $(event.target).closest('.result-link');
            var data = {
                portal: $tar.attr('data-portal') || 0,
                type: $tar.attr('data-type'),
                slug: $tar.attr('data-slug'),
            }
            directItemId = util.makeDirectItemId(data['portal'], data['type'], data['slug']);
        } else {
            var data = util.parseDirectItemId(directItemId);
        }
        util.log('tile-view.js: got a select click event! data: ' + JSON.stringify(data));
        
        // check if this item is in the local detail Result cache
        var result = null;
        if (directItemId in self.detailResultCache) {
            result = self.detailResultCache[directItemId];
            self.displayDetailResult(result);
        } else {
            // if not, load it from the server
            
            // build detail URL
            var query = $.param(data);
            var url = this.detailEndpointURL + '?' + query;
            
            // cancel the currently ongoing request
            if (self.currentDetailHttpRequest) {
                util.log('control-view.js: New detail request! Aborting current request.')
                self.currentDetailHttpRequest.abort();
            }
            
            var detailHadErrors = false;
            self.currentDetailHttpRequest = $.ajax(url, {
                type: 'GET',
                timeout: self.searchXHRTimeout,
                success: function (data, textStatus) {
                    
                    util.log('got resultssss for detail')
                    util.log(data)
                    util.log(textStatus)
                    
                    if ('result' in data) {
                        result = new Result(data.result);
                        // put item in result cache
                        self.detailResultCache[result.id] = result;
                        self.displayDetailResult(result);
                        // add a route navigate history state?
                        if (App.displayOptions.routeNavigation && !noNavigate) {
                            util.log('control-view.js: +++++++++++++++++ since we are fullscreen, publishing detail router URL update!')
                            self.addCurrentHistoryState();
                        } 
                    } else {
                        // if the result came back empty, it might have been deleted on the server, show an error message and close detail view
                        detailHadErrors = true;
                    }
                },
                error: function (xhr, textStatus) {
                    util.log('control-view.js: Detail XHR failed.')
                    if (textStatus === 'abort') {
                        return;
                    }
                    detailHadErrors = true;
                },
                complete: function (xhr, textStatus) {
                    util.log('control-view.js: Search complete: ' + textStatus);
                    
                    if (textStatus === 'abort') {
                        return;
                    }
                    if (textStatus !== 'success') {
                        detailHadErrors = true;
                    }
                    self.currentDetailHttpRequest = null;
                    if (detailHadErrors) {
                        if (xhr.status == 403) {
                            self.displayDetailResult(new Result({type: 'error-403'}));
                        } else {
                            self.displayDetailResult(new Result({type: 'error'}));
                        }
                    }
                }
            });
            
            
        }
    },
    
    // id is: "1.events.forum*tolles-event"
    
    /** Will like/unlike a given result, depending on the current liked status */
    triggerResultLikeOrUnlike: function (result) {
    	var self = this;
    	var url = '/likefollow/'
    		
    	var data = util.getAPIDataForDirectItemId(result.get('id'));
    	if (data == null || !(result.get('type') == 'ideas' || result.get('type') == 'events')) {
    		util.log('Liking cancelled - invalid result type for liking: ' + result.get('type'))
    		return;
    	}
    	
    	var to_like = result.get('liked') ? '0' : '1';
    	var unliked_count = result.get('participant_count') - (result.get('liked') ? 1 : 0);
    	data['like'] = to_like;
    	// if we unlike an idea, also unfollow it
    	if (to_like == '0' && result.get('type') == 'ideas') {
    		data['follow'] = '0';
    	}
    	
    	util.log('Sending like request for slug "' + result.get('slug') + '" and like: ' + to_like);
    	var likeHadErrors = false;
    	self.currentDetailHttpRequest = $.ajax(url, {
            type: 'POST',
            timeout: self.searchXHRTimeout,
            data: data,
            success: function (data, textStatus) {
                
                util.log('got resultssss for like')
                util.log(data)
                util.log(textStatus)
                
                if ('liked' in data) {
                	// for ideas, "participants" are the likers
                	if (result.get('type') == 'ideas') {
                		result.set('participant_count', unliked_count + (data.liked ? 1 : 0));
                	}
                	// graphics update happens here, via subscriptions on change:liked
                	result.set('liked', data.liked);
                	result.set('followed', data.followed);

                	// for ideas, a like triggers a follow, so show the now-following message
                	if (result.get('type') == 'ideas' && data.followed) {
                		self.App.$el.find('.now-following-message').show();
                	}
                } 
            },
            error: function (xhr, textStatus) {
                util.log('control-view.js: Like XHR failed.')
                likeHadErrors = true;
            },
            complete: function (xhr, textStatus) {
                util.log('control-view.js: Like complete: ' + textStatus);
                
                if (textStatus !== 'success') {
                	likeHadErrors = true;
                }
                if (likeHadErrors) {
                    $('.like-button-error').show();
                }
            }
        });
    },
    

    /** Will follow/unfollow a given result, depending on the current followed status */
    triggerResultFollowOrUnfollow: function (result) {
    	var self = this;
    	var url = '/likefollow/'
    		
    	var data = util.getAPIDataForDirectItemId(result.get('id'));
    	if (data == null) {
    		util.log('Following cancelled - invalid result type for liking: ' + result.get('type'));
    		return;
    	}
    	var to_follow = result.get('followed') ? '0' : 1;
    	data['follow'] = to_follow;
    	
    	util.log('Sending follow request for slug "' + result.get('slug') + '" and follow: ' + to_follow);
    	var followHadErrors = false;
    	self.currentDetailHttpRequest = $.ajax(url, {
            type: 'POST',
            timeout: self.searchXHRTimeout,
            data: data,
            success: function (data, textStatus) {
                
                util.log('got resultssss for follow')
                util.log(data)
                util.log(textStatus)
                
                if ('followed' in data) {
                    result.set('followed', data.followed);
                    // graphics update happens via subscriptions on change:followed
                	if (data.followed) {
                		self.App.$el.find('.now-following-message').show();
                	}
                } 
            },
            error: function (xhr, textStatus) {
                util.log('control-view.js: Follow XHR failed.')
                followHadErrors = true;
            },
            complete: function (xhr, textStatus) {
                util.log('control-view.js: Follow complete: ' + textStatus);
                
                if (textStatus !== 'success') {
                	followHadErrors = true;
                }
                if (followHadErrors) {
                    $('.follow-button-error').show();
                }
            }
        });
    },
    
    /** Called manually or deferredly after loading a Result from the server,
     *  to be shown as the Detail View.
     *  @param result: This must be *a detailed* Result model, or null!
     *  Calling this with `null` as parameter closes any open detail view. */
    displayDetailResult: function (result) {
        // we simply unselect the current result
        if (!result) {
            this._setSelectedResult(null);
            this.detailResult = null;
            Backbone.mediator.publish('result:detail-closed');
            return;
        }
        
        // try to find the result with this short id in our collection and set it to selected
        var collectionModel = this.collection.get(result.id);
        if (collectionModel) {
            this._setSelectedResult(collectionModel);
        } else {
            this._setSelectedResult(null);
        }
        // publish the opening intent for the detail view (it does not need to be in our collection)
        this.detailResult = result;
        Backbone.mediator.publish('result:detail-opened', result);
    },
    
    /** State switcher for the filter frame */
    toggleFilterPanel: function (event) {
        if (event) {
            event.preventDefault();
        }
        if (this.state.filterPanelVisible) {
            this.hideFilterPanel(event);
        } else {
            this.showFilterPanel(event);
        }
    },

    /** State switcher for the filter frame */
    showFilterPanel: function (event) {
        if (event) {
            event.preventDefault();
        }
        this.state.filterPanelVisible = true;
        this.$el.find('.map-controls-filters').slideDown(250);
        this.$el.find('.icon-filters').addClass('open');
    },

    /** State switcher for the filter frame */
    hideFilterPanel: function (event) {
        if (event) {
            event.preventDefault();
        }
        this.state.filterPanelVisible = false;
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

    handleStartSearch: function (searchReason) {
        this.$el.find('.icon-loading').removeClass('hidden');
        this.$el.find('.icon-reset').addClass('hidden');
        this.$el.find('.q').blur();
        // disable input in content views during search (up to the views to decide what to disable)
        // except if we are only adding some results after an infinite scroll event
        if (!(this.options.paginationControlsUseInfiniteScroll && searchReason == 'paginate-search')) {
        	_.each(this.App.contentViews, function(view){
        		view.disableInput();
        	});
        }
        
    },

    handleEndSearch: function (searchReason) {
        this.$el.find('.icon-loading').addClass('hidden');
        this.$el.find('.icon-reset').toggleClass('hidden', (!this.state.filtersActive && !this.state.q));
        // enable input in content views during search (up to the views to decide what to enable)
        _.each(this.App.contentViews, function(view){
            view.enableInput();
        });
    },

    /** Called when the App is fully loaded for the first time.
     * 	This is the initial search.
     *     WARNING: Due to the threaded after_render() method, this may
     *         currently actually happen before a full load.
     *  */
    handleAppReady: function (event) {
        util.log('control-view.js: app is ready to search. starting search from URL!')
        this.triggerSearchFromUrl();
    },
    
    /** Executed *every time* after render */
    afterRender: function () {
        var self = this;
        // Create the pagination control view if not exists
        if (!self.paginationControlView && self.options.paginationControlsEnabled && self.App.tileListView) {
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
        if (!self.mobileControlView) {
            // render mobile view buttons
            self.mobileControlView = new MobileControlView({
                model: null,
                elParent: self.App.el,
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
        this.resetAll();
        var urlParams = this.parseUrl(window.location.href.replace(window.location.origin, ''));
        // if infinite scroll is enabled, always show the initial page, unscrolled and unpaginated
        if (this.options.paginationControlsUseInfiniteScroll && 'page' in urlParams) {
        	delete urlParams.page;
        }
        _.each(this.App.contentViews, function(view){
            view.applyUrlSearchParameters(urlParams);
        });
        this.determineActiveFilterStatuses();
        this.render();
        this.triggerDelayedSearch(true, true, noNewNavigateEvent, 'initial-search');
    },
    
    /**
     * The context can contain `reason` for a signal for out-of-date result sets:
     * - viewport-changed: The map was scrolled or window was resized
     * - map-navigate: Router navigate on the map (not called during initial navigation)
     * - ...
     */
    handleStaleResults: function (context) {
        if (context.reason == 'viewport-changed') {
            util.log('*** control-view.js: Received signal for stale results bc of viewport change')
        } else if (context.reason == 'map-navigate') {
            util.log('*** control-view.js: Received signal for stale results bc of map-navigate')
        }
        
        // prevent refreshing results on viewport changes when the mobile view search panel is open,
        // as this is triggered by onscreen keyboards and leads to choppy behaviour
        if (context.reason == 'viewport-changed' && this.App.$el.hasClass('mobile-view-search')) {
        	util.log('*** control-view.js: Prevented refresh of results while search panel is open.')
        	return;
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
                	var noPaginationReset = context.reason == 'viewport-changed';
                    this.triggerDelayedSearch(false, noPaginationReset, false, context.reason);
                } else {
                    util.log('control-view.js: Prevented a search while input is focused!')
                }
            } else {
                // re-render controls so the manual search button will be enabled
                if (!staleBefore) {
                	if (this.paginationControlView) {
                		this.paginationControlView.render();
                	}
                }
            }
        }
    },
    
    /** Adds the current search state, including all parameters and detail view state 
     *  as a URL history state.
     */
    addCurrentHistoryState: function () {
        var self = this;
        Backbone.mediator.publish('navigate:router', self.buildSearchQueryURL(false).replace(self.searchEndpointURL, '/'))
    },
    
    // called with a list of dicts of results freshly returned after a search
    processSearchResults: function (jsonResultList, searchReason) {
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
        
        // if infinite-scroll is active, and this search has been triggered by a paginate event,
        // we add the results to the collection instead of replacing them.
        if (self.options.paginationControlsUseInfiniteScroll && searchReason == 'paginate-search') {
        	self.collection.add(resultModels);
        } else {
        	self.collection.reset(resultModels);
        	
        	// if we had a navigate event and we still have a detail-view open, but it's not in the URL, close it
        	// happens on back/forward buttons, but also on scroll events (where we don't want to close the detail view)
        	if (self.detailResult && !self.state.urlSelectedResultId && !(searchReason == 'viewport-changed')) {
        		self.displayDetailResult(null);
        	} 
        }
        
        // if our URL points directly at an item, select it.
        // the API should take care that it is *always* in the result set
        if (self.state.urlSelectedResultId && (!self.detailResult || self.state.urlSelectedResultId != self.detailResult.id)) {
            self.onResultLinkClicked(null, self.state.urlSelectedResultId, true);
            self.state.urlSelectedResultId = null;
        }
        
    },
    
    // public functions
    
    /**
     * Will set a new selected result and un-set the old one.
     * If result == null, will just un-set the current one.
     */
    _setSelectedResult: function (result) {
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
            this.setHoveredResult(null); // always unhover on select
            
            /** this no longer has any validity
            // selecting a result changes the URL so results can be directly linked
            if (App.displayOptions.routeNavigation) {
                var newUrl = this.buildSearchQueryURL(false).replace(this.searchEndpointURL, this.options.basePageURL);
                App.router.replaceUrl(newUrl);
            }
            */
        }
    },
    
    /**
     * Will set a new hovered result and un-set the old one.
     * If result == null, will just un-set the current one.
     */
    setHoveredResult: function (result) {
        if (result && result == this.selectedResult) {
            return; // prevent setting hovered state on the currently selected result
        }
        if (this.hoveredResult != null) {
            this.hoveredResult.set('hovered', false);
        }
        this.hoveredResult = result;
        if (this.hoveredResult != null) {
            this.hoveredResult.set('hovered', true);
        }
    },
    
    
    /** determine if any filtering method is active (topics or result types) */
    determineActiveFilterStatuses: function () {
        var self = this;
        self.state.filtersActive = false;
        self.state.topicFiltersActive = false;
        self.state.sdgFiltersActive = false;
        self.state.managedTagsFiltersActive = false;
        self.state.typeFiltersActive = false;
        
        if (self.state.activeTopicIds.length > 0) {
            self.state.filtersActive = true;
            self.state.topicFiltersActive = true;
        }
        if (self.state.activeSDGIds.length > 0) {
            self.state.filtersActive = true;
            self.state.sdgFiltersActive = true;
        }
        if (self.state.activeManagedTagsIds.length > 0) {
            self.state.filtersActive = true;
            self.state.managedTagsFiltersActive = true;
        }

        _.each(Object.keys(self.options.availableFilters), function(key) {
            if (self.options.availableFilters[key] != self.state.activeFilters[key]) {
                self.state.filtersActive = true;
                self.state.typeFiltersActive = true;
            }
        });
    },

    search: function (noNavigate, searchReason) {
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
                if (App.displayOptions.routeNavigation && !noNavigate && !self.selectedResult) {
                    util.log('control-view.js: +++++++++++++++++ since we are fullscreen, publishing router URL update!')
                    self.addCurrentHistoryState();
                }
                util.log('got resultssss')
                util.log(data)
                util.log(textStatus)
                var results = data.results;
                self.processSearchResults(results, searchReason);
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
                    self.determineActiveFilterStatuses();
                    self.refreshSearchControls();
                    if (searchReason == 'manual-search') {
                        self.hideFilterPanel();
                    }
                    self.renderActiveFilters();
                    // refresh pagination controls
                    if (self.paginationControlView) {
                    	self.paginationControlView.render();
                    }
                    // if we have done a manual search, set the view to default!
                    if (searchReason == 'manual-search') {
                        self.triggerMobileDefaultView(event);
                    }
                    // scroll tile list to top on manual searches
                    if (searchReason == 'manual-search' || searchReason == 'reset-filters-search' || (searchReason == 'paginate-search' && !self.options.paginationControlsUseInfiniteScroll)) {
                        $('.tile-contents').scrollTop(0); // scroll to top on tile list
                    }
                }
                
                self.currentSearchHttpRequest = null;
                Backbone.mediator.publish('end:search', searchReason);
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
                people: this.options.availableFilters.people ? util.ifundef(urlParams.people, this.options.activeFilters.people) : false,
                events: this.options.availableFilters.events ? util.ifundef(urlParams.events, this.options.activeFilters.events) : false,
                projects: this.options.availableFilters.projects ? util.ifundef(urlParams.projects, this.options.activeFilters.projects) : false,
                groups: this.options.availableFilters.groups ? util.ifundef(urlParams.groups, this.options.activeFilters.groups) : false
            },
            q: util.ifundef(urlParams.q, this.state.q),
            ignoreLocation: util.ifundef(urlParams.ignore_location, this.state.ignoreLocation),
            searchResultLimit: util.ifundef(urlParams.limit, this.state.searchResultLimit),
            activeTopicIds: util.ifundef(urlParams.topics, this.state.activeTopicIds),
            activeSDGIds: util.ifundef(urlParams.sdgs, this.state.activeSDGIds),
            activeManagedTagsIds: util.ifundef(urlParams.managed_tags, this.state.activeManagedTagsIds),
            pageIndex: util.ifundef(urlParams.page, this.state.pageIndex),
            urlSelectedResultId: util.ifundef(urlParams.item, this.state.urlSelectedResultId),
        });
        if (COSINNUS_IDEAS_ENABLED) {
        	this.state.activeFilters['ideas'] = this.options.availableFilters.ideas ? util.ifundef(urlParams.ideas, this.options.activeFilters.ideas) : false;
        }
        if (COSINNUS_ORGANIZATIONS_ENABLED) {
        	this.state.activeFilters['organizations'] = this.options.availableFilters.organizations ? util.ifundef(urlParams.organizations, this.options.activeFilters.organizations) : false;
        }
        if (cosinnus_active_user) {
        	this.options.showMine = util.ifundef(urlParams.mine, this.options.showMine);
        }
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
        if (COSINNUS_IDEAS_ENABLED) {
        	_.extend(searchParams, {
                ideas: this.state.activeFilters.ideas
            });
        }
        if (COSINNUS_ORGANIZATIONS_ENABLED) {
        	_.extend(searchParams, {
        		organizations: this.state.activeFilters.organizations
            });
        }
        if (this.state.activeTopicIds.length > 0) {
            _.extend(searchParams, {
                topics: this.state.activeTopicIds.join(',')
            });
        }
        if (this.state.activeSDGIds.length > 0) {
            _.extend(searchParams, {
                sdgs: this.state.activeSDGIds.join(',')
            });
        }
        if (this.state.activeManagedTagsIds.length > 0) {
            _.extend(searchParams, {
                managed_tags: this.state.activeManagedTagsIds.join(',')
            });
        }
        if (this.state.pageIndex > 0) {
            _.extend(searchParams, {
                page: this.state.pageIndex
            });
        }
        if (this.detailResult) {
            _.extend(searchParams, {
                item: this.detailResult.id
            });
        } else if (this.state.urlSelectedResultId) {
            _.extend(searchParams, {
                item: this.state.urlSelectedResultId
            });
        }
        if (this.options.showMine) {
            _.extend(searchParams, {
            	mine: 1
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
     *         if false, contains only these that should be visible in the browser URL 
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
        url = url + '?' + query;
        
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
            self.resetTypeFilters();
        }
        
        // Topics
        self.resetTopics();
        self.$el.find('.topic-button.selected').each(function(){
            var $button = $(this);
            var bid = parseInt($button.attr('data-topic-id'));
            self.state.activeTopicIds.push(bid);
        });

        // SDGs
        self.resetSDGS();
        self.$el.find('.sdg-button.selected').each(function(){
            var $button = $(this);
            var bid = parseInt($button.attr('data-sdg-id'));
            self.state.activeSDGIds.push(bid);
        });
        
        // ManagedTags
        self.resetManagedTags();
        self.$el.find('.managed-tag-button.selected').each(function(){
            var $button = $(this);
            var bid = parseInt($button.attr('data-managed-tag-id'));
            self.state.activeManagedTagsIds.push(bid);
        });
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
    triggerDelayedSearch: function (fireImmediatelyIfPossible, noPageReset, noNavigate, searchReason) {
        var self = this;
        
        var delay = self.searchDelay;
        if (fireImmediatelyIfPossible) {
            delay = 0;
        }
        if (!noPageReset) {
            self.state.pageIndex = 0;
        }
        clearTimeout(this.searchTimeout);
    	Backbone.mediator.publish('want:search', searchReason);
        self.searchTimeout = setTimeout(function () {
            self.search(noNavigate, searchReason);
        }, delay);
    },

    activeFilterList: function () {
        return _(_(this.state.activeFilters).keys()).select(function (filter) {
            return !!filter;
        });
    },
    
});
