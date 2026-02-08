// When running via Vite proxy, use empty string. 
// When running in Docker with direct access, use the backend URL
const API_BASE = '';


export function getToken() {
 return localStorage.getItem('token');
}

export function setToken(token) {
 localStorage.setItem('token', token);
}

export function clearToken() {
 localStorage.removeItem('token');
}

const DEFAULT_TIMEOUT_MS = 60000; // 60s so slow LLM backend doesn't hang the app forever

export async function api(endpoint, options = {}) {
 const token = getToken();
 const headers = {
  'Content-Type': 'application/json',
  ...options.headers,
 };

 if (token) {
  headers['Authorization'] = `Bearer ${token}`;
 }

 const timeoutMs = options.timeout ?? DEFAULT_TIMEOUT_MS;
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

 try {
  const response = await fetch(`${API_BASE}${endpoint}`, {
   ...options,
   headers,
   signal: controller.signal,
  });
  clearTimeout(timeoutId);

  if (!response.ok) {
   const error = await response.json().catch(() => ({ detail: 'Request failed' }));
   throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
 } catch (error) {
  clearTimeout(timeoutId);
  if (error.name === 'AbortError') {
   throw new Error('Request timeout. Server or Ollama may be busy. Try again or restart Ollama.');
  }
  if (error instanceof TypeError && error.message.includes('fetch')) {
   throw new Error('Cannot connect to server. Please check your connection.');
  }
  throw error;
 }
}

export async function login(username, password) {
 const data = await api('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ username, password }),
 });
 setToken(data.access_token);
 return data;
}

export async function getMe() {
 return api('/auth/me');
}

export async function changePassword(currentPassword, newPassword) {
 return api('/auth/change-password', {
  method: 'POST',
  body: JSON.stringify({
   current_password: currentPassword,
   new_password: newPassword
  }),
 });
}

export async function testAI() {
 return api('/ai/test');
}

export async function getProjects() {
 return api('/projects');
}

export async function createProject(name, description, topoUrl, visibility, backupInterval) {
 return api('/projects', {
  method: 'POST',
  body: JSON.stringify({ 
    name, 
    description,
    topo_url: topoUrl || null,
    visibility: visibility || "Private",
    backup_interval: backupInterval || "Daily"
  }),
 });
}

export async function getProject(projectId) {
 return api(`/projects/${projectId}`);
}

export async function getProjectMembers(projectId) {
 return api(`/projects/${projectId}/members`);
}

export async function addProjectMember(projectId, username, role) {
 return api(`/projects/${projectId}/members`, {
  method: 'POST',
  body: JSON.stringify({ username, role }),
 });
}

export async function updateProjectMemberRole(projectId, username, role) {
 return api(`/projects/${projectId}/members/${username}`, {
  method: 'PUT',
  body: JSON.stringify({ username, role }),
 });
}

export async function removeProjectMember(projectId, username) {
 return api(`/projects/${projectId}/members/${username}`, {
  method: 'DELETE',
 });
}

export async function updateProject(projectId, name, description, topoUrl, visibility, backupInterval) {
 return api(`/projects/${projectId}`, {
  method: 'PUT',
  body: JSON.stringify({ 
    name, 
    description,
    topo_url: topoUrl !== undefined ? topoUrl : null,
    visibility: visibility !== undefined ? visibility : null,
    backup_interval: backupInterval !== undefined ? backupInterval : null
  }),
 });
}

export async function deleteProject(projectId) {
 return api(`/projects/${projectId}`, {
  method: 'DELETE',
 });
}

export async function getUsers() {
 return api('/users');
}

export async function createUser(username, email, phoneNumber, tempPassword) {
 return api('/users', {
  method: 'POST',
  body: JSON.stringify({ username, email, phone_number: phoneNumber, temp_password: tempPassword }),
 });
}

export async function updateUser(username, email) {
 return api(`/users/${username}`, {
  method: 'PUT',
  body: JSON.stringify({ email }),
 });
}

export async function deleteUser(username) {
 return api(`/users/${username}`, {
  method: 'DELETE',
 });
}

// Documents API
export async function uploadDocuments(projectId, files, metadata, folderId) {
 const formData = new FormData();
 
 // Add all files
 files.forEach(file => {
  formData.append('files', file);
 });
 
 // Add metadata as form fields (FastAPI multipart form)
 formData.append('who', metadata.who || '');
 formData.append('what', metadata.what || '');
 if (metadata.where) formData.append('where', metadata.where);
 if (metadata.when) formData.append('when', metadata.when);
 if (metadata.why) formData.append('why', metadata.why);
 if (metadata.description) formData.append('description', metadata.description);
 // Always append folder_id - if null/empty, send empty string (backend will treat as None)
 formData.append('folder_id', folderId || '');
 
 const token = getToken();
 const response = await fetch(`${API_BASE}/projects/${projectId}/documents`, {
  method: 'POST',
  headers: {
   'Authorization': token ? `Bearer ${token}` : '',
   // Don't set Content-Type - browser will set it with boundary
  },
  body: formData,
 });
 
 if (!response.ok) {
  let errorData;
  try {
   errorData = await response.json();
  } catch {
   errorData = { detail: `Upload failed with status ${response.status}` };
  }
  // Handle different error formats
  const errorMessage = errorData.detail || errorData.message || errorData.error || `Upload failed with status ${response.status}`;
  throw new Error(errorMessage);
 }
 
 return response.json();
}

export async function getDocuments(projectId, filters = {}, options = {}) {
 const params = new URLSearchParams();
 if (filters.folder_id) params.append('folder_id', filters.folder_id);
 if (filters.uploader) params.append('uploader', filters.uploader);
 if (filters.search) params.append('search', filters.search);
 const timeout = options.timeout ?? 30000;
 const response = await api(`/projects/${projectId}/documents?${params}`, { timeout });
 // API returns {documents: [...], count: ...}, extract documents array
 return response.documents || response || [];
}

export async function getDocument(projectId, documentId) {
 return api(`/projects/${projectId}/documents/${documentId}`);
}

export async function downloadDocument(projectId, documentId, version = null) {
 const params = version ? `?version=${version}` : '';
 const token = getToken();
 
 const response = await fetch(`/projects/${projectId}/documents/${documentId}/download${params}`, {
  headers: {
   'Authorization': token ? `Bearer ${token}` : '',
  },
 });
 
 if (!response.ok) {
  throw new Error('Download failed');
 }
 
 const blob = await response.blob();
 const url = window.URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'document';
 document.body.appendChild(a);
 a.click();
 a.remove();
 window.URL.revokeObjectURL(url);
}

export async function getDocumentPreview(projectId, documentId, version = null) {
 const params = version ? `?version=${version}` : '';
 return api(`/projects/${projectId}/documents/${documentId}/preview${params}`);
}

export async function getDocumentVersions(projectId, documentId) {
 return api(`/projects/${projectId}/documents/${documentId}/versions`);
}

/** List config versions for a device (for Compare Config modal). Returns { configs: [{ id, document_id, version, filename, created_at }] }. */
export async function getDeviceConfigs(projectId, deviceId) {
 const res = await api(`/projects/${projectId}/devices/${encodeURIComponent(deviceId)}/configs`);
 return res.configs || [];
}

/** Get raw text content of a document (for config diff). Returns string. */
export async function getDocumentContentText(projectId, documentId, version = null) {
 const token = getToken();
 const url = version != null
  ? `${API_BASE || ''}/projects/${projectId}/documents/${documentId}/content?version=${version}`
  : `${API_BASE || ''}/projects/${projectId}/documents/${documentId}/content`;
 const response = await fetch(url, {
  headers: { Authorization: token ? `Bearer ${token}` : '' },
 });
 if (!response.ok) {
  const err = await response.json().catch(() => ({ detail: 'Failed to load content' }));
  throw new Error(err.detail || `Failed with status ${response.status}`);
 }
 return response.text();
}

export async function moveDocumentFolder(projectId, documentId, folderId) {
 const token = getToken();
 const response = await fetch(`${API_BASE}/projects/${projectId}/documents/${documentId}/folder`, {
  method: 'PATCH',
  headers: {
   'Authorization': token ? `Bearer ${token}` : '',
   'Content-Type': 'application/json'
  },
  body: JSON.stringify({ folder_id: folderId || null })
 });
 
 if (!response.ok) {
  let errorData;
  try {
   errorData = await response.json();
  } catch {
   errorData = { detail: `Move failed with status ${response.status}` };
  }
  const errorMessage = errorData.detail || errorData.message || errorData.error || `Move failed with status ${response.status}`;
  throw new Error(errorMessage);
 }
 
 return response.json();
}

export async function renameDocument(projectId, documentId, filename) {
 return api(`/projects/${projectId}/documents/${documentId}/filename`, {
  method: 'PATCH',
  body: JSON.stringify({ filename }),
 });
}

export async function uploadDocumentVersion(projectId, documentId, file) {
 const formData = new FormData();
 formData.append('file', file);
 
 const token = getToken();
 const response = await fetch(`/projects/${projectId}/documents/${documentId}/upload-version`, {
  method: 'POST',
  headers: {
   'Authorization': token ? `Bearer ${token}` : '',
  },
  body: formData,
 });
 
 if (!response.ok) {
  const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
  throw new Error(error.detail || `Upload failed with status ${response.status}`);
 }
 
 return response.json();
}

export async function deleteDocument(projectId, documentId, deleteAllVersions = false) {
 const params = deleteAllVersions ? '?delete_all_versions=true' : '';
 return api(`/projects/${projectId}/documents/${documentId}${params}`, {
  method: 'DELETE',
 });
}

export async function getProjectOptions(projectId) {
 return api(`/projects/${projectId}/options`);
}

export async function saveProjectOption(projectId, field, value) {
  return api(`/projects/${projectId}/options`, {
    method: 'POST',
    body: JSON.stringify({ field, value }),
  });
}

export async function getConfigSummary(projectId) {
  return api(`/projects/${projectId}/summary`);
}

/** Dashboard metrics for NOC (total_devices, healthy, critical, core, dist, access). */
export async function getSummaryMetrics(projectId) {
  return api(`/projects/${projectId}/summary/metrics`);
}

export async function getDeviceDetails(projectId, deviceName) {
  return api(`/projects/${projectId}/summary/${deviceName}`);
}

export async function uploadDeviceImage(projectId, deviceName, file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const token = getToken();
  const response = await fetch(`${API_BASE}/projects/${projectId}/devices/${deviceName}/image`, {
    method: 'POST',
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: formData,
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `Upload failed with status ${response.status}` }));
    throw new Error(errorData.detail || errorData.message || `Upload failed with status ${response.status}`);
  }
  
  return response.json();
}

export async function getDeviceImage(projectId, deviceName) {
  return api(`/projects/${projectId}/devices/${deviceName}/image`);
}

export async function deleteDeviceImage(projectId, deviceName) {
  return api(`/projects/${projectId}/devices/${deviceName}/image`, {
    method: 'DELETE',
  });
}

// Project-Level Analysis API
export async function analyzeProjectOverview(projectId) {
  return api(`/projects/${projectId}/analyze/overview`, {
    method: 'POST',
  });
}

export async function getProjectOverview(projectId) {
  return api(`/projects/${projectId}/analyze/overview`, {
    method: 'GET',
  });
}

export async function analyzeProjectRecommendations(projectId) {
  return api(`/projects/${projectId}/analyze/recommendations`, {
    method: 'POST',
  });
}

export async function getProjectRecommendations(projectId) {
  return api(`/projects/${projectId}/analyze/recommendations`, {
    method: 'GET',
  });
}

/** Server-side LLM busy status for this project (any user/device). Poll to sync UI across clients. */
export async function getProjectLlmStatus(projectId) {
  return api(`/projects/${projectId}/analyze/llm-status`, { method: 'GET', timeout: 10000 });
}

/** Combined overview + recommendations for Summary/Device detail (gap_analysis from recommendations). */
export async function getFullProjectAnalysis(projectId) {
  const [overviewRes, recRes] = await Promise.all([
    api(`/projects/${projectId}/analyze/overview`, { method: 'GET' }).catch(() => ({ overview_text: null, metrics: null })),
    api(`/projects/${projectId}/analyze/recommendations`, { method: 'GET' }).catch(() => ({ recommendations: [], metrics: null })),
  ]);
  const recommendations = recRes.recommendations || [];
  const gap_analysis = recommendations.map((r) => ({
    severity: r.severity || 'Medium',
    device: r.device || 'all',
    issue: r.issue ?? r.message ?? '',
    recommendation: r.recommendation ?? r.message ?? '',
  }));
  return {
    network_overview: overviewRes.overview_text ?? null,
    gap_analysis,
    metrics: overviewRes.metrics || recRes.metrics || null,
  };
}

// Per-device analysis (More Detail page) — LLM can take 1–5 min, use long timeout
const DEVICE_LLM_TIMEOUT_MS = 330000; // 5.5 min to match backend OLLAMA_TIMEOUT

export async function getDeviceOverview(projectId, deviceName) {
  return api(`/projects/${projectId}/analyze/device-overview?device_name=${encodeURIComponent(deviceName)}`);
}

export async function analyzeDeviceOverview(projectId, deviceName) {
  return api(`/projects/${projectId}/analyze/device-overview`, {
    method: 'POST',
    body: JSON.stringify({ device_name: deviceName }),
    timeout: DEVICE_LLM_TIMEOUT_MS,
  });
}

export async function getDeviceRecommendations(projectId, deviceName) {
  return api(`/projects/${projectId}/analyze/device-recommendations?device_name=${encodeURIComponent(deviceName)}`);
}

export async function analyzeDeviceRecommendations(projectId, deviceName) {
  return api(`/projects/${projectId}/analyze/device-recommendations`, {
    method: 'POST',
    body: JSON.stringify({ device_name: deviceName }),
    timeout: DEVICE_LLM_TIMEOUT_MS,
  });
}

export async function getDeviceConfigDrift(projectId, deviceName) {
  return api(`/projects/${projectId}/analyze/device-config-drift?device_name=${encodeURIComponent(deviceName)}`);
}

/** Compare two versions of same document (version history) — raw config files. */
export async function analyzeDeviceConfigDrift(projectId, deviceName, options = {}) {
  const body = { device_name: deviceName };
  if (options.documentId != null && options.fromVersion != null && options.toVersion != null) {
    body.document_id = options.documentId;
    body.from_version = options.fromVersion;
    body.to_version = options.toVersion;
  } else if (options.fromDocumentId && options.toDocumentId) {
    body.from_document_id = options.fromDocumentId;
    body.to_document_id = options.toDocumentId;
  }
  return api(`/projects/${projectId}/analyze/device-config-drift`, {
    method: 'POST',
    body: JSON.stringify(body),
    timeout: DEVICE_LLM_TIMEOUT_MS,
  });
}

// Folders API
export async function getFolders(projectId, options = {}) {
  const timeout = options.timeout ?? 30000;
  const response = await api(`/projects/${projectId}/folders`, { timeout });
  return response.folders || [];
}

export async function createFolder(projectId, name, parentId) {
  return api(`/projects/${projectId}/folders`, {
    method: 'POST',
    body: JSON.stringify({ name, parent_id: parentId || null }),
  });
}

export async function updateFolder(projectId, folderId, name, parentId) {
  return api(`/projects/${projectId}/folders/${folderId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, parent_id: parentId || null }),
  });
}

export async function deleteFolder(projectId, folderId) {
  return api(`/projects/${projectId}/folders/${folderId}`, {
    method: 'DELETE',
  });
}

// Analysis API
export async function createAnalysis(projectId, deviceName, analysisType, customPrompt = null, includeOriginalContent = false) {
  return api(`/projects/${projectId}/analysis`, {
    method: 'POST',
    body: JSON.stringify({
      device_name: deviceName,
      analysis_type: analysisType,
      custom_prompt: customPrompt,
      include_original_content: includeOriginalContent
    }),
  });
}

export async function getAnalyses(projectId, filters = {}) {
  const params = new URLSearchParams();
  if (filters.device_name) params.append('device_name', filters.device_name);
  if (filters.status) params.append('status', filters.status);
  if (filters.analysis_type) params.append('analysis_type', filters.analysis_type);
  
  return api(`/projects/${projectId}/analysis?${params}`);
}

export async function getAnalysis(projectId, analysisId) {
  return api(`/projects/${projectId}/analysis/${analysisId}`);
}

export async function verifyAnalysis(projectId, analysisId, verifiedContent, comments = null, status = 'verified') {
  return api(`/projects/${projectId}/analysis/verify`, {
    method: 'POST',
    body: JSON.stringify({
      analysis_id: analysisId,
      verified_content: verifiedContent,
      comments: comments,
      status: status
    }),
  });
}

export async function getPerformanceMetrics(projectId, deviceName = null, limit = 100) {
  const params = new URLSearchParams();
  if (deviceName) params.append('device_name', deviceName);
  params.append('limit', limit);
  
  return api(`/projects/${projectId}/analysis/performance/metrics?${params}`);
}

// Topology API

/** Fast: fetch nodes/links from DB only (no LLM). Use for instant graph display. */
export async function getNetworkTopology(projectId) {
  return api(`/projects/${projectId}/network-topology`, { timeout: 15000 });
}

/** Slow: triggers LLM analysis. Call only when user requests AI generation. */
export async function generateTopology(projectId) {
  return api(`/projects/${projectId}/topology/generate`, {
    method: 'POST',
  });
}

/** Get saved topology (from LLM result or project). Use for polling after generate. */
export async function getTopology(projectId) {
  return api(`/projects/${projectId}/topology`);
}

export async function saveTopologyLayout(projectId, positions, links, nodeLabels = null, nodeRoles = null) {
  return api(`/projects/${projectId}/topology/layout`, {
    method: 'PUT',
    body: JSON.stringify({
      positions,
      links,
      node_labels: nodeLabels,
      node_roles: nodeRoles
    }),
  });
}