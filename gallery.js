/*
  gallery.js - swipeable photo groups for In Transit posts.
  Each <figure class="gallery"> holds a .gallery-track of .gallery-slide figures.
  Swipe on phones, arrows or keyboard on desktop.
*/
document.querySelectorAll('.gallery').forEach(function (gallery) {
  var track = gallery.querySelector('.gallery-track');
  var slides = track.querySelectorAll('.gallery-slide');
  var total = slides.length;

  if (total < 2) {
    gallery.classList.add('gallery--single');
    return;
  }

  var prev = document.createElement('button');
  prev.className = 'gallery-btn gallery-prev';
  prev.setAttribute('aria-label', 'Previous photo');
  prev.innerHTML = '&#8592;';

  var next = document.createElement('button');
  next.className = 'gallery-btn gallery-next';
  next.setAttribute('aria-label', 'Next photo');
  next.innerHTML = '&#8594;';

  var count = document.createElement('div');
  count.className = 'gallery-count';

  var dots = document.createElement('div');
  dots.className = 'gallery-dots';
  for (var i = 0; i < total; i++) dots.appendChild(document.createElement('span'));

  gallery.append(prev, next, count, dots);
  gallery.setAttribute('tabindex', '0');

  function current() {
    return Math.round(track.scrollLeft / track.clientWidth);
  }

  function goTo(i) {
    i = Math.max(0, Math.min(total - 1, i));
    track.scrollTo({ left: i * track.clientWidth });
  }

  function update() {
    var i = current();
    count.textContent = (i + 1) + ' / ' + total;
    prev.disabled = i === 0;
    next.disabled = i === total - 1;
    dots.querySelectorAll('span').forEach(function (d, j) {
      d.classList.toggle('is-active', j === i);
    });
  }

  prev.addEventListener('click', function () { goTo(current() - 1); });
  next.addEventListener('click', function () { goTo(current() + 1); });
  gallery.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { goTo(current() - 1); e.preventDefault(); }
    if (e.key === 'ArrowRight') { goTo(current() + 1); e.preventDefault(); }
  });

  var ticking = false;
  track.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { update(); ticking = false; });
  });
  window.addEventListener('resize', update);
  update();
});
