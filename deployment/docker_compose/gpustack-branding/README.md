# VirtualAI Model Hub — GPUStack Branding Guide

## How It Works

GPUStack runs unmodified. An nginx reverse proxy sits in front and injects `custom.css` + `custom.js` into every HTML response using `sub_filter`. This lets you rebrand without forking GPUStack source.

```
Browser  -->  nginx proxy (:9090)  -->  GPUStack (:9080)
                 |
                 +-- injects /custom/custom.css
                 +-- injects /custom/custom.js
```

## File Overview

| File | Purpose |
|---|---|
| `nginx-gpustack.conf` | Reverse proxy config with CSS/JS injection |
| `custom.css` | Color and layout overrides |
| `custom.js` | Logo text, page title, and dynamic DOM replacements |

## How to Customize

### Change Brand Name

Edit `custom.js` — update these variables at the top:

```js
var BRAND_NAME = "VirtualAI Model Hub";  // full name (page title)
var BRAND_SHORT = "VirtualAI";           // sidebar logo text
var ORIGINAL_NAME = "GPUStack";          // what to find/replace
```

### Change Accent Colors

Edit `custom.css` — the main accent color is `#6366f1` (indigo). Replace all occurrences:

```css
/* Primary accent */
#6366f1  -->  your color

/* Hover / lighter accent */
#818cf8  -->  your lighter shade

/* Subtle / link hover */
#a5b4fc  -->  your lightest shade

/* Dark background */
#0f1219  -->  your sidebar background
```

### Add a Custom Logo Image

Edit `custom.js` — add to the `replaceBranding()` function:

```js
var logoWrap = document.querySelector('[class*="logo"]');
if (logoWrap && !logoWrap.querySelector('.custom-logo')) {
    var img = document.createElement('img');
    img.src = '/custom/logo.png';
    img.className = 'custom-logo';
    img.style.height = '28px';
    img.style.marginRight = '8px';
    logoWrap.prepend(img);
}
```

Then place your `logo.png` in this directory and add a volume mount in `docker-compose.gpustack.yml`:

```yaml
volumes:
  - ./gpustack-branding/logo.png:/usr/share/nginx/branding/logo.png:ro
```

### Change the Favicon

Place your `favicon.png` in this directory, then add to `nginx-gpustack.conf` inside the `location /` block:

```nginx
sub_filter 'href="/static/favicon.png"' 'href="/custom/favicon.png"';
```

And add the volume mount like the logo above.

### Hide Specific UI Elements

Add to `custom.css`:

```css
/* Hide the version number in sidebar */
[class*="version"] { display: none !important; }

/* Hide a specific menu item (e.g., "Audio") */
.ant-menu-item:has(span:contains("Audio")) { display: none !important; }
```

### Custom Login Page Text

Add to `custom.js` in `replaceBranding()`:

```js
var loginTitle = document.querySelector('[class*="login"] h1, .login-title');
if (loginTitle) {
    loginTitle.textContent = 'VirtualAI Model Hub';
}
```

## Apply Changes

After editing any file, restart the proxy:

```bash
docker restart gpustack-proxy
```

No need to restart GPUStack itself.

## Debugging

- **Direct GPUStack UI** (no branding): http://localhost:9080
- **Branded UI** (through proxy): http://localhost:9090
- **Check CSS is loaded**: Open browser DevTools > Network tab, look for `/custom/custom.css`
- **Check JS is loaded**: DevTools > Console, look for errors from `custom.js`
- **Inspect injected HTML**: `curl -s http://localhost:9090 | head -20` — should show `custom.css` and `custom.js` links

## Architecture Notes

- GPUStack is Apache 2.0 licensed — rebranding is permitted
- The proxy approach means GPUStack can be upgraded independently (`docker pull gpustack/gpustack:latest-cpu`)
- All branding is external — no GPUStack files are modified
- WebSocket connections (for streaming) are proxied correctly
