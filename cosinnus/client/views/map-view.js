'use strict';

var View = require('views/base/view');
var template = require('map/map');

module.exports = View.extend({
    initialize: function () {
        this.template = template;
    },

    getTemplateData: function () {
        return {
            msg: 'messageable!!!!!'
        };
    }
});
