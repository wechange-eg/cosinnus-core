function initializeMap(markers) {
    var mapOptions = {
        zoom: 8,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        maxZoom: 12
    };
    var map = new google.maps.Map(document.getElementById("map"), mapOptions);

    if (markers.length <= 0) {
        var berlin = new google.maps.LatLng(52.5233, 13.4127);
        map.setCenter(berlin);
        return map;
    }

    var bounds = new google.maps.LatLngBounds();
    for (var i = 0; i < markers.length; i++) {
        bounds.extend(markers[i].position);
        markers[i].setMap(map);
    }
    map.fitBounds(bounds);
    map.setCenter(bounds.getCenter());
    var listener = google.maps.event.addListener(map, "idle", function() {
        /*if (map.getZoom() > 8) {
            map.setZoom(8);
        }*/
        google.maps.event.removeListener(listener);
    });
    return map;
}
