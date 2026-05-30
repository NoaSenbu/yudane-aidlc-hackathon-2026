const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

let config = getDefaultConfig(projectRoot);

// npm workspaces（@yudane/* パッケージ）のシンボリックリンク解決
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// @yudane/api-client → モノレポ内の実装へのエイリアス
config.resolver.extraNodeModules = {
  '@yudane/api-client': path.resolve(projectRoot, 'src/features/platform/api-client/api-fetch.ts'),
};

module.exports = withNativeWind(config, { input: './global.css' });
