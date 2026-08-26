import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "../services/api";

interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Small fetch-state hook for GET endpoints (stale-response safe). */
export function useApi<T>(path: string | null) {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    error: null,
    loading: path !== null,
  });
  const mounted = useRef(true);
  const requestSeq = useRef(0);

  const load = useCallback(async () => {
    if (!path) return;
    const seq = ++requestSeq.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await apiGet<T>(path);
      // Ignore out-of-order responses from superseded requests.
      if (mounted.current && seq === requestSeq.current) {
        setState({ data, error: null, loading: false });
      }
    } catch (err) {
      if (mounted.current && seq === requestSeq.current) {
        setState({
          data: null,
          error: err instanceof Error ? err.message : "Unknown error",
          loading: false,
        });
      }
    }
  }, [path]);

  useEffect(() => {
    mounted.current = true;
    void load();
    return () => {
      mounted.current = false;
    };
  }, [load]);

  return { ...state, reload: load };
}
