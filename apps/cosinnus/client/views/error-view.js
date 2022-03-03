'use strict';

var View = require('views/base/view');

module.exports = View.extend({
    
    template: require('xhr-error'),    
    
    initialize: function (options) {
        var self = this;
        View.prototype.initialize.call(self, options);
        
        this.state.message = options.message;
    }
});
