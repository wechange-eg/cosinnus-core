var webpack = require('webpack');
var _ = require('underscore');
var shared = require('./shared.config');

module.exports = _(shared).extend({
    plugins: shared.plugins.concat([
        new webpack.optimize.UglifyJsPlugin({
            compress: {
                warnings: false
            }
        }),
        new webpack.DefinePlugin({
		    DEBUG: false
		})
    ])
});
