var webpack = require('webpack');
var path = require('path');

module.exports = {
    entry: path.join(__dirname, 'cosinnus/client/index.js'),
    output: {
        path: path.join(__dirname, 'cosinnus/static/js/'),
        filename: 'client.js'
    },
    devtool: 'inline-source-map',
    module: {
        loaders: [
            {
                test: /\.html$/,
                loader: 'nunjucks-loader',
                include: [
                    path.join(__dirname, 'cosinnus/templates/cosinnus/universal')
                ],
                query: {
                    config: path.join(__dirname, 'nunjucks.config.js')
                }
            }
        ],
    },
    resolve: {
        root: [
            path.join(__dirname, 'cosinnus/templates/cosinnus/universal'),
            path.join(__dirname, 'cosinnus/client')
        ],
        extensions: [
            '.js',
            '.html',
            ''
        ]
    }
};
