import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE });

export const fetchDatasets  = ()               => api.get('/datasets').then(r => r.data);
export const loadDataset    = (id)             => api.get(`/datasets/${id}`).then(r => r.data);
export const uploadFile     = (formData)       => api.post('/upload', formData).then(r => r.data);
export const runAnalysis    = (data)           => api.post('/analyze', data).then(r => r.data);
export const downloadReport = ()               => `${BASE}/report`;

export default api;
export const runAutopsy = () => api.get('/autopsy').then(r => r.data);
