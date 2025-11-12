// src\types\staratlasOrderDataTypes.ts
import { PublicKey } from "@solana/web3.js"; // Assuming PublicKey is used for identifiers

export interface OrderSide {
  buy?: {};
  sell?: {};
}

export interface OrderAccount {
  publicKey: PublicKey;
  account: {
    orderInitializerPubkey: PublicKey;
    currencyMint: PublicKey;
    assetMint: PublicKey;
    initializerCurrencyTokenAccount: PublicKey;
    initializerAssetTokenAccount: PublicKey;
    orderSide: OrderSide;
    price: BigInt; // Assuming price is stored as string; may need conversion
    orderOriginationQty: BigInt;
    orderRemainingQty: BigInt;
    createdAtTimestamp: BigInt;
  };
}

export type staratlasOrderAccountType = OrderAccount[];
