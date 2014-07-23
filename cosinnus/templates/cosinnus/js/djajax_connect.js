{% load cosinnus_tags %}

$('#{{ node_id }}').keyup(function() {
    console.log('called handler for node id {{ node_id }} with value: ' + $('#{{ node_id }}').val());
    
    $.ajax({
         type:"POST",
         url:"/api/v1/taggable_object/update/",
         data: {
            'app_label': '{{ app_label }}',
            'model_name': '{{ model_name }}',
            'pk': '{{ pk }}',
            'property_name': '{{ property_name }}',
            'property_data':  $('#{{ node_id }}').val()
         },
         success: function(data){
             console.log('Success! for {{ node_id }} ! With data ' + JSON.stringify(data));
         },
         error: function(data){
             console.log('Error! for {{ node_id }} ! With data ' + JSON.stringify(data));
         }
         
    });
});
