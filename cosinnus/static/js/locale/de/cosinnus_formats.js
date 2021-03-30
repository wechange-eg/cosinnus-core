
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
    }
};

$.cosinnus.no_matches_found = 'Keine Übereinstimmungen gefunden';
