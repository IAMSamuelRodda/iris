/**
 * Wallet tools for Solana blockchain interaction
 */

import { Connection, PublicKey, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { z } from "zod";
import { ToolError } from "../errors.js";

// Default to mainnet-beta, can be overridden via environment
const RPC_ENDPOINT =
  process.env.SOLANA_RPC_URL ?? "https://api.mainnet-beta.solana.com";

const connection = new Connection(RPC_ENDPOINT, "confirmed");

// Input schema for getWalletBalance
const inputSchema = z.object({
  walletAddress: z
    .string()
    .describe("The Solana wallet address (base58 encoded public key)"),
  includeTokens: z
    .boolean()
    .optional()
    .default(false)
    .describe("Whether to include SPL token balances"),
});

export const getWalletBalanceSchema = {
  type: "object" as const,
  properties: {
    walletAddress: {
      type: "string",
      description: "The Solana wallet address (base58 encoded public key)",
    },
    includeTokens: {
      type: "boolean",
      description: "Whether to include SPL token balances",
      default: false,
    },
  },
  required: ["walletAddress"],
};

export interface WalletBalance {
  address: string;
  solBalance: number;
  solBalanceLamports: number;
  tokens?: TokenBalance[];
}

export interface TokenBalance {
  mint: string;
  amount: string;
  decimals: number;
  uiAmount: number;
}

/**
 * Get the SOL and optionally token balances for a wallet
 */
export async function getWalletBalance(
  args: Record<string, unknown>
): Promise<WalletBalance> {
  const parsed = inputSchema.safeParse(args);

  if (!parsed.success) {
    throw new ToolError(
      `Invalid arguments: ${parsed.error.message}`,
      "INVALID_ARGS"
    );
  }

  const { walletAddress, includeTokens } = parsed.data;

  let publicKey: PublicKey;
  try {
    publicKey = new PublicKey(walletAddress);
  } catch {
    throw new ToolError(
      `Invalid wallet address: ${walletAddress}`,
      "INVALID_ADDRESS"
    );
  }

  try {
    const lamports = await connection.getBalance(publicKey);

    const result: WalletBalance = {
      address: walletAddress,
      solBalance: lamports / LAMPORTS_PER_SOL,
      solBalanceLamports: lamports,
    };

    if (includeTokens) {
      const tokenAccounts = await connection.getParsedTokenAccountsByOwner(
        publicKey,
        { programId: new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") }
      );

      result.tokens = tokenAccounts.value.map((account) => {
        const info = account.account.data.parsed.info;
        return {
          mint: info.mint,
          amount: info.tokenAmount.amount,
          decimals: info.tokenAmount.decimals,
          uiAmount: info.tokenAmount.uiAmount ?? 0,
        };
      });
    }

    return result;
  } catch (error) {
    if (error instanceof ToolError) throw error;

    throw new ToolError(
      `Failed to fetch balance: ${error instanceof Error ? error.message : "Unknown error"}`,
      "RPC_ERROR"
    );
  }
}
