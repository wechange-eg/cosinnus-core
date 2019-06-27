'use strict';

var BaseView = require('views/base/view');

var TimelineView = require('views/userdashboard/timeline-view');
var GroupWidgetView = require('views/userdashboard/group-widget-view');
var IdeasWidgetView = require('views/userdashboard/ideas-widget-view');
var TypedContentWidgetView = require('views/userdashboard/typed-content-widget-view');
var UiPrefsView = require('views/userdashboard/ui-prefs-view');

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
    
    timelineView: null,
    
    groupWidgetView: null,
    ideasWidgetView: null,
    uiPrefsView: null,
    
    typedContentWidgetTypes: ['pads', 'files', 'messages', 'events', 'todos', 'polls'].concat(COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE ? ['offers'] : []),
    typedContentWidgets: {},
    
    uiPrefKeyRightBarWidget: 'dashboard_widgets_sort_key__',
    
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
        
        self.uiPrefsView = new UiPrefsView(self.options.uiPrefs);
        
        self.el = '.v2-dashboard';
        self.$el = $(self.el);
        self.$el.removeClass('loading');
        
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
        		sortIndex: self.uiPrefsView.getUiPref(self.uiPrefKeyRightBarWidget + type),
        	}, self.app);
    		rightBarPromises.push(self.typedContentWidgets[type].load());
    	});
    	Promise.all(rightBarPromises).then(function(){
        	$.cosinnus.renderMomentDataDate();
        	self.sortRightBarWidgets();
        	self.manageWidgetConditions();
    		self.$rightBar.show();
    		util.log('# #### showing right bar.')
    	});
    },
    
    sortRightBarWidgets: function () {
    	this.$rightBar.find('div.widget-content').sortElements(function(a, b){
    		return $(a).attr('data-sort-index') > $(b).attr('data-sort-index') ? 1 : -1;
    	});
    },
    
    /** After empty widgets have removed themselves, will display the "new users"
     *  info box if too or none few are shown */
    manageWidgetConditions: function () {
    	// show widget info box if ui pref is set
    	if (this.uiPrefsView.getUiPref('timeline__hide_welcome_widget_box')) {
    		this.$rightBar.find('.welcome_widget_box').remove();
    	} else {
    		this.$rightBar.find('.welcome_widget_box').show();
    	}
    },
    
    loadTimeline: function () {
    	var self = this;
    	
    	// show welcome screen if ui pref is set
    	var $welcomeFrame = self.$el.find('.dashboard-welcome-frame');
    	if (self.uiPrefsView.getUiPref('timeline__hide_welcome_screen')) {
    		$welcomeFrame.remove();
    	} else {
    		$welcomeFrame.show();
    	}
    	
    	self.timelineView = new TimelineView({
    		el: self.$el.find('.timeline-root'),
    	}, self.app, self.uiPrefsView);
    	self.timelineView.load();
    },
    
    
    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
    	if (this.$el.hasClass('active') && !this.el.contains(event.target)) {
    		this.$el.removeClass('active');
    		document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	}
    },
    
    /** Moves a widget up or down by swapping it with its sibling.
     *  Params:
     *  	- type: the content type of the source widget (i.e. 'events')
     *  	- directionUp: true for up, false for down
     */
    moveRightSideWidget: function (type, directionUp) {
    	var self = this;
    	
    	// find both widgets
    	var widget = self.$rightBar.find('.widget-content[data-content-type="' + type + '"]');
    	if (widget.length == 0) {
    		return;
    	}
    	var other_widget = directionUp ? widget.prev('.widget-content') : widget.next('.widget-content');
    	if (other_widget.length == 0) {
    		return;
    	}
    	
    	// swap their sort index
    	var idx = widget.attr('data-sort-index');
    	var other_idx = other_widget.attr('data-sort-index');
    	widget.attr('data-sort-index', other_idx);
    	other_widget.attr('data-sort-index', idx);
    	
    	// sort the widgets
    	self.sortRightBarWidgets();
    	
    	// save the uiPrefs
    	var uiPrefs = {};
    	uiPrefs[self.uiPrefKeyRightBarWidget + widget.attr('data-content-type')] = other_idx;
    	uiPrefs[self.uiPrefKeyRightBarWidget + other_widget.attr('data-content-type')] = idx;
    	self.uiPrefsView.saveUiPrefs(uiPrefs);
    },

});
