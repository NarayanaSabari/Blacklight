# Chrome DevTools MCP Implementation Guide for Blacklight Portal

## 🎯 Overview

This guide explains how to use the Chrome DevTools MCP server to analyze, debug, and optimize the Blacklight Portal webapp during development.

## 📋 Prerequisites

- Node.js v20.19+ installed
- Chrome browser (stable version)
- Vite dev server running on `http://localhost:5173` (default)
- Chrome DevTools MCP configured in your MCP client (already done ✅)

## 🔧 MCP Server Configurations

We've configured **two Chrome DevTools MCP servers**:

### 1. **chrome-devtools** (Visual/Interactive)
```json
{
  "command": "npx",
  "args": [
    "-y",
    "chrome-devtools-mcp@latest",
    "--headless=false",
    "--viewport=1920x1080"
  ]
}
```
- **Use for:** Manual testing, UI debugging, visual inspection
- **Shows:** Actual Chrome browser window
- **Best for:** Development, debugging UI issues, watching animations

### 2. **chrome-devtools-headless** (Automated/CI)
```json
{
  "command": "npx",
  "args": [
    "-y",
    "chrome-devtools-mcp@latest",
    "--headless=true",
    "--viewport=1920x1080",
    "--isolated=true"
  ]
}
```
- **Use for:** Automated testing, performance benchmarks, CI/CD
- **Shows:** No UI (background mode)
- **Best for:** Performance testing, screenshot generation, automated checks

---

## 🚀 Common Development Workflows

### **Workflow 1: Performance Analysis**

**Goal:** Identify performance bottlenecks in your portal webapp

**Steps:**
1. Start your Vite dev server:
   ```bash
   cd ui/portal
   npm run dev
   ```

2. Ask your AI assistant:
   ```
   Check the performance of http://localhost:5173 and identify:
   - Core Web Vitals (LCP, FID, CLS)
   - JavaScript bundle sizes
   - Network waterfall issues
   - Render-blocking resources
   - Opportunities for optimization
   ```

3. The MCP server will:
   - Navigate to your local dev server
   - Record a performance trace
   - Analyze Core Web Vitals
   - Provide actionable insights

**Expected Output:**
- LCP (Largest Contentful Paint) timing
- Total Blocking Time
- Bundle size analysis
- Specific recommendations (e.g., "Defer offscreen images")

---

### **Workflow 2: Form Testing & Validation**

**Goal:** Automatically test form inputs, validation, and error states

**Prompt Examples:**

```
Navigate to http://localhost:5173/candidates/new and:
1. Fill the candidate form with test data
2. Test validation by submitting with empty required fields
3. Take screenshots of error states
4. Verify success message after valid submission
```

```
Test the login flow at http://localhost:5173/login:
1. Try invalid credentials and capture error message
2. Try valid credentials and verify redirect
3. Take screenshots at each step
```

**What it does:**
- Uses `fill_form` tool to populate inputs
- Uses `click` tool to submit forms
- Uses `list_console_messages` to check for errors
- Uses `take_screenshot` to document states
- Uses `wait_for` to ensure elements load

---

### **Workflow 3: Responsive Design Testing**

**Goal:** Test your portal across different viewport sizes

**Prompt:**
```
Test http://localhost:5173 at these breakpoints:
- Mobile: 375x667 (iPhone SE)
- Tablet: 768x1024 (iPad)
- Desktop: 1920x1080

For each:
1. Take a screenshot
2. Check for layout issues
3. Test navigation menu interaction
4. Verify all content is accessible
```

**What it does:**
- Uses `resize_page` to change viewport
- Uses `take_snapshot` for accessibility tree
- Uses `take_screenshot` for visual inspection
- Identifies responsive design issues

---

### **Workflow 4: Network Request Analysis**

**Goal:** Debug API calls, identify slow requests, check error handling

**Prompt:**
```
Navigate to http://localhost:5173/candidates and:
1. List all network requests
2. Identify requests taking >1 second
3. Check for failed requests (4xx, 5xx)
4. Analyze request/response headers
5. Check if data is being cached properly
```

**What it does:**
- Uses `list_network_requests` to get all requests
- Uses `get_network_request` to inspect specific requests
- Analyzes timing, headers, payload sizes
- Identifies caching opportunities

---

### **Workflow 5: Console Error Detection**

**Goal:** Catch JavaScript errors, warnings, and console logs

**Prompt:**
```
Navigate to http://localhost:5173 and check:
1. All console errors and warnings
2. Failed network requests logged to console
3. React warnings or deprecation notices
4. Any uncaught exceptions

Provide a summary of issues found.
```

**What it does:**
- Uses `list_console_messages` to get all console output
- Filters by type (error, warn, log)
- Provides line numbers and stack traces
- Helps identify runtime issues

---

### **Workflow 6: End-to-End User Journey Testing**

**Goal:** Test complete user flows like candidate onboarding

**Prompt:**
```
Simulate a complete candidate onboarding flow:

1. Navigate to http://localhost:5173
2. Click on "Add New Candidate"
3. Fill in the candidate form:
   - Name: "John Doe"
   - Email: "john@example.com"
   - Phone: "555-0123"
   - Skills: "React, TypeScript"
4. Upload a resume PDF
5. Click submit
6. Verify success message appears
7. Navigate back to candidates list
8. Verify "John Doe" appears in the list
9. Take screenshots at each step

Report any errors or issues encountered.
```

**What it does:**
- Complete automated user journey
- Uses multiple MCP tools in sequence
- Documents each step with screenshots
- Validates expected outcomes

---

### **Workflow 7: Accessibility Testing**

**Goal:** Ensure portal meets accessibility standards

**Prompt:**
```
Check accessibility of http://localhost:5173:
1. Take a text snapshot (accessibility tree)
2. Verify all interactive elements have proper labels
3. Check keyboard navigation (Tab order)
4. Test form inputs for aria-labels
5. Identify any missing alt text on images
6. Check color contrast issues

Provide an accessibility report with specific issues.
```

**What it does:**
- Uses `take_snapshot` with `verbose: true` for full a11y tree
- Uses `press_key` to test keyboard navigation
- Identifies missing ARIA attributes
- Helps ensure WCAG compliance

---

### **Workflow 8: Performance Regression Testing**

**Goal:** Compare performance before/after code changes

**Prompt:**
```
Performance baseline test for http://localhost:5173:

1. Record a performance trace for the homepage
2. Navigate to /candidates page and record another trace
3. Navigate to /jobs page and record another trace
4. Compare Core Web Vitals across all pages
5. Identify the slowest page
6. Provide performance scores and recommendations

Save these as baseline metrics.
```

**Use Case:**
- Run before making changes (baseline)
- Run after changes (comparison)
- AI can identify performance regressions

---

### **Workflow 9: API Error Handling Testing**

**Goal:** Test how your UI handles backend errors

**Setup:** You can use Chrome DevTools to simulate network errors

**Prompt:**
```
Navigate to http://localhost:5173/candidates and:

1. Use evaluate_script to simulate API failure:
   ```javascript
   // Override fetch to simulate 500 error
   const originalFetch = window.fetch;
   window.fetch = function(...args) {
     if (args[0].includes('/api/candidates')) {
       return Promise.resolve({
         ok: false,
         status: 500,
         json: () => Promise.resolve({ error: "Internal Server Error" })
       });
     }
     return originalFetch.apply(this, args);
   };
   ```

2. Refresh the page
3. Check console for error handling
4. Verify error message is shown to user
5. Take screenshot of error state
```

**What it does:**
- Injects JavaScript to simulate errors
- Tests error boundaries and fallbacks
- Validates user-facing error messages

---

### **Workflow 10: Multi-Tenant Testing**

**Goal:** Test portal across different tenants (relevant for Blacklight's multi-tenant architecture)

**Prompt:**
```
Test multi-tenant isolation:

1. Navigate to http://localhost:5173
2. Login as Tenant A user
3. Take screenshot of dashboard
4. Verify only Tenant A data is visible
5. Logout
6. Login as Tenant B user
7. Take screenshot of dashboard
8. Verify only Tenant B data is visible
9. Compare screenshots to ensure data isolation

Check console for any cross-tenant data leaks.
```

**What it does:**
- Automated multi-tenant testing
- Visual comparison via screenshots
- Security validation for data isolation

---

## 🎨 Portal-Specific Use Cases

### **Testing shadcn/ui Components**

Since your portal uses **shadcn/ui + Tailwind CSS**:

```
Test the shadcn/ui Button component styling:

1. Navigate to http://localhost:5173/components-demo
2. Take screenshots of:
   - Default button variant
   - Primary button variant
   - Destructive button variant
   - Ghost button variant
   - Outline button variant
3. Test hover states by hovering over each button
4. Test disabled states
5. Verify Tailwind classes are applied correctly

Report any styling issues or inconsistencies.
```

### **Testing React Query Integration**

```
Analyze data fetching with React Query:

1. Navigate to http://localhost:5173/candidates
2. Monitor network requests
3. Check console for React Query devtools output
4. Test:
   - Initial data load
   - Data refresh on focus
   - Cached data reuse
   - Loading states
   - Error states
4. Take screenshots of each state
```

### **Testing React Router Navigation**

```
Test React Router navigation flow:

1. Navigate to http://localhost:5173
2. Click on each navigation link
3. Verify URL changes correctly
4. Check browser history works (back/forward)
5. Test 404 page for invalid routes
6. Verify nested routes render correctly
```

---

## 🔍 Advanced Techniques

### **Emulating Network Conditions**

Test how your portal performs on slow connections:

```
Test portal performance on slow 3G:

1. Navigate to http://localhost:5173
2. Use emulate tool to set network to "Slow 3G"
3. Record performance trace
4. Check loading states behavior
5. Verify skeleton loaders appear
6. Test timeout handling

Compare with fast connection results.
```

### **CPU Throttling**

Test on low-powered devices:

```
Test portal on low-end device:

1. Navigate to http://localhost:5173
2. Use emulate tool with CPU throttling (4x slowdown)
3. Test interactions (form submissions, navigation)
4. Check for UI freezing or jank
5. Identify heavy JavaScript operations
```

### **Script Execution for Custom Tests**

Run custom JavaScript in the browser context:

```
Evaluate this script on http://localhost:5173:

```javascript
// Check if React is loaded
const reactVersion = window.React?.version;

// Check if all required global objects exist
const checks = {
  reactLoaded: !!window.React,
  reactVersion: reactVersion,
  reactQueryLoaded: !!window.ReactQuery,
  routerLoaded: !!window.ReactRouterDOM,
  tailwindLoaded: document.documentElement.classList.contains('tw-'),
  shadcnComponentsCount: document.querySelectorAll('[data-radix-*]').length
};

return checks;
```

Report the results.
```

---

## 📊 Performance Metrics Reference

### **Core Web Vitals Targets**

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| **LCP** (Largest Contentful Paint) | ≤2.5s | 2.5s - 4.0s | >4.0s |
| **FID** (First Input Delay) | ≤100ms | 100ms - 300ms | >300ms |
| **CLS** (Cumulative Layout Shift) | ≤0.1 | 0.1 - 0.25 | >0.25 |
| **FCP** (First Contentful Paint) | ≤1.8s | 1.8s - 3.0s | >3.0s |
| **TTI** (Time to Interactive) | ≤3.8s | 3.8s - 7.3s | >7.3s |

### **What to Monitor**

1. **Bundle Size Issues**
   - Large vendor chunks
   - Unnecessary dependencies
   - Missing code splitting

2. **Network Performance**
   - Too many sequential requests
   - Large image files
   - Missing compression

3. **JavaScript Execution**
   - Long tasks blocking main thread
   - Excessive re-renders
   - Memory leaks

4. **Render Performance**
   - Layout thrashing
   - Paint operations
   - Composite layer overhead

---

## 🛠️ Debugging Common Issues

### **Issue: MCP Server Won't Start**

**Solution:**
```bash
# Check Node.js version
node --version  # Should be v20.19+

# Check Chrome is installed
which google-chrome  # macOS: /Applications/Google Chrome.app/...

# Test npx command manually
npx -y chrome-devtools-mcp@latest --help
```

### **Issue: Can't Connect to Local Dev Server**

**Solution:**
1. Ensure Vite dev server is running: `npm run dev`
2. Check port: Default is 5173, update URL if different
3. Check firewall settings
4. Try `http://127.0.0.1:5173` instead of `localhost`

### **Issue: Browser Opens but Nothing Happens**

**Solution:**
- Be more specific in prompts (include full URL)
- Wait for AI to complete the action
- Check console output for errors
- Try `--headless=false` to see what's happening

### **Issue: Screenshots Are Blank**

**Solution:**
- Wait for page to fully load: Add `wait_for` with specific text
- Check viewport size: Some elements may be off-screen
- Verify URL is correct and page rendered

---

## 🎯 Best Practices

### **1. Always Start Dev Server First**
```bash
cd ui/portal
npm run dev
# Wait for "Local: http://localhost:5173"
# Then use Chrome DevTools MCP
```

### **2. Use Specific Prompts**
❌ **Bad:** "Test the portal"
✅ **Good:** "Navigate to http://localhost:5173/candidates, click 'Add Candidate', fill the form, and verify submission"

### **3. Wait for Elements**
Include wait conditions in prompts:
```
Navigate to http://localhost:5173/candidates and wait for "Candidates List" heading to appear
```

### **4. Take Screenshots for Verification**
Always request screenshots for visual verification:
```
Take a screenshot after each step to document the state
```

### **5. Check Console After Actions**
```
After submitting the form, check the console for any errors or warnings
```

### **6. Use Isolated Mode for Clean Tests**
Use `chrome-devtools-headless` (isolated mode) for:
- Performance benchmarks
- Automated tests
- CI/CD pipelines

Use `chrome-devtools` (persistent mode) for:
- Development with login state
- Testing with browser extensions
- Manual debugging

---

## 📝 Sample Test Suite

Here's a comprehensive test suite you can run:

```
Run this comprehensive test suite for http://localhost:5173:

**1. Performance Audit**
- Record performance trace
- Check Core Web Vitals
- Identify optimization opportunities

**2. Accessibility Check**
- Take accessibility tree snapshot
- Check keyboard navigation
- Verify ARIA labels

**3. Responsive Design**
- Test on mobile (375x667)
- Test on tablet (768x1024)
- Test on desktop (1920x1080)

**4. Network Analysis**
- List all API requests
- Check for failed requests
- Identify slow requests (>1s)

**5. Console Errors**
- Check for JavaScript errors
- Check for React warnings
- Check for network errors

**6. Form Testing**
- Test candidate form validation
- Test file upload
- Test error states

**7. Navigation Flow**
- Test all major routes
- Verify browser history
- Test 404 handling

**8. Multi-Tenant**
- Test tenant isolation
- Verify data boundaries

Generate a comprehensive report with:
- Performance score (0-100)
- List of critical issues
- List of warnings
- Optimization recommendations
- Screenshots of key pages
```

---

## 🚀 Integration with CI/CD

You can integrate Chrome DevTools MCP into your CI/CD pipeline:

**GitHub Actions Example:**
```yaml
# .github/workflows/performance-test.yml
name: Performance Testing

on: [pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: cd ui/portal && npm ci
      
      - name: Build production
        run: cd ui/portal && npm run build
      
      - name: Serve production build
        run: cd ui/portal && npx serve -s dist -l 5173 &
      
      - name: Run Chrome DevTools MCP tests
        run: |
          npx chrome-devtools-mcp@latest \
            --headless=true \
            --isolated=true \
            < performance-test-script.js
```

---

## 📚 Additional Resources

- **MCP Tool Reference:** https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md
- **Troubleshooting Guide:** https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/troubleshooting.md
- **Chrome DevTools Documentation:** https://developer.chrome.com/docs/devtools/
- **Puppeteer API:** https://pptr.dev/

---

## 🎉 Quick Start Checklist

- [ ] Vite dev server running (`npm run dev`)
- [ ] Chrome browser installed
- [ ] MCP server configured in mcp.json ✅
- [ ] Test with simple prompt: "Navigate to http://localhost:5173 and take a screenshot"
- [ ] Start with performance analysis
- [ ] Move to form testing
- [ ] Add automated tests to CI/CD

---

## 💡 Pro Tips

1. **Combine Multiple Tools:** Ask AI to perform complex workflows using multiple tools in sequence
2. **Use Verbose Snapshots:** For debugging layout issues, use `take_snapshot` with `verbose: true`
3. **Test Production Builds:** Build your app (`npm run build`) and test the production bundle for accurate performance metrics
4. **Baseline First:** Always establish performance baselines before optimization
5. **Document Issues:** Have AI generate detailed reports with screenshots for team collaboration

---

**Need Help?** Ask your AI assistant specific questions about any workflow above!
