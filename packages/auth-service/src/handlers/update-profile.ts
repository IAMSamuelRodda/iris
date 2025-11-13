import { APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, UpdateCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import type { AuthenticatedEvent } from '../middleware/auth.js';
import type { User } from '../types.js';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);

const USERS_TABLE = process.env.USERS_TABLE || '';

interface UpdateProfileRequest {
  displayName?: string;
  avatarUrl?: string;
  timezone?: string;
  notificationPreferences?: {
    email?: boolean;
    push?: boolean;
    voice?: boolean;
  };
  preferences?: {
    language?: string;
    theme?: 'light' | 'dark' | 'auto';
    voiceEnabled?: boolean;
  };
}

export async function updateProfile(
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

    const body: UpdateProfileRequest = JSON.parse(event.body || '{}');

    // Build update expression dynamically
    const updateExpressions: string[] = [];
    const expressionAttributeNames: Record<string, string> = {};
    const expressionAttributeValues: Record<string, any> = {};

    let valueCounter = 0;

    if (body.displayName !== undefined) {
      updateExpressions.push(`displayName = :val${valueCounter}`);
      expressionAttributeValues[`:val${valueCounter}`] = body.displayName;
      valueCounter++;
    }

    if (body.avatarUrl !== undefined) {
      updateExpressions.push(`avatarUrl = :val${valueCounter}`);
      expressionAttributeValues[`:val${valueCounter}`] = body.avatarUrl;
      valueCounter++;
    }

    if (body.timezone !== undefined) {
      updateExpressions.push(`timezone = :val${valueCounter}`);
      expressionAttributeValues[`:val${valueCounter}`] = body.timezone;
      valueCounter++;
    }

    if (body.notificationPreferences !== undefined) {
      updateExpressions.push(`notificationPreferences = :val${valueCounter}`);
      expressionAttributeValues[`:val${valueCounter}`] = body.notificationPreferences;
      valueCounter++;
    }

    if (body.preferences !== undefined) {
      updateExpressions.push(`preferences = :val${valueCounter}`);
      expressionAttributeValues[`:val${valueCounter}`] = body.preferences;
      valueCounter++;
    }

    if (updateExpressions.length === 0) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'No fields to update' }),
      };
    }

    // Update user profile
    await ddb.send(
      new UpdateCommand({
        TableName: USERS_TABLE,
        Key: { userId: event.auth.userId },
        UpdateExpression: `SET ${updateExpressions.join(', ')}`,
        ExpressionAttributeValues: expressionAttributeValues,
        ...(Object.keys(expressionAttributeNames).length > 0 && {
          ExpressionAttributeNames: expressionAttributeNames,
        }),
      })
    );

    // Get updated user profile
    const result = await ddb.send(
      new GetCommand({
        TableName: USERS_TABLE,
        Key: { userId: event.auth.userId },
      })
    );

    const user = result.Item as User;

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user: {
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
        },
      }),
    };
  } catch (error) {
    console.error('Error updating profile:', error);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to update profile',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
}
