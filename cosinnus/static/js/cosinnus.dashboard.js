(function($, cosinnus){
    cosinnus.dashboard = {
        init: function(holder, group) {
            var that = this;
            this.holder = holder && $(holder) || $('#cosinnus-dashboard');
            this.group = group || false;
            var widget_tags = $('[data-type=widget]', this.holder);
            $.each(widget_tags, function() {
                holder = $(this);
                that.bind_menu(holder);
                that.load(holder);
            });
            var add_widget = $('[data-type=widget-add]', this.holder);
            $('[data-target=widget-add-button]', add_widget).bind("click", {
                holder: $(add_widget)
            }, function(event) {
                event.preventDefault();
                Cosinnus.dashboard.add_empty(event.data.holder);
            });
            return this;
        },
        add: function(holder, args) {
            var that = this;
            args = args || {};
            var app = args.app;
            var widget = args.widget;
            var data = args.data;
            var url = Cosinnus.base_url + 'widgets/add/';
            if (Cosinnus.dashboard.group === false) {
                url = url + "user/";
            } else {
                url = url + "group/" + Cosinnus.dashboard.group + "/";
            }
            url = url + app + "/" + widget + "/";
            if (data === undefined) {
                data = {};
            }
            $.post(url, data, function(data, textStatus, jqXHR) {
                if (jqXHR.getResponseHeader('Content-Type') === "application/json") {
                    var id = data['id'];
                    holder.attr('data-widget-id', id).attr('data-type', 'widget');
                    Cosinnus.dashboard.bind_menu(holder);
                    Cosinnus.dashboard.load(holder);
                } else {
                    Cosinnus.dashboard.show_settings(holder, data, Cosinnus.dashboard.add, {
                        app: app,
                        widget: widget
                    });
                }
            }).fail(function(jqXHR, textStatus, errorThrown) {
                $('[data-target=widget-content]', holder).html('<div class="alert alert-danger">An error occurred while adding the widget.</div>');
            });
        },
        add_empty: function(holder) {
            var that = this;
            $.ajax(Cosinnus.base_url + "widgets/list/").done(function(data, textStatus, jqXHR) {
                var new_holder = $('[data-type=widget-spare]', that.holder).clone().attr('data-type', 'widget-new');
                var list = $('<ul></ul>');
                $.each(data, function(k) {
                    var app = $('<li></li>').append(k);
                    var widgets = $('<ul></ul>');
                    $.each(this, function(i, v) {
                        var widget = $('<a href="#"></a>').append(v).bind("click", {
                            holder: new_holder,
                            app: k,
                            widget: v
                        }, function(event) {
                            event.preventDefault();
                            Cosinnus.dashboard.add(event.data.holder, {
                                app: event.data.app,
                                widget: event.data.widget
                            });
                        });
                        widgets.append($('<li></li>').append(widget));
                    });
                    list.append(app.append(widgets));
                });
                $('[data-target=widget-content]', new_holder).html(list);
                $('[data-target=widget-title]', new_holder).html("Select a widget");
                new_holder.hide().insertBefore(holder).fadeIn("slow");
                // new_holder.insertBefore(holder);
            });
        },
        bind_menu: function(holder) {
            $('[data-type=refresh]', holder).bind("click", {
                holder: holder
            }, function(event) {
                event.preventDefault();
                Cosinnus.dashboard.load(event.data.holder);
            });
            $('[data-type=edit]', holder).bind("click", {
                holder: holder
            }, function(event) {
                event.preventDefault();
                Cosinnus.dashboard.edit(event.data.holder);
            });
            $('[data-type=delete]', holder).bind("click", {
                holder: holder
            }, function(event) {
                event.preventDefault();
                Cosinnus.dashboard.delete(event.data.holder);
            });
        },
        delete: function(holder) {
            var that = this;
            var id = holder.attr('data-widget-id');
            $.post(Cosinnus.base_url + "widget/" + id + "/delete/", function(data) {
                holder.fadeOut("slow", function() {
                    holder.remove();
                });
            }).fail(function(jqXHR, textStatus, errorThrown) {
                $('[data-target=widget-content]', holder).html('<div class="alert alert-danger">An error occurred while removing the widget.</div>');
            });
        },
        edit: function(holder, args) {
            var that = this;
            args = args || {};
            var id = holder.attr('data-widget-id');
            var settings = {};
            if (args.data !== undefined) {
                args['type'] = "POST";
            }
            $.ajax(Cosinnus.base_url + "widget/" + id + "/edit/", args).done(function(data, textStatus, jqXHR) {
                if (jqXHR.getResponseHeader('Content-Type') === "application/json") {
                    Cosinnus.dashboard.load(holder);
                } else {
                    Cosinnus.dashboard.show_settings(holder, data, Cosinnus.dashboard.edit);
                }
            }).fail(function(jqXHR, textStatus, errorThrown) {
                $('[data-target=widget-content]', holder).html('<div class="alert alert-danger">An error occurred while configuring the widget.</div>');
            });
        },
        load: function(holder) {
            var that = this;
            var id = holder.attr('data-widget-id');
            $.ajax(Cosinnus.base_url + "widget/" + id + "/").done(function(data, textStatus, jqXHR) {
                $('[data-target=widget-content]', holder).html(data);
                $('[data-target=widget-title]', holder).html(jqXHR.getResponseHeader('X-Cosinnus-Widget-Title'));
                var title_url = jqXHR.getResponseHeader('X-Cosinnus-Widget-Title-URL');
                if (title_url !== null) {
                    $('[data-target=widget-title-url]', holder).attr("href", title_url);
                } else {
                    $('[data-target=widget-title-url]', holder).children().unwrap();
                }
                holder.attr("data-app-name", jqXHR.getResponseHeader('X-Cosinnus-Widget-App-Name'));
                holder.attr("data-widget-name", jqXHR.getResponseHeader('X-Cosinnus-Widget-Widget-Name'));
            }).fail(function(jqXHR, textStatus, errorThrown) {
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
            });
        },
        show_settings: function(holder, data, submit_callback, submit_data) {
            var content = $(data);
            var form = $('[type=submit]', content).parents('form');
            form.submit(function(event) {
                event.preventDefault();
                submit_data = submit_data || {};
                submit_data.data = form.serialize();
                submit_callback(holder, submit_data);
            });
            $('[data-target=widget-content]', holder).html(content);
        },
    };
}(jQuery, window.Cosinnus));