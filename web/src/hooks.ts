import { useCallback, useEffect, useState } from "react";
import { api, type TokenSource } from "./api";
import { useAuth } from "./auth";

/** Loads JSON from the API; `reload` refetches. */
export function useApi<T>(path: string | null, authenticated = true) {
  const { accessToken } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setError(null);
    api<T>(path, authenticated ? accessToken : null).then(
      (d) => live && setData(d),
      (e) => live && setError(e),
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, authenticated]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, reload };
}

export function useTokenSource(): TokenSource {
  return useAuth().accessToken;
}
