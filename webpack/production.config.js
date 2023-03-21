var webpack = require('webpack');
var _ = require('underscore');
var shared = require('./shared.config');
const TerserPlugin = require("terser-webpack-plugin");

module.exports = _(shared).extend({
    plugins: shared.plugins.concat([
        new webpack.DefinePlugin({
		    DEBUG: false
		})
    ]),
    optimization: {
        minimize: true,
        minimizer: [new TerserPlugin()],
    }
});
