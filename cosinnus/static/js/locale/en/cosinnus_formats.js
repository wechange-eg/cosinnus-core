
// We need some new flavours of moment().calendar()
// based on http://momentjs.com/downloads/moment-with-langs.js

// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.momentShort = {
    calendar : {
        sameDay : '[today]',
        nextDay : '[tomorrow]',
        nextWeek : 'dddd',
        lastDay : '[yesterday]',
        lastWeek : '[last] dddd',
        sameElse : 'L'
    }
};

// internationalisation objects for momentJs calendar view WITH time:
$.cosinnus.momentFull = {
    calendar : {
        sameDay : '[today at] LT',
        nextDay : '[tomorrow at] LT',
        nextWeek : 'dddd [at] LT',
        lastDay : '[yesterday at] LT',
        lastWeek : '[last] dddd [at] LT',
        sameElse : 'L [at] LT'
    }
};


$.cosinnus.fullcalendar_format = {
    firstDay: 1, // Monday
    buttonText: {
        today: "Today",
        month: "Month",
        week: "Week",
        day: "Day"
    },
    monthNames: ['January','February','March','April',
        'May','June','July','August',
        'September','October','November','December'],
    monthNamesShort: ['Jan','Feb','Mar','Apr','May',
        'Jun','Jul','Aug','Sept','Okt','Nov','Dec'],
    dayNames: ['Sunday','Monday','Tuesday',
        'Wednesday','Thursday','Friday','Saturday'],
    dayNamesShort: ['Su','Mo','Tu','We','Th','Fr','Sa'],
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

$.cosinnus.no_matches_found = 'No matches found';
