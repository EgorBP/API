import { useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'gifs-api-demo.tokens';

export function useTokens() {
  const [tokens, setTokensState] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (tokens) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [tokens]);

  return useMemo(
    () => ({
      tokens,
      accessToken: tokens?.access_token || '',
      refreshToken: tokens?.refresh_token || '',
      setTokens: setTokensState,
      clearTokens: () => setTokensState(null),
    }),
    [tokens],
  );
}
