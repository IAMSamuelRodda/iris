import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, QueryCommand, GetCommand, PutCommand, UpdateCommand } from '@aws-sdk/lib-dynamodb';
import { PublicKey } from '@solana/web3.js';
import { nanoid } from 'nanoid';
import bs58 from 'bs58';
import nacl from 'tweetnacl';
import { createJWT } from '../utils/jwt.js';
import type { User } from '../types.js';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);

const CHALLENGES_TABLE = process.env.CHALLENGES_TABLE || '';
const USERS_TABLE = process.env.USERS_TABLE || '';

interface WalletVerifyRequest {
  walletAddress: string;
  signature: string;
}

export async function verifyWalletSignature(
  event: APIGatewayProxyEvent
): Promise<APIGatewayProxyResult> {
  try {
    const body: WalletVerifyRequest = JSON.parse(event.body || '{}');

    if (!body.walletAddress || !body.signature) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Wallet address and signature are required' }),
      };
    }

    // Get the most recent unused challenge for this wallet
    const challengeResult = await ddb.send(
      new QueryCommand({
        TableName: CHALLENGES_TABLE,
        IndexName: 'WalletAddressIndex',
        KeyConditionExpression: 'walletAddress = :wallet',
        FilterExpression: '#used = :false AND expiresAt > :now',
        ExpressionAttributeNames: { '#used': 'used' },
        ExpressionAttributeValues: {
          ':wallet': body.walletAddress,
          ':false': false,
          ':now': Date.now(),
        },
        Limit: 1,
        ScanIndexForward: false, // Get most recent first
      })
    );

    if (!challengeResult.Items || challengeResult.Items.length === 0) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'No valid challenge found. Please request a new challenge.' }),
      };
    }

    const challenge = challengeResult.Items[0];

    // Verify signature
    const publicKey = new PublicKey(body.walletAddress);
    const messageBytes = new TextEncoder().encode(challenge.challenge);
    const signatureBytes = bs58.decode(body.signature);

    const isValid = nacl.sign.detached.verify(
      messageBytes,
      signatureBytes,
      publicKey.toBytes()
    );

    if (!isValid) {
      return {
        statusCode: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Invalid signature' }),
      };
    }

    // Mark challenge as used
    await ddb.send(
      new UpdateCommand({
        TableName: CHALLENGES_TABLE,
        Key: { challengeId: challenge.challengeId },
        UpdateExpression: 'SET #used = :true',
        ExpressionAttributeNames: { '#used': 'used' },
        ExpressionAttributeValues: { ':true': true },
      })
    );

    // Get or create user
    const userResult = await ddb.send(
      new QueryCommand({
        TableName: USERS_TABLE,
        IndexName: 'WalletAddressIndex',
        KeyConditionExpression: 'walletAddress = :wallet',
        ExpressionAttributeValues: { ':wallet': body.walletAddress },
        Limit: 1,
      })
    );

    let user: User;

    if (!userResult.Items || userResult.Items.length === 0) {
      // Create new user with wallet
      const userId = nanoid();
      user = {
        userId,
        email: `${body.walletAddress}@wallet.local`, // Placeholder email
        walletAddress: body.walletAddress,
        createdAt: Date.now(),
        lastLoginAt: Date.now(),
      };

      await ddb.send(
        new PutCommand({
          TableName: USERS_TABLE,
          Item: user,
        })
      );
    } else {
      user = userResult.Items[0] as User;

      // Update last login time
      await ddb.send(
        new UpdateCommand({
          TableName: USERS_TABLE,
          Key: { email: user.email },
          UpdateExpression: 'SET lastLoginAt = :now',
          ExpressionAttributeValues: { ':now': Date.now() },
        })
      );
    }

    // Create JWT
    const jwtToken = createJWT({
      userId: user.userId,
      email: user.email,
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: jwtToken,
        user: {
          userId: user.userId,
          email: user.email,
          walletAddress: user.walletAddress,
        },
      }),
    };
  } catch (error) {
    console.error('Error verifying wallet signature:', error);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to verify signature',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
}
