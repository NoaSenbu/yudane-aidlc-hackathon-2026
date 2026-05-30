import { registerRootComponent } from 'expo';

import App from './App';

// registerRootComponent は AppRegistry.registerComponent('main', ...) + Android の初期化を担う。
// Expo Go / ネイティブビルド両方に対応している。
registerRootComponent(App);
