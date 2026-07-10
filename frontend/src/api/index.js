import axios from "axios";

const DEV_API = "http://127.0.0.1:8000";
const baseURL = import.meta.env.VITE_API_URL ?? DEV_API;

// A production bundle that falls back to localhost points every visitor's
// browser at their own machine, and the only symptom is that all six panels
// render an error state at once. Say so at build/boot time instead.
if (import.meta.env.PROD && !import.meta.env.VITE_API_URL) {
  console.error(
    "[SENTINEL] VITE_API_URL is unset in a production build; API calls will " +
      `go to ${DEV_API} and fail. Set it in the Vercel project's environment variables.`
  );
}

const apiClient = axios.create({
  // The Space sleeps on the free tier; a cold start pays the ~25s model warmup
  // on top of container boot, which overruns a 30s timeout.
  baseURL,
  timeout: 60000,
});

const get = async (url, params) => (await apiClient.get(url, { params })).data;

export const getSummary = () => get("/statistics/summary");
export const getModelCard = () => get("/model-card");
export const getSuspiciousNetworks = (limit = 50) => get("/suspicious-networks", { limit });
export const getPatternStatistics = () => get("/statistics/patterns");
export const getHeatmapData = () => get("/statistics/heatmap");

export const getNetworkGraph = (accountId, hops = 1) => get(`/network/${accountId}`, { hops });
export const getAccountExplanation = (accountId) => get(`/account/${accountId}/explanation`);
export const getTransactions = (accountId, { illicitOnly = false, limit = 50 } = {}) =>
  get(`/network/${accountId}/transactions`, { illicit_only: illicitOnly, limit });

export const searchAccounts = (q) => get("/accounts/search", { q });
