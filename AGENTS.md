# AGENTS.md - AI Agent Guidelines for FairTicket Project

## Project Overview

FairTicket is an AI-based ticket booking system designed to detect and prevent macro/bot abuse.
The project consists of:
- **Main App**: FastAPI backend + vanilla HTML/CSS/JS frontend (ticket booking demo)
- **Swords**: Chrome extension + Python automation tools for testing/validation

## Build & Run Commands

### Main Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start development server (port 5000)
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# Or use the batch file (Windows)
server.bat
```

### Swords (Automation Tools)
```bash
# Install swords dependencies
pip install -r swords/requirements.txt

# Start CAPTCHA API server
python swords/captcha_api_server.py
```

### No Test Framework Configured
This project does not have a formal test setup. Manual testing via browser is the primary method.

## Project Structure

```
/                       # Root
  main.py               # FastAPI server (auth, logging, static files)
  requirements.txt      # Python dependencies
  server.bat            # Windows startup script
  
/html/                  # Frontend pages
  index.html            # Performance listing
  login.html, signup.html
  performance_detail.html, queue.html
  seat_select.html, section_select.html
  discount.html, order_info.html
  payment.html, booking_complete.html
  viewer*.html          # Admin/analytics views

/js/                    # Frontend JavaScript modules
  auth.js               # Authentication (login/signup/session)
  utils.js              # Utility functions (UUID, formatting, navigation)
  logger.js             # Booking flow logging, mouse tracking
  flow-manager.js       # Booking state management
  browser-info.js       # Device/browser detection

/css/                   # Stylesheets
  main.css              # Base styles, CSS variables, layout
  components.css        # Reusable component styles

/data/                  # JSON data files
  performances.json     # Performance catalog
  users.json            # User database (dev only)

/logs/                  # Booking flow logs (JSON)

/swords/                # Automation tools subproject
  chrome-extension/     # Chrome extension for ticket automation
  modules/              # Python modules (VLM, popup handling)
  captcha_api_server.py # CAPTCHA solving API
```

## Code Style Guidelines

### Python (Backend)

**Imports**: Standard library first, then third-party, then local
```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
```

**Naming**:
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

**Type Hints**: Use Pydantic models for request/response validation
```python
class SignupData(BaseModel):
    email: str
    password: str
    name: str
    phone: str
```

**Error Handling**: Use HTTPException with Korean error messages
```python
raise HTTPException(status_code=400, detail="Korean error message here")
```

**Comments**: Korean comments are acceptable and common in this codebase

### JavaScript (Frontend)

**No build step**: Vanilla ES6+ JavaScript, loaded via script tags
**No modules**: Functions are global, use `function` declarations

**Naming**:
- Variables/functions: `camelCase`
- Constants: `UPPER_SNAKE_CASE`

**Patterns**:
```javascript
// Function declarations
function doSomething() { }

// Async/await for API calls
async function fetchData() {
    try {
        const response = await fetch('/api/endpoint');
        const data = await response.json();
    } catch (error) {
        console.error('Error:', error);
    }
}
```

**DOM Manipulation**: Use vanilla DOM APIs
```javascript
document.getElementById('element-id')
document.querySelector('.class-name')
element.innerHTML = `template string`
```

**Session Storage**: Used for state between pages
```javascript
sessionStorage.setItem('bookingFlow', JSON.stringify(data));
const data = JSON.parse(sessionStorage.getItem('bookingFlow'));
```

### CSS

**CSS Variables**: Defined in `:root` in main.css
```css
:root {
  --primary-color: #FF3D7F;
  --spacing-md: 16px;
}
```

**Naming**: BEM-like but simpler
- `.component-name`
- `.component-name-element`
- `.modifier-class`

## API Endpoints

```
GET  /                  # Redirect to /html/index.html
POST /api/auth/signup   # User registration
POST /api/auth/login    # User login
POST /api/logs          # Save booking flow log
GET  /api/logs          # List all log files
GET  /api/logs/{file}   # Get specific log file
```

## Key Patterns to Follow

### Logging System (logger.js)
When tracking user behavior, use this pattern:
```javascript
logStageEntry('stage_name');
// ... user actions ...
logStageExit('stage_name', { additionalData });
```

### Flow Management (flow-manager.js)
```javascript
initFlow(performanceData);
updateFlowData({ selectedSeats: [...] });
const flowData = getFlowData();
```

### Booking Flow Steps
1. performance (index.html)
2. performance_detail
3. queue
4. seat_select
5. discount
6. order_info
7. payment
8. complete

## Git Workflow

**Branch naming**: `issue-{number}` or descriptive names
**PR Template**: Use template in `.github/ISSUE_TEMPLATE/pull_request_template.md`
**Merge target**: `dev` branch (not main directly)

## Important Notes

1. **No TypeScript**: Pure JavaScript, no type checking
2. **No linting**: No ESLint/Prettier configured
3. **No test framework**: Manual browser testing only
4. **Korean language**: UI and comments are primarily Korean
5. **Static files**: FastAPI serves all static content from root
6. **Dev passwords**: Stored in plain text (demo only, NOT for production)

## Anti-Macro Detection Data Points

The logging system captures:
- `is_trusted`: Browser's isTrusted event property (false = scripted)
- `click_duration`: Time between mousedown/mouseup (bots < 10ms)
- `mouse_trajectory`: Array of [x, y, timestamp] for movement analysis
- Response timing between page loads and user actions
