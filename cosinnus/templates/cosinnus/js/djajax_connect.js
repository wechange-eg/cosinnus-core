{% load cosinnus_tags %}

function djajax_trigger_{{ node_id }}() {
    console.log('called handler for node id {{ node_id }} with value: ' + $('#{{ node_id }}').val());
    var node_value = $('[djajax-id={{ node_id }}]').{{ value_selector }}({% if value_selector_arg %}'{{value_selector_arg}}'{% endif %})
    
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
             } else {
                 console.log('Error in Saving! for {{ node_id }} ! With data ' + JSON.stringify(data));
             }
             
         },
         error: function(data){
             console.log('Error! for {{ node_id }} ! With data ' + JSON.stringify(data));
         }
         
    });
};

{% comment %}  ****  Triggers  ****  {% endcomment %}

{% if "lose_focus" in trigger_on %}
    $('[djajax-id={{ node_id }}]').focusout(function(e) {
        djajax_trigger_{{ node_id }}();
    });
{% endif %}

{% if "enter_key" in trigger_on %}
$('[djajax-id={{ node_id }}]').keydown(function(e) {
    if (e.keyCode == 13) {
        {% if not "lose_focus" in trigger_on %}
            // only triggered here if the blur() event won't trigger anyways
            djajax_trigger_{{ node_id }}();
        {% endif %}
        $('[djajax-id={{ node_id }}]').blur();
        return false;
    }
});
{% endif %}

{% if "value_changed" in trigger_on %}
    $('[djajax-id={{ node_id }}]').change(function(e) {
        djajax_trigger_{{ node_id }}();
    });
{% endif %}