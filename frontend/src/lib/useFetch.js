import { useCallback, useEffect, useRef, useState } from "react";

/* Dashboard, Heatmap, PatternChart and NetworkView each carried their own copy
 * of the same useState/useEffect/try/catch/finally block. This is that block,
 * once.
 *
 * `keep` holds the previous data while a refetch is in flight, so a filter
 * change dims the chart instead of flashing a skeleton and jumping the layout.
 */
export function useFetch(fn, deps = [], { keep = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  // Ref so a slow response from a stale dependency set can't overwrite a fresh one.
  const latest = useRef(0);
  const refetch = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const ticket = ++latest.current;
    let cancelled = false;

    setLoading(true);
    if (!keep) setData(null);

    fn()
      .then((result) => {
        if (cancelled || ticket !== latest.current) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (cancelled || ticket !== latest.current) return;
        setError(err);
      })
      .finally(() => {
        if (!cancelled && ticket === latest.current) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, loading, refetch, stale: loading && data != null };
}
