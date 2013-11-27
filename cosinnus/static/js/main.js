// gmaps
"use strict";
var app = {};

app.init = function () {
    //this.vLoadGoogleMaps();
    this.vInitCalendarWidget();
    this.vInitNavClickToOpenSubNav();
//    this.vLoadYouTube();
};


// Load the IFrame Player API code asynchronously.
app.vLoadYouTube = function () {
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/player_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
};

app.vInitCalendarWidget = function () {
    $('#calendar').datepicker($.datepicker.regional["de"]);
};


// TODO check if player and onYoutTubePlayerAPIReady() need to be global
// Replace the 'ytplayer' element with an <iframe> and
// YouTube player after the API code downloads.
var player;
function onYouTubePlayerAPIReady() {
    player = new YT.Player('ytplayer', {
        height: '350',
        width: '540',
        videoId: 'M7lc1UVf-VE'
    });
};

app.vInitNavClickToOpenSubNav = function () {
    // navigation 1st level: show subnav only
    $(".nav-main .has-subnavi > a").click(function (e) {
        e.preventDefault();
        var sub = $(this).parent(".has-subnavi").find(".subnavi");
        sub.css("visibility", (sub.css("visibility") == "hidden") && "visible" || "hidden");
        return false;
    });
};


/*app.vLoadGoogleMaps = function () {
 var script = document.createElement("script");
 script.type = "text/javascript";
 script.src = "http://maps.googleapis.com/maps/api/js?sensor=true&callback=initialize";
 document.body.appendChild(script);
 }
 */
// needs to be global for callback
/*function initialize() {
 var mapOptions = {
 zoom: 8,
 center: new google.maps.LatLng(-34.397, 150.644),
 mapTypeId: google.maps.MapTypeId.ROADMAP
 }
 var map = new google.maps.Map(document.getElementById("map"), mapOptions);
 }*/


// Init Application
$(document).ready(function () {
    app.init();
});