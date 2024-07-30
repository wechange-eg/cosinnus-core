
// We need some new flavours of moment().calendar()
// based on http://momentjs.com/downloads/moment-with-langs.js

// internationalisation objects for momentJs calendar view WITHOUT time:
$.cosinnus.momentShort = {
    calendar : {
        sameDay : '[dzisiaj]',
        nextDay : '[jutro]',
        nextWeek : 'dddd',
        lastDay : '[wczoraj]',
        lastWeek : '[w zeszłym] dddd',
        sameElse : 'L'
    }
};

// internationalisation objects for momentJs calendar view WITH time:
$.cosinnus.momentFull = {
    calendar : {
        sameDay : '[dzisiaj o] LT',
        nextDay : '[jutro o] LT',
        nextWeek : 'dddd [o] LT',
        lastDay : '[wczoraj o] LT',
        lastWeek : '[zeszłym] dddd [o] LT',
        sameElse : 'L [o] LT'
    }
};


$.cosinnus.fullcalendar_format = {
    firstDay: 1, // Monday
    buttonText: {
        today: "Dzisiaj",
        month: "Miesiąc",
        week: "Tydzień",
        day: "Dzień",
        list: "Lista"
    }
};

$.cosinnus.no_matches_found = 'Nie znaleziono dopasowań';
