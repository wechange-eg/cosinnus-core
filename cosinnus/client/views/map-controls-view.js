'use strict';

var View = require('views/base/view');
var ErrorView = require('views/error-view');
var util = require('lib/util.js');

module.exports = View.extend({
	
	template: require('map/map-controls'),
	
	defaults: {
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
        topicsVisible: false,
        topicsHtml: '',
        controlsEnabled: true,
        filterGroup: null,
    },
    
    searchEndpointURL: '/maps/search/',
    activeTopicIds: null,
    searchDelay: 400,
    whileSearchingDelay: 5000,
	
    options: {},
    
    initialize: function (options) {
    	self.options = $.extend(true, {}, self.defaults, options);
        this.model.on('want:search', this.handleStartSearch, this);
        this.model.on('end:search', this.handleEndSearch, this);
        this.model.on('change:controls', this.render, this);
        this.model.on('error:search', this.handleXhrError, this);
        View.prototype.initialize.call(this);
    },

    events: {
        'click .result-filter': 'toggleFilter',
        'click .reset-filters': 'resetFilters',
        'click .show-topics': 'showTopics',
        'click .layer-button': 'switchLayer',
        'change #id_topics': 'toggleTopicFilter',
        'focusin .q': 'toggleTyping',
        'focusout .q': 'toggleTyping',
        'keyup .q': 'handleTyping',
        'keydown .q': 'handleKeyDown',
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
    
    showTopics: function (event) {
        event.preventDefault();
        this.model.showTopics();
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
    
    toggleTopicFilter: function (event) {
        var topic_ids = $(event.currentTarget).val();
        this.model.toggleTopicFilter(topic_ids);
    },

    toggleTyping: function (event) {
        this.state.typing = !this.state.typing;
        this.$el.find('.icon-search').toggle();
    },

    handleTyping: function (event) {
        if (util.isIgnorableKey(event)) {
            event.preventDefault();
            return false;
        }
        
        var query = $(event.currentTarget).val();
        if (query.length > 2 || query.length === 0) {
            this.model.set({
                q: query
            });
            this.model.attemptSearch();
        }
    },
    
    handleKeyDown: function (event) {
        if (event.keyCode == 13) {
            event.preventDefault();
            return false;
        }
    },

    handleStartSearch: function (event) {
        this.$el.find('.icon-search').addClass('hidden');
        this.$el.find('.icon-loading').removeClass('hidden');
    },

    handleEndSearch: function (event) {
        if (!this.state.typing) {
            this.$el.find('.icon-search').removeClass('hidden');
        }
        this.$el.find('.icon-loading').addClass('hidden');
        var $message = this.$el.find('form .message');
        $message.hide();
    },

    handleXhrError: function (event) {
        var $message = this.$el.find('form .message');
        new ErrorView({
            message: 'Ein Fehler ist bei der Suche aufgetreten.',
            el: $message
        }).render();
        $message.show();
    },
    
    
    
    
    /** FROM HERE ON FROM models/map.js **/


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
                if (App.displayOptions.fullscreen) {
                    Backbone.mediator.publish('navigate:router', self.buildURL(false).replace(self.get('searchEndpointURL'), '/map/'))
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
        
        var url = this.get('searchEndpointURL');
        if (this.get('filterGroup')) {
            url = url + this.get('filterGroup') + '/';
        }
        return url + '?' + query;
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

    activeFilterList: function () {
        return _(_(this.get('activeFilters')).keys()).select(function (filter) {
            return !!filter;
        });
    },
    
    
    
    
    
    
    
    

    afterRender: function () {
        // update topics selector with current topics
        var topics_selector = this.$el.find('#id_topics');
        if (topics_selector.length > 0 && this.model.get('activeTopicIds')) {
            topics_selector.val(this.model.get('activeTopicIds')).select2();
        }
    }
});
