/**
 * Tailwind CSS 設定（NativeWind v4 + Direction D「黒服のコンシェルジュ」）。
 *
 * Direction D デザインシステムのトークンを移植。SSOT は
 * aidlc-docs/construction/design-system/direction-d-design-system.md §2 を参照。
 */
const { hairlineWidth } = require('nativewind/theme');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.tsx', './src/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // Direction D — 黒服のコンシェルジュ
        'd-bg': '#0B0B0D',
        'd-bg-2': '#14110A',
        'd-line': 'rgba(201,162,75,0.18)',
        'd-gold': '#C9A24B',
        'd-gold-2': '#E7CE8A',
        'd-gold-3': '#8E6F2E',
        'd-ink': '#F5F1E8',
        'd-ink-2': '#B8B0A0',
        'd-ink-3': '#7A7468',
      },
      fontFamily: {
        'd-serif': ['ShipporiMincho_400Regular'],
        'd-display': ['Cinzel_400Regular'],
      },
      borderRadius: {
        'd-panel': '4px',
        'd-cta': '3px',
      },
      borderWidth: {
        hairline: hairlineWidth(),
      },
    },
  },
  plugins: [],
};
