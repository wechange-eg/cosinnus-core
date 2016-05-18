'use strict';

module.exports = Backbone.Model.extend({
    initialize: function () {
        this.set(this.defaultFilters);
    },

    search: function (callback) {
        var self = this;

        // Generate some mock data.

        var activeTypes = _(_(this.defaultFilters).keys()).select(function (filter) {
            return self.get(filter);
        });

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

        callback(results);
    },

    defaultFilters: {
        people: true,
        events: true,
        projects: true,
        groups: true
    },

    resetFilters: function () {
        this.set(this.defaultFilters);
    }
});
