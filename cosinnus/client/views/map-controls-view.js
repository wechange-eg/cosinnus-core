'use strict';

var View = require('views/base/view');
var template = require('map/map-controls');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
    },

    events: {
        'click .result-filter': 'toggleFilter',
        'click .reset-filters': 'resetFilters',
        'click .layer-button': 'switchLayer'
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
    }
});
