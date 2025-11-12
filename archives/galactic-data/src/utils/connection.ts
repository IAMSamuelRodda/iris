// src/utils/connection.ts
import { SecretManagerServiceClient } from '@google-cloud/secret-manager';
import { initializeApp, cert, getApp, getApps } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';

let firestoreDb: Firestore | null = null;

const secretClient = new SecretManagerServiceClient();

async function accessSecret(secretName: string): Promise<string> {
  const [version] = await secretClient.accessSecretVersion({ name: secretName });
  const payload = version.payload?.data?.toString();
  if (!payload) {
    throw new Error(`Failed to access secret version for ${secretName}`);
  }
  return payload;
}

export const initializeFirestore = async () => {
  if (getApps().length === 0) {
    const secretName = `projects/galactic-data/secrets/SECRET_FIRESTORE_PRIVATE_KEY/versions/latest`;
    const serviceAccountJSON = await accessSecret(secretName);
    const serviceAccount = JSON.parse(serviceAccountJSON);
    initializeApp({
      credential: cert(serviceAccount),
    });
  }
  firestoreDb = getFirestore(getApp());
  console.log('Firestore initialized');
};

export const db = () => {
  if (!firestoreDb) {
    throw new Error('Firestore has not been initialized. Call initializeFirestore first.');
  }
  return firestoreDb;
};
