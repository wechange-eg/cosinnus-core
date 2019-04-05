'use strict';

var BaseView = require('views/base/view');
var ContentControlView = require('views/base/content-control-view');
var TileView = require('views/tile-view');
var util = require('lib/util');

module.exports = ContentControlView.extend({

    template: require('tiles/tile-list'),
    
    // Marker storage dict of {<resultModel.id>: tileView, ...}
    // id corresponds to self.collection.get(<id>)
    // updated through the handlers of self.collection's signals
    tiles: {},
    
    // the Masonry grid for our tiles
    grid: null,
    
    // on every inputs disable, that thread +1s this counter it and may only
    // re-enable inputs if the counter stayed the same in the meantime
    // (i.e. no new threads are running now) to prevent enabled inputs on working threads
    disableCounter: 0,
    
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
        // this calls self.applyUrlSearchParameters()
        ContentControlView.prototype.initialize.call(self, options, app, collection);
        
        // result events
        self.collection.on({
           'add' : self.thisContext(self.tileAdd),
           'change:hovered': self.thisContext(self.tileChangeHover),
           'change:selected': self.thisContext(self.tileChangeSelected),
           'change': self.thisContext(self.tileUpdate),
           'remove': self.thisContext(self.tileRemove),
           'update': self.thisContext(self.tilesUpdate),
           'reset': self.thisContext(self.tilesReset),
        });
        
        Backbone.mediator.subscribe('error:search', self.onSearchError, self);

        Backbone.mediator.subscribe('tile-detail:opened', self.onTileDetailOpened, self);
        Backbone.mediator.subscribe('tile-detail:closed', self.onTileDetailClosed, self);
    },

    render: function () {
        var self = this;
        ContentControlView.prototype.render.call(self);
        
        self.renderTilesInitial();
        
        // scroll listener
        self.$el.find('.tile-contents').off('scroll').on('scroll', self.onTileListScrolled);
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        data['controlView'] = _.extend(
            {},
            self.App.controlView.options,
            self.App.controlView.state
        );
        return data;
    },
    
    afterRender: function () {
        var self = this;
    },
    
    /** Shows and reloads the tile view */
    reload: function () {
    	util.log('*** Reloading Tile View ***')
    	this.$el.toggleClass('tile-list-splitscreen', this.options.splitscreen);
    	this.$el.toggleClass('tile-list-tile-fullscreen', !this.options.splitscreen);
        this.$el.show();
    },
    
    /** Hides the tile view */
    hide: function () {
    	util.log('*** Hiding Tile View ***')
    	this.$el.hide();
    },
    
    /** Handles events for infinite scroll */
    onTileListScrolled: function (event) {
    	var $list = $(event.target);
    	if ($list.scrollTop() + $list.innerHeight() >= $list[0].scrollHeight - 250) {
        	Backbone.mediator.publish('tile-list:scroll-end-reached');
    	}
    },
    
    
    // extended from content-control-view.js
    applyUrlSearchParameters: function (urlParams) {
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
    
    /** Swaps out a new tile set by disabling the tile list interaction, 
     *     loading the new tiles into a seperate container, waiting until all their
     *  images have loaded, and then swapping in the new container for the old one. */ 
    swapTileset: function(newTileModels) {
        var self = this;
        var $old_grid = self.grid;
        var old_tiles = self.tiles;
        self.tiles = {};
        
        // disable tile view, set old container aside above the new one
        self.disableInput();
        self.disableCounter += 1;
        var localDisableCounter = self.disableCounter;
        if ($old_grid) {
            $old_grid.removeAttr('id').css({'z-index': 1});
        }
        // load new tiles into new container (which is covered by old)
        self.grid = self.$el.find('#tile-container-proto')
            .clone()
            .attr('id', 'tile-container')
            .appendTo(self.$el.find('#tile-container-proto').parent())
            .show();
        // use a local grid variable because new threads might
        // swap out self.grid before imagesloaded resolves
        var grid = self.grid;
        
        _.each(newTileModels, function(result){
            self.tileAdd(result);
        });
        
        grid.imagesLoaded( function() { 
            grid.masonry({
                // set itemSelector so .grid-sizer is not used in layout
                itemSelector: '.grid-item',
                // use element for option
                columnWidth: '.grid-sizer',
                percentPosition: true,
                transitionDuration: 0
            });
            
            if ($old_grid) {
                $old_grid.hide();
            }
            // re-enable tile-view input unless a new thread is now running
            if (self.disableCounter == localDisableCounter) {
                self.enableInput(true);
            }
            
            // cleanly remove old tile views and old grid to not cause leaks
            if (old_tiles) {
                _.each(old_tiles, function(tile){
                    tile.remove();
                });
            }
            if ($old_grid) {
                $old_grid.remove();
            }
        });
        
        util.log('TODO: add a case for imagesLoaded() never triggering!')
    },
    
    /** Orders Masonry to reorder tiles after a refresh */
    gridRefresh: function () {
        var self = this;
        self.grid.imagesLoaded( function() { 
            self.grid.masonry('reloadItems');
            self.grid.masonry('layout')
        });
    },
    
    disableInput: function() {
        this.$el.addClass('disabled');
    },
    
    enableInput: function(local_enable) {
        // we ignore the enable signal from the content view and only
        // re-enable the tile view once we have rendered the results.
        if (local_enable) {
            this.$el.removeClass('disabled');
        }
    },

    onTileDetailOpened: function () {
    	this.App.$el.addClass('tile-detail-open');
    	this.App.tileListView.gridRefresh();
    },
    
    onTileDetailClosed: function () {
    	this.App.$el.removeClass('tile-detail-open');
    	this.App.tileListView.gridRefresh();
    },
    
    
    
    onSearchError: function() {
        // when the search fails, re-enable the tile-list
        this.enableInput(true);
    },
    
    // Private
    // -------

    renderTilesInitial: function () {
        // nothing to do here for now
    },

});
