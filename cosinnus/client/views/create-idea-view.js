'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');


module.exports = BaseView.extend({
    
    // reference back to the main App
    App: null,
    
    controlView: null,
    
    model: null,

    template: require('tiles/create-idea'),
    
    // The DOM events specific to an item.
    events: {
        'click .tile-close-button': 'onCloseClicked',
        'click .trigger-create-idea-submit': 'onSubmitClicked',
    },
    
    initialize: function (options, app, controlView) {
        var self = this;
        BaseView.prototype.initialize.call(self, options);
        self.App = app;
        self.controlView = controlView;
        
        Backbone.mediator.subscribe('ideas:create-view-opened', self.onViewOpened, self);
        Backbone.mediator.subscribe('ideas:create-view-closed', self.onViewClosed, self);
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
    
    afterRender: function () {
    	init_simplemde($('#idea-create-description')[0]);
    },
    
    onViewOpened: function () {
    	this.$el.find('#idea-create-title').focus();
    	this.App.mapView.activateDraggableMarker('ideas');
    	$('.trigger-create-idea').hide();
    },
    
    onViewClosed: function () {
    	this.App.mapView.deactivateDraggableMarker();
    	$('.trigger-create-idea').show();
    },
    
    // the view is being closed
    onCloseClicked: function (event) {
    	this.controlView.closeCreateIdeaView(event);
    },
    
    // submit button was clicked
    onSubmitClicked: function (event) {
    	// collect "form" values and navigate to the real create URL
    	var title = this.$el.find('#idea-create-title').val();
    	var description = inited_simplemde.value();
    	var latlng = this.App.mapView.getDraggableMarkerLatLng();
    	var url = '/ideas/add/?' + 
	    	'title=' + encodeURIComponent(title) + '&' + 
	    	'lat=' + latlng.lat + '&' + 
	    	'lon=' + latlng.lng + '&' +
	    	'description=' + encodeURIComponent(description); 
    	window.location.href = url;
    }
    
});
