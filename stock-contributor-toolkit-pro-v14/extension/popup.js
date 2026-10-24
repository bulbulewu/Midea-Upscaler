/* StockMeta Helper - popup logic */
const $ = (id) => document.getElementById(id);
const msg = (t) => { $("msg").textContent = t; setTimeout(() => $("msg").textContent = "", 2500); };

// restore saved metadata
chrome.storage.local.get(["title", "desc", "kws"], (d) => {
  if (d.title) $("title").value = d.title;
  if (d.desc) $("desc").value = d.desc;
  if (d.kws) $("kws").value = d.kws;
});

$("save").onclick = () => {
  chrome.storage.local.set(
    { title: $("title").value.trim(), desc: $("desc").value.trim(), kws: $("kws").value.trim() },
    () => msg("Saved ✓")
  );
};

$("copy").onclick = async () => {
  const text = `Title: ${$("title").value.trim()}\nDescription: ${$("desc").value.trim()}\nKeywords: ${$("kws").value.trim()}`;
  try {
    await navigator.clipboard.writeText(text);
    msg("Copied ✓");
  } catch (e) { msg("Copy blocked by browser"); }
};

$("fill").onclick = async () => {
  const data = { title: $("title").value.trim(), desc: $("desc").value.trim(), kws: $("kws").value.trim() };
  chrome.storage.local.set(data, async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const res = await chrome.tabs.sendMessage(tab.id, { action: "fill", data });
      msg(res && res.ok ? `Filled ${res.filled} field(s) ✓` : "No matching fields found on this page");
    } catch (e) {
      msg("Open an Adobe Stock or Shutterstock upload page first");
    }
  });
};
