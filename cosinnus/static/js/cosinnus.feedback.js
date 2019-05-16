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
    
        var post_data = {
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
    

    cosinnus_move_element: function(obj_id_list, current_folder_id) {
       // called from js code that is rendered via a cosinnus_tags.py templatetag!
       $('#cosinnus_move_element_obj_ids').val(obj_id_list.join(","));
       $('#cosinnus_move_element_current_folder_id').val(current_folder_id);
       $('#move_element_modal_error').hide();
       $.cosinnus.modal_activate();
       $('#cosinnus_move_element_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_move_element_submit);
       $('#cosinnus_move_element_modal').modal('show');
   },
   
   cosinnus_move_element_submit: function() {
       if (!$('#cosinnus_move_element_obj_ids').val()) {
           return;
       };
       
       var element_ids = $('#cosinnus_move_element_obj_ids').val();
       var target_folder_id = $('#cosinnus_move_element_selected_folder').val();
       var current_folder_id = $('#cosinnus_move_element_current_folder_id').val()
       // don't do anything if we target the same folder the element is in
       if (target_folder_id == current_folder_id) {
           $('#cosinnus_move_element_modal').modal('hide');
           return;
       }
       var post_data = {
           'element_ids': element_ids.split(','),
           'target_folder_id': target_folder_id,
       };
       
       $.cosinnus.modal_deactivate();
       $.ajax({
            type:"POST",
            url: cosinnus_move_element_object_url,
            data: post_data,
            success: function(data){
                if (data && data.successful_ids) {
                    $('#cosinnus_move_element_modal').modal('hide');
                    $.each(data.successful_ids, function(key, element_id) {
                    	$('#cosinnus_list_element_' + element_id).fadeOut(800, function() {
                    		$(this).remove();
                    	});
                    });
                    // hide all checked elements
                    $('.item_checkbox_mark_all_false').click();
                } else if (data == 'ok_folder') {
                    console.log('NYI');
                }
            },
            error: function(data){
                $.cosinnus.display_report_error('#cosinnus_move_element_modal');
            }
       });
   },
   

   cosinnus_delete_element: function(obj_id_list, current_folder_id) {
      // called from js code that is rendered via a cosinnus_tags.py templatetag!
      $('#cosinnus_delete_element_obj_ids').val(obj_id_list.join(","));
      $('#delete_element_modal_error').hide();
      $.cosinnus.modal_activate();
      $('#cosinnus_delete_element_submit_btn').unbind().click($.cosinnus.Feedback.cosinnus_delete_element_submit);
      $('#cosinnus_delete_element_modal').modal('show');
  },
  
  cosinnus_delete_element_submit: function() {
      if (!$('#cosinnus_delete_element_obj_ids').val()) {
          return;
      };
      
      var element_ids = $('#cosinnus_delete_element_obj_ids').val();
      var post_data = {
          'element_ids': element_ids.split(',')
      };
      
      $.cosinnus.modal_deactivate();
      $.ajax({
           type:"POST",
           url: cosinnus_delete_element_object_url,
           data: post_data,
           success: function(data){
               if (data && data.successful_ids) {
                   $('#cosinnus_delete_element_modal').modal('hide');
                   $.each(data.successful_ids, function(key, element_id) {
                   	$('#cosinnus_list_element_' + element_id).fadeOut(800, function() {
                   		$(this).remove();
                   	});
                   });
                   // hide all checked elements
                   $('.item_checkbox_mark_all_false').click();
               } else if (data == 'ok_folder') {
                   console.log('NYI');
               }
           },
           error: function(data){
               $.cosinnus.display_report_error('#cosinnus_delete_element_modal');
           }
      });
  },
  
  cosinnus_register_likefollow: function() {
	  $('body').on('click', '.likefollow-button.action-do-likefollow', function(event){
		  var $this = $(this);
		  var ct = $this.data('ct');
		  var id = $this.data('id');
		  var type = $this.data('type');
		  var selected = $this.hasClass('selected');
		  selected = !selected;
		  var $button = $('.'+type+'-button[data-ct="'+ct+'"][data-id="'+id+'"]')
		  $button.toggleClass('selected', selected);
		  if (selected) {
			  $button.next('.likefollow-button-success-message').fadeIn(function(){ $(this).addClass('hide-on-click'); });
		  } else {
			  $button.next('.likefollow-button-success-message').hide().removeClass('hide-on-click');
		  }
		  
		  var params = {};
		  params[type] = selected ? '1' : '0';
		  $.cosinnus.Feedback.cosinnus_fire_likefollow(ct, id, params);
		  
	  });
	  
  },
  
  /**
   * Fires a like/follow. Expects a param dict likefollowParams
   * containing either/both of `like` `follow` with values '1' or '0'.
   */
  cosinnus_fire_likefollow: function(contentType, id, likefollowParams) {
	  var likefollowUrl = '/likefollow/';
	  var post_data = likefollowParams;
	  post_data['ct'] = contentType;
	  post_data['id'] = id;
	  
	  $.ajax({
          type:"POST",
          url: likefollowUrl,
          data: post_data,
          success: function(data){
          },
          error: function(data){
          }
     });
	  
  },
  
};

$(function() {
	$.cosinnus.Feedback.cosinnus_register_likefollow();
});
