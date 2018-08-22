'use strict';

var BaseView = require('views/base/view');
var Result = require('models/result');
var util = require('lib/util');

var templates = {
    'projects': require('tiles/tile-detail-projects'),
    'groups': require('tiles/tile-detail-groups'),
    'people': require('tiles/tile-detail-people'),
    'events': require('tiles/tile-detail-events'),
    'ideas': require('tiles/tile-detail-ideas'),
    'error-403': require('tiles/tile-detail-error-403'),
    'error': require('tiles/tile-detail-error'),
};

module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    model: Result,

    template: null,
    
    // The DOM events specific to an item.
    events: {
        'click .result-link': 'onResultLinkClicked',
        'click .tile-close-button': 'onDeselectClicked',
        'click .topic-filter-link': 'onTopicLinkClicked',
        'click .button-like': 'onLikeButtonClicked',
        'click .button-follow': 'onFollowButtonClicked',
        'click .button-report-object': 'onReportButtonClicked',
    },
    
    initialize: function (options, app) {
        var self = this;
        BaseView.prototype.initialize.call(self, options);
        self.App = app;
        
        Backbone.mediator.subscribe('result:detail-opened', self.onDetailOpened, self);
        Backbone.mediator.subscribe('result:detail-closed', self.onDetailClosed, self);
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

    /** Adjust this view's template based on the result type it displays (and other states) */
    fitTemplate: function () {
        var self = this;
        if (self.model.get('type') == 'people') {
            self.state.isSmall = true;
        } 
    },
    
    // a new result is being selected
    onDetailOpened: function (result) {
        var self = this;
        this.model = result;
        if (result.get('type') in templates) {
            this.template = templates[result.get('type')];
        } else {
            this.template = templates['error'];
        }

        this.model.on({
        	'change:liked': self.thisContext(self.render),
        	'change:followed': self.thisContext(self.render),
        });
        this.fitTemplate();
        this.render();
        this.App.controlView.triggerMobileDetailView();
        // render moment dates
        $.cosinnus.renderMomentDataDate();
        Backbone.mediator.publish('tile-detail:opened');
    },
    
    // a result is being unselected
    onDetailClosed: function () {
        this.model = null;
        this.render();
        this.App.controlView.untriggerMobileDetailView();
        this.App.controlView.addCurrentHistoryState();
        Backbone.mediator.publish('tile-detail:closed');
    },
    
    /** Called when a topic link is clicked to filter for that topic only */
    onTopicLinkClicked: function(event) {
        // make sure to close
        this.App.controlView.displayDetailResult(null);
        this.App.controlView.onTopicLinkClicked(event);
    },
    
    /**
     * Called when a tile detail close button is clicked.
     * We only change the Result model's .selected property and
     * don't do any rendering here (this is mediated through signals from the control view).
     */
    onDeselectClicked: function () {
        util.log('tile-view.js: got a deselect click event!');
        // this voluntary action adds a history state!
        this.App.controlView.displayDetailResult(null, true);
        if (App.displayOptions.routeNavigation) {
            util.log('tile-detail-view.js: +++++++++++++++++ since we are fullscreen, publishing detail-close router URL update!')
            App.controlView.addCurrentHistoryState();
        } 
    },
    

    /**
     * Called when a link is clicked that leads to opening a detail view.
     * We only change the Result model's .selected property and
     * don't do any rendering here.
     */
    onResultLinkClicked: function (event) {
        this.App.controlView.onResultLinkClicked(event);
    },
    
    onLikeButtonClicked: function (event) {
    	this.App.controlView.triggerResultLikeOrUnlike(this.model);
    },
    
    onFollowButtonClicked: function (event) {
    	this.App.controlView.triggerResultFollowOrUnfollow(this.model);
    },
    
    /** report the currently open detail view object */
    onReportButtonClicked: function (event) {
    	$.cosinnus.Feedback.cosinnus_report_object(this.model.get("report_model"), this.model.get("report_id"), this.model.get("title"));
    }
    
});
