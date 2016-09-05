module.exports = function(booleanish, options) {
    var content = options.fn(this);

    if (options.data.root.raw) {
        var raw_if = options.hash['raw_if'];
        return '{% if ' + raw_if + ' %}' + content + '{% endif %}';
    } else if (booleanish) {
        return content;
    }

    return '';
}
