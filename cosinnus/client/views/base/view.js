'use strict';

module.exports = Backbone.View.extend({
    render: function () {
        var data = this.getTemplateData();
        this.$el.html(this.template.render(data));
        console.log('base');
    }
});
