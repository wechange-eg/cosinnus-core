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
        $form.find('input,textarea,button').attr('disabled', 'disabled');
    	
    	window.AjaxForms.submitForm($form, data).then(function(data){
    		window.AjaxForms.handleData(data);
		}).catch(function(responseJSON){
			if (responseJSON && 'form_errors' in responseJSON) {
			    if ($form.attr('data-ajax-form-error-message')) {
                    alert($form.attr('data-ajax-form-error-message'));
                } else if ('__all__' in responseJSON['form_errors']) {
                    alert(responseJSON['form_errors']['__all__']);
			    } else {
    				alert('Please fill out all required fields!');
			    }
			} else {
				alert('An error occured while posting the comment. Please reload the page and try again!');
			}
			
			// re-enable form
	        $form.removeClass('disabled');
	        $form.find('input,textarea,button').removeAttr('disabled');
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
	
	/**
	 * possible params: {
	 * 		'result_html': str,
	 * 		'new_form_html': str,
	 * 		'ajax_form_id': str,
	 * 	} 
	 */
	handleData: function (data) {
		// replace the sent form with a new one
		if ('new_form_html' in data && 'ajax_form_id' in data) {
			$('form#' + data['ajax_form_id']).replaceWith(data['new_form_html']);
		}
		// place the result html at the anchor 
		if ('result_html' in data && 'ajax_form_id' in data) {
			$(data['result_html'])
				.hide()
				.insertAfter('[data-target="ajax-form-result-anchor"][data-ajax-form-id="' + data['ajax_form_id'] + '"]')
				.fadeIn();
			$(data['result_html'])
				.hide()
				.insertBefore('[data-target="ajax-form-result-anchor-before"][data-ajax-form-id="' + data['ajax_form_id'] + '"]')
				.fadeIn();
		}
		if ('ajax_form_id' in data) {
			// delete elements marked to delete 
            $('[data-target="ajax-form-delete-element"][data-ajax-form-id="' + data['ajax_form_id'] + '"]')
                .fadeOut(200, function() {
                    $(this).remove();
        			// show elements marked to show
        			$('[data-target="ajax-form-show-element"][data-ajax-form-id="' + data['ajax_form_id'] + '"]').show();
                });
			// execute oncomplete code
			var oncomplete = $('[data-target="ajax-form"][id="' + data['ajax_form_id'] + '"]').attr('data-ajax-oncomplete');
			if (oncomplete) {
				eval(oncomplete);
			}
		
		}
	},
}


$(function() {
	window.AjaxForms.registerAjaxForms();
});
