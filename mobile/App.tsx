/**
 * YUDANE Mobile Root Component。
 *
 * Phase A2 段階では最小の placeholder。Step A9 で React Navigation Stack 構成に置換する。
 */
import './src/styles/global.css';

import { StatusBar } from 'expo-status-bar';
import { Text, View } from 'react-native';

export default function App() {
  return (
    <View className="flex-1 items-center justify-center bg-d-bg">
      <StatusBar style="light" />
      <Text className="text-d-gold-2 text-2xl font-d-serif">YUDANE</Text>
      <Text className="text-d-ink-2 text-sm mt-2">Step A2: Expo SDK 52 setup OK</Text>
    </View>
  );
}
