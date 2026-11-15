/*
  map.js - the interactive trip map on map.html.
  Stops come from map-data.js; the route is drawn through them in order.
*/
(function () {
  var stops = window.TRIP_STOPS || [];
  var accent = '#d2691e';

  var map = L.map('trip-map', {
    zoomControl: true,
    scrollWheelZoom: true,
    worldCopyJump: false
  });

  // Light grey base map with place names on top (Esri, free with attribution).
  var esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/';
  L.tileLayer(esri + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16,
    attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors'
  }).addTo(map);

  // State borders sit between the base map and the place names.
  map.createPane('labels');
  map.getPane('labels').style.zIndex = 450;
  map.getPane('labels').style.pointerEvents = 'none';
  if (window.US_STATE_BORDERS) {
    L.polyline(window.US_STATE_BORDERS, {
      color: '#a8a59b', weight: 1, opacity: 0.9, interactive: false
    }).addTo(map);
  }
  L.tileLayer(esri + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16, pane: 'labels'
  }).addTo(map);

  var starIcon = L.divIcon({
    className: 'trip-marker trip-marker--start',
    html: '<svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true">' +
          '<path d="M12 2.2l2.9 6.1 6.7.8-4.9 4.6 1.3 6.6L12 17l-6 3.3 1.3-6.6L2.4 9.1l6.7-.8z" ' +
          'fill="' + accent + '" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    iconSize: [34, 34],
    iconAnchor: [17, 18],
    popupAnchor: [0, -14]
  });

  var dotIcon = L.divIcon({
    className: 'trip-marker trip-marker--post',
    html: '<span></span>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -8]
  });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  var points = [];
  stops.forEach(function (s, i) {
    var ll = [s.lat, s.lng];
    points.push(ll);
    var html =
      '<a class="trip-popup" href="' + esc(s.url) + '">' +
        (s.cover ? '<img src="' + esc(s.cover) + '" alt="" />' : '') +
        '<span class="trip-popup-body">' +
          '<span class="trip-popup-meta">' + esc(s.date) + ' · ' + esc(s.place) +
            (s.start ? ' · <strong>Start</strong>' : '') + '</span>' +
          '<span class="trip-popup-title">' + esc(s.title) + '</span>' +
          '<span class="trip-popup-link">Read the post →</span>' +
        '</span>' +
      '</a>';
    var marker = L.marker(ll, {
      icon: s.start ? starIcon : dotIcon,
      title: s.title,
      zIndexOffset: s.start ? 1000 : i
    }).addTo(map).bindPopup(html, { maxWidth: 260, minWidth: 220 });

    if (s.start) {
      marker.bindTooltip('Start · ' + s.place, {
        permanent: true, direction: 'right', offset: [16, 0], className: 'trip-label'
      });
    }
  });

  if (points.length > 1) {
    L.polyline(points, { color: accent, weight: 3, opacity: 0.85, dashArray: '1 7', lineCap: 'round' }).addTo(map);
  }

  // Show the whole country, widening if the trip ever goes beyond it.
  var bounds = L.latLngBounds([[24.5, -125], [49.5, -66.5]]);
  points.forEach(function (p) { bounds.extend(p); });
  map.fitBounds(bounds, { padding: [20, 20] });

  window.addEventListener('resize', function () { map.invalidateSize(); });
})();
