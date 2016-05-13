'use strict';

var template = require('map/map');

module.exports = Backbone.View.extend({
    render: function () {
        console.log(__dirname);
        console.log('MapView#render');
        this.$el.html(template.render({
            msg: 'messageable!'
        }));
    }
});
