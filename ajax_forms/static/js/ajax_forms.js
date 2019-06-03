'use strict';

window.AjaxForms = {
		
	registerAjaxForms: function () {
		// register all 
		$('body').on('submit', 'form[data-target="ajax-form"]', window.AjaxForms.handleFormSubmit);
	},
	
	handleFormSubmit: function (event) { 
		event.preventDefault();  // prevent form from submitting
        var $form = $(event.target);
        
        $form.addClass('disabled');
        $form.find('input,textarea').attr('disabled', 'disabled');
    	
    	var finally_compat = function() {
			// self.hideLoadingPlaceholder();
    		
		};
    	window.AjaxForms.submitForm($form).then(function(data){
    		window.AjaxForms.handleData(data);
			finally_compat();
			alert('success')
		}).catch(function(message){
			//self.handleError(message);
			finally_compat();
			alert('fail')
			
			// re-enable form
	        $form.removeClass('disabled');
	        $form.find('input,textarea').removeAttr('disabled');
			
			console.log(message)
		});
    }, 
	
	submitForm: function ($form) {
		return new Promise(function(resolve, reject) {
			var data = $form.serialize();
			data['ajax-form-id'] = $form.attr('id');
			
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
	          	reject(textStatus);
	          },
			});
		});
	},
	
	handleData: function (data) {
		// we get passed {'result_html': str, 'new_form_html': str, 'ajax-form-id'} here, 
		// and place them in the given 
	},
}


$(function() {
	window.AjaxForms.registerAjaxForms();
});