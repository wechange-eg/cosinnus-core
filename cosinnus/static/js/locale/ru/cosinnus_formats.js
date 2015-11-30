
// We need some new flavours of moment().calendar()
// based on http://momentjs.com/downloads/moment-with-langs.js

// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.momentShort = {
    calendar : {
        sameDay: "[сегодня]",
        sameElse: "L",
        nextDay: '[за́втра]',
        nextWeek: 'dddd',
        lastDay: '[вчера́]',
        lastWeek: '[в прошлый] dddd'
    }
};

// internationalisation objects for momentJs calendar view WITH time:
$.cosinnus.momentFull = {
    calendar : {
        sameDay: "[сегодня umв] LT",
        sameElse: "L [в] LT",
        nextDay: '[за́втра в] LT',
        nextWeek: 'dddd [в] LT',
        lastDay: '[вчера́ в] LT',
        lastWeek: '[в прошлый] dddd [в] LT'
    },
};


$.cosinnus.fullcalendar_format = {
    firstDay: 1, // Monday
    buttonText: {
        today: "сегодня",
        month: "месяц",
        week: "неделя",
        day: "день"
    },
    monthNames: ['январь','февраль','март','апрель',
        'май','июнь','июль','август',
        'сентябрь','октябрь','ноябрь','декабрь'],
    monthNamesShort: ['янв','фев','мар','апр',
          'май','июн','июл','авг',
          'сен','окт','ноя','дек'],
    dayNames: ['воскресенье','понедельник','вторник',
        'среда','четверг','пятница','суббота'],
    dayNamesShort: ['во','по','вт', 'ср','че','пя','су'],
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

$.cosinnus.no_matches_found = 'Ничего не найдено';
