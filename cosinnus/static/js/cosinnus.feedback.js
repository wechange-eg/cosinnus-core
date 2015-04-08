// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.Feedback = {

     cosinnus_report_object: function(cls, id, title) {
        // called from js code that is rendered via a cosinnus_tags.py templatetag!
        $('#cosinnus_report_title').text(title);
        $('#cosinnus_report_cls').val(cls);
        $('#cosinnus_report_id').val(id);
        $('#cosinnus_report_text').val('');
        $('#report_modal_error').hide();
        $.cosinnus.modal_activate();
        $('#cosinnus_report_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_report_submit);
        $('#cosinnus_report_modal').modal('show');
    },
    
    cosinnus_report_submit: function() {
        if (!$('#cosinnus_report_text').val()) {
            $('#cosinnus_report_empty_text_error_msg').show();
            return;
        };
    
        post_data = {
            'cls': $('#cosinnus_report_cls').val(),
            'id': $('#cosinnus_report_id').val(),
            'text': $('#cosinnus_report_text').val(),
        };
        
        $.cosinnus.modal_deactivate();
        $.ajax({
             type:"POST",
             url: cosinnus_report_object_url,
             data: post_data,
             success: function(data){
                 if (data['status'] == 'success') {
                     $.cosinnus.display_report_success('#report_modal_error');
                 } else {
                     $.cosinnus.display_report_error('#report_modal_error');
                 }
                 
             },
             error: function(data){
                 $.cosinnus.display_report_error('#report_modal_error');
             }
        });
    },
    

    cosinnus_move_element: function(obj_id, current_folder_id) {
       // called from js code that is rendered via a cosinnus_tags.py templatetag!
        $('#cosinnus_move_element_obj_id').val(obj_id);
        $('#cosinnus_move_element_current_folder_id').val(current_folder_id);
       $('#move_element_modal_error').hide();
       $.cosinnus.modal_activate();
       $('#cosinnus_move_element_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_move_element_submit);
       $('#cosinnus_move_element_modal').modal('show');
   },
   
   cosinnus_move_element_submit: function() {
       if (!$('#cosinnus_move_element_obj_id').val()) {
           return;
       };
       
       var element_id = $('#cosinnus_move_element_obj_id').val();
       var target_folder_id = $('#cosinnus_move_element_selected_folder').val();
       var current_folder_id = $('#cosinnus_move_element_current_folder_id').val()
       // don't do anything if we target the same folder the element is in
       if (target_folder_id == current_folder_id || element_id == target_folder_id) {
           $('#cosinnus_move_element_modal').modal('hide');
           return;
       }
       post_data = {
           'element_id': element_id,
           'target_folder_id': target_folder_id,
       };
       
       $.cosinnus.modal_deactivate();
       $.ajax({
            type:"POST",
            url: cosinnus_move_element_object_url,
            data: post_data,
            success: function(data){
                if (data == 'ok_element') {
                    $('#cosinnus_move_element_modal').modal('hide');
                    $('#cosinnus_list_element_' + element_id).fadeOut(800, function() {
                        $(this).remove();
                    });
                } else if (data == 'ok_folder') {
                    console.log('NYI');
                }
            },
            error: function(data){
                $.cosinnus.display_report_error('#cosinnus_move_element_modal');
            }
       });
   },
};
