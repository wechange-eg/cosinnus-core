'use strict';

module.exports = Backbone.Model.extend({
    default: {
        filters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        layer: 'street'
    },

    initialize: function () {
        this.set('filters', _(this.default.filters).clone());
        this.set('layer', this.default.layer);
        this.searchDelay = 0;
    },

    search: function (callback) {
        var self = this;

        // Retrieve active filters.
        var activeTypes = _(_(this.default.filters).keys()).select(function (filter) {
            return self.get('filters')[filter];
        });

        // Generate some random markers for each of the active filter types
        // in the current map viewport.
        var results = [];
        _(activeTypes).each(function (type) {
            _(15).times(function () {
                var lat = self.get('south') + Math.random() * (self.get('north') - self.get('south'));
                var lon = self.get('west') + Math.random() * (self.get('east') - self.get('west'));

                results.push({
                    type: type,
                    lat: lat,
                    lon: lon
                });
            });
        });

        self.set('results', results);
        self.trigger('change:results');
    },

    toggleFilter (resultType) {
        var filters = this.get('filters');
        filters[resultType] = !filters[resultType];
        this.set('filters', filters);
        this.wantsToSearch();
    },

    resetFilters: function () {
        this.set('filters', _(this.default.filters).clone());
        this.wantsToSearch();
    },

    wantsToSearch: function () {
        var self = this;
        clearTimeout(this.searchTimeout);
        self.searchTimeout = setTimeout(function () {
            self.search();
        }, self.searchDelay);
    }
});
