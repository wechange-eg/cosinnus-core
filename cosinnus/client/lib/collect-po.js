'use strict';

var fs = require('fs');
var PO = require('pofile');
var _ = require('underscore');

module.exports = {
        
    parsePO: function (languages) {
        var podicts = {};
        _.each(languages, function(lang){
            try {
                // we try to read the cosinnus-core po file and the main server project po file 
                // (which is copied to the cosinnus-core directory during deploy)
                var paths = [
                    './cosinnus/locale/' + lang + '/LC_MESSAGES/django.po',
                    './cosinnus/locale_extra/' + lang + '/LC_MESSAGES/django.po',
                ];
                var langdict = {};
                _.each(paths, function(path){
                    var po_contents = null;
                    try {
                        po_contents = fs.readFileSync(path, 'utf-8').toString();
                    } catch (e) {
                        console.log('Could not open translation PO file "' + path + '" for language for JS generation. If this language is not supported in the current cosinnus project, you can safely ignore this message.');
                    }
                    if (po_contents) {
                        var po = PO.parse(po_contents);
                        _.each(po.items, function(item){
                            // check for those translation items that contain "__INCLUDE_JS_PO__" as comment
                            if (_.some(item.extractedComments, function(comment){return comment.indexOf("__INCLUDE_JS_PO__") >= 0})) {
                                if (!item.obsolete && !item.flags.fuzzy) {
                                    langdict[item.msgid] = item.msgstr[0];
                                }
                            }
                        });
                    }
                });
                podicts[lang] = langdict;
            } catch (e) {
                console.log(e)
            }
        });
        return podicts;
    }
    
};
