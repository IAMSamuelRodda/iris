// src\services\staratlasOrderData.ts
import { Connection, PublicKey, clusterApiUrl } from '@solana/web3.js';
import { Program, AnchorProvider } from '@project-serum/anchor';
import { GALACTIC_MARKETPLACE_IDL, Order as OrderType } from '@staratlas/galactic-marketplace';
import { db } from '../utils/connection.js'; // Firestore connection utility
import staratlasOrderDataModel from '../models/staratlasOrderDataModel.js';
import dotenv from 'dotenv';

dotenv.config();

const GALACTIC_MARKETPLACE_PROGRAM_ID = new PublicKey(process.env.GALACTIC_MARKETPLACE_PROGRAM_ID || '');
const NODE_RPC_HOST = process.env.SECRET_NODE_RPC_HOST || clusterApiUrl('mainnet-beta');
const connection = new Connection(NODE_RPC_HOST, 'confirmed');
const provider = new AnchorProvider(connection, {} as any, { commitment: 'confirmed' });

// Adjusted function to upsert data into Firestore
async function upsertOrderDataInFirestore<T extends { [x: string]: any }>(collectionName: string, documentId: string, data: T): Promise<void> {
  const docRef = db().collection(collectionName).doc(documentId); // Access the Firestore connection using db()
  const doc = await docRef.get();
  if (!doc.exists) {
    console.log(`Creating document ${documentId} in collection ${collectionName}`);
    await docRef.set(data);
  } else {
    console.log(`Updating document ${documentId} in collection ${collectionName}`);
    await docRef.update(data);
  }
}

export async function fetchAndUpsertOrderAccounts(): Promise<void> {
    const galacticMarketplaceProgram = new Program<typeof GALACTIC_MARKETPLACE_IDL>(GALACTIC_MARKETPLACE_IDL, GALACTIC_MARKETPLACE_PROGRAM_ID, provider);

    try {
        const programAccounts = await galacticMarketplaceProgram.account.orderAccount.all();
        
        for (const account of programAccounts) {
            const orderData: staratlasOrderDataModel = {
                publicKey: account.publicKey.toString(),
                account: {
                    orderInitializerPubkey: account.account.orderInitializerPubkey.toString(),
                    currencyMint: account.account.currencyMint.toString(),
                    assetMint: account.account.assetMint.toString(),
                    initializerCurrencyTokenAccount: account.account.initializerCurrencyTokenAccount.toString(),
                    initializerAssetTokenAccount: account.account.initializerAssetTokenAccount.toString(),
                    orderSide: account.account.orderSide,
                    price: account.account.price.toString(),
                    orderOriginationQty: account.account.orderOriginationQty.toString(),
                    orderRemainingQty: account.account.orderRemainingQty.toString(),
                    createdAtTimestamp: account.account.createdAtTimestamp.toString(),
                }
            };

            // Explicitly cast to match Firestore's expected type
            await upsertOrderDataInFirestore<{ [key: string]: any }>('staratlasGalacticMarketplace', 'data', orderData as { [key: string]: any });
        }

        console.log('Order data has been successfully updated in Firestore.');
    } catch (error) {
        console.error("Error during the process:", error);
    }
}
