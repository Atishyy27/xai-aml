// frontend/src/api/index.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000',
});

export const getSuspiciousNetworks = async (accountId, hops = 1) => {
  const params = {};
  if (accountId) {
    params.account_id = accountId;
    params.hops = hops;
  }

  const response = await apiClient.get('/suspicious-networks', { params });
  return response.data;
};


export const getNetworkGraph = async (networkId, hops = 1) => {
  const response = await apiClient.get(`/network/${networkId}?hops=${hops}`);
  return response.data;
};

export const getAccountExplanation = async (accountId) => {
  const response = await apiClient.get(`/account/${accountId}/explanation`);
  return response.data;
};

export const getHeatmapData = async () => {
    try {
        const response = await apiClient.get('/statistics/heatmap');
        return response.data;
    } catch (error) {
        console.error("Error fetching heatmap data:", error);
        throw error;
    }
};

export const getPatternStatistics = async () => {
  try {
    const response = await apiClient.get('/statistics/patterns'); // fixed here
    return response.data;
  } catch (error) {
    console.error("Error fetching pattern statistics:", error);
    throw error;
  }
};

export const getIllicitTransactions = async (accountId) => {
  const response = await apiClient.get(`/network/${accountId}/illicit-transactions`);
  return response.data;
};