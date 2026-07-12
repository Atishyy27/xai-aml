import { useCallback, useEffect, useRef, useState } from "react";

/* Dashboard, Heatmap, PatternChart and NetworkView each carried their own copy
 * of the same useState/useEffect/try/catch/finally block. This is that block,
 * once.
 *
 * `keep` holds the previous data while a refetch is in flight, so a filter
 * change dims the chart instead of flashing a skeleton and jumping the layout.
 */
// A request still in flight after this long is almost certainly waiting on the
// free instance to wake from sleep (~50s), not on the network. Callers use
// `slow` to say so, instead of showing a spinner that looks like a hang.
const SLOW_AFTER_MS = 6000;

export function useFetch(fn, deps = [], { keep = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [slow, setSlow] = useState(false);
  const [nonce, setNonce] = useState(0);

  // Ref so a slow response from a stale dependency set can't overwrite a fresh one.
  const latest = useRef(0);
  const refetch = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const ticket = ++latest.current;
    let cancelled = false;

    setLoading(true);
    setSlow(false);
    if (!keep) setData(null);

    const slowTimer = setTimeout(() => {
      if (!cancelled && ticket === latest.current) setSlow(true);
    }, SLOW_AFTER_MS);

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
        if (!cancelled && ticket === latest.current) {
          setLoading(false);
          setSlow(false);
        }
      });

    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, loading, slow, refetch, stale: loading && data != null };
}
