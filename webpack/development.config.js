var _ = require('underscore');
var shared = require('./shared.config');

module.exports = _(shared).extend({
    devtool: 'inline-source-map'
});
