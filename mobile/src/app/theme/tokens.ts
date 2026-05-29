/**
 * テーマトークン（NFR-A11Y-01、WCAG 2.2 AA 相当のコントラスト目標）。
 *
 * mockup の Indigo base / cold rose / cyan パレットを土台化する。
 * 各 Unit はこのトークンを参照し、独自色のハードコードを避ける。
 */

export const colors = {
  /** ベース背景（Indigo 系ダーク）。 */
  bgBase: '#1A1336',
  bgSurface: '#241A4D',
  /** テキスト（背景に対し AA 達成を目標）。 */
  textPrimary: '#FFFFFF',
  textSecondary: '#C9C2E8',
  /** アクセント。 */
  accentRose: '#E8B4D0',
  accentCyan: '#4DE1FF',
  /** 状態色。 */
  warning: '#FFC857',
  danger: '#FF6B6B',
  success: '#4DE1FF',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

export const typography = {
  /** 動的フォントスケーリングの基準（NFR-A11Y-03 で拡張）。 */
  baseFontSize: 16,
  lineHeightRatio: 1.5,
} as const;

export type ColorToken = keyof typeof colors;
