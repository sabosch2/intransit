/*
  map-data.js - where each post was written, in trip order.
  The route on the Map page is drawn through these stops from top to bottom.
  To add a post: copy a stop, put it at the END of the list, and change
  its details. Coordinates are latitude, longitude (Google Maps shows them
  when you right-click a spot).
*/
window.TRIP_STOPS = [
  {
    title: "VAN BUILDOUT",
    place: "Los Angeles, CA",
    lat: 34.0522,
    lng: -118.2437,
    date: "14 Nov 2026",
    url: "blog/van-buildout.html",
    cover: "blog/images/van-buildout-cover.jpg",
    start: true
  }
];
