var webpack = require('webpack');
var _ = require('underscore');
var shared = require('./shared.config');

module.exports = _(shared).extend({
    devtool: 'inline-source-map',
    plugins: shared.plugins.concat([
    	new webpack.DefinePlugin({
		    DEBUG: true
		})
    ])
});

console.log(module.exports.plugins)
