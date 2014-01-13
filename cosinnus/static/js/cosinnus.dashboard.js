(function($, cosinnus){
    cosinnus.dashboard = {
        init: function(holder) {
            var that = this;
            this.holder = holder && $(holder) || $('#cosinnus-dashboard');
            var widget_tags = $('div[data-type=widget]', this.holder);
            $.each(widget_tags, function() {
                that.load($(this));
            });
            return this;
        },
        list: function() {
            var that = this;
            $.ajax(Cosinnus.base_url + "widgets/list/").done(function(data){
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
        load: function(holder) {
            var that = this;
            var id = holder.data('widget-id');
            $.ajax(Cosinnus.base_url + "widget/" + id + "/").done(
                function(data) {
                    holder.html(data);
                }).fail(
                function() {
                    var error = $('<div class="alert alert-danger">An error occurred while performing the request. </div>');
                    var reload = $('<a href="#" class="alert-link">Reload</a>').bind("click", {
                        holder: holder
                    }, function(event) {
                        Cosinnus.dashboard.load(event.data.holder);
                    });
                    error.append(reload);
                    holder.html(error);
                });
        },
    };
}(jQuery, window.Cosinnus));