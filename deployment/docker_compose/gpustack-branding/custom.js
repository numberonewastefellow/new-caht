/**
 * VirtualAI Model Hub — GPUStack Branding Override
 * Replaces GPUStack branding with VirtualAI branding via DOM manipulation.
 */
(function () {
  "use strict";

  var BRAND_NAME = "VirtualAI Model Hub";
  var BRAND_SHORT = "VirtualAI";
  var ORIGINAL_NAME = "GPUStack";

  /**
   * Replace page title
   */
  function updateTitle() {
    if (document.title.indexOf(ORIGINAL_NAME) !== -1) {
      document.title = document.title.replace(ORIGINAL_NAME, BRAND_SHORT);
    } else if (document.title === "" || document.title === ORIGINAL_NAME) {
      document.title = BRAND_NAME;
    }
  }

  /**
   * Replace text content in the sidebar logo area and anywhere GPUStack appears
   */
  function replaceBranding() {
    // Replace logo text in sidebar
    var logoElements = document.querySelectorAll(
      '[class*="logo"] span, [class*="logo"] a, [class*="brand"] span'
    );
    logoElements.forEach(function (el) {
      if (el.textContent.trim() === ORIGINAL_NAME) {
        el.textContent = BRAND_SHORT;
        el.style.background =
          "linear-gradient(135deg, #6366f1, #818cf8, #a5b4fc)";
        el.style.webkitBackgroundClip = "text";
        el.style.webkitTextFillColor = "transparent";
        el.style.backgroundClip = "text";
        el.style.fontWeight = "700";
        el.style.fontSize = "18px";
        el.style.letterSpacing = "-0.02em";
      }
    });

    // Walk all text nodes and replace GPUStack occurrences in headings
    var headings = document.querySelectorAll("h1, h2, h3, .ant-page-header-heading-title");
    headings.forEach(function (el) {
      if (el.textContent.indexOf(ORIGINAL_NAME) !== -1) {
        el.textContent = el.textContent.replace(
          new RegExp(ORIGINAL_NAME, "g"),
          BRAND_SHORT
        );
      }
    });

    updateTitle();
  }

  // Run on initial load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", replaceBranding);
  } else {
    replaceBranding();
  }

  // Watch for SPA navigation and dynamic content changes
  var observer = new MutationObserver(function (mutations) {
    var shouldUpdate = false;
    for (var i = 0; i < mutations.length; i++) {
      var m = mutations[i];
      if (m.type === "childList" && m.addedNodes.length > 0) {
        shouldUpdate = true;
        break;
      }
      if (
        m.type === "characterData" &&
        m.target.textContent &&
        m.target.textContent.indexOf(ORIGINAL_NAME) !== -1
      ) {
        shouldUpdate = true;
        break;
      }
    }
    if (shouldUpdate) {
      replaceBranding();
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  // Also watch for title changes
  var titleObserver = new MutationObserver(updateTitle);
  var titleEl = document.querySelector("title");
  if (titleEl) {
    titleObserver.observe(titleEl, { childList: true, characterData: true });
  }
})();
