'use strict';

module.exports = Backbone.View.extend({
    initialize: function (options) {
        this.state = options && options.state || {};
    },

    render: function () {
        var self = this;
        // Collect the data to be rendered; can be overridden in child view.
        var data = this.getTemplateData();
        // Use nunjucks to render the template (specified in child view).
        if (this.template && this.template.render &&
            typeof this.template.render === 'function') {
            this.$el.html(this.template.render(data));
        }
        // After a repaint (to allow further rendering in #afterRender),
        // call the after render method if it exists.
        setTimeout(function () {
            self.afterRender && self.afterRender();
        }, 0);
        return this;
    },

    // Default implementation to retrieve data to be rendered.
    // If a model is set, return its attributes as JSON, otherwise
    // an empty object with any state attributes on the view mixed in.
    getTemplateData: function () {
        var modelData = this.model && this.model.toJSON() || {};
        var data = _(modelData).extend(this.state);
        return data;
    }
});
