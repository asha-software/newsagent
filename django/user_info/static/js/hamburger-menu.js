document.addEventListener('DOMContentLoaded', function() {
  const hamburgerIcon = document.querySelector('.hamburger-icon');
  const menuItems = document.querySelector('.menu-items');
  const menuOverlay = document.querySelector('.menu-overlay');
  const menuCloseBtn = document.querySelector('.menu-close-btn');

  // Function to close the menu
  function closeMenu() {
    hamburgerIcon.classList.remove('active');
    menuItems.classList.remove('active');
    menuOverlay.classList.remove('active');
  }

  // Toggle menu when hamburger icon is clicked
  hamburgerIcon.addEventListener('click', function() {
    hamburgerIcon.classList.toggle('active');
    menuItems.classList.toggle('active');
    menuOverlay.classList.toggle('active');
  });

  // Close menu when clicking outside
  menuOverlay.addEventListener('click', closeMenu);

  // Close menu when clicking the close button
  if (menuCloseBtn) {
    menuCloseBtn.addEventListener('click', closeMenu);
  }

  // Close menu when pressing escape key
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      closeMenu();
    }
  });
});
