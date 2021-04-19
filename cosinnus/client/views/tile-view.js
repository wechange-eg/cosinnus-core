'use strict';

var BaseView = require('views/base/view');
var Result = require('models/result');
var util = require('lib/util');

var tileTemplateDefault = require('tiles/grid-tile-default');

if (COSINNUS_CLOUD_ENABLED) {
    var tileTemplateCloudfile = require('tiles/grid-tile-cloudfile');
}

module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    model: Result,

    template: tileTemplateDefault, // determined in `fitTemplate()`
    
    // The DOM events specific to an item.
    events: {
        'click .result-link': 'onResultLinkClicked',
        'click .topic-filter-link': 'onTopicLinkClicked',
        'click .text-topic-filter-link': 'onTextTopicLinkClicked',

        'mouseenter': 'onMouseEnter',
        'mouseleave': 'onMouseLeave',
    },
    
    initialize: function (options, app) {
        var self = this;
        BaseView.prototype.initialize.call(self, options);
        self.App = app;
        
        self.model.on({
            'change:hovered': self.thisContext(self.onHoverChanged),
        });
        self.fitTemplate();
    },
    
    /** Adjust this view's template based on the result type it displays (and other states) */
    fitTemplate: function () {
        var self = this;
        if (self.model.get('type') == 'cloudfile') {
            self.template = tileTemplateCloudfile;
            self.state.isSmall = true;
            self.state.noImage = true;
        } else if (self.model.get('type') == 'people') {
            self.state.isSmall = true;
        } 
        self.state.isYou = self.model.get('type') == 'people' && cosinnus_active_user && self.model.get('slug') == cosinnus_active_user.username;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        data['controlView'] = _.extend(
            {},
            self.App.controlView.options,
            self.App.controlView.state
        );
        return data;
    },
    
    /**
     * Called when the .hovered property of the Result model was changed.
     * We actually do the display and re-render here, because
     * the selected change may be triggered in other views.
     */
    onHoverChanged: function () {
        this.$el.toggleClass('hovered', this.model.get('hovered'));
    },
    
    
    onMouseEnter: function() {
        if (!this.model.get('selected')) {
            util.log('tile-view.js: got a hover event! id: ' + this.model.id);
            this.App.controlView.setHoveredResult(this.model);
        }
    },
    onMouseLeave: function() {
        if (!this.model.get('selected')) {
            util.log('tile-view.js: got an unhover event! id: ' + this.model.id);
            this.App.controlView.setHoveredResult(null);
        }
    },
    
    /** Called when a topic link is clicked to filter for that topic only */
    onTopicLinkClicked: function(event) {
        this.App.controlView.onTopicLinkClicked(event);
    },

    onTextTopicLinkClicked: function(event) {
        this.App.controlView.onTextTopicLinkClicked(event);
    },
    
    /**
     * Called when a link is clicked that leads to opening a detail view.
     * We only change the Result model's .selected property and
     * don't do any rendering here.
     */
    onResultLinkClicked: function (event) {
        this.App.controlView.onResultLinkClicked(event);
    },
    
});
