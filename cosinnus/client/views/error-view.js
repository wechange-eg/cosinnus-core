'use strict';

var View = require('views/base/view');
var template = require('xhr-error');

module.exports = View.extend({
    initialize: function (options) {
    	var self = this;
        this.template = template;
        View.prototype.initialize.call(self, options);
        this.state = {
            message: options.message
        };
    }
});
