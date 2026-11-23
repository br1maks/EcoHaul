export const getTelegramWebApp = () => {
  return window.Telegram?.WebApp;
};

export const isTelegramWebApp = () => {
  return !!window.Telegram?.WebApp;
};

export const getTelegramUser = () => {
  return window.Telegram?.WebApp?.initDataUnsafe?.user;
};

export const hapticFeedback = {
  light: () => {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light');
  },
  medium: () => {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium');
  },
  heavy: () => {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('heavy');
  },
  success: () => {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
  },
  error: () => {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
  },
  warning: () => {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('warning');
  },
  selection: () => {
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
  },
};

export const initTelegramWebApp = () => {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.ready();
    webApp.expand();
  }
};

export const closeTelegramWebApp = () => {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.close();
  }
};

export const showTelegramAlert = (message: string) => {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.showAlert(message);
  } else {
    alert(message);
  }
};

export const showTelegramConfirm = (message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.showConfirm(message, (confirmed) => {
        resolve(confirmed);
      });
    } else {
      resolve(confirm(message));
    }
  });
};
