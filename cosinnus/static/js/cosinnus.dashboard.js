
//  ************   vvvvvvvvvv REMOVE THIS OR REFACTOR, TEST ONLY! vvvvvvvvvvvvvvvv *************


//Dashboard: activate links
$('.js-todo-link').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    location.href = location.pathname + 'todo/';
});

(function($, cosinnus){
    cosinnus.dashboard = {
        init: function(holder, group) {
            var that = this;
            this.holder = holder && $(holder) || $('#cosinnus-dashboard');
            this.group = group || false;
            var widget_tags = $('[data-type=widget]', this.holder);
            $.each(widget_tags, function() {
                holder = $(this);
                that.initWidget(holder);
            });
            this.refreshUI();
            
            var add_widget = $('[data-type=widget-add]', this.holder);
            $('[data-target=widget-add-button]', add_widget).bind("click", {
                holder: $(add_widget)
            }, function(event) {
                event.preventDefault();
                Cosinnus.dashboard.add_empty(event.data.holder);
            });
            return this;
        },
        initWidget: function(widget_node) {
            this.bind_menu(widget_node);
            this.load(widget_node, 0, true);
        },
        add: function(holder, args) {
            var that = this;
            args = args || {};
            var app = args.app;
            var widget = args.widget;
            var data = args.data;
            var url = "/";
            if (Cosinnus.dashboard.group === false) {
                url = url + "widgets/add/user/";
            } else {
                url = url + cosinnus_group_url_path + "/" + Cosinnus.dashboard.group + "/widgets/add/";
            }
            url = url + app + "/" + widget + "/";
            if (data === undefined) {
                data = {};
            }
            $.post(url, data, function(data, textStatus, jqXHR) {
                // if (jqXHR.getResponseHeader('Content-Type') === "application/json") {
                // we assume here we got the rendered widget back and replace the config dialog with the widget
                var widget = that.swapWidgetFromData(data, holder);
                that.initWidget(widget);
                
            }).fail(function(jqXHR, textStatus, errorThrown) {
                $('[data-target=widget-content]', holder).prepend('<div class="alert alert-danger">An error occurred while adding the widget.</div>');
            });
        },
        /** Exchanges a widget for a new widget that is being parsed from server data HTML.
         *  return: the widget as a jQuery node. */
        swapWidgetFromData: function(data, old_widget, dontRemove) {
            var widget_node = $.parseHTML(data, keepScripts=true);
            old_widget.before(widget_node);
            var widget = old_widget.prev();
            widget.hide().fadeIn("slow");
            if (!(dontRemove !== undefined && dontRemove)) {
                old_widget.remove();
            }
            return widget;
        },
        add_empty: function(holder) {
            var that = this;
            var url = "/";
            if (Cosinnus.dashboard.group === false) {
                url = url + "widgets/add/user/";
            } else {
                url = url + cosinnus_group_url_path + "/" + Cosinnus.dashboard.group + "/widgets/add/";
            }
            
            $.ajax(url).done(function(data, textStatus, jqXHR) {
                var widget_anchor = $('[data-type=widget-anchor]', that.holder);
                var widget = that.swapWidgetFromData(data, widget_anchor, true);
                
                var save_button = $('[data-target=widget-save-button]', widget);
                save_button.bind("click", {
                    holder: widget
                }, function(event) {
                    event.preventDefault();
                    // save widget: we get the form data of the visible form to POST to backend
                    Cosinnus.dashboard.add(event.data.holder, {
                        app: $('form:visible', widget).attr('data-widget-app'),
                        widget:$('form:visible', widget).attr('data-widget-widget'),
                        data: $('form:visible', widget).serialize()
                    });
                });
                // cancel button just removes the element
                var cancel_button = $('[data-target=widget-cancel-button]', widget);
                cancel_button.bind("click", {
                    holder: widget
                }, function(event) {
                    event.preventDefault();
                    event.data.holder.fadeOut("slow");
                });
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
            $.post("/" + "widget/" + id + "/delete/", function(data) {
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
            var app = args.app;
            var widget = args.widget;
            var extra_url = '';
            if (app !== undefined && widget !== undefined) {
                extra_url += app + '/' + widget + '/';
            }
            var id = holder.attr('data-widget-id');
            var settings = {};
            
            if (args.data !== undefined) {
                args['type'] = "POST";
            }
            // either POSTing or GETing here, what we do after depends on that
            $.ajax("/" + "widget/" + id + "/edit/" + extra_url, args).done(function(data, textStatus, jqXHR) {
                
                if (args['type'] == "POST") {
                    // if (jqXHR.getResponseHeader('Content-Type') === "application/json") {
                    // we assume here we got the rendered widget back and replace the config dialog with the widget
                    // first, we destroy the old widget that has been hiding
                    holder.next().remove();
                    var widget = that.swapWidgetFromData(data, holder);
                    that.initWidget(widget);
                    
                } else {
                    /* Swap widget for its edit view widget (but only hide the widget) */
                    var widget = that.swapWidgetFromData(data, holder, true);
                    holder.hide();
                    var save_button = $('[data-target=widget-save-button]', widget);
                    save_button.bind("click", {
                        holder: widget
                    }, function(event) {
                        event.preventDefault();
                        // save widget: we get the form data of the visible form to POST to backend
                        Cosinnus.dashboard.edit(event.data.holder, {
                            app: $('form:visible', widget).attr('data-widget-app'),
                            widget:$('form:visible', widget).attr('data-widget-widget'),
                            data: $('form:visible', widget).serialize()
                        });
                    });
                    var cancel_button = $('[data-target=widget-cancel-button]', widget);
                    cancel_button.bind("click", {
                        holder: widget
                    }, function(event) {
                        event.preventDefault();
                        // save widget: we get the form data of the visible form to POST to backend
                        Cosinnus.dashboard.cancel_edit(event.data.holder);
                    });
                }
            }).fail(function(jqXHR, textStatus, errorThrown) {
                $('[data-target=widget-content]', holder).html('<div class="alert alert-danger">An error occurred while configuring the widget.</div>');
            });
        },
        cancel_edit: function(holder) {
            holder.next().fadeIn("slow");
            holder.remove();
        },
        load: function(holder, offset, delayRefresh) {
            var that = this;
            var id = holder.attr('data-widget-id');
            offset = parseInt(offset || 0);
            delayRefresh = (typeof delayRefresh === "undefined") ? false : delayRefresh;
            
            if (typeof id !== "undefined") {
                $.ajax("/" + "widget/" + id + "/" + offset + "/").done(function(data, textStatus, jqXHR) {
                    var rows_returned = parseInt(data['X-Cosinnus-Widget-Num-Rows-Returned'] || 0);
                    var has_more_data = 'true' === (data['X-Cosinnus-Widget-Has-More-Data'] || 'false');
                    
                    // display the fetched data if we have actually gotten something back, or if
                    // this is the initial query (we expect a rendered "no content" message)
                    if (rows_returned > 0 || offset == 0) {
                        $('[data-target=widget-content]', holder).append(data['X-Cosinnus-Widget-Content']);
                    }
                    if (has_more_data > 0) {
                        // attach the function to load the next set of data from the backend to the "More" button
                        $('[data-target=widget-reload-button]', holder).unbind('click');
                        $('[data-target=widget-reload-button]', holder).click(function() {
                            that.load(holder, offset + rows_returned);
                        });
                    } else {
                        // hide the "More button"
                        $('[data-target=widget-reload-button]', holder).hide();
                    }
                        
                    var s = data['X-Cosinnus-Widget-Title'];
                    
                    $('[data-target=widget-title]', holder).html(s);
                    var title_url = data['X-Cosinnus-Widget-Title-URL'];
                    if (title_url) {
                        $('[data-target=widget-title-url]', holder).attr("href", title_url);
                    } else {
                    	$('[data-target=widget-title-url]', holder).removeAttr("href");
                    }
                    holder.attr("data-app-name", data['X-Cosinnus-Widget-App-Name']);
                    holder.attr("data-widget-name", data['X-Cosinnus-Widget-Widget-Name']);
                    
                    if (delayRefresh) {
                        Cosinnus.dashboard.delayedRefreshUI(); 
                    } else {
                        Cosinnus.dashboard.refreshUI();
                    }
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
            }
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
        refreshUI: function() {
            $.cosinnus.renderMomentDataDate();
            $( window ).trigger( 'dashboardchange' );
        },
        _delayedRefreshTimer: 0,
        delayedRefreshUI: function(){
            clearTimeout(this._delayedRefreshTimer);
            this._delayedRefreshTimer = setTimeout(Cosinnus.dashboard.refreshUI, 250);
        },
    };
}(jQuery, window.Cosinnus));


