// src\models\staratlasOrderDataModel.ts
interface OrderSide {
  sell?: object;
  buy?: object;
}

interface staratlasOrderDataModel {
  publicKey: string; // Document ID in Firestore
  account: {
    orderInitializerPubkey: string;
    currencyMint: string;
    assetMint: string;
    initializerCurrencyTokenAccount: string;
    initializerAssetTokenAccount: string;
    orderSide: OrderSide;
    price: string;
    orderOriginationQty: string;
    orderRemainingQty: string;
    createdAtTimestamp: string; // ISO 8601 format date string
  };
}

export default staratlasOrderDataModel;
