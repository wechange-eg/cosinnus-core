// wrap in a self executing anonymous function that sets $ as jQuery namespace
(function( $ ){
	$.cosinnus = {
		fadedown : function() {
			// toggle editable elements like documents
			$('.fadedown .btn:first-child .fa-chevron-down').parent().click(function() {
				if ($(this).find('i').hasClass('fa-chevron-up')) {
					// already open
					$(this)
						.closest('.fadedown')
						.find('> :not(:first-child)')
						.stop()
						.slideUp();
					$(this).find('i').removeClass('fa-chevron-up').addClass('fa-chevron-down');
					$(this).closest('.fadedown').removeClass('open');
				} else {
					$(this)
						.closest('.fadedown')
						.find('> :not(:first-child)')
						.stop()
						.slideDown();
					$(this).find('i').removeClass('fa-chevron-down').addClass('fa-chevron-up');
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

			$('.attachments-selector').each(function() {
				function formatAttachment(hit) {
					var icon = {
						main: 'circle',
						calendar: 'calendar',
						files: 'folder',
						documents: 'file',
						todos: 'check-square',
						etherpad: 'pencil',
						messages: 'envelope',
						notes: 'comment',
						events: 'clock-o'
					};
					var html = '<span class="app-'+hit.app+'-attachment">'+
						'<i class="fa fa-'+icon[hit.app]+'"></i> '+
						hit.text+'</span>';
					return html;
				}

				$(this).select2({
					placeholder: 'Anhänge',
					escapeMarkup: function(m) { return m; }, // do not escape HTML
					formatSelection: formatAttachment, // do not alter selected elements
					formatResult: formatAttachment, // do not alter found options
					multiple: true,
					minimumInputLength: 3,
					data: [
						{id:0, app:'calendar', text:'Event: Hamsterwerfen'},
						{id:1, app:'documents', text:'Dokument: Sitzungsprotokoll'},
						{id:2, app:'todos', text:'Todo-Liste: Hätte gestern gemacht werden müssen'},
						{id:3, app:'etherpad', text:'Etherpad: Lorem!'},
						{id:4, app:'etherpad', text:'Etherpad: Mauern'},
						{id:5, app:'etherpad', text:'Etherpad: Sinnwerkstatt'},
						{id:6, app:'etherpad', text:'Etherpad: Thinkfarm'},
						{id:7, app:'etherpad', text:'Etherpad: Berlin'},
						{id:8, app:'etherpad', text:'Etherpad: Cosinnus'}
					]
				});
			});
		},

		fullcalendar : function() {
			var german = {
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
				}
			};

			$('.big-calendar').fullCalendar($.extend({
				header: {
					left: 'prev,next today',
					center: 'title',
					right: 'year,month,basicWeek,week' // basicDay
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
			}, german));

			$('.small-calendar').fullCalendar($.extend({
				header: {
					left: 'prev',
					center: 'title',
					right: 'next'
				},
				dayClick: function(date, allDay, jsEvent, view) {
					$(this).trigger('fullCalendarDayClick',[date,jsEvent]);
				},
				viewRender: function(date, cell) {
					// A day has to be rendered because of redraw or something
					$(cell).closest('.small-calendar').trigger('fullCalendarViewRender',[cell]);
				}

			}, german));

		},

		calendarCreateDoodle : function() {
			function selectDays() {
				$('#calendar-doodle-days-selector-list table tr').sortElements(function(a, b){
					return $(a).attr('data-date') > $(b).attr('data-date') ? 1 : -1;
				});

				// mark the days that are picked in the calendar
				$('#calendar-doodle-days-selector-list table tr').each(function() {
					var dateDataAttr = $(this).attr('data-date');
					$('#calendar-doodle-days-selector .small-calendar '+
						'td[data-date='+dateDataAttr+']:not(.fc-other-month)')
						.addClass('selected');
				});

				// when table empty hide even the headline
				if($('#calendar-doodle-days-selector-list table tbody tr').length==1) {
					$('#calendar-doodle-days-selector-list table thead tr').hide();
				} else {
					$('#calendar-doodle-days-selector-list table thead tr').show();
				}
			}
			// instant initialize
			selectDays();

			$("#calendar-doodle-days-selector .small-calendar")
				.on("fullCalendarDayClick", function(event, date, jsEvent) {
					var dayElement = jsEvent.currentTarget;
					if ($(dayElement).hasClass('fc-other-month')) return;

					var dateDataAttr = date.getFullYear() + "-"
						+ ((date.getMonth()+1).toString().length === 2
							? (date.getMonth()+1)
							: "0" + (date.getMonth()+1)) + "-"
						+ (date.getDate().toString().length === 2
							? date.getDate()
							: "0" + date.getDate());

					// unselect all and re-select later
					$(dayElement).parent().parent().find('td').removeClass('selected');

					if ($('#calendar-doodle-days-selector-list table tr[data-date='+dateDataAttr+']').length===0) {
						// add to list (select) now

						$('#calendar-doodle-days-selector-list table tr')
							.last()
							.clone()
							.show()
							.attr('data-date',dateDataAttr)
							.insertBefore($('#calendar-doodle-days-selector-list table tr').last())
							.children(":first")
							.click(function() {
								$(this).parent().remove();
								$("#calendar-doodle-days-selector .small-calendar")
									.fullCalendar('render');
							})
							.next()
							.text(dateDataAttr)
							.next()
							.children()
							.val('')
							.parent()
							.next()
							.children()
							.val('');

					} else {
						// remove from list now
						$('#calendar-doodle-days-selector-list table tr[data-date='+dateDataAttr+']').remove();
					}

					selectDays();
				})
				.on("fullCalendarViewRender", function(event, cell) {
					selectDays();
				});

			$('#createDoodleButton').click(function() {
				// validate and fire
				if ($('#calendar-doodle-days-selector-list table tbody tr').length==1) {
					// no dates
					$('#createDoodleWarningModal').modal('show');
					return;
				}

				if ($('#createDoodleTitleInput').val()=="") {
					// no title
					$('#createDoodleWarningModal').modal('show');
					return;
				}

				// collect data
				doodleData = {
					title: $('#createDoodleTitleInput').val(),
					dates: []
				};
				$('#calendar-doodle-days-selector-list table tbody tr').each(function() {
					doodleData.dates.push({
						date: $(this).attr('data-date'),
						time1: $(this).find('input').first().val(),
						time2: $(this).find('input').last().val()
					});
				});
				// remove last hidden line
				doodleData.dates.pop();

				// drop the entered data to console
				console.log(doodleData);
			});
		},


		calendarDoodleVote : function() {
			// Vote an option 
			$(
				'.doodle-vote-table .doodle-vote-inputarea .doodle-vote-yes a, '+
				'.doodle-vote-table .doodle-vote-inputarea .doodle-vote-maybe a, '+
				'.doodle-vote-table .doodle-vote-inputarea .doodle-vote-no a'
			).click(function(event) {
				event.preventDefault();

				// remove old selection
				$(this).parent().removeClass('doodle-vote-yes');
				$(this).parent().removeClass('doodle-vote-maybe');
				$(this).parent().removeClass('doodle-vote-no');

				// set new selection
				$(this).parent().addClass('doodle-vote-'+$(this).attr('data-doodle-option'));

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

		checkBox : function() {
			$('body .fa-square-o, body .fa-check-square-o').parent().click(function() {
				if ($(this).find('i').hasClass('fa-check-square-o')) {
					// already checked
					$(this).find('i').removeClass('fa-check-square-o').addClass('fa-square-o');
				} else {
					$(this).find('i').removeClass('fa-square-o').addClass('fa-check-square-o');
				}
			});
		},


		todosSelect : function() {
			$('body').on('click','.fa-star-o',function() {
				$(this).removeClass('fa-star-o');
				$(this).addClass('fa-star');
			});
			$('body').on('click','.fa-star',function() {
				$(this).removeClass('fa-star');
				$(this).addClass(' fa-star-half-o');
			});
			$('body').on('click','.fa-star-half-o',function() {
				$(this).removeClass(' fa-star-half-o');
				$(this).addClass('fa-star-o');
			});

		},

		datePicker : function() {
			$('#datePickerModal').on('shown.bs.modal', function() {
				// read date that is already picked
				// "#newTaskDate"
				var dateElementSelector = $(this).find('.small-calendar').attr('data-dateelement');
				// "2014-04-28"
				var date = $(dateElementSelector).attr('data-date');
				$('#datePickerModal .modal-body .small-calendar')
					.fullCalendar('render')
					.find('td[data-date='+date+']')
					.addClass('selected');
			});

			$('#datePickerModal .small-calendar')
				.on("fullCalendarDayClick", function(event, date, jsEvent) {
					var dayElement = jsEvent.currentTarget;
					if ($(dayElement).hasClass('fc-other-month')) return;

					var dateDataAttr = date.getFullYear() + "-"
						+ ((date.getMonth()+1).toString().length === 2
							? (date.getMonth()+1)
							: "0" + (date.getMonth()+1)) + "-"
						+ (date.getDate().toString().length === 2
							? date.getDate()
							: "0" + date.getDate());

					// unselect all and re-select later
					$(dayElement).parent().parent().find('td').removeClass('selected');
					$(dayElement).addClass('selected');


					// When date picked, update date in form
					$($(this).attr('data-dateelement'))
						.attr('data-date', dateDataAttr)
						.trigger('renderAnnotationDataDate');
				});
		},



		annotationDataDate : function() {
			// when .annotation elements have a data-date attribute, render date.

			$('.annotation').on("renderAnnotationDataDate", function() {
				if (!$(this).attr('data-date')) return;
				var data_date = $(this).attr('data-date');

				if (data_date == 'today') {
					// if attribute is 'today', fill with current date
					// if it is not 'today', it is 2014-04-28.
					data_date = new Date();
					data_date = data_date.getFullYear() + "-"
						+ ((data_date.getMonth()+1).toString().length === 2
							? (data_date.getMonth()+1)
							: "0" + (data_date.getMonth()+1)) + "-"
						+ (data_date.getDate().toString().length === 2
							? data_date.getDate()
							: "0" + data_date.getDate());
					$(this).attr('data-date',data_date);
				}

				data_date = moment(data_date);

				moment.lang('de', {
					calendar : {
						lastDay : '[gestern]',
						sameDay : '[heute]',
						nextDay : '[morgen]',
						lastWeek : '[letzten] dddd',
						nextWeek : '[nächsten] dddd',
						sameElse : 'L'
					}
				});
				moment.lang('de');

				var cal = moment(data_date).calendar();
				$(this).text(cal);
			});

			$('.annotation').each(function() {
				$(this).trigger('renderAnnotationDataDate');
			});
		},

		todoCreateTask : function() {
			$('#createTodoButton').hide();
			$('#newTaskDescription').val('');
			$('#newTaskDescription').on('propertychange keyup input paste change', function() {
				if ($(this).val()) {
					$('#createTodoButton').slideDown();
				} else {
					$('#createTodoButton').slideUp();
				}
			});

			$('#createTodoButton').click(function() {
				var data = {
					description: $('#newTaskDescription').val(),
					date: $('#newTaskDate').attr('data-date')
				};
				console.log(data);
			});
		},

		etherpadEditMeta : function() {
			$('#etherpadSaveMetaButton').hide();
			$('.input-area input, .input-area select, #etherpadTitle')
				.on('propertychange keyup input paste change', function() {
				$('#etherpadSaveMetaButton').slideDown();
			});
		},

		buttonHref : function() {
			// allow href attribute for buttons
			$('button').each(function() {
				if ($(this).attr('href')) {
					$(this).click(function() {
						window.location.href = $(this).attr('href');
					});
				}
			});
		},

		doodleList : function() {
			$('#newDoodleButton').hide();
			$('#newDoodleTitle').val('');
			$('#newDoodleTitle').on('propertychange keyup input paste change', function() {
				if ($(this).val()) {
					$('#newDoodleButton')
						.prev()
						.removeClass('large-space')
						.next()
						.show();
				} else {
					$('#newDoodleButton')
						.prev()
						.addClass('large-space')
						.next()
						.hide();
				}
			});
		},

		fileList : function() {
			$('#fileToUpload').val('');
			$('#uploadFileButton').hide();
			$('#fileToUpload').on('change', function() {
				if ($(this).val()) {
					$('#uploadFileButton')
						.prev()
						.removeClass('large-space')
						.next()
						.show();
				} else {
					$('#uploadFileButton')
						.prev()
						.addClass('large-space')
						.next()
						.hide();
				}
			});
		},

		messagesList : function() {
			$('.fa-square-o, .fa-check-square-o').parent().click(function() {
				// message selected or deselected
				if ($('.fa-check-square-o').length) {
					$('.messages-delete-button, .messages-archive-button').slideDown();
				} else {
					$('.messages-delete-button, .messages-archive-button').slideUp();
				}
			});

			if (!$('.fa-check-square-o').length) {
				$('.messages-delete-button, .messages-archive-button').hide();
			}
		},

		messagesWrite : function() {
			$('.app-message-text').on('propertychange keyup input paste change', function() {
				if ($(this).val()) {
					$('.app-message-send-button').slideDown();
				} else {
					$('.app-message-send-button').slideUp();
				}
			});
			if ($('.app-message-text').length && !$('.app-message-text').val()) {
				$('.app-message-send-button').hide();
			}
		}

	};
})( jQuery );



$(function() {
	$.cosinnus.checkBox();
	$.cosinnus.fadedown();
	$.cosinnus.selectors();
	$.cosinnus.fullcalendar();
	$.cosinnus.searchbar();
	$.cosinnus.todosSelect();
	$.cosinnus.datePicker();
	$.cosinnus.annotationDataDate();
	$.cosinnus.todoCreateTask();
	$.cosinnus.etherpadEditMeta();
	$.cosinnus.buttonHref();
	$.cosinnus.calendarCreateDoodle();
	$.cosinnus.doodleList();
	$.cosinnus.calendarDoodleVote();
	$.cosinnus.fileList();
	$.cosinnus.messagesList();
	$.cosinnus.messagesWrite();
});
