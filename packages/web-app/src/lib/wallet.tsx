import { useMemo } from 'react';
import {
  ConnectionProvider,
  WalletProvider,
} from '@solana/wallet-adapter-react';
import { PhantomWalletAdapter } from '@solana/wallet-adapter-wallets';
import { clusterApiUrl } from '@solana/web3.js';

export function WalletConnectionProvider({ children }: { children: React.ReactNode }) {
  // Use Solana devnet for development, mainnet-beta for production
  const endpoint = useMemo(() => {
    const network = import.meta.env.VITE_SOLANA_NETWORK || 'devnet';
    return network === 'mainnet-beta'
      ? import.meta.env.VITE_SOLANA_RPC_ENDPOINT || clusterApiUrl('mainnet-beta')
      : clusterApiUrl(network as 'devnet' | 'testnet');
  }, []);

  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      // Add more wallet adapters as needed
    ],
    []
  );

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} autoConnect>
        {children}
      </WalletProvider>
    </ConnectionProvider>
  );
}
