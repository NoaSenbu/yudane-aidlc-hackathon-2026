import './global.css';

import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { createQueryClient } from './src/app/providers/query-client';
import { MainTabs } from './src/navigation/MainTabs';

const queryClient = createQueryClient();

export default function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <MainTabs />
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
