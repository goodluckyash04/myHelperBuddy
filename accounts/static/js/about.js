/**
 * About Page JavaScript
 * Handles smooth scrolling and animations
 */

document.addEventListener('DOMContentLoaded', function () {
  // Smooth scroll for quick navigation
  const quickNavItems = document.querySelectorAll('.quick-nav-item');

  quickNavItems.forEach(item => {
    item.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      const targetSection = document.querySelector(targetId);

      if (targetSection) {
        // Remove active class from all items
        quickNavItems.forEach(nav => nav.classList.remove('active'));

        // Add active class to clicked item
        this.classList.add('active');

        // Smooth scroll to section
        targetSection.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Highlight active quick nav on scroll
  const sections = document.querySelectorAll('.feature-section');

  function highlightNav() {
    let scrollPos = window.scrollY + 100;

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      const sectionId = section.getAttribute('id');

      if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {
        quickNavItems.forEach(item => {
          item.classList.remove('active');
          if (item.getAttribute('href') === '#' + sectionId) {
            item.classList.add('active');
          }
        });
      }
    });
  }

  window.addEventListener('scroll', highlightNav);

  // Fade in feature cards on scroll
  const featureCards = document.querySelectorAll('.advanced-feature-card, .automation-card');

  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const cardObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '0';
        entry.target.style.transform = 'translateY(20px)';

        setTimeout(() => {
          entry.target.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, 100);

        cardObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  featureCards.forEach(card => {
    cardObserver.observe(card);
  });
});
