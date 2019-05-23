'use strict';

var BaseView = require('views/base/view');
var QuicksearchResultView = require('views/navbar/quicksearch-result-view');
var util = require('lib/util');

module.exports = BaseView.extend({

	app: null,
	
    template: require('navbar/quicksearch'),
    
    // QuicksearchResult collection
    collection: null,
    
    // the parent el, containing the search textbox and button
    $searchBarEl: null,
    
    // will be set to self.options during initialization
    defaults: {
    	query: null,
    	searchMethods: {
    		'default': '/search/?q={{q}}',
    		'map': '/map/?q={{q}}',
    		'groups': '/search/?groups=mine&q={{q}}',
    	},
    	topicsSearchMethods: {
    		// <title>: <url>,
    	},
    	// this will be added to the state.topicsSearchMethods for matching topics
    	topicsUrl: '/map/?topics={{t}}',
        
        state: {
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        
        self.$searchBarEl = $('#nav-quicksearch');
        // events that have to be defined here because they happen in the searchBarEl:
        self.$searchBarEl.on('focus', '.nav-search-box', self.thisContext(self.onSearchBoxFocusIn));
        self.$searchBarEl.on('keydown', '.nav-search-box', self.thisContext(self.onSearchBoxKeyDown));
        self.$searchBarEl.on('input', '.nav-search-box', self.thisContext(self.onSearchBoxTyped));
        self.$searchBarEl.on('click', '.nav-button-search', self.thisContext(self.onSearchIconClicked));
        
        // TODO: add a collection for quicksearch DB results!
        return;
        
        // result events
        self.collection.on({
           'add' : self.thisContext(self.tileAdd),
           'change': self.thisContext(self.tileUpdate),
           'remove': self.thisContext(self.tileRemove),
           'update': self.thisContext(self.tilesUpdate),
           'reset': self.thisContext(self.tilesReset),
        });
        
    },

    render: function () {
        var self = this;
        BaseView.prototype.render.call(self);
        
        util.log('*** Rendered quicksearch! ***')
        console.log(self.options.topicsJson)
    	this.$searchBarEl.find('.dropdown-underdrop').height(this.$el.outerHeight());
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        return data;
    },
    
    /** Searchbox focused */
    onSearchBoxFocusIn: function (event) {
    	this.showDropdown();
    },
    
    /** Searchbox key downs, for special keys */
    onSearchBoxKeyDown: function (event) {
    	if (event.keyCode == 13) {
    		this.fireSearch();
    	}
    },
    
    /** Searchbox text input */
    onSearchBoxTyped: function (event) {
    	if (!event.shiftKey && !event.ctrlKey) {
    		this.updateSearchSuggestions();
    	}
    },
    
    /** rerenders the list of clickable search suggestions, e.g. after new input was made */
    updateSearchSuggestions: function () {
    	var self = this;
    	var query = self.getCurrentQuery();
    	
    	// apply the current query to the urls in searchMethods
    	var searchMethods = _(self.options.searchMethods).clone();
    	for (var method in searchMethods) {
    		searchMethods[method] = searchMethods[method].replace('{{q}}', encodeURIComponent(query));
    	}
    	self.state.searchMethods = searchMethods;
    	// match topics to the current query and generate topic search suggestions
    	var topicsSearchMethods = {};
    	for (var topicId in self.options.topicsJson) {
    		var topic = self.options.topicsJson[topicId];
    		if (topic.toLowerCase().indexOf(query.toLowerCase()) > -1) {
    			var title = util.iReplace(topic, query, '<b>$1</b>');
    			var url = self.options.topicsUrl.replace('{{t}}', topicId);
    			topicsSearchMethods[title] = url;
    		}
    	}
    	self.state.topicsSearchMethods = topicsSearchMethods
    	
    	self.state.query = query || null;
    	self.render();
    },

    /** Get the text from the search box */
    getCurrentQuery: function() {
    	return this.$searchBarEl.find('.nav-search-box').val().trim();
    },
    
    /** Fire off a search. If no arguments given, fires the default search
     * 	with the currently entered text */
    fireSearch: function (type, query) {
    	var self = this;
    	if (!type) {
    		type = 'default';
    	}
    	if (!query) {
    		query = self.getCurrentQuery();
    	}
    	if (query && query.length > 0) {
    		var url = self.options.searchMethods[type].replace('{{q}}', encodeURIComponent(query));
    		window.location = url;
    	} 
    },
    
    /** Shows the quicksearch result list */
    showDropdown: function () {
    	util.log('*** Showing quicksearch results ***')
    	document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	this.$searchBarEl.addClass('active');
    },
    
    /** Hides the quicksearch result list */
    hideDropdown: function () {
    	util.log('*** Hiding quicksearch results ***')
    	this.$el.hide();
    },
    
    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
    	if ((this.$searchBarEl.hasClass('active') && !this.$searchBarEl[0].contains(event.target)) 
				|| $(event.target).hasClass('nav-search-backdrop')) {
    		this.$searchBarEl.removeClass('active');
    		document.removeEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	}
    },
    
    onSearchIconClicked: function (event) {
    	if (this.$searchBarEl.hasClass('active') && 0 == 1) { // todo check for has text
    		this.fireSearch();
    	} else {
    		this.$searchBarEl.find('.nav-search-box').focus();
    	}
    },
    
    
    // ResultCollection Event handlers
    // --------------

    tileAdd: function(result) {
        // adding a tile that is already there? impossibru! but best be sure.
        if (result.id in this.tiles) {
            this.tileRemove(result);
        }

        var tile = new TileView({
	            model: result,
	            elParent: '#tile-container',
	        }, 
	        this.App).render();
        this.tiles[result.id] = tile;
    },

    tileRemove: function(result) {
        if (result.get('selected')) {
            util.log('tile-list-view.js: TODO:: was ordered to remove a tile that is currently selected. NOT DOING ANYTHING RN!')
            return;
        }
        if (result.id in this.tiles) {
            var tile = this.tiles[result.id];
            
            tile.remove();
            
            delete this.tiles[result.id];
            util.log('Removed tile at ' + result.id);
        }
    },

    tileUpdate: function(result) {
        // don't use this trigger when only hovered/selected state was changed - they have their own handlers
        var attrs = result.changedAttributes();
        if (attrs && ('selected' in attrs || 'hovered' in attrs)) {
            return;
        }
        if (result.id in this.tiles) {
            var tile = this.tiles[result.id];
            tile.render();
        }
    },
    
    /** Handler for when tiles have been added to the collection, like after an infinite scroll event */
    tilesUpdate: function(resultCollection, options) {
        var self = this;

        self.gridRefresh();
        self.enableInput(true);
    },
    
    /** Handler for when the entire collection changes */
    tilesReset: function(resultCollection, options) {
        // options.previousModels contains the old models if we need them
        this.swapTileset(resultCollection.models);
    },
    
    

});
