import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';
import { SESClient, SendEmailCommand } from '@aws-sdk/client-ses';
import { nanoid } from 'nanoid';
import { rateLimitMiddleware } from '../middleware/rate-limit.js';
import { logger } from '../utils/logger.js';
import type { SendMagicLinkRequest, MagicLinkToken } from '../types.js';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);
const ses = new SESClient({});

const TOKENS_TABLE = process.env.TOKENS_TABLE || '';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const FROM_EMAIL = process.env.FROM_EMAIL || 'noreply@staratlas-agent.com';
const TOKEN_EXPIRY_MINUTES = 15;

export async function sendMagicLink(
  event: APIGatewayProxyEvent
): Promise<APIGatewayProxyResult> {
  try {
    // Check rate limit first
    const rateLimitResult = await rateLimitMiddleware(event, {
      maxRequests: 3, // 3 requests per minute
      windowSeconds: 60,
    });

    if (rateLimitResult) {
      return rateLimitResult;
    }

    const body: SendMagicLinkRequest = JSON.parse(event.body || '{}');

    if (!body.email) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Email is required' }),
      };
    }

    // Normalize email to lowercase
    const normalizedEmail = body.email.toLowerCase().trim();

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(normalizedEmail)) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Invalid email format' }),
      };
    }

    // Generate secure token
    const token = nanoid(32);
    const now = Date.now();
    const expiresAt = now + (TOKEN_EXPIRY_MINUTES * 60 * 1000);

    // Store token in DynamoDB
    const tokenData: MagicLinkToken = {
      token,
      email: normalizedEmail,
      createdAt: now,
      expiresAt,
      used: false,
    };

    await ddb.send(
      new PutCommand({
        TableName: TOKENS_TABLE,
        Item: tokenData,
      })
    );

    // Send email with magic link
    const magicLink = `${FRONTEND_URL}/auth/verify?token=${token}`;
    const emailParams = {
      Source: FROM_EMAIL,
      Destination: {
        ToAddresses: [normalizedEmail],
      },
      Message: {
        Subject: {
          Data: 'Your Star Atlas Agent Login Link',
        },
        Body: {
          Html: {
            Data: `
              <h2>Welcome to Star Atlas Agent</h2>
              <p>Click the link below to sign in to your account:</p>
              <p><a href="${magicLink}">Sign in to Star Atlas Agent</a></p>
              <p>This link will expire in ${TOKEN_EXPIRY_MINUTES} minutes.</p>
              <p>If you didn't request this email, you can safely ignore it.</p>
            `,
          },
          Text: {
            Data: `Welcome to Star Atlas Agent\n\nClick the link below to sign in:\n${magicLink}\n\nThis link expires in ${TOKEN_EXPIRY_MINUTES} minutes.`,
          },
        },
      },
    };

    await ses.send(new SendEmailCommand(emailParams));

    logger.info('Magic link sent successfully', {
      email: normalizedEmail,
      tokenExpiresIn: TOKEN_EXPIRY_MINUTES,
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Magic link sent successfully',
        email: normalizedEmail,
      }),
    };
  } catch (error) {
    logger.error(
      'Failed to send magic link',
      { email: (error as any).email },
      error instanceof Error ? error : new Error(String(error))
    );
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to send magic link',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
    };
  }
}
