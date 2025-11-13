import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';
import { nanoid } from 'nanoid';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);

const CHALLENGES_TABLE = process.env.CHALLENGES_TABLE || '';
const CHALLENGE_EXPIRY_MINUTES = 5;

interface WalletChallengeRequest {
  walletAddress: string;
}

interface WalletChallenge {
  challenge: string;
  walletAddress: string;
  createdAt: number;
  expiresAt: number;
  used: boolean;
}

export async function createWalletChallenge(
  event: APIGatewayProxyEvent
): Promise<APIGatewayProxyResult> {
  try {
    const body: WalletChallengeRequest = JSON.parse(event.body || '{}');

    if (!body.walletAddress) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Wallet address is required' }),
      };
    }

    // Generate challenge message
    const challenge = `Sign this message to authenticate with Star Atlas Agent.\n\nWallet: ${body.walletAddress}\nNonce: ${nanoid(16)}\nTimestamp: ${Date.now()}`;
    const challengeId = nanoid(32);
    const now = Date.now();
    const expiresAt = now + (CHALLENGE_EXPIRY_MINUTES * 60 * 1000);

    // Store challenge in DynamoDB
    const challengeData: WalletChallenge & { challengeId: string } = {
      challengeId,
      challenge,
      walletAddress: body.walletAddress,
      createdAt: now,
      expiresAt,
      used: false,
    };

    await ddb.send(
      new PutCommand({
        TableName: CHALLENGES_TABLE,
        Item: challengeData,
      })
    );

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        challenge,
        challengeId,
        expiresAt,
      }),
    };
  } catch (error) {
    console.error('Error creating wallet challenge:', error);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to create challenge',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
}
