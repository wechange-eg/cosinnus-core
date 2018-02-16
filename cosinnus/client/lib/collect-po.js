'use strict';

var fs = require('fs');
var PO = require('pofile');

module.exports = {
		
	parsePO: function () {
		var _podict = {};
		var po_contents = fs.readFileSync('./cosinnus/locale/de/LC_MESSAGES/django.po', 'utf-8').toString();
		var po = PO.parse(po_contents);
		
		// po.items[815].extractedComments
		// .msgid
		// .msgstr []
		// .obsolete == false
		
		return {'po': po};
	}
    
};
