'use strict';

// Pub-sub event mediator and  data store.
module.exports = {
    publish: function (eventName, data) {
        $('html').trigger(eventName, data);
    },

    subscribe: function (events, data, handler) {
        $('html').on(events, data, handler);
    }
};
