'use strict';

module.exports = {
    protocol: function () {
        console.log('returning protocol: ' + window.location.protocol) 
        return window.location.protocol;
    }
};
