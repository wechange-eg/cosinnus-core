'use strict';

var View = require('views/base/view');
var ErrorView = require('views/error-view');
var template = require('map/map-controls');
var util = require('lib/util.js');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
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

    afterRender: function () {
        // update topics selector with current topics
        var topics_selector = this.$el.find('#id_topics');
        if (topics_selector.length > 0 && this.model.get('activeTopicIds')) {
            topics_selector.val(this.model.get('activeTopicIds')).select2();
        }
    }
});
