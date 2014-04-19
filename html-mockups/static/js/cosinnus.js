// wrap in a self executing anonymous function that sets $ as jQuery namespace
(function( $ ){
	$.cosinnus = {
		fadedown : function() {
			// toggle editable elements like documents
			$('.fadedown .btn:first-child .media-body, '+
				'.fadedown .btn:first-child .fa-chevron-down').click(function() {
				if ($(this).closest('.fadedown').hasClass('open')) {
					$(this)
						.closest('.fadedown')
						.find('> :not(:first-child)')
						.stop()
						.slideUp();
					$(this).closest('.fadedown').removeClass('open');
				} else {
					$(this)
						.closest('.fadedown')
						.find('> :not(:first-child)')
						.stop()
						.slideDown();
					$(this).closest('.fadedown').addClass('open');
				}
			});
			// hide fadedown boxes unless .open class explicit set
			$('.fadedown').not('.open').find('> :not(:first-child)').hide();
		},


		selectors : function() {
			$('.user-selector').select2();
			$('.privacy-selector').select2({ minimumResultsForSearch: -1});
			$('.privacy-selector').change(function(){
				$(this).prev().prev().attr('class',
					$(this).val() == 'private' ? 'fa fa-fw fa-lock' : 'fa fa-fw fa-globe'
				);
			}).trigger('change');

			$('.bolt-selector').select2({ minimumResultsForSearch: -1});
			$('.bolt-selector').change(function(){
				$(this).prev().prev().attr('class',
					$(this).val() == 'flash' ? 'fa fa-fw fa-bolt' : 'fa fa-fw fa-sun-o'
				);
			}).trigger('change');

			$('.light-selector').select2({ minimumResultsForSearch: -1});
			$('.light-selector').change(function(){
				$(this).prev().prev().attr('class',
					$(this).val() == 'light' ? 'fa fa-fw fa-lightbulb-o' : 'fa fa-fw fa-moon-o'
				);
			}).trigger('change');

			$('.tags-selector, .location-selector').each(function() {
				$(this).select2({
					tags: $(this).attr('data-tags').split(',')
				});
			});
		},

		fullcalendar : function() {
			$('#calendar').fullCalendar({
				header: {
					left: 'prev,next today',
					center: 'title',
					right: 'year,month,basicWeek,week' // basicDay
				},
				editable: true,
				firstDay: 1, // Monday
				buttonText: {
					today: "Heute",
					month: "Monat",
					week: "Woche",
					day: "Tag"
				},
				monthNames: ['Januar','Februar','März','April',
					'Mai','Juni','Juli','August',
					'September','Oktober','November','Dezember'],
				monthNamesShort: ['Jan','Feb','Mär','Apr','Mai',
					'Jun','Jul','Aug','Sept','Okt','Nov','Dez'],
				dayNames: ['Sonntag','Montag','Dienstag',
					'Mittwoch','Donnerstag','Freitag','Samstag'],
				dayNamesShort: ['So','Mo','Di','Mi','Do','Fr','Sa'],
				titleFormat: {
					month: 'MMMM yyyy',
					week: "d.[ MMMM][ yyyy]{ - d. MMMM yyyy}",
					day: 'dddd d. MMMM yyyy'
				},
				columnFormat: {
					month: 'ddd',
					week: 'ddd d',
					day: ''
				},
				axisFormat: 'H:mm', 
				timeFormat: {
					'': 'H:mm', 
					agenda: 'H:mm{ - H:mm}'
				},

				events: [
					{
						title: 'All Day Event',
						start: new Date(2014, 3, 23)
					},
					{
						title: 'Long Event',
						start: new Date(2014, 4, 4),
						end: new Date(2014, 3, 30)
					},
					{
						id: 999,
						title: 'Repeating Event',
						start: new Date(2014, 3, 7, 16, 0),
						allDay: false
					}
				]
			});
		},

		// searchbar in top fixed navigation
		searchbar : function() {
			$('#searchbar').hover( function() {
				$(this).addClass('expanded');
				$(this).addClass('mouseover');
			}, function() {
				if (!$(this).find('input').is(':focus'))
					$(this).removeClass('expanded');
				$(this).removeClass('mouseover');
			});
			$('#searchbar').find('input').blur( function() {
				if(!$(this).parent().hasClass('mouseover'))
					$(this).parent().removeClass('expanded');
			});
			$('#searchbar').click( function() {
				$(this).addClass('expanded');
			});

		},

		todosSelect : function() {
			$('body').on('click','.fa-square-o',function() {
				$(this).removeClass('fa-square-o');
				$(this).addClass('fa-check-square-o');
			});
			$('body').on('click','.fa-check-square-o',function() {
				$(this).removeClass('fa-check-square-o');
				$(this).addClass('fa-square-o');
			});

			$('body').on('click','.fa-star-o',function() {
				$(this).removeClass('fa-star-o');
				$(this).addClass('fa-star');
			});
			$('body').on('click','.fa-star',function() {
				$(this).removeClass('fa-star');
				$(this).addClass('fa-star-o');
			});
		}
	};
})( jQuery );



$(function() {
	$.cosinnus.fadedown();
	$.cosinnus.selectors();
	$.cosinnus.fullcalendar();
	$.cosinnus.searchbar();
	$.cosinnus.todosSelect();
});
