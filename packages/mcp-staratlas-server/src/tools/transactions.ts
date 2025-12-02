/**
 * Transaction history tools for Solana blockchain
 */

import {
  Connection,
  PublicKey,
  LAMPORTS_PER_SOL,
  ParsedTransactionWithMeta,
} from "@solana/web3.js";
import { z } from "zod";
import { ToolError } from "../errors.js";

// Default to mainnet-beta, can be overridden via environment
const RPC_ENDPOINT =
  process.env.SOLANA_RPC_URL ?? "https://api.mainnet-beta.solana.com";

const connection = new Connection(RPC_ENDPOINT, "confirmed");

// Input schema for getTransactionHistory
const inputSchema = z.object({
  walletAddress: z
    .string()
    .describe("The Solana wallet address (base58 encoded public key)"),
  limit: z
    .number()
    .int()
    .min(1)
    .max(50)
    .optional()
    .default(10)
    .describe("Maximum number of transactions to return (1-50, default 10)"),
  before: z
    .string()
    .optional()
    .describe("Fetch transactions before this signature (for pagination)"),
});

export const getTransactionHistorySchema = {
  type: "object" as const,
  properties: {
    walletAddress: {
      type: "string",
      description: "The Solana wallet address (base58 encoded public key)",
    },
    limit: {
      type: "number",
      description: "Maximum number of transactions to return (1-50, default 10)",
      default: 10,
    },
    before: {
      type: "string",
      description: "Fetch transactions before this signature (for pagination)",
    },
  },
  required: ["walletAddress"],
};

export interface TransactionInfo {
  signature: string;
  blockTime: number | null;
  slot: number;
  status: "success" | "failed";
  fee: number;
  feeLamports: number;
  type: string;
  description: string;
}

export interface TransactionHistory {
  address: string;
  transactions: TransactionInfo[];
  hasMore: boolean;
  oldestSignature: string | null;
}

/**
 * Infer transaction type from parsed transaction
 */
function inferTransactionType(
  tx: ParsedTransactionWithMeta | null,
  walletAddress: string
): { type: string; description: string } {
  if (!tx?.meta || !tx.transaction) {
    return { type: "unknown", description: "Unable to parse transaction" };
  }

  const instructions = tx.transaction.message.instructions;
  const accountKeys = tx.transaction.message.accountKeys.map((k) =>
    k.pubkey.toBase58()
  );

  // Check for token transfers
  for (const ix of instructions) {
    if ("program" in ix) {
      const program = ix.program;
      const parsed = "parsed" in ix ? ix.parsed : null;

      if (program === "spl-token" && parsed) {
        const ixType = parsed.type;
        if (ixType === "transfer" || ixType === "transferChecked") {
          const info = parsed.info;
          const isOutgoing = info.authority === walletAddress || info.source === walletAddress;
          return {
            type: "token_transfer",
            description: isOutgoing
              ? `Sent ${info.tokenAmount?.uiAmount ?? info.amount} tokens`
              : `Received tokens`,
          };
        }
      }

      if (program === "system" && parsed) {
        const ixType = parsed.type;
        if (ixType === "transfer") {
          const info = parsed.info;
          const isOutgoing = info.source === walletAddress;
          const amount = info.lamports / LAMPORTS_PER_SOL;
          return {
            type: "sol_transfer",
            description: isOutgoing
              ? `Sent ${amount.toFixed(4)} SOL`
              : `Received ${amount.toFixed(4)} SOL`,
          };
        }
      }
    }
  }

  // Check for known program interactions
  const programIds = accountKeys.filter((key) => {
    // Common Solana programs
    return (
      key === "11111111111111111111111111111111" || // System
      key === "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" || // Token
      key === "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL" // Associated Token
    );
  });

  if (programIds.length > 0) {
    return { type: "program_interaction", description: "Program interaction" };
  }

  return { type: "other", description: "Transaction" };
}

/**
 * Get transaction history for a wallet address
 */
export async function getTransactionHistory(
  args: Record<string, unknown>
): Promise<TransactionHistory> {
  const parsed = inputSchema.safeParse(args);

  if (!parsed.success) {
    throw new ToolError(
      `Invalid arguments: ${parsed.error.message}`,
      "INVALID_ARGS"
    );
  }

  const { walletAddress, limit, before } = parsed.data;

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
    // Fetch signatures for the address
    const signatures = await connection.getSignaturesForAddress(publicKey, {
      limit: limit + 1, // Fetch one extra to check if there are more
      before: before || undefined,
    });

    const hasMore = signatures.length > limit;
    const signaturesForFetch = signatures.slice(0, limit);

    // Fetch full transaction details for each signature
    const transactions: TransactionInfo[] = [];

    for (const sig of signaturesForFetch) {
      let txInfo: TransactionInfo;

      try {
        const tx = await connection.getParsedTransaction(sig.signature, {
          maxSupportedTransactionVersion: 0,
        });

        const { type, description } = inferTransactionType(tx, walletAddress);

        txInfo = {
          signature: sig.signature,
          blockTime: sig.blockTime ?? null,
          slot: sig.slot,
          status: sig.err ? "failed" : "success",
          fee: tx?.meta?.fee ? tx.meta.fee / LAMPORTS_PER_SOL : 0,
          feeLamports: tx?.meta?.fee ?? 0,
          type,
          description,
        };
      } catch {
        // If we can't fetch details, provide basic info from signature
        txInfo = {
          signature: sig.signature,
          blockTime: sig.blockTime ?? null,
          slot: sig.slot,
          status: sig.err ? "failed" : "success",
          fee: 0,
          feeLamports: 0,
          type: "unknown",
          description: "Transaction details unavailable",
        };
      }

      transactions.push(txInfo);
    }

    const oldestSignature =
      transactions.length > 0
        ? transactions[transactions.length - 1].signature
        : null;

    return {
      address: walletAddress,
      transactions,
      hasMore,
      oldestSignature,
    };
  } catch (error) {
    if (error instanceof ToolError) throw error;

    throw new ToolError(
      `Failed to fetch transaction history: ${error instanceof Error ? error.message : "Unknown error"}`,
      "RPC_ERROR"
    );
  }
}
