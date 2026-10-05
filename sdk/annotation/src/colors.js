export const COLORS = Object.freeze({
  yellow: { label: '黄色', value: '#f2d37b' },
  coral: { label: '珊瑚', value: '#e8a390' },
  mint: { label: '薄荷', value: '#9ed8bc' },
  blue: { label: '天空', value: '#a5c8eb' },
  violet: { label: '淡紫', value: '#c7b4e9' },
});
export const DEFAULT_COLOR = 'yellow';
export function colorKey(value) { return Object.hasOwn(COLORS,value) ? value : DEFAULT_COLOR; }
