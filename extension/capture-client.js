/** Only the service worker mutates capture storage. Popup lifetime cannot cancel delivery. */
function call(action, ...args) {
  return chrome.runtime
    .sendMessage({ type: "forkos.capture", action, args })
    .then((reply) => {
      if (!reply?.ok)
        throw new Error(
          reply?.error ?? "Yakalama servisine ulaşılamadı; kuyruğu kontrol et.",
        );
      return reply.result;
    });
}
export const enqueue = (item) => call("enqueue", item);
export const enqueueTodo = (item) => enqueue({ ...item, type: "todo" });
export const enqueueNote = (item) => enqueue({ ...item, type: "note" });
export const enqueueOpportunity = (item) =>
  enqueue({ ...item, type: "opportunity" });
export const retryFailed = () => call("retryFailed");
export const clearFailed = (confirmed) => call("clearFailed", confirmed);
export const replaceFailed = (id, payload) =>
  call("replaceFailed", id, payload);
