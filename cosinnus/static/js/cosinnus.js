// send CSRF-tokens on jQuery POSTs
(function ($, window, document) {
    window.Cosinnus = {
        init: function(base_url) {
            this.base_url = cosinnus_base_url;
            $.ajaxSetup({
                // From the Django documentation:
                // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
                crossDomain: false,
                beforeSend: function(xhr, settings) {
                    if (!Cosinnus.csrfSafeMethod(settings.type)) {
                        xhr.setRequestHeader("X-CSRFToken", Cosinnus.getCookie('csrftoken'));
                    }
                    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                }
            });
            return this;
        },
        getCookie: function(name) {
            // From the Django documentation:
            // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },
        csrfSafeMethod: function(method) {
            // From the Django documentation:
            // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }
    };
    $.fn.cosinnus = Cosinnus.init(cosinnus_base_url);
}(jQuery, this, this.document));


// wrap in a self executing anonymous function that sets $ as jQuery namespace
(function( $ ){
    $.cosinnus = {
        fadedown : function(target) {
            // DIV.fadedown is a wrapper that contains a button with toggle element
            // and other elements that will be hidden or shown depending on the state.
            
            if (typeof target === "undefined") {
                target = 'body';
            }
            $(target).on('click','.fadedown .btn:first-child .fadedown-clickarea, .fadedown .btn:first-child.fadedown-clickarea',function(e) {
                if (!$(this).closest('.fadedown').hasClass('open')) {
                    // closed
                    $(this)
                        .closest('.fadedown')
                        .addClass('open')
                        .find('> :not(:first-child)')
                        .stop()
                        .slideDown();
                    $(this).find('i.fa-chevron-down')
                        .removeClass('fa-chevron-down')
                        .addClass('fa-chevron-up');
                } else if ($(this).find('i').hasClass('fa-chevron-up')) {
                    // already open and can be closed
                    $(this)
                        .closest('.fadedown')
                        .removeClass('open')
                        .find('> :not(:first-child)')
                        .stop()
                        .slideUp();
                    $(this).find('i.fa-chevron-up')
                        .removeClass('fa-chevron-up')
                        .addClass('fa-chevron-down');
                }
                e.stopPropagation();
                return false;
            });
            // hide fadedown boxes unless .open class explicit set
            $('.fadedown').not('.open').find('> :not(:first-child)').hide();
        },
        
        closeFadedown : function(target) {
            target.removeClass('open');
            $.cosinnus.fadedown(target.parent());
        },

        editThisClickarea : function() {
            $('.edit-this-clickarea').click(function(event) {
                event.preventDefault();
                var button = $(this).closest('.btn-emphasized, .btn-extra-emphasized')
                if (button.hasClass('btn-extra-emphasized')) {
                    button.attr('_button_class', 'btn-extra-emphasized');
                } else {
                    button.attr('_button_class', 'btn-emphasized');
                }
                button.removeClass('btn-emphasized')
                    .removeClass('btn-extra-emphasized')
                    .addClass('btn-default');
                var media_body = $(this).next();
                media_body.addClass('media-body-form-control')
                    .attr('_href', media_body.attr('href')).removeAttr('href').find('span').toggle();
                media_body.find('input').show();
                $(this).hide();
            });
        },
        
        restoreThisClickarea : function(target_selector) {
            var button = $(target_selector).closest('.btn-default');
            button.removeClass('btn-default')
                .addClass(button.attr('_button_class'))
                .removeAttr('_button_class');
            var media_body = $(target_selector).next();
            media_body.removeClass('media-body-form-control')
                      .attr('href', media_body.attr('_href'))
                      .removeAttr('_href')
                      .find('span').text(media_body.find('input').val()).toggle();
            media_body.find('input').hide();
            $(target_selector).show();
            $.cosinnus.closeFadedown($(target_selector).closest('.fadedown'));
        },

        selectors : function() {
            // Various inputs that use jQuery select2 plugin
            // http://ivaynberg.github.io/select2/

            $('.input-area-privacy-selector a').click( function() {
                var translation = {
                    de: {
                        lock: 'Privat',
                        globe: 'Öffentlich'
                    },
                    en: {
                        lock: 'Private',
                        globe: 'Global'
                    }
                };

                if ($(this).find('i').hasClass('fa-globe')) {
                    // switch to private
                    $(this).find('i').removeClass('fa-globe').addClass('fa-lock');
                    $(this).find('span').html(translation[$.cosinnus.lang].lock);
                    $(this).find('input').val('private');
                } else {
                    // switch to public
                    $(this).find('i').addClass('fa-globe').removeClass('fa-lock');
                    $(this).find('span').html(translation[$.cosinnus.lang].globe);
                    $(this).find('input').val('global');
                }
            }).trigger('click');

            $('.tags-selector, .location-selector').each(function() {
                $(this).select2({
                    width: 'off',
                    tags: $(this).attr('data-tags').split(',')
                });
            });

            $('.user-selector').each(function() {
                $(this).select2();
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

            // Small links that expand an input or something somewhere else
            $('a').each(function () {
                if ($(this).attr('data-show-id')) {
                    $(this).click(function() {
                        $('#'+$(this).attr('data-show-id')).slideDown();
                        $(this).parent().remove();
                    });
                }
            });
        },

        fullcalendar : function() {
            // There are two kinds of calendar in cosinnus: big and small.
            // The .big-calendar fills the content and shows events.
            // Users can add events here.
            // The .small-calendar is for tooltips or small static date chooser.
            // both are based on jQuery fullcalendar. http://arshaw.com/fullcalendar/

            if ($('.big-calendar').length && typeof(cosinnus_calendarEvents) !== "undefined") {
                $('.big-calendar').empty();
                $('.big-calendar').fullCalendar($.extend({
                    header: {
                        left: 'prev,next today',
                        center: 'title',
                        right: 'year,month,basicWeek,week' // basicDay
                    },
    
                    // cosinnus_calendarEvents is a global var containing the events
                    // set by the backend somewhere in the BODY.
                    events: cosinnus_calendarEvents,
                    select: function(startDate, endDate, allDay, jsEvent, view) {
                        $(this.element)
                            .closest('.big-calendar')
                            .trigger('fullCalendarSelect',[startDate, endDate, allDay, jsEvent, view]);
                    },
                    eventClick: function(event, jsEvent, view) {
                        $(this)
                            .closest('.big-calendar')
                            .trigger('fullCalendarEventClick',[event, jsEvent, view]);
                    },
                    selectable: true,
                    selectHelper: true
                }, $.cosinnus.fullcalendar_format));
            }
            
            if ($('.small-calendar').length) {
                $('.small-calendar').empty();
                $('.small-calendar').fullCalendar($.extend({
                    header: {
                        left: 'prev',
                        center: 'title',
                        right: 'next'
                    },
                    events: (typeof cosinnus_calendarWidgetEvents !== "undefined" ? cosinnus_calendarWidgetEvents : []),
                    dayClick: function(date, allDay, jsEvent, view) {
                        $(this).trigger('fullCalendarDayClick',[date,jsEvent]);
                    },
                    viewRender: function(date, cell) {
                        // A day has to be rendered because of redraw or something
                        $(cell).closest('.small-calendar').trigger('fullCalendarViewRender',[cell]);
                    }
    
                }, $.cosinnus.fullcalendar_format));
            }
        },


        calendarBig : function() {
            // The big calendar fills the whole content area and contains the user's events.

            $('.big-calendar')
                .on("fullCalendarSelect", function(event, startDate, endDate, allDay, jsEvent, view) {
                    // Dates have been selected. Now the user might want to add an event.
                    var startDateDataAttr = startDate.getFullYear() + "-"
                        + ((startDate.getMonth()+1).toString().length === 2
                            ? (startDate.getMonth()+1)
                            : "0" + (startDate.getMonth()+1)) + "-"
                        + (startDate.getDate().toString().length === 2
                            ? startDate.getDate()
                            : "0" + startDate.getDate());

                    var endDateDataAttr = endDate.getFullYear() + "-"
                        + ((endDate.getMonth()+1).toString().length === 2
                            ? (endDate.getMonth()+1)
                            : "0" + (endDate.getMonth()+1)) + "-"
                        + (endDate.getDate().toString().length === 2
                            ? endDate.getDate()
                            : "0" + endDate.getDate());

                    // allDay is always true as times can not be selected.


                    $('#calendarConfirmStartDate').val(startDateDataAttr);
                    $('#calendarConfirmEndDate').val(endDateDataAttr);

                    if (startDateDataAttr == endDateDataAttr) {
                        // Event has one day
                        $('#calendarConfirmEventOneday').show();
                        $('#calendarConfirmEventMultiday').hide();

                        moment.lang(moment.lang(),$.cosinnus.momentShort);
                        eventDate = moment(startDateDataAttr);
                        var eventDate = moment(eventDate).calendar();
                        $('#calendarConfirmEventDate').text(eventDate);

                        $('#confirmEventModal').modal('show');
                    } else {
                        // Event has multiple days
                        $('#calendarConfirmEventOneday').hide();
                        $('#calendarConfirmEventMultiday').show();

                        // There is no time, so use momentShort.
                        moment.lang(moment.lang(),$.cosinnus.momentShort);
                        startDate = moment(startDateDataAttr);
                        var startDate = moment(startDate).calendar();
                        $('#calendarConfirmEventStart').text(startDate);

                        endDate = moment(endDateDataAttr);
                        var endDate = moment(endDate).calendar();
                        $('#calendarConfirmEventEnd').text(endDate);

                        $('#confirmEventModal').modal('show');
                    }
            });

        },


        // When creating or editing an event the user has to select date and time.
        // Clicking one date input shows all calendars on the whole page.
        calendarDayTimeChooser : function() {
            // Hide calendar when clicking outside
            $(document).click(function(event) {
                var thisdaytimechooser = $(event.target).closest('.calendar-date-time-chooser');
                if(thisdaytimechooser.length) {
                    // Don't hide any chooser
                } else {
                    // hide all
                    $('.calendar-date-time-chooser .small-calendar').slideUp();
                }
            });

            $('.calendar-date-time-chooser input.calendar-date-time-chooser-date')
                .click(function() {
                $('.calendar-date-time-chooser .small-calendar').slideDown();
            });

            $('.calendar-date-time-chooser i').click(function() {
                $('.calendar-date-time-chooser .small-calendar').slideDown();
            });

            $('.calendar-date-time-chooser .small-calendar').hide();


            // on every re-drawing of the calendar select the choosen date
            $('.calendar-date-time-chooser .small-calendar')
                .on("fullCalendarViewRender", function(event, cell) {
                    // select choosen day

                    var date = $(this)
                        .closest('.calendar-date-time-chooser')
                        .find('.calendar-date-time-chooser-hiddendate')
                        .val();
                    // "2014-04-28"
                    if (date) $(this)
                        .find('td[data-date='+date+']')
                        .addClass('selected');
                })
                .trigger('fullCalendarViewRender')

                // when clicked on a day: use this!
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
                    $(this)
                        .closest('.calendar-date-time-chooser')
                        .find('.calendar-date-time-chooser-hiddendate')
                        .val(dateDataAttr);

                    // Update INPUT with human readable date
                    moment.lang(moment.lang(),$.cosinnus.momentShort);
                    var humanDateString = moment(dateDataAttr).calendar();
                        $(this)
                            .closest('.calendar-date-time-chooser')
                            .find('.calendar-date-time-chooser-date')
                            .val(humanDateString);
                });

            // Set INPUT with human readable date
            $('.calendar-date-time-chooser').each(function() {
                var dateDataAttr = $(this)
                    .find('.calendar-date-time-chooser-hiddendate')
                    .val();

                if (dateDataAttr) {
                    moment.lang(moment.lang(),$.cosinnus.momentShort);
                    var humanDateString = moment(dateDataAttr).calendar();
                        $(this)
                            .find('.calendar-date-time-chooser-date')
                            .val(humanDateString);
                }
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
                $(this).parent()
                    .addClass('doodle-vote-'+$(this).attr('data-doodle-option'))
                    .find('input')
                    .val(
                        $(this).attr('data-doodle-option') == 'yes' ? 2 :
                        $(this).attr('data-doodle-option') == 'no' ? 0 : 1
                    );
                // remove strong elements for all items
                $(this).parent().children().each(function() {
                    $(this).html($(this).text());
                });
                $(this).html('<strong>' + $(this).text() + '</strong>');
                
            });
        },


        // searchbar in top fixed navigation, expands on hover, contracts on hover-out on navbar
        searchbar : function() {
            $('#searchbar').hover( function() {
                $(this).addClass('expanded');
            }, function() {
                // nothing on leave
            });
            $('.navbar').hover( function() {
                // nothing on enter
            }, function() {
                if (!$('#searchbar').find('input').is(':focus'))
                    $('#searchbar').removeClass('expanded');
            });
            
            $('#searchbar').click( function() {
                $(this).addClass('expanded');
                $(this).find('input').click();
            });

        },

        checkBox : function() {
            // Parents of checkboxes like <i class="fa fa-square-o"></i> are always clickable.
            // If they contain a <input type="hidden" /> too, this will contain the value.

            $('body .fa-square-o, body .fa-check-square-o').parent().unbind("click").click(function(e) {
                if ($(this).attr('disabled')) {
                    return;
                }
                if ($(this).find('i').hasClass('fa-check-square-o')) {
                    // uncheck checked box and remove button highlight
                    var $input = $(this)
                        .find('i')
                        .removeClass('fa-check-square-o')
                        .addClass('fa-square-o')
                        .next(); // INPUT type="hidden"
                    if ($input.attr('type') == 'checkbox') {
                        $input.prop('checked', false);
                    } else {
                        $input.attr('value','false')
                    }
                    $input.trigger('change');
                    
                    $(this)
                    	.removeClass('checkbox-checked')
                        .parents('.btn-extra-emphasized')
                        .first()
                        .removeClass('btn-extra-emphasized')
                        .addClass('btn-emphasized');
                } else {
                    // check unchecked box and highlight button
                    $input = $(this)
                        .find('i')
                        .removeClass('fa-square-o')
                        .addClass('fa-check-square-o')
                        .next(); // INPUT type="hidden"
                    if ($input.attr('type') == 'checkbox') {
                        $input.prop('checked', true);
                    } else {
                        $input.attr('value','true');
                    }
                    $input.trigger('change');
                        
                    $(this)
                    	.addClass('checkbox-checked')
                        .parents('.btn-emphasized')
                        .first()
                        .removeClass('btn-emphasized')
                        .addClass('btn-extra-emphasized');
                }
                e.preventDefault();
                return false;
            });

            // set INPUT type="hidden" value on startup
            $('body .fa-square-o, body .fa-check-square-o').each(function() {
                if ($(this).hasClass('fa-check-square-o')) {
                    // checked
                    $input = $(this).next(); // INPUT type="hidden"
                    if ($input.attr('type') == 'checkbox') {
                        $input.prop('checked', true);
                    } else {
                        $input.attr('value','true');
                    }
                } else {
                    $input = $(this).next(); // INPUT type="hidden"
                    if ($input.attr('type') == 'checkbox') {
                        $input.prop('checked', false);
                    } else {
                        $input.attr('value','false');
                    }
                }
            });
        },
        
        /** Click triggers for labels of onoffSwitches */
        onoffSwitch: function() {
        	$('body').on('click', '.onoffswitch-frame', function(event){
        		$(event.target).parent().find('input[type="checkbox"]').click();
        	});
        },
        
        /** Click triggers for the .hide-on-click class and
         * 	other elements that disappear when an element is clicked. */
        hideOnClick: function() {
        	$('body').on('click', function(event){
        		var $target = $(event.target);
        		
        		// hide all .hide-on-click
        		$('.hide-on-click:visible').hide();
        		// hide all .hide-on-click-outside if clicked outside them
        		$('.hide-on-click-outside').each(function(){
        			var item = this;
        			var $item = $(item);
        			if (!item.contains(event.target)) {
        				$item.hide();
        			}
        		});
        		// hide nav-flyouts that are expanded if clicked outside them, except for their menu button
        		$('.nav-flyout').each(function(){
        			var item = this;
        			var $item = $(item);
        			if ((!item.contains(event.target) || $target.hasClass('nav-flyout-backdrop')) 
        					&& $item.hasClass('in') && '#'+item.id != $target.parents('a').attr('data-target')
        					&& '#'+item.id != $target.attr('data-target')) {
        				$item.collapse('hide');
        			}
        		});
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
            $('#datePickerModal').on('shown.bs.modal', function(e) {
                // Find the element that has been clicked
                // and look up the element that stores the date there.
                if ($(e.relatedTarget).attr('data-dateelement')) {
                    var dateElement = $($(e.relatedTarget).attr('data-dateelement'));
                } else {
                    var dateElement = $(e.relatedTarget);
                }
                // $('#newTaskDate')

                // read date that is already picked
                 $(this).find('.small-calendar').data('data-dateelement', dateElement);
                // "2014-04-28"
                var date = dateElement.attr('data-date');
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

                    // When submit button pressed, update currently selected date in form
                    var target_element = $(this).data('data-dateelement');
                    $('#datePickerModal_submit').unbind('click');
                    $('#datePickerModal_submit').click(function() {
                        target_element
                            .attr('data-date', dateDataAttr)
                            .trigger('renderMomentDataDate')
                            .trigger('change');
                        if (target_element.next().is('input')) {
                            target_element.next().val(dateDataAttr);
                        }
                    });
                    
                });
        },



        renderMomentDataDate : function() {
            
            // when .moment-data-date elements have a data-date attribute, render date.
            $('.moment-data-date').on("renderMomentDataDate", function() {
                // set current language for moment formatting
                var moment_lang = typeof cosinnus_current_language === "undefined" ? "" : cosinnus_current_language; 
                moment.lang(moment_lang || "en");
                
                if (!$(this).attr('data-date')) return;
                // Format: 2014-05-05
                // Format: 2013-02-08 09:30:26
                var data_date = $(this).attr('data-date');
                // Does the format include a specific time?
                var with_time = (data_date.length > 10);

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
                
                /** No moment custom time format for now **/
                /*
                if (with_time) {
                    moment.lang(moment.lang());//,$.cosinnus.momentFull);
                } else {
                    moment.lang(moment.lang());//,$.cosinnus.momentShort);
                } 
                */
                
                var mom = moment(data_date);
                var diff_days = mom.diff(moment(), 'days');
                
                if ($(this).attr('data-date-style') == 'short') {
                    // render the date without time
                    moment.lang(moment.lang(),$.cosinnus.momentShort);
                    $(this).text(mom.calendar());
                } else {
                    if ((diff_days > -1 && diff_days < 1) || diff_days < -4 ) {
                        // render the date difference for today, tomorrow, and longer than 4 days ago
                        $(this).text(mom.fromNow());
                    } else {
                        // render "letzten Montag um 12:00 Uhr" for the last 3 days
                        $(this).text(mom.calendar());
                    }
                }
                // add the absolute date as tooltip
                if ($(this).attr('data-date-notooltip') != 'true') {
                    $(this).attr('title', mom.format('LLLL'));
                }
            });

            $('.moment-data-date').each(function() {
                $(this).trigger('renderMomentDataDate');
            });
        },


        inputDynamicSendButton : function() {
            // User enters something in a input or textarea or span.contenteditable,
            // this activates the next submit button

            $('.next-button-is-for-sending').each(function() {
                    // save the original margin bottom
                    $(this).closest('.btn, .sendbutton')
                        .data('margin-bottom',parseInt($(this).closest('.btn, .sendbutton').css('margin-bottom')))
                        .after('<div></div>'); // Fixes Chrome floating bug that hides send button
                })
                    .on('propertychange input paste change', function() {
                    var sendbutton = $(this).closest('.btn, .sendbutton').nextAll('.btn, .sendbutton').first();
                    if ($(this).val()) {
                        sendbutton.show();
                        $(this).closest('.btn, .sendbutton').css('margin-bottom',0);
                    } else {
                        sendbutton.hide();
                        $(this)
                            .closest('.btn, .sendbutton')
                            .css('margin-bottom',$(this).closest('.btn, .sendbutton').data('margin-bottom'));
                    }
                });

        },

        etherpadEditMeta : function() {
            $('#etherpadSaveMetaButton').hide();
            $('.input-area input, .input-area select, #etherpadTitle')
                .on('propertychange keyup input paste change', function() {
                $('#etherpadSaveMetaButton').slideDown();
            });
        },

        etherpadList : function() {
            $('#etherpadCreateInput').val('');
            $('#etherpadCreateButton').hide();
            $('#etherpadCreateInput').on('propertychange keyup input paste change', function() {
                if ($(this).val()) {
                    $('#etherpadCreateButton')
                        .prev()
                        .removeClass('large-space')
                        .next()
                        .show();
                } else {
                    $('#etherpadCreateButton')
                        .prev()
                        .addClass('large-space')
                        .next()
                        .hide();
                }
            });
        },

        buttonHref : function() {
            // allow href attribute for buttons
            $('body').on('click','button,div',function() { // for href divs
                var $this = $(this);
                if ($this.attr('href') && !($this.attr('data-lightbox'))) {
                    if ($this.attr('target') == '_blank') {
                        window.open($(this).attr('href'), '_blank');
                    } else {
                        $(location).attr("href", $(this).attr('href'));
                    }
                }
            });
            // don't use the div's href link if an inner <a> element was clicked!
            $('body').on('click', 'button[href] a[href],div[href] a[href]', function(e) {
                var $this = $(this);
                if ($this.attr('target') == '_blank') {
                    window.open($(this).attr('href'), '_blank');
                } else {
                    $(location).attr("href", $(this).attr('href'));
                }
                e.preventDefault();
                return false;
            });

            // Disable all nonsense links <a href="#">
            $('body').on('click','a[href="#"]',function(e) {
                e.preventDefault();
            });
            
            // add a click-proxy on media-body buttons that have .click-previous-a
            $('.click-previous-a').on('click',function(e) {
                $(this).prev('a').click();
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

        itemCheckboxList : function() {
            
            // A checkbox was clicked. Show buttons depending on what is checked:
            //   - "check all" button if at least one is checked, except when every box is checked show the "uncheck all"
            //   - action buttons when something is checked
            //   - deselect all button when every box is checked
            $('.item_checkbox_element .fa-square-o, .item_checkbox_element .fa-check-square-o').parent().click(function() {
                if ($('.item_checkbox_element .fa-check-square-o').length && !$('.item_checkbox_element .fa-square-o').length) {
                    $('.item_checkbox_action_button, .item_checkbox_mark_all_false').show();
                    $('.item_checkbox_mark_all_true').hide();
                } else if ($('.item_checkbox_element .fa-check-square-o').length) {
                    $('.item_checkbox_action_button, .item_checkbox_mark_all_true').show();
                    $('.item_checkbox_mark_all_false').hide();
                } else {
                    $('.item_checkbox_action_button, .item_checkbox_mark_all').hide();
                }
                // fill any checkbox counter with the number of checked boxes
                $('.item_checkbox_count_label').text('(' + $('.item_checkbox_element .fa-check-square-o').length + ')');
            });
            
            // one of the "check all" or "uncheck all" buttons was clicked
            $('.item_checkbox_mark_all').unbind("click").click(function(e){
                var $button = $(this);
                $('.item_checkbox_element i.fa-square-o, .item_checkbox_element i.fa-check-square-o').each(function(){
                    if ($button.hasClass('item_checkbox_mark_all_true')) {
                        // check all was clicked
                        $(this)
	                        .removeClass('fa-square-o')
	                        .addClass('fa-check-square-o')
	                        .next() // INPUT type="hidden"
	                        .attr('value','true')
	                        .parent()
	                        	.addClass('checkbox-checked')
		                        .parents('.btn-emphasized')
			                        .first()
				                        .removeClass('btn-emphasized')
				                        .addClass('btn-extra-emphasized');
                        $('.item_checkbox_mark_all').hide();
                        $('.item_checkbox_mark_all_false').show();
                        $('.item_checkbox_action_button').show();
                    } else {
                    	// uncheck all was clicked
                        $(this)
	                        .addClass('fa-square-o')
	                        .removeClass('fa-check-square-o')
	                        .next() // INPUT type="hidden"
	                        .attr('value','false')
	                        .parent()
	                        	.removeClass('checkbox-checked')
		                        .parents('.btn-extra-emphasized')
		                        	.first()
				                        .removeClass('btn-extra-emphasized')
				                        .addClass('btn-emphasized');
                        $('.item_checkbox_mark_all').hide();
                        $('.item_checkbox_action_button').hide();
                    }
                });
                // fill any checkbox counter with the number of checked boxes
                $('.item_checkbox_count_label').text('(' + $('.item_checkbox_element .fa-check-square-o').length + ')');
                e.preventDefault();
                return false;
            });
            
            // hide all context buttons on start
            if (!$('.item_checkbox_element .fa-check-square-o').length) {
                $('.item_checkbox_action_button, .item_checkbox_mark_all').hide();
            }
        },
        
        /** Returns an array of input names for all checkbox elements that are checked 
         * 	or [] if none are checked. */
        getListOfCheckedItems: function() {
        	var input_names = [];
        	$('.item_checkbox_element i.fa-check-square-o').each(function(){
                input_names.push(
            		$(this)
            		.next() // INPUT type="hidden"
	                .attr('name')
	            );
        	});
        	return input_names;
        },

        multilineEllipsis : function() {
            $('.multiline-ellipsis-realend a').click(function() {
                $(this)
                    .closest('.multiline-ellipsis')
                    .parent()
                    .css('height','auto');
            });
        },

        pressEnterOn : function(target_selector) {
            var e = jQuery.Event("keydown");
            e.which = 13;
            e.keyCode = 13;
            $(target_selector).trigger(e);
        },

        map : function() {
            if (!$('#map').length) return;
            var map = L.map('map').setView([0,0], 10);
            L.tileLayer('https://otile1-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png', {
                attribution: 'Open Streetmap',
                maxZoom: 15,
                minZoom:3
            }).addTo(map);


            var markers = [];
            // mapdata is a global var set directly in HTML
            $(mapData).each(function(id,marker) {
                var markerOptions = {};
                if (marker.avatar) {
                    var markerIcon = L.icon({
                        iconUrl: marker.avatar,
                        iconSize:     [40, 40], // size of the icon
                        iconAnchor:   [20, 40], // point of the icon which will correspond to marker's location
                        popupAnchor:  [0, -40] // point from which the popup should open relative to the iconAnchor
                    });

                    markerOptions.icon = markerIcon;
                }
                var marker = L
                    .marker([marker.lat, marker.lon], markerOptions)
                    .bindPopup(marker.title)
                    .addTo(map);
                markers.push(marker);
            });

            var markerGroup = new L.featureGroup(markers);
            map.fitBounds(markerGroup.getBounds());
            
            $('#map').data('map', map);
            $('#mapgrow').click(function() {
                $('#map').addClass('large');
                //$('#map').data('map').setZoom( 6 );
                $('#map').data('map')._onResize();
                $(this).hide();
                $('#mapshrink').show();
            })
            $('#mapshrink').click(function() {
                $('#map').removeClass('large');
                //$('#map').data('map').setZoom( 3 );
                $('#map').data('map')._onResize();
                $(this).hide();
                $('#mapgrow').show();
            })
            
        },
        

        initFileUpload: function() {
            if (!$('#fileupload').length) {
                return;
            }

            $('#fileupload').fileupload({
                dataType: 'json',
                dropZone: $('.dropzone'),
                singleFileUploads: false,
                add: function (e, data) {
                    
                    // sort out size 0 files (those may also be folders in browsers not supporting folder upload)
                    for (var i=data.files.length-1; i >= 0; i--) {
                        if (data.files[i].size == 0) {
                            data.files.splice(i, 1);
                        }
                    }
                    if (data.files.length == 0) {
                        alert('You tried to upload an empty file, or your browser does not support uploading whole folders.');
                        return;
                    }
                    
                    // collect infos (relative path) of files, if provided by the browser
                    var fileData = [];
                    for (var i=0; i<data.files.length; i++) {
                        var relativePath = data.files[i].relativePath || null;
                        fileData.push({'name': data.files[i].name, 'relative_path': relativePath});
                    }
                    // add file info to the POST data
                    var formData = {};
                    if (typeof $('#fileupload').attr('data-form-data') !== 'undefined') {
                        formData = JSON.parse($('#fileupload').attr('data-form-data'));
                    }
                    formData['file_info'] = JSON.stringify(fileData);
                    data.formData = formData;
                    
                    /*if (!data.files || data.files.length != 1) {
                        alert('Es kann nur eine Datei auf einmal hochgeladen werden!');
                        return;
                    }
                    */
                    /* var file = data.files[0];
                     * if (file.size == 0 || file.size > SETTING_MAX_IMAGE_UPLOAD_SIZE) {
                     *     alert('Upload of images is only supported up to '+SETTING_MAX_IMAGE_UPLOAD_SIZE/1048576+' MB! (Yours was '+Math.round(parseInt(file.size)/10000) / 100 +' MB)');
                     *     return;
                     * } 
                    */
                    
                    // clone and show progress bar
                    var proto_bar = $('#' + $(this).data('cosinnus-upload-select2-target-field') + '_progressbar');
                    data.context = proto_bar.clone().removeAttr('id').insertAfter(proto_bar).show();
                    
                    data.submit();
                },
                progress: function (e, data) {
                    var progress = parseInt(data.loaded / data.total * 100, 10);
                    data.context.find('span').css('width', progress+'%');
                },
                done: function (e, data) {
                    if (data.result.status == 'ok') {
                        // we act like we had just typed the uploaded file's name in the select2 field
                        // and had clicked the result in the select2 result dropdown 
                        // by directly interfacing with the select2 object on that field
                        if (data.result.on_success == 'add_to_select2') {
                            $('#attachments-existing-files').show();
                            var select2_obj = $('#s2id_' + $(this).data('cosinnus-upload-select2-target-field')).data('select2');
                            if (!select2_obj) {
                                alert('Upload complete but the file could not be added to the field. Type in the filename to attach it!')
                            }
                            $.each(data.result.data, function(index, select2_data) {
                                select2_obj.onSelect(select2_data);
                            });
                        } else if (data.result.on_success == 'refresh_page') {
                            location.reload();
                            return; // return so we don't remove the progress bar on page refresh (confuses users)
                        } else if (data.result.on_success == 'render_object') {
                            $.each(data.result.data, function(index, object_html) {
                                // append rendered object to object list
                                $(object_html).hide().insertAfter('#object_list_anchor').fadeIn(800);
                                $.cosinnus.checkBox();
                                $.cosinnus.itemCheckboxList();
                            });
                        }
                        
                    } else if (data.result.status == 'denied') {
                        alert('Die Datei die hochgeladen wurde war zu groß oder nicht für den Upload zugelassen!');
                    } else if (data.result.status == 'invalid') {
                        alert('Die Datei die hochgeladen wurde war zu groß oder nicht für den Upload zugelassen!');
                    } else {
                        alert('Es gab einen unbekannten Fehler beim hochladen. Wir werden das Problem umgehend beheben!');
                    }

                    data.context.remove(); // remove progress bar
                },
                fail: function (e, data) {
                    alert('Es gab einen Fehler beim Hochladen. Möglicherweise ist der Server nicht erreichbar, oder ihr Browser unterstützt diese Art des Uploads nicht. Bitte beachte auch die Hinweise zum Hochladen von Ordnern!')
                    data.context.remove(); // remove progress bar
                }
            });
            // hover effect for file dropzones, from https://github.com/blueimp/jQuery-File-Upload/wiki/Drop-zone-effects
            $(document).bind('dragover', function (e) {
                var dropZone = $('.dropzone');
                var foundDropzone;
                var timeout = window.dropZoneTimeout;
                var found = false;
                var node = e.target;
                
                if (!timeout) {
                    dropZone.addClass('in');
                } else {
                    clearTimeout(timeout);
                }

                do {
                    if ($(node).hasClass('dropzone')) {
                        found = true;
                        foundDropzone = $(node);
                        break;
                    }
                    node = node.parentNode;
                } while (node != null);
                
                if (found) {
                    foundDropzone.addClass('hover');
                } else {
                    dropZone.removeClass('hover');
                }

                window.dropZoneTimeout = setTimeout(function () {
                    window.dropZoneTimeout = null;
                    dropZone.removeClass('in hover');
                }, 100);
            });
            $(document).bind('drop dragover', function (e) {
                e.preventDefault();
            });
        },
        
        /** Enables toggling content by clicking a button.
         *    Set this up by giving your button elements: 
         *    - a data-id="<num>", different for each
         *    - a data-toggle-group="<name>", same for each (if omitted, assumes global group)
         *    - the class "toggleable_button" 
         *    
         *    Give your content elements (multiple supported, for example for content, and a button highlight)
         *    - the same data-id
         *    - the same data-toggle-group
         *    - the class "toggleable_content"
         *    */
        toggleable : function() {
            $('.toggleable_button').off('click').click(function () {
                var group = $(this).data('toggle-group');
                if (group) {
                    $('.toggleable_content[data-toggle-group='+$(this).data('toggle-group')+']').hide();
                } else {
                    $('.toggleable_content').hide();
                }
                $('.toggleable_content[data-id='+$(this).data('id')+']').show();
            });
        },

		/**
		 * Wrap your text in a div with class `.truncated-textfield` to have it
		 * automatically limited to a height. If some text is hidden, the div
		 * will become clickable to show the entire height of text.
		 */
		truncatedTextfield : function() {
			$('.truncated-textfield:not(.truncated-textfield-applied)').each(function() {
				var field = this; 
				// if the field overflows its bounds (plus a little buffer for browser-weirdness)
				if (field.scrollHeight > field.offsetHeight + 5) { 
					$(field).addClass('truncated-textfield-applied');
				}
			});
			if (!$.cosinnus.truncatedTextfieldInited) {
				$('body').on('click', '.truncated-textfield-applied', function() {
					$(this).removeClass('truncated-textfield truncated-textfield-applied');
				});
				$.cosinnus.truncatedTextfieldInited = true;
			}
		},
		truncatedTextfieldInited : false,

        
        modal_activate: function() {
            $('._elem-action-disabled').attr('disabled', false);
            $('._elem-action-hidden').show();
            $('._elem-action-shown').hide();
            $('._elem-start-shown').show();
            $('._elem-start-hidden').hide();
            $('._elem-success-shown').hide();
        },
        
        modal_deactivate: function() {
            $('._elem-action-disabled').attr('disabled', true);
            $('._elem-action-hidden').hide();
            $('._elem-action-shown').show();
            $('._elem-success-shown').hide();
        },
        
        display_report_error: function(jq_id) {
            $(jq_id).show();
            $.cosinnus.modal_activate();
        },
        
        display_report_success: function(jq_id) {
            $(jq_id).hide();
            $.cosinnus.modal_activate();
            $('._elem-success-shown').show();
            $('._elem-success-hidden').hide();
        },
        
        
        decodeEntities : (function() {
            // this prevents any overhead from creating the object each time
            var element = document.createElement('div');
        
            function decodeHTMLEntities (str) {
                if(str && typeof str === 'string') {
                    // strip script/html tags
                    str = str.replace(/<script[^>]*>([\S\s]*?)<\/script>/gmi, '');
                    str = str.replace(/<\/?\w(?:[^"'>]|"[^"]*"|'[^']*')*>/gmi, '');
                    element.innerHTML = str;
                    str = element.textContent;
                    element.textContent = '';
                }
        
                return str;
            }
        
            return decodeHTMLEntities;
        })(),

        dashboardArrange: function() {
            if (!$('#dashboard').length) return;

            // Widgets nach Priorität sortiert in Array aufnehmen
            var widgets = [];
            $('#dashboard .dashboard-widget').each(function() {
                widgets.push({
                    'priority': $(this).data('widget-priority'),
                    'element': $(this),
                });
            });
            widgets.sort(function(a, b) {
                return a.priority - b.priority;
            });

            $( window ).on('orientationchange ready dashboardchange', function() {
                if ($('textarea:focus, input:focus').length > 0) {
                    return;
                }
                
                // Dashboard-Höhe blockieren
                $('#dashboard').css('min-height', $('#dashboard').height());

                // Anzahl angezeigter Spalten herausfinden
                var cols = 1;
                if ($('#dashboard #dashboard-col2').is(":visible")) {
                    // mindestens sm
                    cols = 2;
                }
                if ($('#dashboard #dashboard-col3').is(":visible")) {
                    // mindestens md
                    cols = 3;
                }

                // Verschiebe alle Widgets in den unsichtbaren Parkplatz
                $.each(widgets, function(index, widget) {
                    widget.element.appendTo('#dashboard #dashboard-unsorted');
                });

                // Verteile die Widgets auf die Spalten
                // Bevorzuge die am wenigsten gefüllte Spalte und bei Gleichstand die am weitesten links
                $.each(widgets, function(index, widget) {
                    var heightCol1 = $('#dashboard #dashboard-col1').height();
                    var heightCol2 = $('#dashboard #dashboard-col2').height();
                    var heightCol3 = $('#dashboard #dashboard-col3').height();
                    if ((cols == 1) || ((cols == 2) && (heightCol1 <= heightCol2)) || ((cols == 3) && (heightCol1 <= heightCol2) && (heightCol1 <= heightCol3))) {
                        widget.element.appendTo('#dashboard #dashboard-col1');
                    } else if ((cols == 2) || ((cols == 3) && (heightCol2 <= heightCol3))) {
                        widget.element.appendTo('#dashboard #dashboard-col2');
                    } else {
                        widget.element.appendTo('#dashboard #dashboard-col3');
                    }
                });

                // Dashboard-Höhe freigeben
                $('#dashboard').css('min-height', 0);

            });
        },

        toggleGroup: function() {
            // Immer genau ein Element aus der Gruppe .togglegroup wird angezeigt. Innerhalb der Elemente gibt es einen Umschalt-Knopf .togglegroup-button

            $('.togglegroup').each(function() {
                var togglegroup = $(this);
                var hasactive = false; // is there an active item?
                togglegroup.find('> *').each(function() {
                    $(this).addClass('togglegroup-item');

                    if( $(this).hasClass('togglegroup-active')) {
                        if (hasactive == true) {
                            // Es gibt schon ein aktives Item, also dieses deaktivieren
                            $(this).removeClass('togglegroup-active');
                            return;
                        }
                        hasactive = true;
                    }
                });
                if (!hasactive) {
                    // Add active status to first item
                    togglegroup.find('> *').first().addClass('togglegroup-active');
                }


                togglegroup.find('> *:not(.togglegroup-active)').each(function() {
                    // Hide the items that are not active
                    $(this).hide();
                });

                togglegroup.find('.togglegroup-button').click(function(e) {
                    var item = false;
                    if ($(this).hasClass('togglegroup-item')) {
                        item = $(this);
                    } else {
                        item = $(this).closest('.togglegroup-item');
                    }

                    item.hide();
                    if (item.next().length) {
                        item.next().show();
                    } else {
                        item.parent().find('> *').first().show();
                    }

                    e.preventDefault();
                });

            });
        },
        

        toggleSwitch: function() {
            /** All elements with class .toggle-switch will toggle (show/hide)
             * (or for checkboxed, read the checked state, then show if checked)
             *  the element with id equal to the value in their 'data-toggle-target' attribute. */
            $('.toggle-switch').on('change', function() {
                var target_id = $(this).attr('data-toggle-target');
                if (target_id) {
                    var target = $('#' + target_id);
                    if ($(this).is(':checkbox')) {
                        if ($(this).is(':checked')) {
                            target.show();
                        } else {
                            target.hide();
                        }
                    } else {
                        target.toggle();
                    }
                }
            });
        },
        
        snapToBottom: function() {
            /* Snap class="snap-to-bottom" elements to the bottom of the page when they are scrolled out of view.
             * This code assumes there is only one (!) of such elements on any page! */
            
            function refresh_snap() {
                var placeholder = $('.snap-to-bottom-placeholder');
                var elem = $('.snap-to-bottom');
                
                if (placeholder.length > 0) {
                    // should we place the snapped element back inside the page?
                    if (( placeholder.offset()['top'] + placeholder.outerHeight() ) <= ( $(window).height() + $(window).scrollTop() )) {
                        // remove placeholder
                        placeholder.remove();
                        elem.data('snapped', false);
                        elem.css({'position':'', 'bottom': '', 'width': ''});
                    } 
                } 
                else if (elem.length > 0) {
                    // should we make the page element snap to the screen?
                    var elem_height = elem.outerHeight();
                    var elem_width = elem.outerWidth();
                    elem.css({'position':'', 'bottom': '', 'width': ''});
                    if (( elem.offset()['top'] + elem_height ) > ( $(window).height() + $(window).scrollTop() )) {
                        if (!elem.data('snapped')) {
                            // leave a placeholder with the same height and width
                            elem.after('<div class="snap-to-bottom-placeholder" style="width: '+ elem_width +'px; height: '+ elem_height +'px;"></div>')
                            elem.css({'position':'fixed', 'bottom': '0', 'width': elem_width + 'px'});
                            elem.data('snapped', true);
                        }
                    } 
                }
            }
            if (typeof this.snapToBottomRegistered === "undefined") {
                $(window).on('resize orientationchange', function() {
                    $('.snap-to-bottom-placeholder').remove();
                    $('.snap-to-bottom').data('snapped', false).css({'position':'', 'bottom': '', 'width': ''});
                    refresh_snap();
                });
                $(window).on('scroll', refresh_snap);
                this.snapToBottomRegistered = true;
            }
            refresh_snap();
        },
        

        embeddifyURLs: function() {
            /* Adds the current site domain to each href-URL that doesn't start with 'http', 
             * and sets the ``target`` attr of each element with a href to "_blank". */
            var domain = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '');
            $('*[href]').each(function(idx, elem){
                var $this = $(this);
                if ($this.attr('href').substring(0,4) != 'http') {
                    $this.attr('href', domain + $this.attr('href'));
                }
                if (!$this.attr('target')) {
                    $this.attr('target', '_blank');
                }
            });
        },
        
        addBtnTitles: function() {
            /* For all <button> with class="btn", if they have a media-body that is only text, add this text
             * as a title="..." attribute to the button. Useful for buttons with outflowing text. */
            $('button.btn').each(function(idx, button){
                button = $(button);
                if (!button.attr('title')) {
                    var media_body = button.find('.media-body');
                    if (media_body.children().length == 0) {
                        button.attr('title', media_body.text().trim());
                    }
                }
            });
        },
        
        /** Will also set the `title` attribute of any button or link to the text of the 
         *  element pointed at by the `titledby` attribute, or itself's text if `self` is given. */
        titledby: function(parent) {
        	if (typeof parent === 'undefined') {
        		parent = $('body');
        	}
        	parent.find('button[titledby], a[titledby]').each(function(idx, el){
                $el = $(el);
                var target = $el.attr('titledby');
                if (target == 'self') {
                	target = $el;
                } else {
                	target = $el.find(target);
                }
                $el.attr('title', target.text().trim());
            });
        },
        
        updateQueryString: function(key, value, url) {
            /** Adds/replaces/removes a URL query parameter. 
             * If no URL is given, will use the current browser URL. */
            if (!url) url = window.location.href;
            var re = new RegExp("([?&])" + key + "=.*?(&|#|$)(.*)", "gi"),
                hash;

            if (re.test(url)) {
                if (typeof value !== 'undefined' && value !== null)
                    return url.replace(re, '$1' + key + "=" + value + '$2$3');
                else {
                    hash = url.split('#');
                    url = hash[0].replace(re, '$1$3').replace(/(&|\?)$/, '');
                    if (typeof hash[1] !== 'undefined' && hash[1] !== null) 
                        url += '#' + hash[1];
                    return url;
                }
            }
            else {
                if (typeof value !== 'undefined' && value !== null) {
                    var separator = url.indexOf('?') !== -1 ? '&' : '?';
                    hash = url.split('#');
                    url = hash[0] + separator + key + '=' + value;
                    if (typeof hash[1] !== 'undefined' && hash[1] !== null) 
                        url += '#' + hash[1];
                    return url;
                }
                else
                    return url;
            }
        },
        
        addClassChangeTrigger: function() {
        	// from: https://stackoverflow.com/questions/1950038/jquery-fire-event-if-css-class-changed
        	//Create a closure
        	(function(){
        		 // Your base, I'm in it!
	        	 var originalAddClassMethod = jQuery.fn.addClass;
	        	 jQuery.fn.addClass = function(){
	        	     // Execute the original method.
	        	     var result = originalAddClassMethod.apply( this, arguments );
	        	     // trigger a custom event
	        	     jQuery(this).trigger('cssClassChanged');
	        	     // return the original result
	        	     return result;
	        	 }
        		 // Your base, I'm in it!
	        	 var originalRemoveClassMethod = jQuery.fn.removeClass;
	        	 jQuery.fn.removeClass = function(){
	        	     // Execute the original method.
	        	     var result = originalRemoveClassMethod.apply( this, arguments );
	        	     // trigger a custom event
	        	     jQuery(this).trigger('cssClassChanged');
	        	     // return the original result
	        	     return result;
	        	 }
        	})();

        	//document ready function
        	$(function(){
        	});
        },

	    fixBootstrapModalScroll: function() {
	    	$("body").bind('cssClassChanged', function(){ 
	    		if ($(this).hasClass('modal-open')) {
	    			$('html').addClass('modal-open');
	    		} else {
	    			$('html').removeClass('modal-open');
	    		}
	    	});
	    },
	    
	    fixBootstrapMobileNavbar: function() {
	    	$('#navbar').on('show.bs.collapse', function(x) {
	    	    $('html').attr("style", "overflow: hidden");
	    	});
	    	$('#navbar').on('hide.bs.collapse', function(x) {
	    		$('html').attr("style", "");
	    	});
	    },
	    
    	
        dashboardArrangeInput: function() {
            $(window).on('dashboardArrangeInputShow', function() {
                // Alle Widgets mit unsichtbaren Elementen abdecken
                $('#dashboard > * > .dashboard-widget')
                    .css('position', 'relative')
                    .append('<div class="sortable-widget-overlay"></div>');

                // Make widgets sortable
                $('#dashboard > *').sortable({ 'connectWith': 'dashboardwidgets' });

                $('#dashboardArrangeInputShow').hide();
                $('#dashboardArrangeInputSave').show();
                $('#dashboardArrangeInputCancel').show();
                $('#dashboardArrangeMessage').show();
            });
            
            $('#dashboardArrangeInputShow').click(function() { $(window).trigger('dashboardArrangeInputShow'); });
            $('#dashboardArrangeInputCancel').click(function() { 
                $('#dashboardArrangeInputSave').attr('disabled', 1);
                $('#dashboardArrangeInputCancel').attr('disabled', 1);
                location.reload();
            });
            
            $(window).on('dashboardArrangeInputSave', function() {
                var widgets = {};

                // Iterate all widgets and find the intended priority
                $('#dashboard > * > .dashboard-widget').each(function() {
                    widgets[$(this).data('widget-id')] = {
                        'priority': Math.round($(this).position().top + ($(this).parent('#dashboard-col2').length ? 1 : 0) + ($(this).parent('#dashboard-col3').length ? 2 : 0)),
                        'widget-id': $(this).data('widget-id'),
                        'app-name': $(this).data('app-name'),
                        'widget-name': $(this).data('widget-name'),
                    };
                });

                $('#dashboardArrangeInputSave').hide();
                $('#dashboardArrangeInputCancel').hide();
                $('#dashboardArrangeInputWait').show();
                
                // save widget configs to server
                $.post( "/widgets/save/", { widget_data: JSON.stringify(widgets) }, "json")
                .done(function( data ) {
                    //$('#dashboardArrangeInputWait').hide();
                    //$('#dashboardArrangeInputShow').show();
                    //$('#dashboard .dashboard-widget .sortable-widget-overlay').remove();
                    location.reload();
                })
                .fail(function() {
                    $('#dashboardArrangeInputWait').hide();
                    $('#dashboardArrangeInputSave').show();
                    alert('There was an error when saving the layout! Your changes have not been saved.')
                })
                .always(function() {
                });
                
            });
            $('#dashboardArrangeInputSave').click(function() { $(window).trigger('dashboardArrangeInputSave'); });

        },
        popover: function() {
            $('.popover-button').popover();
        },

    };
})( jQuery );

// Set global language here
$.cosinnus.lang = cosinnus_current_language;
if (typeof moment !== "undefined") {
    moment.lang($.cosinnus.lang);
}

if (typeof $.fn.select2 !== "undefined") {
    // select2 localizations
    $.fn.select2.defaults=$.extend($.fn.select2.defaults, { 
        formatNoMatches: function () { return $.cosinnus.no_matches_found; }, 
    }); 
}

/* string sprintf format for JS
 * from http://stackoverflow.com/a/4673436
 * 
 * "{0} is dead, but {1} is alive! {0} {2}".format("ASP", "ASP.NET");
 *    -->   "ASP is dead, but ASP.NET is alive! ASP {2}"
*/
if (!String.prototype.format) {
    String.prototype.format = function() {
      var args = arguments;
      return this.replace(/{(\d+)}/g, function(match, number) { 
        return typeof args[number] != 'undefined'
          ? args[number]
          : match
        ;
      });
    };
  }

$(function() {
    $.cosinnus.checkBox();
    $.cosinnus.onoffSwitch();
    $.cosinnus.hideOnClick();
    $.cosinnus.fadedown();
    $.cosinnus.selectors();
    $.cosinnus.fullcalendar();
    $.cosinnus.calendarBig();
    $.cosinnus.editThisClickarea();
    $.cosinnus.searchbar();
    $.cosinnus.todosSelect();
    $.cosinnus.datePicker();
    $.cosinnus.renderMomentDataDate();
    $.cosinnus.etherpadEditMeta();
    $.cosinnus.etherpadList();
    $.cosinnus.inputDynamicSendButton();
    $.cosinnus.buttonHref();
    $.cosinnus.calendarDayTimeChooser();
    $.cosinnus.calendarDoodleVote();
    $.cosinnus.fileList();
    $.cosinnus.itemCheckboxList();
    $.cosinnus.multilineEllipsis();
    $.cosinnus.map();
    $.cosinnus.initFileUpload();
    $.cosinnus.dashboardArrange();
    $.cosinnus.dashboardArrangeInput();
    $.cosinnus.popover();
    $.cosinnus.toggleGroup();
    $.cosinnus.toggleSwitch();
    $.cosinnus.snapToBottom();
    $.cosinnus.addBtnTitles();
    $.cosinnus.titledby();
    $.cosinnus.addClassChangeTrigger();
    $.cosinnus.fixBootstrapModalScroll();
    $.cosinnus.fixBootstrapMobileNavbar();
    $.cosinnus.truncatedTextfield();
});

