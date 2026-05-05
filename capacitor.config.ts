import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'site.shadowcypher.app',
  appName: 'ShadowCypher',
  webDir: 'www',
  server: {
    androidScheme: 'https',
  },
  android: {
    buildOptions: {
      keystorePath: 'shadowcypher.keystore',
      keystoreAlias: 'shadowcypher',
    },
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: '#020202',
      showSpinner: false,
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
