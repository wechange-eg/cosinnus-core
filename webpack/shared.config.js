var webpack = require('webpack');
var path = require('path');
var base = path.resolve('.');

var fs = require('fs');
var PO = require('pofile');

function parsePO () {
	var _podict = {};
	var po_contents = fs.readFileSync('./cosinnus/locale/de/LC_MESSAGES/django.po', 'utf-8').toString();
	var po = PO.parse(po_contents);
	return {'po': po};
}

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
	      'OMGSASCHA': JSON.stringify(parsePO())
	    })
    ],
    node: {
	  fs: "empty"
	},
}
