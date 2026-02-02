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
  },

  // New localhost ticketing site (issue-GB)
  localhost: {
    selectors: {
      // Queue page
      queuePosition: ['#queue-position'],
      queueTotal: ['#queue-total'],
      
      // Section selection page
      sectionMap: ['#section-map'],
      gradeCards: ['.card'],
      nextButton: ['#next-btn', '.btn-primary'],
      
      // Seat selection page
      seats: ['.seat.available'],
      selectedSeats: ['.seat.selected'],
      takenSeats: ['.seat.taken'],
      seatGrid: ['#seat-grid'],
      confirmButton: ['#next-btn'],
      
      // CAPTCHA (appears on seat_select.html)
      captchaOverlay: ['#captcha-overlay'],
      captchaCanvas: ['canvas#captcha-canvas', '#captcha-canvas'],
      captchaInput: ['input#captcha-input', '#captcha-input'],
      captchaSubmit: ['button#captcha-submit-btn', '#captcha-submit-btn'],
      
      // Common elements
      popup: ['.modal', '.overlay'],
      popupClose: ['.close', '.btn-close'],
      loading: ['.spinner', '.loading'],
    },
    
    timing: {
      clickDelay: 80,
      pageLoadTimeout: 8000,
      elementTimeout: 4000,
      popupTimeout: 2500,
      seatSelectDelay: 120,
      retryDelay: 600,
      queueCheckInterval: 1000, // Check queue status every 1s
    },
    
    retry: {
      maxAttempts: {
        clickStart: 4,
        selectZone: 3,
        selectSeat: 8,
        confirm: 3,
        solveCaptcha: 5,
      },
      backoffMultiplier: 1.5,
    },
    
    seatPreferences: {
      preferCenter: true,
      minSeatsDistance: 0,
      maxSeatsDistance: 2,
      grades: ['VIP', 'R', 'S', 'A'], // Preferred grades in order
    },
    
    captcha: {
      selectors: ['#captcha-overlay'],
      input: ['#captcha-input'],
      button: ['#captcha-submit-btn'],
      canvas: ['#captcha-canvas'],
      solverEndpoint: 'http://localhost:5000/api/solve_captcha',
    },
    
    features: {
      autoRefresh: false,
      handlePopups: true,
      solveCaptcha: true,  // Enable CAPTCHA solving
      multiSeatSelect: true,
      handleQueue: true,   // Handle queue/waiting room
    }
  }
};

/**
 * Get site config by hostname
 */
function getSiteConfig(hostname = window.location.hostname) {
  // Use localhost config for localhost/127.0.0.1
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return SiteConfig.localhost;
  }
  
  // Default to mocktest for all other sites
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
