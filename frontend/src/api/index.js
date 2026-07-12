import axios from "axios";

const DEV_API = "http://127.0.0.1:8000";
const PROD_API = "https://xai-aml-final.onrender.com";

// A production bundle falling back to localhost points every visitor's browser
// at their own machine, and the only symptom is all six panels erroring at
// once. So production falls back to the deployed API, not to DEV_API: the site
// works whether or not VITE_API_URL is set, and setting it still wins.
const baseURL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? PROD_API : DEV_API);

// Exported so the UI can name the host it actually failed to reach, rather than
// hardcoding the dev address into an error a production visitor might read.
export const API_BASE = baseURL;

const apiClient = axios.create({
  baseURL,
  // Render's free instance sleeps. A cold start is ~50s of container wake before
  // the app answers at all, and the first data request pays another ~25s of model
  // warmup (graph build + SHAP explainer) on top. Measured: 63s just to reach
  // /health on a sleeping instance -- a 60s timeout aborted the first load of the
  // day before the API could ever reply.
  timeout: 180000,
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

/* Book-level intelligence: what laundering looks like across all 51k
 * transactions, as opposed to how one account scored. */
export const getRiskClock = () => get("/statistics/clock");
export const getChannelMix = () => get("/statistics/channels");
export const getAmountProfile = () => get("/statistics/amounts");
export const getRiskDrivers = (limit = 8) => get("/statistics/drivers", { limit });
