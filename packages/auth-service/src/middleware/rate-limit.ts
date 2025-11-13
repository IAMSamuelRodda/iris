import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, PutCommand, UpdateCommand } from '@aws-sdk/lib-dynamodb';

const ddbClient = new DynamoDBClient({});
const ddb = DynamoDBDocumentClient.from(ddbClient);

const RATE_LIMIT_TABLE = process.env.RATE_LIMIT_TABLE || '';

interface RateLimitConfig {
  maxRequests: number;
  windowSeconds: number;
}

interface RateLimitRecord {
  key: string;
  count: number;
  expiresAt: number;
}

const DEFAULT_CONFIG: RateLimitConfig = {
  maxRequests: 5,
  windowSeconds: 60,
};

/**
 * Rate limiting middleware using DynamoDB
 * Tracks request counts per identifier (email/IP) within a time window
 */
export async function checkRateLimit(
  identifier: string,
  config: RateLimitConfig = DEFAULT_CONFIG
): Promise<{ allowed: boolean; retryAfter?: number }> {
  const now = Date.now();
  const windowStart = now - (config.windowSeconds * 1000);
  const key = `ratelimit:${identifier}:${Math.floor(now / (config.windowSeconds * 1000))}`;

  try {
    // Get current count
    const result = await ddb.send(
      new GetCommand({
        TableName: RATE_LIMIT_TABLE,
        Key: { key },
      })
    );

    const record = result.Item as RateLimitRecord | undefined;

    if (!record) {
      // First request in this window
      await ddb.send(
        new PutCommand({
          TableName: RATE_LIMIT_TABLE,
          Item: {
            key,
            count: 1,
            expiresAt: now + (config.windowSeconds * 1000),
          },
        })
      );
      return { allowed: true };
    }

    if (record.count >= config.maxRequests) {
      // Rate limit exceeded
      const retryAfter = Math.ceil((record.expiresAt - now) / 1000);
      return { allowed: false, retryAfter };
    }

    // Increment count
    await ddb.send(
      new UpdateCommand({
        TableName: RATE_LIMIT_TABLE,
        Key: { key },
        UpdateExpression: 'SET #count = #count + :inc',
        ExpressionAttributeNames: { '#count': 'count' },
        ExpressionAttributeValues: { ':inc': 1 },
      })
    );

    return { allowed: true };
  } catch (error) {
    console.error('Rate limit check failed:', error);
    // Fail open - allow request if rate limit check fails
    return { allowed: true };
  }
}

/**
 * Extract identifier from event (email from body or IP from headers)
 */
export function extractIdentifier(event: APIGatewayProxyEvent): string {
  // Try to get email from request body
  try {
    const body = JSON.parse(event.body || '{}');
    if (body.email) {
      return body.email.toLowerCase();
    }
  } catch {
    // Invalid JSON, continue to IP fallback
  }

  // Fallback to IP address
  const ip = event.requestContext?.identity?.sourceIp ||
             event.headers['x-forwarded-for']?.split(',')[0].trim() ||
             'unknown';
  return ip;
}

/**
 * Rate limit middleware wrapper
 */
export async function rateLimitMiddleware(
  event: APIGatewayProxyEvent,
  config?: RateLimitConfig
): Promise<APIGatewayProxyResult | null> {
  const identifier = extractIdentifier(event);
  const result = await checkRateLimit(identifier, config);

  if (!result.allowed) {
    return {
      statusCode: 429,
      headers: {
        'Content-Type': 'application/json',
        'Retry-After': String(result.retryAfter || 60),
      },
      body: JSON.stringify({
        error: 'Too many requests',
        message: `Please try again in ${result.retryAfter} seconds`,
      }),
    };
  }

  return null; // Allow request to continue
}
