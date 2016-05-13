// Main JavaScript file — main entry for webpack

'use strict';

var Router = require('router');

// Register routes.
window.router = new Router();

// Start routing after the DOM is loaded.
$(function () {
    Backbone.history.start({
        pushState: true
    });
});
