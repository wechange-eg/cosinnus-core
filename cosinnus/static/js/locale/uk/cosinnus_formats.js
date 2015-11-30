
// We need some new flavours of moment().calendar()
// based on http://momentjs.com/downloads/moment-with-langs.js

// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.momentShort = {
    calendar : {
        sameDay: "[сьогодні]",
        sameElse: "L",
        nextDay: '[завтра]',
        nextWeek: 'dddd',
        lastDay: '[вчора]',
        lastWeek: '[останній] dddd'
    }
};

// internationalisation objects for momentJs calendar view WITH time:
$.cosinnus.momentFull = {
    calendar : {
        sameDay: "[сьогодні в] LT",
        sameElse: "L [в] LT",
        nextDay: '[завтра в] LT',
        nextWeek: 'dddd [в] LT',
        lastDay: '[вчора в] LT',
        lastWeek: '[останній] dddd [в] LT'
    },
};


$.cosinnus.fullcalendar_format = {
    firstDay: 1, // Monday
    buttonText: {
        today: "сьогодні",
        month: "місяць",
        week: "тиждень",
        day: "день"
    },
    monthNames: ['січень','лютого','березня','квітня',
        'травня','червень','липня','серпня',
        'Вересень','жовтень','листопад','грудня'],
    monthNamesShort: ['січ','лют','бер','кві','тра',
        'чер','лип','сер','Вер','жов','лис','гру'],
    dayNames: ['неділя','понеділок','Вівторок',
        'середа','четвер',"П'ятниця",'субота'],
    dayNamesShort: ['не','по','Ві','се','че','ят','су'],
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

$.cosinnus.no_matches_found = 'Співпадінь не знайдено';
