{% load cosinnus_tags %}

function djajax_get_value_{{ node_id }}() {
    {% if value_object_property %}
        return $('[djajax-id={{ node_id }}]')[0].{{ value_object_property }};
    {% else %}
        return $('[djajax-id={{ node_id }}]').{{ value_selector }}({% if value_selector_arg %}'{{value_selector_arg}}'{% endif %});
    {% endif %}  
};

function djajax_set_value_{{ node_id }}(value) {
    {% if value_object_property %}
        $('[djajax-id={{ node_id }}]')[0].{{ value_object_property }} = value;
    {% else %}
        $('[djajax-id={{ node_id }}]').{{ value_selector }}({% if value_selector_arg %}'{{value_selector_arg}}',{% endif %}value);
    {% endif %}  
};

function djajax_trigger_{{ node_id }}(e) {
    console.log('called handler for node id {{ node_id }} with value: ' + $('#{{ node_id }}').val());
    var node_value = djajax_get_value_{{ node_id }}();
    
    {% if value_transform %}
        var transform_function = window["{{ value_transform }}"];
        if (typeof transform_function === 'function') {
            node_value = transform_function(node_value);
        } else {
            console.warn('Djajax: Value transform could not be applied for node_id "{{node_id}}". Supplied transform function could not be found or was not a function.')
        }
    {% endif %}
    
    {% if not empty == "true" %}
        if (node_value == null || node_value == '') {
            console.log('Submitted field value for {{ node_id }} was found to be empty, but djajax empty=False was set! Restoring last value.');
            // restore last data
            djajax_set_value_{{ node_id }}($('[djajax-id={{ node_id }}]').attr('djajax-last-value'));
            return;
        }
    {% endif %}
       
    $.ajax({
         type:"POST",
         url:"{{ post_to }}",
         data: {
            'app_label': '{{ app_label }}',
            'model_name': '{{ model_name }}',
            'pk': '{{ pk }}',
            'property_name': '{{ property_name }}',
            'property_data':  node_value,
            '{{ property_name }}': node_value,
         },
         success: function(data){
             if (data['status'] == 'success') {
                 console.log('Success! for {{ node_id }} ! With data ' + JSON.stringify(data));
                 // save last data
                 $('[djajax-id={{ node_id }}]').attr('djajax-last-value', djajax_get_value_{{ node_id }}());
                 {% if on_success %}
                 // execute on_success
                 {{ on_success|safe }}
                 {% endif %}
             } else {
                 console.log('Error in Saving! for {{ node_id }} ! With data ' + JSON.stringify(data));
                 // restore last data
                 console.log('restoring lasta data:' + $('[djajax-id={{ node_id }}]').attr('djajax-last-value'))
                 djajax_set_value_{{ node_id }}($('[djajax-id={{ node_id }}]').attr('djajax-last-value'));
             }
             
         },
         error: function(data){
             console.log('Error! for {{ node_id }} ! With data ' + JSON.stringify(data));
             // restore last data
             console.log('restoring lasta data:' + $('[djajax-id={{ node_id }}]').attr('djajax-last-value'))
             djajax_set_value_{{ node_id }}($('[djajax-id={{ node_id }}]').attr('djajax-last-value'));
         
         }
         
    });
};

{% comment %}  ****  Triggers  ****  {% endcomment %}

{% if "lose_focus" in trigger_on %}
    $('[djajax-id={{ node_id }}]').focusout(function(e) {
        djajax_trigger_{{ node_id }}(e);
    });
{% endif %}

{% if "enter_key" in trigger_on %}
$('[djajax-id={{ node_id }}]').keydown(function(e) {
    if (e.keyCode == 13) {
        {% if not "lose_focus" in trigger_on %}
            // only triggered here if the blur() event won't trigger anyways
            djajax_trigger_{{ node_id }}(e);
        {% endif %}
        $('[djajax-id={{ node_id }}]').blur();
        return false;
    }
});
{% endif %}

{% if "value_changed" in trigger_on %}
$('[djajax-id={{ node_id }}]').change(function(e) {
    djajax_trigger_{{ node_id }}(e);
});
{% endif %}

{% if "click" in trigger_on %}
$('[djajax-id={{ node_id }}]').click(function(e) {
    djajax_trigger_{{ node_id }}(e);
});
{% endif %}


// set last-node-value
$('[djajax-id={{ node_id }}]').attr('djajax-last-value', djajax_get_value_{{ node_id }}());
