import { APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import type { AuthenticatedEvent } from '../middleware/auth.js';
import type { User } from '../types.js';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);

const USERS_TABLE = process.env.USERS_TABLE || '';

export async function getProfile(
  event: AuthenticatedEvent
): Promise<APIGatewayProxyResult> {
  try {
    if (!event.auth) {
      return {
        statusCode: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Unauthorized' }),
      };
    }

    // Get user profile from DynamoDB using userId
    const result = await ddb.send(
      new GetCommand({
        TableName: USERS_TABLE,
        Key: { userId: event.auth.userId },
      })
    );

    if (!result.Item) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'User not found' }),
      };
    }

    const user = result.Item as User;

    // Don't expose sensitive fields
    const profileData = {
      userId: user.userId,
      email: user.email,
      walletAddress: user.walletAddress,
      displayName: user.displayName,
      avatarUrl: user.avatarUrl,
      timezone: user.timezone,
      notificationPreferences: user.notificationPreferences,
      preferences: user.preferences,
      createdAt: user.createdAt,
      lastLoginAt: user.lastLoginAt,
    };

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user: profileData,
      }),
    };
  } catch (error) {
    console.error('Error getting profile:', error);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to get profile',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
}
