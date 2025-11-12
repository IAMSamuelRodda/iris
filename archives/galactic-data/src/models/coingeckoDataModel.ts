// src\models\coingeckoDataModel.ts
interface CoingeckoToken {
  id: string; // Unique ID for each token, acts as a document ID in Firestore
  price: number;
  name: string;
  symbol: string;
  lastUpdated: string; // ISO 8601 format date string
}

export default CoingeckoToken;
