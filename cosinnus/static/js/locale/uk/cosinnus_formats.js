
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
        day: "день",
        list: "Список"
    }
};

$.cosinnus.no_matches_found = 'Співпадінь не знайдено';
