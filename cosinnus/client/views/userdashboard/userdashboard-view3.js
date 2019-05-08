'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({

	app: null,
	
    template: require('userdashboard/userdashboard'),
    
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
        
    },

    render: function () {
        var self = this;
        BaseView.prototype.render.call(self);
        
        util.log('*** Rendered user dashboard! ***')
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        data['dashydata'] = 'such dashy';
        return data;
    },
    
    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
    	if (this.$el.hasClass('active') && !this.el.contains(event.target)) {
    		this.$el.removeClass('active');
    		document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
    	}
    },
    
    

});
