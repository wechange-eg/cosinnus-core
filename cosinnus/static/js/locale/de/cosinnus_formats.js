
// We need some new flavours of moment().calendar()
// based on http://momentjs.com/downloads/moment-with-langs.js

// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.momentShort = {
    calendar : {
        sameDay: "[heute]",
        sameElse: "L",
        nextDay: '[morgen]',
        nextWeek: 'dddd',
        lastDay: '[gestern]',
        lastWeek: '[letzten] dddd'
    }
};

// internationalisation objects for momentJs calendar view WITH time:
$.cosinnus.momentFull = {
    calendar : {
        sameDay: "[heute um] LT",
        sameElse: "L [um] LT",
        nextDay: '[morgen um] LT',
        nextWeek: 'dddd [um] LT',
        lastDay: '[gestern um] LT',
        lastWeek: '[letzten] dddd [um] LT'
    },
};


$.cosinnus.fullcalendar_format = {
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

$.cosinnus.no_matches_found = 'Keine Übereinstimmungen gefunden';
