'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

var paginationControlsTemplate = require('map/pagination-controls');


/** 
 * A small view, basically just to encapsulate the pagination control
 * template and buttons, to be able to render and refresh them independently
 * of the search controls. 
 * This is contained by and delegates almost everything back to the control-view.
 * */
module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    controlView: null,
    
    template: paginationControlsTemplate,
    
    // The DOM events specific to an item.
    events: {
        'click .toggle-search-on-scroll': 'toggleSearchOnScrollClicked',
        'click .stale-search-button': 'staleSearchButtonClicked',
        'click .trigger-pagination-forward': 'paginationForwardClicked',
        'click .trigger-pagination-backward': 'paginationBackClicked',
        'click .onoffswitch-text-label': 'onOffSwitchLabelClicked',
        'click .trigger-create-idea': 'createIdeaClicked',
    },
    
    initialize: function (options, app, controlView) {
        var self = this;
        BaseView.prototype.initialize.call(self, options);
        self.App = app;
        self.controlView = controlView;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        data = _.extend(
            data,
            self.controlView.options,
            self.controlView.state
        );
        return data;
    },
    
    
    // Events  -------------

    /** Trigger for state button elements */
    onOffSwitchLabelClicked: function (event) {
        $(event.target).next().find('input[type="checkbox"]').click()
    },
    
    // delegate to controlView
    toggleSearchOnScrollClicked: function (event) {
        self.controlView.toggleSearchOnScrollClicked(event);
    },
    
    // delegate to controlView
    staleSearchButtonClicked: function (event) {
        self.controlView.staleSearchButtonClicked(event);
    },
    
    // delegate to controlView
    paginationForwardClicked: function (event) {
        self.controlView.paginationForwardClicked(event);
    },
    
    // delegate to controlView
    paginationBackClicked: function (event) {
        self.controlView.paginationBackClicked(event);
    },
    
    // delegate to controlView
    createIdeaClicked: function (event) {
        self.controlView.openCreateIdeaView(event);
    },
    
});
