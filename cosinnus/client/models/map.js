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
                Backbone.mediator.publish('navigate:router', url.replace('/maps/search', '/map/'))
            }
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
        }
        this.search();
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
