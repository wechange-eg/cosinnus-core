'use strict';

var Result = require('models/result');
var util = require('lib/util.js');

module.exports = Backbone.Collection.extend({
    
    model: Result,
    
    /** Results are always sorted by relevance */
    comparator: function (result_1, result_2) {
        if (result_1.get('relevance') == result_2.get('relevance')) {
            return 0;
        } else if (result_1.get('relevance') > result_2.get('relevance')) {
            return -1;
        } else {
            return 1;
        }
    }
    
});