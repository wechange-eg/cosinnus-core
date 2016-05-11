// Main JavaScript file.  Will be built to app.js by webpack.

'use strict';

var Router = require('router');

// Register routes.
window.router = new Router();

$(function () {
    // Start routing after the DOM is loaded.
    Backbone.history.start({
        pushState: true
    });
});
