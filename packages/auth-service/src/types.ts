export interface MagicLinkToken {
  token: string;
  email: string;
  createdAt: number;
  expiresAt: number;
  used: boolean;
}

export interface JWTPayload {
  userId: string;
  email: string;
  iat: number;
  exp: number;
}

export interface User {
  userId: string;
  email?: string; // Optional for wallet-only users
  createdAt: number;
  lastLoginAt: number;
  walletAddress?: string;
  // Profile fields
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

export interface SendMagicLinkRequest {
  email: string;
}

export interface VerifyMagicLinkRequest {
  token: string;
}

export interface AuthenticatedRequest {
  userId: string;
  email: string;
}
