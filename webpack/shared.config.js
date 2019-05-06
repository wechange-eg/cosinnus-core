var webpack = require('webpack');
var path = require('path');
var base = path.resolve('.');

var collectPO = require('../cosinnus/client/lib/collect-po.js');

// add languages for the map here!
var LANGUAGES = ['en', 'de', 'ru', 'uk', 'fr', 'pl', 'be'];

module.exports = {
    entry: path.join(base, 'cosinnus/client/app.js'),
    output: {
        path: path.join(base, 'cosinnus/static/js/'),
        filename: 'client.js'
    },
    module: {
        loaders: [
            {
                test: /\.html$/,
                loader: 'nunjucks-loader',
                include: [
                    path.join(base, 'cosinnus/templates/cosinnus/universal')
                ],
                query: {
                    config: path.join(base, 'nunjucks.config.js')
                }
            },
        ],
    },
    resolve: {
        root: [
            path.join(base, 'cosinnus/templates/cosinnus/universal'),
            path.join(base, 'cosinnus/client')
        ],
        extensions: [
            '.js',
            '.html',
            ''
        ]
    },
    plugins: [
    	new webpack.DefinePlugin({
	      'COSINNUS_PO_TRANS': JSON.stringify(collectPO.parsePO(LANGUAGES))
	    })
    ],
    node: {
	  fs: "empty"
	},
}
