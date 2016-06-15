'use strict';

module.exports = Backbone.Model.extend({
    default: {
        filters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        layer: 'street',
        limitWithoutClustering: 3
    },

    initialize: function () {
        var self = this;
        self.set('filters', _(self.default.filters).clone());
        self.set('layer', self.default.layer);
        self.searchDelay = 1000,
        self.whileSearchingDelay = 5000;
        Backbone.mediator.subscribe('navigate:map', function () {
            self.initialSearch();
        });
    },

    search: function () {
        var self = this;
        var url = self.buildURL(true);
        self.set('searching', true);
        $.get(url, function (res) {
            self.set('searching', false);
            self.trigger('end:search');
            // (The search endpoint is single-thread).
            // If there is a queued search, requeue it.
            if (self.get('wantsToSearch')) {
                self.attemptSearch();
            // Update the results if there isn't a queued search.
            } else {
                self.set('results', res);
                self.trigger('change:results');
                // Save the search state in the url.
                Backbone.mediator.publish('navigate:router', self.buildURL(false).replace('/maps/search', '/map/'))
            }
        }).fail(function () {
            self.set('searching', false);
            self.trigger('end:search');
            self.trigger('error:search');
        });
    },

    initialSearch: function () {
        var json = this.parseUrl(window.location.href.replace(window.location.origin, ''));
        if (_(json).keys().length) {
            this.set({
                filters: {
                    people: json.people,
                    events: json.events,
                    projects: json.projects,
                    groups: json.groups
                },
                q: json.q,
                north: json.ne_lat,
                east: json.ne_lon,
                south: json.sw_lat,
                west: json.sw_lon
            });
            this.trigger('change:bounds');
            this.trigger('change:controls');
        }
        this.search();
    },

    buildURL: function (padded) {
        var north = padded ? this.get('paddedNorth') : this.get('north');
        var east = padded ? this.get('paddedEast') : this.get('east');
        var south = padded ? this.get('paddedSouth') : this.get('south');
        var west = padded ? this.get('paddedWest') : this.get('west');
        var searchParams = {
            q: this.get('q'),
            ne_lat: north,
            ne_lon: east,
            sw_lat: south,
            sw_lon: west,
            people: this.get('filters').people,
            events: this.get('filters').events,
            projects: this.get('filters').projects,
            groups: this.get('filters').groups
        };
        if (!this.get('clustering')) {
            _(searchParams).extend({
                limit: this.limitWithoutClustering
            });
        }
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
            // Increase the search delay when a search is in progress.
            delay = self.get('searching') ?
                self.whileSearchingDelay : self.searchDelay;
        clearTimeout(this.searchTimeout);
        self.set('wantsToSearch', true);
        self.trigger('want:search');
        self.searchTimeout = setTimeout(function () {
            self.search();
            self.set('wantsToSearch', false);
        }, delay);
    },

    parseUrl: function (url) {
        if (url.indexOf('?') >= 0) {
            var json = JSON.parse('{"' + decodeURI(url.replace(/[^?]*\?/, '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
        } else {
            var json = {};
        }
        _(_(json).keys()).each(function (key) {
            if (json[key] !== '') {
                try {
                    json[key] = JSON.parse(json[key]);
                } catch (err) {}
            }
        });
        return json;
    },

    activeFilters: function () {
        return _(_(this.get('filters')).keys()).select(function (filter) {
            return !!filter;
        });
    }
});
