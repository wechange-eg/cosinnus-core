'use strict';

var util = require('lib/util.js');

module.exports = Backbone.Model.extend({
    
    defaults: {
        /** id: Results get an id in the form of "<result_type>.<result_id>" from the backend.
         *         Example:  "3.215"  */
        
        /**  Object type of the result. currently:
         *  'groups', 'projects', 'events', 'people'.
         *  And the special result type: 'error' */
        type: null,
        
        /** Centralised hovered state of this result in the views. 
         *  Used to transport hovered state over the same result, even if displayed in different 
         *  views (tile, map, etc). The corresponding change:hovered signal can be subscribed to 
         *  to register visual changes in the views.  */
        hovered: false,
        
        /** Centralised selected/clicked state of this result in the views. 
         *  Used to transport selected state over the same result, even if displayed in different 
         *  views (tile, map, etc). The corresponding selected signal can be subscribed to to 
         *  register visual changes in the views.  */
        selected: false,

        /** Latitude/longitude coordinates. 
         *  If null, this Result has no location, but can still be displayed in for example the Tile View. */
        lat: null,
        lon: null,
        
        /** Result relevance as float, 0 or positive, can be larger than 1.0! */
        relevance: 0.0,
        
        /** All other attributes come directly from the backend, and aren't listed here as
         *  they are only used in the templates directly. */
    },
    
    initialize: function(){
        
    },
    
    locEquals: function(other_result) {
        return this.get('lat') != null 
            && this.get('lon') != null
            && other_result.get('lat') == this.get('lat') 
            && other_result.get('lon') == this.get('lon');
    },
    
    getLocs: function() {
        return [this.get('lat'), this.get('lon')];
    }

});