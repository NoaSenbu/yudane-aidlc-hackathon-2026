/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.tsx', './src/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // 既存（reel-screen.tsx 互換）
        'indigo-950': '#1A1336',
        'indigo-900': '#241A4D',
        // v2 YUDANE PRIVÉ カラートークン
        prive: {
          bg: '#080814',      // ベース背景（漆黒）
          surface: '#10101E', // カード面
          card: '#18182E',    // カード内要素
          border: '#28285A',  // 区切り線
          gold: '#C9A96E',    // ゴールドアクセント
          cream: '#E8E0D0',   // クリームテキスト
          muted: '#6A6A8A',   // 補助テキスト
          rouge: '#C07A7A',   // 警告・逃げた
          teal: '#4DCFC0',    // 成功・論破済み
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'System', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
