'use strict';

var util = require('lib/util.js');

module.exports = Backbone.View.extend({
    
    /**
     * Sets these values on the view:
     *  - self.options: 
     *      - purpose: the general behavioural settings for the view. only differ from default
     *          if passed through as View.init(options). don't change during runtime
     *      - value: extended self.defaults with the parameter options
     *  - self.state:
     *      - purpose: current state variables of the view. defaults can be set in 
     *          self.defaults.state, or passed through View.init(options.state).
     *          constantly change with the view's current state
     *      - value: self.options.state if exists or {}
     */
    initialize: function (options) {
        this.options = $.extend(true, {}, this.defaults, options);
        this.state = this.options && this.options.state || {};
    },
    
    /**
     * If self.options.elParent is set,
     *         the given el is ignored at first and elParent is considered the 
     *         parent element, so
     *         instead of creating this template by filling a giving element,
     *         the complete rendered template will appended to the given $el,
     *         and then become this views actual $el!
     */
    render: function () {
        var self = this;
        // Collect the data to be rendered; can be overridden in child view.
        var data = this.getTemplateData();
        // Use nunjucks to render the template (specified in child view).
        if (this.template && this.template.render &&
            typeof this.template.render === 'function') {
            var rendered = this.template.render(data);
            
            if (self.options.elParent) {
                // if this element is not in place yet, append it to the parent
                // otherwise replace it
                rendered = $(rendered);
                if (self.$el.parent().length == 0) {
                    $(self.options.elParent).append(rendered);
                } else {
                    self.$el.replaceWith(rendered);
                }
                this.setElement(rendered);
            } else {
                this.$el.html(rendered);
            }

            $.cosinnus.titledby(this.$el);
        }
        // After a repaint (to allow further rendering in #afterRender),
        // call the after render method if it exists.
        setTimeout(function () {
            self.afterRender && self.afterRender();
        }, 0);
        return this;
    },

    /**
     *  Default implementation to retrieve data to be rendered.
     *  If a model is set, return its attributes as JSON, otherwise
     *  an empty object with any options and state attributes on the 
     *  view mixed in.
     */
    getTemplateData: function () {
        var modelData = this.model && this.model.toJSON() || {'noModel': true};
        var data = _.extend(
            modelData,
            this.options,
            this.state,
            {
                'cosinnus_active_user': cosinnus_active_user,
                'COSINNUS_IDEAS_ENABLED': COSINNUS_IDEAS_ENABLED,
                'COSINNUS_SHOW_SUPERUSER_CONTROLS': COSINNUS_SHOW_SUPERUSER_CONTROLS,
            }
        );
        return data;
    },
    
    /** Wrap you signal handlers in this function inside views to retain
     *  the view as `this` as context.
     *  Example: 
     *      collection.on({
     *         'add' : self.thisContext(self.myCall)
     *      });
     *  ==>  myCall(...) will have `this` set to `self`
    */
    thisContext: function(func) {
        var self = this;
        return function(){
            func.apply(self, arguments);
        };
    }
});
