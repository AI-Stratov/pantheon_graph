/** Wire format of /api/graph and of the static graph.json snapshot. */

export type Properties = Record<string, unknown>;

export interface NodeData {
  id: string;
  label: string;
  kind: string | null;
  properties: Properties;
}

export interface EdgeData {
  id: string;
  /** Parent edges always point parent → child. */
  source: string;
  target: string;
  kind: string;
  label: string | null;
  properties: Properties;
}

export interface GraphData {
  nodes: NodeData[];
  edges: EdgeData[];
}

export type Gender = 'male' | 'female';

export function text(node: NodeData, key: string): string | undefined {
  const value = node.properties[key];
  return typeof value === 'string' && value ? value : undefined;
}

export function list(node: NodeData, key: string): string[] {
  const value = node.properties[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function genderOf(node: NodeData): Gender | null {
  const value = node.properties.gender;
  if (value === 'male' || value === 'female') return value;
  // Older data encoded gender in the kind
  return node.kind === 'god' ? 'male' : node.kind === 'goddess' ? 'female' : null;
}

/** Screen area covered by floating UI, in CSS pixels. */
export interface Insets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}
