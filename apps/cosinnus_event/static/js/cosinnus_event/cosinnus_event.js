
// reading out the selected dates, formatting then and putting them into the form for django
$('#form-event').submit(function() {
  var totalForms = 0;
  var newFormIdx = $('#id_suggestions-INITIAL_FORMS').val();
  var formEvent = $(this);

  var addSuggestionToForm = function(idx, datum, time) {
    if (!idx) { // no form index, so a new suggestion form needs creating
      idx = newFormIdx;
      newFormIdx++;
    }

    var name = 'suggestions-' + idx + '-from_date'
    var dateTime = moment(datum + ' ' + time).format(cosinnus_datetime_format);
    var splitDateTime = dateTime.split(' ');
    var valdate = splitDateTime[0];
    var valtime = splitDateTime[1];

    // the from_date input for date
    $('<input />')
      .attr('type', 'hidden')
      .attr('id', 'id_' + name + '_0')
      .attr('name', name + '_0')
      .attr('value', valdate)
      .appendTo(formEvent);
    // the from_date_input for time
    $('<input />')
    .attr('type', 'hidden')
    .attr('id', 'id_' + name + '_1')
    .attr('name', name + '_1')
    .attr('value', valtime)
    .appendTo(formEvent);
  

    // to_date unused atm; to_date == from_date
    name = name.replace('from_date', 'to_date');
    // the from_date input for date
    $('<input />')
      .attr('type', 'hidden')
      .attr('id', 'id_' + name + '_0')
      .attr('name', name + '_0')
      .attr('value', valdate)
      .appendTo(formEvent);
    // the from_date_input for time
    $('<input />')
    .attr('type', 'hidden')
    .attr('id', 'id_' + name + '_1')
    .attr('name', name + '_1')
    .attr('value', valtime)
    .appendTo(formEvent);

    // increase number of forms for management form
    totalForms++;
  };
  
  var dateList = [];
  var hasErrors = false;
  
  $('#calendar-doodle-days-selector-list table tbody tr').each(function() {
    var datum = $(this).attr('data-date');
    if (!datum) return;

    var time1 = $(this).find('input').first();
    //var time2 = $(this).find('input').last();
    
    // support entries like '2130' and empty entries
    var time_val = convertDoodleStringTime(time1.val());
    if (time_val == null) {
    	hasErrors = true;
    }
    
    dateList.push([time1.attr('data-form-idx'), datum, time_val]);
  });
  
  if (hasErrors) {
      alert("Eine oder mehrere der Zeitangaben haben ein ungültiges Format!");
      return false;
  }
  
  // deduplication of selected dates and adding them to the actual django form
  for (i = dateList.length-1; i >= 0; i--) {
    var dateItem = dateList[i];
    var hasDuplicate = false;
    
    for (j = dateList.length-1; j >= 0; j--) {
        var dateItem2 = dateList[j];
        if (dateItem !== dateItem2 && dateItem[1] == dateItem2[1] && dateItem[2] == dateItem2[2]) { 
          hasDuplicate = true;
          break;
        }
    }
    
    if (hasDuplicate) {
      dateList.splice(i, 1);
    } else {
        // adding the date item to the actual django form
      addSuggestionToForm(dateItem[0], dateItem[1], dateItem[2]);
    }
  }
  
  $('#id_suggestions-TOTAL_FORMS').val(totalForms);
  
  return true; // now submit
});

/**
 * Will accept and convert string times to a proper "12:30" format.
 * Acceptable examples:
 * 		"3" --> "03:00"
 * 		"330" --> "03:30"
 * 		"12" --> "12:00"
 * 		"1245" --> "12:45"
 * 		"12.45" --> "12:45"
 * 		"12:45" --> "12:45"
 */
var convertDoodleStringTime = function(stringTime) {
    var time_val = stringTime || '00:00';
    time_val = time_val.replace(':', '').replace('.', '');
    if (isNaN(time_val) || time_val.length > 4) {
        // invalid format
        return null;
    }
    if (time_val.length == 1 || time_val.length == 3) {
    	time_val = '0' + time_val;
    }
    if (time_val.length == 2) {
    	time_val = time_val + '00';
    }
    if (time_val.length >=3 && time_val.length <=4) {
    	time_val = time_val.slice(0,time_val.length-2) + ':' + time_val.slice(time_val.length-2);
    }
    return time_val;
}


var calendarCreateDoodle = function() {
    if (!$('#calendar-doodle-days-selector-list').length) {
        return;
    }
    var CREATE_MULTIPLE_DOODLE_DAYS = true;
    var formEvent = $('#form-event');
    
    function selectDays(reSort) {
    	if (reSort) {
    		$('#calendar-doodle-days-selector-list table tbody tr:not(.proto)').sortElements(function(a, b){
    			return $(a).attr('data-date') > $(b).attr('data-date') ? 1 : -1;
    		});
    	}

        // mark the days that are picked in the calendar
        $('#calendar-doodle-days-selector-list table tr').each(function() {
        	var dateDataAttr = $(this).attr('data-date');
        	if (dateDataAttr) {
        		var formIdx = $(this).find('.doodle-time-input').attr('data-form-idx');
        		var deleteName = 'suggestions-' + formIdx + '-DELETE';
        		// check if the current date is not already marked as to-delete
        		if (formEvent.find('input[name="' + deleteName + '"]').attr('value') != 'true') {
        			$('#calendar-doodle-days-selector .small-calendar '+
        					'td[data-date='+dateDataAttr+']:not(.fc-other-month)')
        					.addClass('selected');
        		}
        	}
        });

        // when table empty hide even the headline
        if($('#calendar-doodle-days-selector-list table tbody tr').length==1) {
            $('#calendar-doodle-days-selector-list table thead').hide();
        } else {
            $('#calendar-doodle-days-selector-list table thead').show();
        }
    }
    
    // instant initialize
    selectDays(true);

    $("#calendar-doodle-days-selector .small-calendar").on("fullCalendarDayClick", function(event, date) {
        var dayElement = event.currentTarget;
        if ($(dayElement).hasClass('fc-other-month')) return;

        var dateDataAttr = date.date.getFullYear() + "-"
            + ((date.date.getMonth()+1).toString().length === 2
                ? (date.date.getMonth()+1)
                : "0" + (date.date.getMonth()+1)) + "-"
            + (date.date.getDate().toString().length === 2
                ? date.date.getDate()
                : "0" + date.date.getDate());

        // unselect all and re-select later
        $(dayElement).parent().parent().find('td').removeClass('selected');

        if (CREATE_MULTIPLE_DOODLE_DAYS || $('#calendar-doodle-days-selector-list table tr[data-date='+dateDataAttr+']').length===0) {
            // add to list (select) now

            var $dateInput = $('#calendar-doodle-days-selector-list table tr.proto')
                .clone()
                .removeClass('proto')
                .show()
                .attr('data-date',dateDataAttr)
                .appendTo($('#calendar-doodle-days-selector-list table tbody'));
            $dateInput.find('.doodle-delete-button').click(function() {
                $(this).parent().remove();
                $("#calendar-doodle-days-selector .small-calendar").fullCalendar('render');
            });
            $dateInput.find('.doodle-date-input')
                .attr('data-date', dateDataAttr)
                .addClass('moment-data-date');
            $dateInput.find('.doodle-time-input').val('');
            
        } else {
            // remove from list now
            $('#calendar-doodle-days-selector-list table tr[data-date='+dateDataAttr+']').remove();
        }

        selectDays();
        $.cosinnus.renderMomentDataDate();
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
                time1: $(this).find('input').first().val()
            });
        });
        // remove last hidden line
        doodleData.dates.pop();
    });
    
    
    // highlighting for invalid time formats
    $('#calendar-doodle-days-selector-list').on('focusout', '.doodle-time-input', function(){
    	var $this = $(this);
		$this.toggleClass('doodle-input-error', convertDoodleStringTime($this.val()) == null);
    });
};

