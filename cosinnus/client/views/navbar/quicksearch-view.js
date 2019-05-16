'use strict';

var BaseView = require('views/base/view');
var QuicksearchResultView = require('views/navbar/quicksearch-result-view');
var util = require('lib/util');

module.exports = BaseView.extend({

	app: null,
	
    template: require('navbar/quicksearch'),
    
    // QuicksearchResult collection
    collection: null,
    
    // will be set to self.options during initialization
    defaults: {
        
        state: {
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	'focus .nav-search-box': 'onSearchBoxFocusIn',
    	'click .nav-button-search': 'onSearchIconClicked',
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        
        // TODO!
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
        // typing listener
        self.$el.find('#search').off('keyup').on('keyup', self.thisContext(self.onTextInput));
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        data['more'] = 'lol';
        return data;
    },
    
    /** Handles events for infinite scroll */
    onTextInput: function (event) {
    	var self = this;
    	
    	var $input = $(event.target);
    	var text = $input.val().trim();
    	util.log('quicksearch got search input ' + text);
    	if (text.length > 0) {
    		// TODO: show first results, fire query
    		self.showDropdown();
    	} else {
    		//self.hideDropdown(); we never hide, just ender something different
    	}
    },
    
    /** Searchbox focused */
    onSearchBoxFocusIn: function (event) {
    	this.showDropdown();
    },
    
    /** Shows the quicksearch result list */
    showDropdown: function () {
    	util.log('*** Showing quicksearch results ***')
    	var dropdown = this.$el.find('.nav-quicksearch-results');
    	this.$el.find('.dropdown-underdrop').height(dropdown.outerHeight());
    	document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	this.$el.addClass('active');
    },
    
    /** Hides the quicksearch result list */
    hideDropdown: function () {
    	util.log('*** Hiding quicksearch results ***')
    	this.$el.find('.nav-quicksearch-results').hide();
    },
    
    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
    	if (this.$el.hasClass('active') && !this.el.contains(event.target)) {
    		this.$el.removeClass('active');
    		document.removeEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	}
    },
    
    onSearchIconClicked: function (event) {
    	if (this.$el.hasClass('active') && 0 == 1) { // todo check for has text
    		// todo: fire search
    	} else {
    		this.$el.find('.nav-search-box').focus();
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
