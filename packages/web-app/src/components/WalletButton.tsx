import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import '@solana/wallet-adapter-react-ui/styles.css';

export function WalletButton() {
  return (
    <WalletMultiButton className="wallet-adapter-button-trigger" />
  );
}
