document.addEventListener('DOMContentLoaded', function () {
  const titles = document.querySelectorAll('.slider-title');
  const detailBox = document.querySelector('.slider-detail');

  titles.forEach(title => {
    title.addEventListener('mouseenter', () => {
      // Remove active from all
      titles.forEach(t => t.classList.remove('active'));

      // Add active to hovered
      title.classList.add('active');

      // Update detail text
      detailBox.textContent = title.getAttribute('data-detail');
    });
  });

  // Optional: reset detail on mouse leave of slider-titles container
  const titlesContainer = document.querySelector('.slider-titles');
  titlesContainer.addEventListener('mouseleave', () => {
    const active = document.querySelector('.slider-title.active');
    if (active) {
      detailBox.textContent = active.getAttribute('data-detail');
    } else {
      detailBox.textContent = '';
    }
  });
});
