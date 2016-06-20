'use strict';

// Main application class

var Router = require('router');
var mediator = require('mediator');
var auto = require('auto');

module.exports = function Application () {
    self = this;

    self.router = new Router();

    self.start = function () {
        self.initMediator();
        // Start routing...
        Backbone.history.start({
            pushState: true
        });
        // A global resize event
        $(window).on('resize', function () {
            Backbone.mediator.publish('resize:window');
        });
        // Autoinitialize inline views and models.
        auto.initialize();

    };

    self.initMediator = function () {
        self.mediator = Backbone.mediator = mediator;
        self.mediator.settings = window.settings || {};
        self.mediator.subscribe('navigate:router', function (event, url) {
            if (url) {
                self.router.navigate(url, {
                    trigger: false
                });
            }
        });
    };
};
