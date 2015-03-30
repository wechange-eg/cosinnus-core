// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.Feedback = {

     cosinnus_report_object: function(cls, id, title) {
        $('#cosinnus_report_title').text(title);
        $('#cosinnus_report_cls').val(cls);
        $('#cosinnus_report_id').val(id);
        $('#cosinnus_report_text').val('');
        $('#report_modal_error').hide();
        $.cosinnus.Feedback._report_modal_activate();
        $('#cosinnus_report_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_report_submit);
        $('#cosinnus_report_modal').modal('show');
    },
    
    _report_modal_activate: function() {
        $('._elem-action-disabled').attr('disabled', false);
        $('._elem-action-hidden').show();
        $('._elem-action-shown').hide();
        $('._elem-start-shown').show();
        $('._elem-start-hidden').hide();
        $('._elem-success-shown').hide();
    },
    
    _report_modal_deactivate: function() {
        $('._elem-action-disabled').attr('disabled', true);
        $('._elem-action-hidden').hide();
        $('._elem-action-shown').show();
        $('._elem-success-shown').hide();
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
        
        function display_report_error() {
            console.log('error submitting');
            $('#report_modal_error').show();
            $.cosinnus.Feedback._report_modal_activate();
        };
        function display_report_success() {
            console.log('success submitting');
            $('#report_modal_error').hide();
            $.cosinnus.Feedback._report_modal_activate();
            $('._elem-success-shown').show();
            $('._elem-success-hidden').hide();
        };
        
        $.cosinnus.Feedback._report_modal_deactivate();
        $.ajax({
             type:"POST",
             url: cosinnus_report_object_url,
             data: post_data,
             success: function(data){
                 if (data['status'] == 'success') {
                     display_report_success();
                 } else {
                     display_report_error();
                 }
                 
             },
             error: function(data){
                 display_report_error();
             }
        });
    },
};
