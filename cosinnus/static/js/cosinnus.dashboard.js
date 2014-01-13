(function($, cosinnus){
    cosinnus.dashboard = {
        init: function(holder, base_url) {
            var that = this;
            this.holder = holder && $(holder) || $('#cosinnus-dashboard');
            this.base_url = base_url || '/';
            var widget_tags = $('div[data-type=widget]', this.holder);
            $.each(widget_tags, function() {
                var id = $(this).data('widget-id');
                that.load(id, $(this));
            });
            return this;
        },
        list: function() {
            var that = this;
            $.ajax(this.base_url + "widgets/list/").done(function(data){
                var list = $('<ul></ul>');
                $.each(data, function(k) {
                    console.log(k);
                    var app = $('<li></li>').append(k);
                    var widgets = $('<ul></ul>');
                    $.each(this, function(i, v) {
                        console.log(v);
                        var widget = $('<li></li>').append(v);
                        widgets.append(widget);
                    });
                    app.append(widgets);
                    list.append(app);
                });
                that.holder.html(list);
            });
        },
        load: function(widget, holder) {
            var that = this;
            $.ajax(this.base_url + "widget/" + widget + "/").done(function(data){
                holder.html(data);
            });
        },
    };
}(jQuery, window.Cosinnus));