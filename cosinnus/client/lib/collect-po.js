'use strict';

var fs = require('fs');
var PO = require('pofile');
var _ = require('underscore');

module.exports = {
		
	parsePO: function (languages) {
		var podicts = {};
		_.each(languages, function(lang){
			try {
				var po_contents = fs.readFileSync('./cosinnus/locale/' + lang + '/LC_MESSAGES/django.po', 'utf-8').toString();
				var po = PO.parse(po_contents);
				// po.items[815].extractedComments
				// .msgid
				// .msgstr []
				// .obsolete == false
				var langdict = {};
				_.each(po.items, function(item){
					// check for those translation items that contain "__INCLUDE_JS_PO__" as comment
					if (_.some(item.extracedComments, function(comment){return comment.indexOf("__INCLUDE_JS_PO__") >= 0})) {
						if (!item.obsolete) {
							langdict[item.msgid] = item.msgstr[0];
							console.log('\n>>adding ' + item.msgid)
						}
					}
				});
				podicts[lang] = langdict;
				console.log('Added dict for lang ' + lang)
			} catch (e) {
				console.log('\n>> collect-po.js: Error in PO-collect for language "' + lang + '" : ' + e.toString());
			}
		});
		console.log('>>\nreturning podicts:')
		console.log(podicts)
		return podicts;
	}
    
};
