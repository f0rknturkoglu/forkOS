/** Sayfa navigasyonundan ONCE yayilan iptal edilebilir olay adi. */
const BEFORE_NAVIGATION_EVENT = "forkos:before-navigation";

type NavigationRequest = {
  href: string;
};

export function requestNavigation(href: string): boolean {
  return window.dispatchEvent(
    new CustomEvent<NavigationRequest>(BEFORE_NAVIGATION_EVENT, {
      detail: { href },
      cancelable: true,
    }),
  );
}
