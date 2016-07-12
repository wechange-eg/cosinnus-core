var webpack = require('webpack');
var path = require('path');
var base = path.resolve('.');

module.exports = {
    entry: path.join(base, 'cosinnus/client/index.js'),
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
            }
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
    }
}
