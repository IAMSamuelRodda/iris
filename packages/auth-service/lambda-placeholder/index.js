// Placeholder Lambda handler for auth-service
exports.handler = async (event) => {
  const path = event.rawPath;
  const method = event.requestContext.http.method;

  // Send magic link endpoint
  if (path === '/auth/magic-link' && method === 'POST') {
    const body = JSON.parse(event.body || '{}');
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Magic link placeholder - email sending not yet implemented',
        email: body.email || 'No email provided',
        note: 'Check your email for the login link (not actually sent in placeholder mode)',
      }),
    };
  }

  // Verify magic link endpoint
  if (path === '/auth/verify' && method === 'POST') {
    const body = JSON.parse(event.body || '{}');
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Magic link verification placeholder',
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.placeholder',
        user: {
          userId: 'placeholder-user-id',
          email: 'user@example.com',
        },
        note: 'This is a placeholder JWT token',
      }),
    };
  }

  // Wallet challenge endpoint
  if (path === '/auth/wallet/challenge' && method === 'POST') {
    const body = JSON.parse(event.body || '{}');
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Wallet challenge placeholder',
        challenge: `Sign this message to authenticate with Star Atlas Agent.\n\nWallet: ${body.walletAddress || 'unknown'}\nNonce: placeholder-nonce\nTimestamp: ${Date.now()}`,
        challengeId: 'placeholder-challenge-id',
        expiresAt: Date.now() + (5 * 60 * 1000),
      }),
    };
  }

  // Wallet verify endpoint
  if (path === '/auth/wallet/verify' && method === 'POST') {
    const body = JSON.parse(event.body || '{}');
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Wallet verification placeholder',
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.wallet-placeholder',
        user: {
          userId: 'placeholder-user-id',
          email: 'wallet@placeholder.com',
          walletAddress: body.walletAddress || 'unknown',
        },
        note: 'This is a placeholder JWT token for wallet auth',
      }),
    };
  }

  return {
    statusCode: 404,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ error: 'Not found', path }),
  };
};
