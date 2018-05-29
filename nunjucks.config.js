module.exports = function(env){
    function parse (parser, nodes, lexer) {
        var tok = parser.nextToken();
        key = parser.parseSignature(null, true);
        parser.advanceAfterBlockEnd(tok.value);
        return new nodes.CallExtension(this, 'run', key);
    }
    
    function Translation () {
        this.tags = ['trans'];
        this.parse = parse;
        this.run = function (ctx, key) {
        	// cosinnus_current_language is defined in base.html
        	// COSINNUS_PO_TRANS is defined in webpack/shared.config.js
        	if (cosinnus_current_language in COSINNUS_PO_TRANS && key in COSINNUS_PO_TRANS[cosinnus_current_language]) {
        		var trans = COSINNUS_PO_TRANS[cosinnus_current_language][key];
        		if (trans && trans.length > 0) {
        			return trans;
        		}
        	}
            return key;
        };
    }

    function Ignore () {
        this.tags = ['load'];
        this.parse = parse;
        this.run = function () {
            return '';
        };
    }

    env.addExtension('translation', new Translation());
    env.addExtension('passThrough', new Ignore());
}
