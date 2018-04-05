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
    },
    
    /** Returns a if it is defined, else b */
    ifundef: function(a, b) {
        return typeof a == "undefined" ? b : a;
    },
    
    log: function(obj) {
    	// determine test/prod environment
    	if (DEBUG) {
    		if (typeof obj == "string") {
    			console.log(obj + '    || from:  ' + new Error().stack.replace(/(?:\r\n|\r|\n)/g, '').split(' at ')[2]);
    		} else {
    			console.log(obj);
    		}
    	}
    },
    
    /** Returns a statusData dict of important state data of a text input,
     *  to be restored later using `restoreInputStatus()` */
    saveInputStatus: function ($input) {
    	var elem = $input[0];
    	return {
    		hadFocus: $input.is(":focus"),
    		val: elem.value,
    		start: elem.selectionStart,
    		end: elem.selectionEnd
    	}
    },
    
    /** Restores a text input's state saved with `saveInputStatus` */
    restoreInputStatus: function ($input, statusData) {
    	var elem = $input[0];
    	elem.value = statusData['val'];
    	elem.setSelectionRange(statusData['start'], statusData['end']);
    	if (statusData['hadFocus']) {
    		$input.focus();
    	}
    }
    
};
