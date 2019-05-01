'use strict';

var BaseView = require('views/base/view');
var GroupWidgetView = require('views/userdashboard/group-widget-view');
var IdeasWidgetView = require('views/userdashboard/ideas-widget-view');
var TypedContentWidgetView = require('views/userdashboard/typed-content-widget-view');
var util = require('lib/util');

module.exports = BaseView.extend({

	app: null,
    template: null,
    el: null, // will be set to dashboard root manually
    $el: null, // will be set to dashboard root manually
    leftBar: '.dashboard-left-bar-content',
    $leftBar: null, 
    rightBar: '.dashboard-right-bar-content',
    $rightBar: null,
    timeline: '.timeline-root',
    $timeline: null,
    
    groupWidgetView: null,
    ideasWidgetView: null,
    
    typedContentWidgetTypes: ['pads', 'files', 'messages', 'events', 'todos', 'polls'],
    typedContentWidgets: {},
    
    // will be set to self.options during initialization
    defaults: {
        
        state: {
            
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	//'focus .nav-search-box': 'onSearchBoxFocusIn',
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        self.el = '.v2-dashboard';
        self.$el = $(self.el);
        self.$leftBar = self.$el.find(self.leftBar);
        self.$rightBar = self.$el.find(self.rightBar);
        self.$timeline = self.$el.find(self.timeline);
        
        self.loadLeftBar();
        self.loadRightBar();
        self.loadTimeline();
    },
    
    /** Loads all widgets on the left bar and only then displays it */
    loadLeftBar: function () {
    	var self = this;
    	self.groupWidgetView = new GroupWidgetView({
    		el: self.$el.find('.group-widget-root'),
    	}, self.app);
    	self.ideasWidgetView = new IdeasWidgetView({
    		el: self.$el.find('.ideas-widget-root'),
    	}, self.app);
    	
    	var leftBarPromises = [
    		self.groupWidgetView.load(),
    		self.ideasWidgetView.load(),
    	];
    	Promise.all(leftBarPromises).then(function(){
    		self.$leftBar.show();
    	});
    	
    },
    
    /** Loads all widgets on the right bar and only then displays it */
    loadRightBar: function () {
    	var self = this;

    	var rightBarPromises = [];
    	// for each content type, initialize the widget on that type and load its contents
    	$.each(self.typedContentWidgetTypes, function(i, type){
    		self.typedContentWidgets[type] = new TypedContentWidgetView({
        		elParent: self.$el.find('.typed-widgets-root'),
        		type: type,
        		sortIndex: i,
        	}, self.app);
    		rightBarPromises.push(self.typedContentWidgets[type].load());
    	});
    	Promise.all(rightBarPromises).then(function(){
        	$.cosinnus.renderMomentDataDate();
        	self.sortRightBarWidgets();
    		self.$rightBar.show();
    		util.log('# #### showing right bar.')
    	});
    },
    
    sortRightBarWidgets: function () {
    	this.$rightBar.find('div.widget-content').sortElements(function(a, b){
    		return $(a).attr('data-sort-index') > $(b).attr('data-sort-index') ? 1 : -1;
    	});
    },
    
    loadTimeline: function () {
    	var self = this;
    	// todo: load timeline
    	
    },
    
    

    
    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
    	if (this.$el.hasClass('active') && !this.el.contains(event.target)) {
    		this.$el.removeClass('active');
    		document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	}
    },
    
    

});
