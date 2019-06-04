'use strict';

window.AjaxForms = {
		
	registerAjaxForms: function () {
		// register all 
		$('body').on('submit', 'form[data-target="ajax-form"]', window.AjaxForms.handleFormSubmit);
	},
	
	handleFormSubmit: function (event) { 
		event.preventDefault();  // prevent form from submitting
        var $form = $(this);
        
        // serialize and disable form (serialization must be done before disabling)
		var data = $form.serializeArray();
		data.push({'name': 'ajax_form_id', 'value': $form.attr('id')});
        $form.addClass('disabled');
        $form.find('input,textarea').attr('disabled', 'disabled');
    	
    	window.AjaxForms.submitForm($form, data).then(function(data){
    		window.AjaxForms.handleData(data);
		}).catch(function(responseJSON){
			if (responseJSON && 'form_errors' in responseJSON) {
				alert('Please fill out all required fields!')
			} else {
				alert('An error occured while posting the comment. Please reload the page and try again!');
			}
			
			// re-enable form
	        $form.removeClass('disabled');
	        $form.find('input,textarea').removeAttr('disabled');
		});
    }, 
	
	submitForm: function ($form, data) {
		return new Promise(function(resolve, reject) {
			$.ajax({
			  url: $form.attr("action"),
			  type: 'POST',
			  data: data, 
			  success: function (response, textStatus, xhr) {
	              if (xhr.status == 200) {
	              	resolve(response);
	              } else {
	              	reject(xhr.statusText);
	              }
	          },
	          error: function (xhr, textStatus) {
	          	  reject(xhr.responseJSON);
	          },
			});
		});
	},
	
	handleData: function (data) {
		// we get passed {'result_html': str, 'new_form_html': str, 'ajax_form_id'} here, 
		// we replace the sent form with a new one, and place the result html at the anchor 
		$('form#' + data['ajax_form_id']).replaceWith(data['new_form_html']);
		$(data['result_html'])
			.hide()
			.insertBefore('[data-target="ajax-form-result-anchor"][data-ajax-form-id="' + data['ajax_form_id'] + '"]')
			.fadeIn();
	},
}


$(function() {
	window.AjaxForms.registerAjaxForms();
});
