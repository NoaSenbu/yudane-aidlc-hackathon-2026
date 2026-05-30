/**
 * Babel 設定（Expo SDK 52 + NativeWind v4 + Reanimated）。
 *
 * - babel-preset-expo: jsxImportSource を nativewind に切替（NativeWind v4 公式推奨）
 * - nativewind/babel: Tailwind CSS のクラス名 → スタイル変換
 * - react-native-reanimated/plugin: 必ず最後（公式制約）
 */
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
    plugins: ['react-native-reanimated/plugin'],
  };
};
