module.exports = function(context, options) {
    var name = options.fn(this);
    if (options.data.root.raw) {
        return '{{' + name + '}}';
    } else {
        return context[name];
    }
}
