import { FileDetails, GraphResponse, Repository } from './types';

const API_BASE = '/api';

export async function fetchRepositories(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/repos`);
  if (!res.ok) throw new Error('Failed to fetch repositories');
  return res.json();
}

export async function indexRepository(path: string, name?: string): Promise<{ repo_id: string }> {
  const res = await fetch(`${API_BASE}/repos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, name }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to index repository');
  }
  return res.json();
}

export async function fetchDependencyGraph(repoId: string): Promise<GraphResponse> {
  const res = await fetch(`${API_BASE}/repos/${repoId}/graph/dependencies`);
  if (!res.ok) throw new Error('Failed to fetch dependency graph');
  return res.json();
}

export async function fetchCallGraph(repoId: string): Promise<GraphResponse> {
  const res = await fetch(`${API_BASE}/repos/${repoId}/graph/calls`);
  if (!res.ok) throw new Error('Failed to fetch call graph');
  return res.json();
}

export async function fetchHierarchyGraph(repoId: string): Promise<GraphResponse> {
  const res = await fetch(`${API_BASE}/repos/${repoId}/graph/hierarchy`);
  if (!res.ok) throw new Error('Failed to fetch hierarchy graph');
  return res.json();
}

export async function fetchFileDetails(repoId: string, fileId: string): Promise<FileDetails> {
  const res = await fetch(`${API_BASE}/repos/${repoId}/files/${fileId}`);
  if (!res.ok) throw new Error('Failed to fetch file details');
  return res.json();
}
