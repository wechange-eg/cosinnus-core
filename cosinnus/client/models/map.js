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
        this.searchDelay = 1000,
        this.whileSearchingDelay = 5000;
    },

    search: function () {
        var self = this;
        var url = this.buildURL();
        self.trigger('start:search');
        self.set('searching', true);
        $.get(url, function (res) {
            self.set('results', res);
            self.trigger('change:results');
            self.trigger('end:search');
            self.set('searching', false);
            // If there is a queued search, requeue it.
            if (self.get('wantsToSearch')) {
                self.attemptSearch();
            }
        });
    },

    buildURL: function () {
        var searchParams = {
            q: this.get('q'),
            ne_lat: this.get('north'),
            ne_lon: this.get('east'),
            sw_lat: this.get('south'),
            sw_lon: this.get('west'),
            people: this.get('filters').people,
            events: this.get('filters').events,
            projects: this.get('filters').projects,
            groups: this.get('filters').groups
        };
        var query = $.param(searchParams);
        return '/maps/search?' + query;
    },

    toggleFilter (resultType) {
        var filters = this.get('filters');
        filters[resultType] = !filters[resultType];
        this.set('filters', filters);
        this.attemptSearch();
    },

    resetFilters: function () {
        this.set('filters', _(this.default.filters).clone());
        this.attemptSearch();
    },

    // Register a change in the controls or the map UI which should queue
    // a search attempt.
    attemptSearch: function () {
        var self = this,
            delay = self.get('searching') ?
                self.whileSearchingDelay : self.searchDelay;
        clearTimeout(this.searchTimeout);
        self.set('wantsToSearch', true);
        self.searchTimeout = setTimeout(function () {
            self.search();
            self.set('wantsToSearch', false);
        }, delay);
    },

    mockSearchService: function (url, cb) {
        var json = JSON.parse('{"' + decodeURI(url.replace('/map/search?', '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
        _(_(json).keys()).each(function (key) {
            if (json[key] !== '') {
                try {
                    json[key] = JSON.parse(json[key]);
                } catch (err) {}
            }
        })
        // Retrieve active filters.
        var activeTypes = _(_(this.default.filters).keys()).select(function (filter) {
            return json[filter];
        });
        // Generate some random markers for each of the active filter types
        // in the current map viewport.
        var results = [];
        _(activeTypes).each(function (type) {
            _(60).times(function () {
                var lat = json['south'] + Math.random() * (json['north'] - json['south']);
                var lon = json['west'] + Math.random() * (json['east'] - json['west']);

                results.push({
                    type: type,
                    lat: lat,
                    lon: lon,
                    title: 'Title',
                    url: 'http://example.com',
                    imageUrl: '/static/images/group-avatar-placeholder.png',
                    address: '2 High St.'
                });
            });
        });
        cb(results);
    },

    activeFilters: function () {
        return _(_(this.get('filters')).keys()).select(function (filter) {
            return !!filter;
        });
    }
});
