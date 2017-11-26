'use strict';

module.exports = Backbone.Model.extend({
    default: {
        availableFilters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        activeFilters: {
            people: true,
            events: true,
            projects: true,
            groups: true
        },
        layer: 'street',
        pushState: true,
        topicsVisible: false,
        topicsHtml: '',
        controlsEnabled: true,
        filterGroup: null,
        baseUrl: '/maps/search/',
        activeTopicIds: null,
    },

    limitWithoutClustering: 400,

    searchDelay: 400,

    whileSearchingDelay: 5000,

    initialize: function (attributes, options) {
        var self = this;
        var attrs = $.extend(true, {}, self.default, options);
        self.set(attrs);
        Backbone.mediator.subscribe('navigate:map', function () {
            self.initialSearch();
        });
        Backbone.Model.prototype.initialize.call(this);
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
                if (self.get('pushState')) {
                    Backbone.mediator.publish('navigate:router', self.buildURL(false).replace(self.get('baseUrl'), '/map/'))
                }
            }
        }).fail(function () {
            self.set('searching', false);
            self.trigger('end:search');
            self.trigger('error:search');
        });
    },

    initialSearch: function () {
        var json = this.parseUrl(window.location.href.replace(window.location.origin, ''));
        var ifundef = function(a, b) {
            return typeof a == "undefined" ? b : a;
        };
        
        if (_(json).keys().length) {
            this.set({
                activeFilters: {
                    people: ifundef(json.people, this.get('activeFilters').people),
                    events: ifundef(json.events, this.get('activeFilters').events),
                    projects: ifundef(json.projects, this.get('activeFilters').projects),
                    groups: ifundef(json.groups, this.get('activeFilters').groups)
                },
                q: ifundef(json.q, this.get('q')),
                north: ifundef(json.ne_lat, this.get('north')),
                east: ifundef(json.ne_lon, this.get('east')),
                south: ifundef(json.sw_lat, this.get('south')),
                west: ifundef(json.sw_lon, this.get('west')),
                limit: ifundef(json.limits, this.get('limit')),
                activeTopicIds: ifundef(json.topics, this.get('activeTopicIds'))
            });
            if (json.topics) {
                this.showTopics();
            }
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
        var topic_ids = '';
        if (this.get('activeTopicIds')) {
            topic_ids = this.get('activeTopicIds').join(',');
        }
        var searchParams = {
            q: this.get('q'),
            ne_lat: north,
            ne_lon: east,
            sw_lat: south,
            sw_lon: west,
            people: this.get('activeFilters').people,
            events: this.get('activeFilters').events,
            projects: this.get('activeFilters').projects,
            groups: this.get('activeFilters').groups,
            topics: topic_ids
        };
        if (!this.get('clustering')) {
            _(searchParams).extend({
                limit: this.get('limit') || this.limitWithoutClustering
            });
        }
        var query = $.param(searchParams);
        
        var url = this.get('baseUrl');
        if (this.get('filterGroup')) {
            url = url + this.get('filterGroup') + '/';
        }
        return url + '?' + query;
    },

    toggleFilter: function (resultType) {
        var activeFilters = this.get('activeFilters');
        activeFilters[resultType] = !activeFilters[resultType];
        this.set('activeFilters', activeFilters);
        this.attemptSearch();
    },

    resetFilters: function () {
        this.set('activeFilters', _(this.get('availableFilters')).clone());
        this.attemptSearch();
    },
    
    showTopics: function () {
        this.set('topicsVisible', true);
    },
    
    toggleTopicFilter: function (topic_ids) {
        this.set('activeTopicIds', topic_ids);
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
            var json = JSON.parse('{"' + decodeURI(url.replace(/\%2C/g, ',').replace(/[^?]*\?/, '').replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}')
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
        if (typeof json['topics'] === "number" || (typeof json['topics'] === "string" && json['topics'].length > 0)) {
            json['topics'] = json['topics'].toString().split(',');
        }
        return json;
    },

    activeFilterList: function () {
        return _(_(this.get('activeFilters')).keys()).select(function (filter) {
            return !!filter;
        });
    }
});
