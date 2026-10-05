export type AnnotationColor = 'yellow' | 'coral' | 'mint' | 'blue' | 'violet';
export type AnchorStatus = 'exact' | 'relocated' | 'unresolved';
export interface DocumentIdentity { namespace: string; id: string; revision?: string | null }
export interface AnnotationAnchor {
  start: number; end: number; quote: string; prefix: string; suffix: string;
  status?: AnchorStatus;
}
export interface AnnotationRecord extends AnnotationAnchor {
  id: string; version: number; color?: AnnotationColor; comment?: string;
  anchor?: Partial<AnnotationAnchor> & { status: AnchorStatus };
}
export interface AnnotationAPI {
  list(identity: { namespace: string; documentId: string; revision: string | null }): Promise<AnnotationRecord[]>;
  create(identity: { namespace: string; documentId: string; revision: string | null }, note: AnnotationAnchor & { color: AnnotationColor; comment: string }): Promise<AnnotationRecord>;
  update(identity: { namespace: string; documentId: string; revision: string | null }, note: AnnotationRecord, change: { color: AnnotationColor; comment: string; expected: number }): Promise<AnnotationRecord>;
}
export interface AnnotationInstance { refresh(): Promise<AnnotationRecord[]>; destroy(): void }
export declare const COLORS: Readonly<Record<AnnotationColor, { label: string; value: string }>>;
export declare const DEFAULT_COLOR: AnnotationColor;
export declare function colorKey(value: unknown): AnnotationColor;
export declare function mountAnnotations(options: {
  container: Element;
  document: DocumentIdentity;
  api: AnnotationAPI;
  locale?: string;
  onSaved?: (record: AnnotationRecord) => void;
  onError?: (error: Error) => void;
}): Promise<AnnotationInstance>;
