'use strict';

var util = require('lib/util.js');

module.exports = Backbone.Model.extend({
	
	defaults: {
		/** id: Results get an id in the form of "<result_type>.<result_id>" from the backend.
		 * 		Example:  "3.215"  */
		
		/**  Object type of the result. currently:
		 *  'groups', 'projects', 'events', 'people' */
		type: null,
		
		/** Centralised hover state of this result in the views. 
		 *  Used to transport hover state over the same result, even if displayed in different 
		 *  views (tile, map, etc). The corresponding change:hover signal can be subscribed to 
		 *  to register visual changes in the views.  */
		hover: false,
		
		/** Centralised selected/clicked state of this result in the views. 
		 *  Used to transport hover state over the same result, even if displayed in different 
		 *  views (tile, map, etc). The corresponding selected signal can be subscribed to to 
		 *  register visual changes in the views.  */
		selected: false,

		/** Latitude/longitude coordinates. 
		 *  If null, this Result has no location, but can still be displayed in for example the Tile View. */
		lat: null,
		lon: null,
		
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