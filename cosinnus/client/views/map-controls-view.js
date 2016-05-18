'use strict';

var View = require('views/base/view');
var template = require('map/map-controls');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
    },

    events: {
        'click .result-filter': 'toggleFilter',
        'click .reset-filters': 'resetFilters'
    },

    // Event Handlers
    // --------------

    toggleFilter: function (event) {
        var type = $(event.currentTarget).attr('id');
        this.model.set(type, !this.model.get(type));
    },

    resetFilters: function (event) {
        event.preventDefault();
        this.model.resetFilters();
        this.render();
    }
});
