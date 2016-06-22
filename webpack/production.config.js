var webpack = require('webpack');
var shared = require('./shared.config');

module.exports = Object.assign({}, shared, {
    plugins: [
        new webpack.optimize.UglifyJsPlugin({
            compress: {
                warnings: false
            }
        })
    ]
});
