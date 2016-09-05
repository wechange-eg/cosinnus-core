module.exports = function(booleanish, options) {
    var content = options.fn(this);

    if (options.data.root.raw) {
        return '{% if ' + booleanish + '%}' + content + '{% endif %}';
    } else if (booleanish) {
        return content;
    }

    return '';
}
