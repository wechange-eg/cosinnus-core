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
