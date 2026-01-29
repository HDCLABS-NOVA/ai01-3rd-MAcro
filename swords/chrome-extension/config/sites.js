/**
 * Site-Specific Configuration
 */

const SiteConfig = {
  interpark: {
    // Selectors for various elements
    selectors: {
      // Reservation button
      reserveButton: [
        '#ProductForm .btn_Booking',
        '.book-now',
        'a[href*="Book"]',
        'button:contains("예매")'
      ],

      // Popups and modals
      popup: [
        '.popupContainer',
        '.modal-overlay',
        '#layerPopup',
        '[class*="popup"]'
      ],
      
      popupClose: [
        '.closeButton',
        '.btn_Close',
        '[class*="close"]',
        'button:contains("닫기")'
      ],

      // Zone selection
      zones: [
        '.area-list .zone',
        '[data-zone-id]',
        '.seat-zone'
      ],

      // Seat selection
      seats: [
        '.seat:not(.sold):not(.disabled)',
        '[data-seat-status="available"]',
        '.seat.available'
      ],
      soldSeats: [
        '.seat.sold',
        '[data-seat-status="sold"]'
      ],

      // Confirmation button
      confirmButton: [
        '#btnConfirm',
        '.btn-confirm',
        '.complete-button',
        'button[class*="complete"]'
      ],

      // Loading indicators
      loading: [
        '.loading',
        '.spinner',
        '[class*="load"]'
      ]
    },

    // Timing configurations (milliseconds)
    timing: {
      clickDelay: 50,           // Delay between clicks
      pageLoadTimeout: 10000,   // Max wait for page load
      elementTimeout: 5000,     // Max wait for element
      popupTimeout: 3000,       // Max wait for popup
      seatSelectDelay: 100,     // Delay between seat selections
      retryDelay: 500,          // Delay before retry
    },

    // Retry strategies
    retry: {
      maxAttempts: {
        clickStart: 5,
        selectZone: 3,
        selectSeat: 10,
        confirm: 3,
      },
      backoffMultiplier: 1.5,  // Exponential backoff
    },

    // Seat selection preferences
    seatPreferences: {
      preferCenter: true,
      minSeatsDistance: 0,     // Min distance between selected seats
      maxSeatsDistance: 3,     // Max distance (for consecutive seats)
      zones: ['VIP', 'R', 'S'], // Preferred zones in order
    },

    // CAPTCHA detection
    captcha: {
      selectors: [
        '#captcha',
        '.captcha-container',
        'iframe[src*="captcha"]'
      ],
      solverEndpoint: 'http://localhost:8000/solve_captcha',
    },

    // Feature flags
    features: {
      autoRefresh: true,
      handlePopups: true,
      solveCaptcha: true,
      multiSeatSelect: true,
    }
  },

  // Add other sites here (yes24, ticketlink, etc.)
  yes24: {
    // Similar structure
  },

  // Mock test site (also used for localhost)
  mocktest: {
    selectors: {
      reserveButton: ['#btnReserve', '#btnConfirm', '.btn-confirm', '.reserve-btn'],
      popup: ['.popup', '#popup'],
      popupClose: ['.popup button', 'button[onclick*="closePopup"]'],
      zones: ['.zone', '.section-box'],
      seats: ['.seat:not(.sold)'],
      soldSeats: ['.seat.sold'],
      confirmButton: ['#btnConfirm'],
      // Next button for zone selection
      nextButton: ['#btnNext', '.btn-next'],
      loading: ['.loading'],
    },
    timing: {
      clickDelay: 100,
      pageLoadTimeout: 5000,
      elementTimeout: 3000,
      popupTimeout: 2000,
      seatSelectDelay: 150,
      retryDelay: 500,
    },
    retry: {
      maxAttempts: {
        clickStart: 3,
        selectZone: 2,
        selectSeat: 5,
        confirm: 3,
      },
      backoffMultiplier: 1.5,
    },
    seatPreferences: {
      preferCenter: true,
      minSeatsDistance: 0,
      maxSeatsDistance: 3,
      zones: ['VIP', 'R', 'S'],
    },
    captcha: {
      selectors: [
        '#captcha',
        '.captcha-container',
        '.captcha-wrap',
        '#captcha_layer'
      ],
      input: [
        'input[placeholder="문자 입력"]',
        '#captchaConfig',
        'input[name="captcha"]'
      ],
      button: [
        '#btnCaptcha',
        '.btn_confirm'
      ],
      solverEndpoint: 'http://localhost:8000/solve_captcha',
    },
    features: {
      autoRefresh: false, // Don't refresh test page
      handlePopups: true,
      solveCaptcha: false,
      multiSeatSelect: true,
    }
  }
};

/**
 * Get site config by hostname
 * Simplified to always use mocktest configuration
 */
function getSiteConfig(hostname = window.location.hostname) {
  // Always use mocktest config for all sites
  return SiteConfig.mocktest;
}

/**
 * Smart selector - tries multiple selectors in order
 */
function smartSelect(selectorArray, context = document) {
  for (const selector of selectorArray) {
    const element = context.querySelector(selector);
    if (element) return element;
  }
  return null;
}

/**
 * Smart select all - returns first successful selector
 */
function smartSelectAll(selectorArray, context = document) {
  for (const selector of selectorArray) {
    const elements = context.querySelectorAll(selector);
    if (elements.length > 0) return Array.from(elements);
  }
  return [];
}

// Export
if (typeof window !== 'undefined') {
  window.SiteConfig = SiteConfig;
  window.getSiteConfig = getSiteConfig;
  window.smartSelect = smartSelect;
  window.smartSelectAll = smartSelectAll;
}
