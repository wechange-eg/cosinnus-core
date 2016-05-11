var webpack = require('webpack')
var path = require('path');

module.exports = {
    entry: './cosinnus/static/js/index.js',
    output: {
        path: './cosinnus/static/js/',
        filename: 'app.js'
    },
    module: {
        loaders: [
            {
                test: /\.njk\.html$/,
                loader: 'nunjucks-loader'
            }
        ],
    },
    resolve: {
        root: [
            path.join(__dirname, 'cosinnus/templates/cosinnus'),
            path.join(__dirname, 'cosinnus/static/js/app')
        ],
        extensions: [
            '.js',
            '.njk.html',
            ''
        ]
    }
}
