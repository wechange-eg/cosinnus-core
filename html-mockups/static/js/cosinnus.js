$( "body" ).on( "click", ".fadedown", function() {
	$(this).find('> :not(:first-child)').stop().slideToggle();
});
