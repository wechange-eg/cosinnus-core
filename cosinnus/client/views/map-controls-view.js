'use strict';

var View = require('views/base/view');
var template = require('map/map-controls');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
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
        if (query.length > 2) {
            this.model.set({
                q: query
            });
            this.model.wantsToSearch();
            
        }
    }
});
