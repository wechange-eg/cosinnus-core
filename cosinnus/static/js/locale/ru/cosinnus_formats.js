
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
    }
};

$.cosinnus.no_matches_found = 'Ничего не найдено';
