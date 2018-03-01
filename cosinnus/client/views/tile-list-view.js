'use strict';

var ContentControlView = require('views/base/content-control-view');
var TileView = require('views/tile-view');
var util = require('lib/util');

module.exports = ContentControlView.extend({

	template: require('tiles/tile-list'),
	
    // Marker storage dict of {<resultModel.id>: tileView, ...}
    // id corresponds to self.collection.get(<id>)
    // updated through the handlers of self.collection's signals
    tiles: {},
    
    // will be set to self.options during initialization
    defaults: {
    	// is the window in full-screen mode (instead of inside a widget or similar)
    	fullscreen: true,
    	
    	// is this view shown together with the map view as a 50% split screen?
    	splitscreen: false,
    	
	    state: {
	    	
	    }
    },
    
    initialize: function (options, app, collection) {
        var self = this;
        // this calls self.initializeSearchParameters()
        ContentControlView.prototype.initialize.call(self, options, app, collection);
        
        // result events
        self.collection.on({
    	   'add' : self.thisContext(self.tileAdd),
    	   'change:hovered': self.thisContext(self.tileChangeHover),
    	   'change:selected': self.thisContext(self.tileChangeSelected),
    	   'change': self.thisContext(self.tileUpdate),
    	   'remove': self.thisContext(self.tileRemove),
    	   'reset': self.thisContext(self.tilesReset),
    	});
    },

    render: function () {
    	var self = this;
        ContentControlView.prototype.render.call(self);
    	self.renderTilesInitial();
    	return self;
    },
    
    afterRender: function () {
        var self = this;
    },
    
    // extended from content-control-view.js
    initializeSearchParameters: function (urlParams) {
    	// don't need this here
    },
    
    // extended from content-control-view.js
    contributeToSearchParameters: function(forAPI) {
    	// don't need this here
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

    tileChangeHover: function(result) {
    	
    },
    
    tileChangeSelected: function(result) {
    	
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
    
    /** Handler for when the entire collection changes */
    tilesReset: function(resultCollection, options) {
    	var self = this;
    	_.each(options.previousModels, function(result){
    		self.tileRemove(result);
    	});
    	_.each(resultCollection.models, function(result){
    		self.tileAdd(result);
    	});
    },
    
    
    // Private
    // -------

    renderTilesInitial: function () {
    	
    },

});
