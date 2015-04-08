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
    

    cosinnus_move_element: function(obj_id) {
       // called from js code that is rendered via a cosinnus_tags.py templatetag!
       $('#cosinnus_move_element_obj_id').val(obj_id);
       $('#move_element_modal_error').hide();
       $.cosinnus.modal_activate();
       $('#cosinnus_move_element_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_move_element_submit);
       $('#cosinnus_move_element_modal').modal('show');
   },
   
   cosinnus_move_element_submit: function() {
       if (!$('#cosinnus_move_element_obj_id').val()) {
           return;
       };
       
       post_data = {
           'element_id': $('#cosinnus_move_element_obj_id').val(),
           'target_folder_id': $('#cosinnus_move_element_selected_folder').val(),
       };
       
       $.cosinnus.modal_deactivate();
       $.ajax({
            type:"POST",
            url: cosinnus_move_element_object_url,
            data: post_data,
            success: function(data){
                if (data['status'] == 'success') {
                    //$.cosinnus.display_report_success('#cosinnus_move_element_modal');
                    console.log('success! close modal and hide pad!')
                } else {
                    $.cosinnus.display_report_error('#cosinnus_move_element_modal');
                }
            },
            error: function(data){
                $.cosinnus.display_report_error('#cosinnus_move_element_modal');
            }
       });
   },
};
