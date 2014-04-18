$(function() {


	// toggle editable elements like documents
	$('.fadedown .btn:first-child .media-body, '+
	  '.fadedown .btn:first-child .fa-chevron-down').click(function() {
		$(this).closest('.fadedown').find('> :not(:first-child)').stop().slideToggle();
	});



	$('.user-selector').select2();
	$('.privacy-selector').select2({ minimumResultsForSearch: -1});
	$('.privacy-selector').change(function(){
		$(this).prev().prev().attr('class',
			$(this).val() == 'private' ? 'fa fa-fw fa-lock' : 'fa fa-fw fa-globe'
		);
	});

	$('.tags-selector, .location-selector').each(function() {
		$(this).select2({
			tags: $(this).attr('data-tags').split(',')
		});
	});

});
