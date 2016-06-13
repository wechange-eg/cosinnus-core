'use strict';

var View = require('views/base/view');
var template = require('xhr-error');

module.exports = View.extend({
    initialize: function (options) {
        this.template = template;
        View.prototype.initialize.call(this);
        this.state = {
            message: options.message
        };
    }
});
