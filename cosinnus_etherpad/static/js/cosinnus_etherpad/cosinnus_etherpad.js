$(function() {
    /** Etherpad fullscreen toggle */
    
    $('.fullscreen-toggle').click(function() {
        $('.etherpad-iframe').toggleClass('fullscreen');
    });
});