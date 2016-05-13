var webpack = require('webpack');
var path = require('path');

module.exports = {
    entry: path.join(__dirname, 'cosinnus/client/index.js'),
    output: {
        path: path.join(__dirname, 'cosinnus/static/js/'),
        filename: 'client.js'
    },
    module: {
        loaders: [
            {
                test: /\.njk$/,
                loader: 'nunjucks-loader'
            }
        ],
    },
    resolve: {
        root: [
            path.join(__dirname, 'cosinnus/templates/cosinnus'),
            path.join(__dirname, 'cosinnus/client')
        ],
        extensions: [
            '.js',
            '.njk',
            ''
        ]
    }
};
