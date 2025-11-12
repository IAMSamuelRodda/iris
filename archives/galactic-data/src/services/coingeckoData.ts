// src\services\coingeckoData.ts
import fetch from 'node-fetch';

import { db } from '../utils/connection.js';
import CoingeckoToken from '../models/coingeckoDataModel.js';
import dotenv from 'dotenv';

dotenv.config();

// Function to update or create data in Firestore
async function upsertDataInFirestore<T extends { [x: string]: any }>(collectionName: string, documentId: string, data: T): Promise<void> {
  const docRef = db().collection(collectionName).doc(documentId);
  const doc = await docRef.get();
  if (!doc.exists) {
    console.log(`Creating document ${documentId} in collection ${collectionName}`);
    await docRef.set(data);
  } else {
    console.log(`Updating document ${documentId} in collection ${collectionName}`);
    await docRef.update(data);
  }
}

export async function getPrices(): Promise<void> {
  const tokenIds = process.env.TOKEN_IDS;
  const apiUrl = `${process.env.COINGECKO_API_URL_PUBLIC}&vs_currency=usd&ids=${tokenIds}`;
  console.log('Fetching prices from CoinGecko API...', apiUrl);

  try {
    const response = await fetch(apiUrl);
    const data = await response.json();

    if (!Array.isArray(data)) {
      console.error('Fetched data is not an array:', data);
      return;
    }

    for (const tokenInfo of data) {
      // Explicitly cast the data object to match Firestore's expected type
      const tokenData = {
        id: tokenInfo.id,
        price: tokenInfo.current_price,
        name: tokenInfo.name,
        symbol: tokenInfo.symbol,
        lastUpdated: tokenInfo.last_updated
      };
      await upsertDataInFirestore<{ [key: string]: any }>('coingeckoData', 'data', tokenData as { [key: string]: any });
    }

    console.log('Firestore has been updated with the latest prices.');
  } catch (error) {
    console.error('Error fetching Coingecko Data:', error);
  }
}