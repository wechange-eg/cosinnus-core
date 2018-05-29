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
                var langdict = {};
                _.each(po.items, function(item){
                    // check for those translation items that contain "__INCLUDE_JS_PO__" as comment
                    if (_.some(item.extractedComments, function(comment){return comment.indexOf("__INCLUDE_JS_PO__") >= 0})) {
                        if (!item.obsolete && !item.flags.fuzzy) {
                            langdict[item.msgid] = item.msgstr[0];
                        }
                    }
                });
                podicts[lang] = langdict;
            } catch (e) {
            }
        });
        return podicts;
    }
    
};
