'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({
    
    // reference back to the main App
    app: null,
    
    template: require('navbar/main-menu'),
    
    // The DOM events specific to an item.
    events: {
    },
    
    defaults: {

        state: {
            
        }
    },

    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        // decode the `contextDataJSON` that got passed by the app.js init call as HTML encoded strings 
        for (var datakey in self.options.contextDataJSON) {
        	self.options[datakey] = JSON.parse($("<textarea/>").html(self.options.contextDataJSON[datakey]).text());
        }
        for (var datakey in self.options.contextData) {
        	self.options[datakey] = self.options.contextData[datakey];
        }
        
    },

    render: function () {
        var self = this;
        BaseView.prototype.render.call(self);
        util.log('*** Rendered navbar main menu! ***')
        $.cosinnus.renderMomentDataDate();
        return self;
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        return data;
    },
    
    
});
