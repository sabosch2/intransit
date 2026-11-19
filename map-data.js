/*
  map-data.js - the stops on the Map page, in trip order.
  The dotted route is drawn through every stop from top to bottom.

  A post: title, place, lat, lng, date, url and cover (start: true for the
  first one, which gets the star). Clicking its pin opens a card for the post.

  A place we only stayed (no post of its own): just place, lat, lng, date and
  stay: true. It shows as a small grey dot with no card, e.g.
    { place: "Gooseberry, UT", lat: 38.79, lng: -111.69, date: "15 Nov 2026", stay: true },

  Coordinates are latitude, longitude (right-click a spot in Google Maps).
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
  },
  {
    title: "WE’RE MARRIED!",
    place: "San Diego, CA",
    lat: 32.7157,
    lng: -117.1611,
    date: "19 Nov 2026",
    url: "blog/were-married.html",
    cover: "blog/images/were-married-cover.jpg"
  }
];
