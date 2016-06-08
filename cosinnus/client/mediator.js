'use strict';

// Pub-sub event mediator and  data store.
module.exports = function Router () {
    this.publish = function (eventName, data) {
        $('html').trigger(eventName, data);
    };

    this.subscribe = function (events, data, handler) {
        $('html').on(events, data, handler);
    };
};
