// frontend/src/api/index.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
});

export const getSuspiciousNetworks = async () => {
  const response = await apiClient.get('/suspicious-networks');
  return response.data;
};

export const getNetworkGraph = async (networkId) => {
  const response = await apiClient.get(`/network/${networkId}`);
  return response.data;
};

export const getAccountExplanation = async (accountId) => {
  const response = await apiClient.get(`/account/${accountId}/explanation`);
  return response.data;
};