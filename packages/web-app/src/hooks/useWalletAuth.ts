import { useWallet } from '@solana/wallet-adapter-react';
import { useState } from 'react';
import bs58 from 'bs58';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export function useWalletAuth() {
  const { publicKey, signMessage } = useWallet();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authenticate = async (): Promise<string | null> => {
    if (!publicKey || !signMessage) {
      setError('Wallet not connected');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Request challenge from server
      const challengeResponse = await fetch(`${API_BASE_URL}/auth/wallet/challenge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          walletAddress: publicKey.toBase58(),
        }),
      });

      if (!challengeResponse.ok) {
        throw new Error('Failed to get challenge');
      }

      const { challenge } = await challengeResponse.json();

      // 2. Sign the challenge with the wallet
      const message = new TextEncoder().encode(challenge);
      const signature = await signMessage(message);

      // 3. Submit signature for verification
      const verifyResponse = await fetch(`${API_BASE_URL}/auth/wallet/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          walletAddress: publicKey.toBase58(),
          signature: bs58.encode(signature),
        }),
      });

      if (!verifyResponse.ok) {
        throw new Error('Failed to verify signature');
      }

      const { token } = await verifyResponse.json();

      // Store JWT token
      localStorage.setItem('auth_token', token);

      return token;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    authenticate,
    loading,
    error,
    isConnected: !!publicKey,
  };
}
