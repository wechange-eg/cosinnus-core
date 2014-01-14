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
        delete: function(holder) {

        },
        edit: function(holder) {

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
                function(data, textStatus, jqXHR) {
                    $('[data-target=widget-content]', holder).html(data);
                    $('[data-target=widget-title]', holder).html(jqXHR.getResponseHeader('X-Cosinnus-Widget-Title'));
            }).fail(
                function(jqXHR, textStatus, errorThrown) {
                    var error = $('<div class="alert alert-danger">An error occurred while loading the widget. </div>');
                    var reload = $('<a href="#" class="alert-link">Reload</a>').bind("click", {
                        holder: holder
                    }, function(event) {
                        event.preventDefault();
                        Cosinnus.dashboard.load(event.data.holder);
                    });
                    error.append(reload);
                    $('[data-target=widget-content]', holder).html(error);
                    $('[data-target=widget-title]', holder).html(textStatus);
            }).always(
                function() {
                    var menu = $('[data-target=widget-menu]', holder).empty();
                    var li = $('<li></li>');
                    var link = $('<a href="#">Edit</a>').bind("click", {
                            holder: holder
                        }, function(event) {
                            event.preventDefault();
                            Cosinnus.dashboard.edit(event.data.holder);
                        });
                    menu.append(li.clone().append(link));
                    link = $('<a href="#">Delete</a>').bind("click", {
                        holder: holder
                    }, function(event) {
                        event.preventDefault();
                        Cosinnus.dashboard.delete(event.data.holder);
                    });
                    menu.append(li.clone().append(link));
                    link = $('<a href="#">Reload</a>').bind("click", {
                        holder: holder
                    }, function(event) {
                        event.preventDefault();
                        Cosinnus.dashboard.load(event.data.holder);
                    });
                    menu.append(li.clone().append(link));
            });
        },
    };
}(jQuery, window.Cosinnus));