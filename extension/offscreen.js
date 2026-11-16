// Only parses bounded text supplied by the worker. Never inserts feed markup into the DOM.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "PARSE_RSS_INTERNAL" || sender.id !== chrome.runtime.id)
    return;
  try {
    const doc = new DOMParser().parseFromString(
      message.text,
      "application/xml",
    );
    if (
      doc.querySelector("parsererror") ||
      doc.documentElement.localName !== "rss" ||
      !doc.querySelector("channel")
    )
      throw new Error("Invalid RSS.");
    const text = (node, selector) =>
      node.querySelector(selector)?.textContent?.trim() || null;
    const nodes = doc.querySelectorAll("channel > item");
    const items = [...nodes]
      .map((node) => ({
        id: text(node, "guid") || text(node, "link"),
        url: text(node, "link"),
        title: text(node, "title"),
        summary: text(node, "description"),
        published_at: text(node, "pubDate"),
        updated_at: null,
      }))
      .sort(
        (a, b) =>
          (Date.parse(b.published_at) || 0) - (Date.parse(a.published_at) || 0),
      )
      .slice(0, 200);
    sendResponse({ ok: true, items, items_available: nodes.length });
  } catch {
    sendResponse({ ok: false, error: "Invalid feed response." });
  }
});
