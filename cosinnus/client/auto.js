'use strict';

var Map = require('models/map');
var MapView = require('views/map-view');

module.exports = {
    initialize: function () {
        Backbone.mediator.subscribe('init:map', this.map);
        Backbone.mediator.publish('init:client');
    },

    map: function (event, params) {
        var d = {
            pushState: false
        };
        var settings = JSON.parse(params.settings);
        settings = $.extend(true, {}, d, settings);
        
        var map = new Map({}, {
            availableFilters: settings.availableFilters,
            activeFilters: settings.activeFilters,
            topicsHtml: $("<div/>").html(settings.topicsHtml).text(),
            pushState: settings.pushState,
            controlsEnabled: settings.controlsEnabled,
            filterGroup: settings.filterGroup,
        });

        new MapView({
            el: params.el,
            model: map,
            location: settings.location,
            markerIcons: settings.markerIcons
        }).render();
    }
};
