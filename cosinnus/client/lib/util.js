'use strict';

module.exports = {
    protocol: function () {
        return window.location.protocol;
    },
    
    isIgnorableKey: function (event) {
        var keycodes = [
            9,  // tab
            13, // enter
            16, // shift
            17, // ctrl
            18, // alt
            19, // pause/break
            20, // capslock
            27, // escape
            33, // pageup
            34, // pagedown
            35, // end
            36, // home
            37, // leftarrow
            38, // uparrow
            39, // rightarrow
            40, // downarrow
            45, // insert
            46 // delete
        ];
        return _(keycodes).contains(event.keyCode);
    }
};
