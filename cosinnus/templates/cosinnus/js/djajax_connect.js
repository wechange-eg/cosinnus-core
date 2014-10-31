{% load djajax_tags %}

/** ******** DJAJAX FUNCTIONS ******** */
function executeFunctionByName(functionName, context /*, args */) {
    var args = [].slice.call(arguments).splice(2);
    var namespaces = functionName.split(".");
    var func = namespaces.pop();
    for(var i = 0; i < namespaces.length; i++) {
      context = context[namespaces[i]];
    }
    return context[func].apply(this, args);
  }

function djajax_get_value(item) {
    if ('value_object_property' in item) {
        return $('[djajax-id='+item.node_id+']')[0][item.value_object_property];
    } else {
        if ('value_selector_arg' in item) {
            return $('[djajax-id='+item.node_id+']')[item.value_selector](item.value_selector_arg);
        } else {
            return $('[djajax-id='+item.node_id+']')[item.value_selector]();
        }
    }  
};

function djajax_set_value(item, value) {
    if ('value_object_property' in item) {
        $('[djajax-id='+item.node_id+']')[0][item.value_object_property] = value;
    } else {
        if ('value_selector_arg' in item) {
            return $('[djajax-id='+item.node_id+']')[item.value_selector](item.value_selector_arg, value);
        } else {
            return $('[djajax-id='+item.node_id+']')[item.value_selector](value);
        }
    }
};


function djajax_trigger(e, item) {
    console.log('called handler for node id ' + item.node_id + ' with value: ' + $('#' + item.node_id).val());
    var node_value = djajax_get_value(item);
    
    if ('value_transform' in item) {
        var transform_function = window[item.value_transform];
        if (typeof transform_function === 'function') {
            node_value = transform_function(node_value);
        } else {
            console.warn('Djajax: Value transform could not be applied for node_id "' + item.node_id + '". Supplied transform function could not be found or was not a function.')
        }
    }
    
    if (item.empty != "true") {
        if (node_value == null || node_value == '') {
            console.log('Submitted field value for ' + item.node_id + ' was found to be empty, but djajax empty=False was set! Restoring last value.');
            // restore last data
            djajax_set_value(item, $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value'));
            return;
        }
    }
    
    var post_data = {
        'app_label': item.app_label,
        'model_name': item.model_name,
        'pk': item.pk,
        'property_name': item.property_name,
        'property_data':  node_value,
    };
    post_data[item.property_name] = node_value;
    
    $.ajax({
         type:"POST",
         url: item.post_to,
         data: post_data,
         success: function(data){
             if (data['status'] == 'success') {
                 console.log('Success! for ' + item.node_id + ' ! With data ' + JSON.stringify(data));
                 // save last data
                 $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value', djajax_get_value(item));
                 
                 if ('on_success' in item) {
                     if ('on_success_args' in item) {
                         executeFunctionByName(item.on_success, window, item.on_success_args);
                     } else {
                         executeFunctionByName(item.on_success, window);
                     }
                 }
                 
             } else {
                 console.log('Error in Saving! for ' + item.node_id + ' ! With data ' + JSON.stringify(data));
                 // restore last data
                 console.log('restoring lasta data:' + $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value'))
                 djajax_set_value(item, $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value'));

                 if ('on_error' in item) {
                     if ('on_error_args' in item) {
                         executeFunctionByName(item.on_error, window, item.on_error_args);
                     } else {
                         executeFunctionByName(item.on_error, window);
                     }
                 }
             }
             
         },
         error: function(data){
             console.log('Error! for ' + item.node_id + ' ! With data ' + JSON.stringify(data));
             // restore last data
             console.log('restoring lasta data:' + $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value'))
             djajax_set_value(item, $('[djajax-id=' + item.node_id + ']').attr('djajax-last-value'));

             if ('on_error' in item) {
                 if ('on_error_args' in item) {
                     executeFunctionByName(item.on_error, window, item.on_error_args);
                 } else {
                     executeFunctionByName(item.on_error, window);
                 }
             }
         }
         
    });
};

/** ******** DJAJAX ITEMS ******** */
{% for item in djajax_items %}
    var item_json_{{ item.node_id }} = {{ item|jsonify }};
{% endfor %}

/** ******** DJAJX TRIGGERS ******** */
{% spaceless %}
{% for item in djajax_items %}
    {% with item_id=item.node_id %}
        {% if "lose_focus" in item.trigger_on %}
            $('[djajax-id={{ item_id }}]').focusout(function(e) {
                djajax_trigger(e, item_json_{{ item.node_id }});
            });
        {% endif %}
        {% if "enter_key" in item.trigger_on %}
            $('[djajax-id={{ item_id }}]').keydown(function(e) {
                if (e.keyCode == 13) {
                    {% if not "lose_focus" in item.trigger_on %}
                        // only triggered here if the blur() event won't trigger anyways
                        djajax_trigger(e, item_json_{{ item_id }});
                    {% endif %}
                    $('[djajax-id={{ item_id }}]').blur();
                    return false;
                }
            });
        {% endif %}
        {% if "value_changed" in item.trigger_on %}
            $('[djajax-id={{ item_id }}]').change(function(e) {
                djajax_trigger(e, item_json_{{ item_id }});
            });
        {% endif %}
        {% if "click" in item.trigger_on %}
            $('[djajax-id={{ item_id }}]').click(function(e) {
                djajax_trigger(e, item_json_{{ item_id }});
            });
        {% endif %}
        // set last-node-value
        $('[djajax-id={{ item_id }}]').attr('djajax-last-value', djajax_get_value(item_json_{{ item_id }}));
    {% endwith %}
{% endfor %}
{% endspaceless %}