import { useEffect, useState } from "react";

export interface Route {
  path: string;
  params: URLSearchParams;
}

function safelyDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/** Exact segment matcher with named `:param` support for the small hash router. */
export function matchRoutePath(pattern: string, path: string): URLSearchParams | null {
  const patternSegments = pattern.split("/");
  const pathSegments = path.split("/");
  if (patternSegments.length !== pathSegments.length) return null;

  const params = new URLSearchParams();
  for (let index = 0; index < patternSegments.length; index += 1) {
    const expected = patternSegments[index];
    const actual = pathSegments[index];
    if (expected.startsWith(":")) {
      if (!actual) return null;
      params.set(expected.slice(1), safelyDecode(actual));
    } else if (expected !== actual) {
      return null;
    }
  }
  return params;
}

function read(pattern?: string): Route {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  const resolvedPath = path || "/";
  const params = new URLSearchParams(query);
  if (pattern) {
    for (const [key, value] of matchRoutePath(pattern, resolvedPath) ?? []) {
      params.set(key, value);
    }
  }
  return { path: resolvedPath, params };
}

/** Basit hash router. TanStack Router'a gecis Faz 2'de. */
export function useHashRoute(pattern?: string): Route {
  const [route, setRoute] = useState<Route>(() => read(pattern));
  useEffect(() => {
    const onChange = () => setRoute(read(pattern));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, [pattern]);
  return route;
}

export function navigate(path: string): void {
  location.hash = path.startsWith("#") ? path.slice(1) : path;
}
