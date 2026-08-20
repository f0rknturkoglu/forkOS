import { useEffect, useState } from "react";

export interface Route {
  path: string;
  params: URLSearchParams;
}

function read(): Route {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path: path || "/", params: new URLSearchParams(query) };
}

/** Basit hash router. TanStack Router'a gecis Faz 2'de. */
export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function navigate(path: string): void {
  location.hash = path.startsWith("#") ? path.slice(1) : path;
}
