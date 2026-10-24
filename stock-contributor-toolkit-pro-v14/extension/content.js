/* StockMeta Helper - content script.
   Fills title / description / keyword fields on contributor upload pages.
   Uses defensive multi-selector matching since portal markup changes often. */
chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action !== "fill") return;
  const { title, desc, kws } = req.data || {};
  let filled = 0;

  const setNative = (el, value) => {
    if (!el || !value) return false;
    const proto = el.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  };

  const first = (sels) => {
    for (const s of sels) {
      const el = document.querySelector(s);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  };

  // --- title ---
  const titleEl = first([
    'input[data-testid="title-input"]', 'textarea[data-testid="title-input"]',
    'input[name="title"]', 'textarea[name="title"]',
    'input[placeholder*="title" i]', 'textarea[placeholder*="title" i]',
    '#title', '.title-input input', '.title-input textarea',
  ]);
  if (setNative(titleEl, title)) filled++;

  // --- description ---
  const descEl = first([
    'textarea[data-testid="description-input"]', 'textarea[name="description"]',
    'textarea[placeholder*="description" i]', '#description',
  ]);
  if (setNative(descEl, desc)) filled++;

  // --- keywords (comma-separated paste into tag inputs) ---
  const kwEl = first([
    'input[data-testid="keywords-input"]', 'textarea[data-testid="keywords-input"]',
    'input[name="keywords"]', 'textarea[name="keywords"]',
    'input[placeholder*="keyword" i]', 'textarea[placeholder*="keyword" i]',
    '#keywords', '.keywords-input input',
  ]);
  if (kwEl && kws) {
    // many portals accept comma-separated paste into a tag box
    kwEl.focus();
    if (setNative(kwEl, kws)) {
      kwEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      filled++;
    }
  }

  sendResponse({ ok: filled > 0, filled });
  return true;
});
