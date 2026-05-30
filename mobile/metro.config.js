/**
 * Metro bundler 設定（Expo SDK 52 + monorepo workspace + NativeWind v4）。
 *
 * - getDefaultConfig: Expo の既定 Metro 設定
 * - withNativeWind: Tailwind CSS の global.css を入力として読み込む（v4 公式推奨）
 * - monorepo workspace 対応: watchFolders 拡張で workspace ルートを監視
 */
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('node:path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

const config = getDefaultConfig(projectRoot);

// monorepo: workspace ルートを watch + node_modules 解決
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];
config.resolver.disableHierarchicalLookup = false;

module.exports = withNativeWind(config, { input: './src/styles/global.css' });
