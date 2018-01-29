'use strict';

// Pub-sub event mediator and  data store.
module.exports = {
    publish: function (eventName, data) {
        Backbone.trigger(eventName, data);
    },

    subscribe: function (event, callback, context) {
        Backbone.on(event, callback, context);
    }
};
