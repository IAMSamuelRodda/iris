/**
 * Star Atlas Fleet tools using SAGE API
 *
 * Provides fleet status information for Star Atlas players.
 *
 * MVP Implementation Notes:
 * - Discovers player profile existence
 * - Full fleet enumeration requires SAGE SDK with IDL (post-MVP)
 * - See: https://build.staratlas.com/dev-resources/apis-and-data/sage
 */

import { Connection, PublicKey } from "@solana/web3.js";
import { z } from "zod";
import { ToolError } from "../errors.js";

// Default to mainnet-beta
const RPC_ENDPOINT =
  process.env.SOLANA_RPC_URL ?? "https://api.mainnet-beta.solana.com";

const connection = new Connection(RPC_ENDPOINT, "confirmed");

// Profile Faction Program ID (where player profiles live)
const PROFILE_FACTION_PROGRAM_ID = new PublicKey(
  "pFACSRuobDmvfMKq1bAzwj27t6d2GJhSCHb1VcfnRmq"
);

// Input schema for getFleetStatus
const inputSchema = z.object({
  walletAddress: z
    .string()
    .describe(
      "The Solana wallet address to check fleets for (base58 encoded public key)"
    ),
});

export const getFleetStatusSchema = {
  type: "object" as const,
  properties: {
    walletAddress: {
      type: "string",
      description:
        "The Solana wallet address to check fleets for (base58 encoded public key)",
    },
  },
  required: ["walletAddress"],
};

// Fleet state types (for future use when SAGE SDK integrated)
export type FleetState =
  | "Idle"
  | "MineAsteroid"
  | "MoveSubwarp"
  | "MoveWarp"
  | "Respawn"
  | "StarbaseLoadingBay"
  | "Unknown";

export interface FleetInfo {
  address: string;
  label: string;
  state: FleetState;
  stateDetails: Record<string, unknown>;
  shipCount: number;
  stats: {
    cargoCapacity: number;
    fuelCapacity: number;
    ammoCapacity: number;
    foodCapacity: number;
  };
  location?: {
    sector: [number, number];
    starbase?: string;
  };
}

export interface FleetStatusResult {
  walletAddress: string;
  playerProfileAddress: string | null;
  fleetCount: number;
  fleets: FleetInfo[];
  note?: string;
}

/**
 * Find player profile accounts for a wallet
 *
 * Star Atlas uses ProfileFaction accounts that link wallets to profiles.
 */
async function findPlayerProfiles(
  walletAddress: PublicKey
): Promise<PublicKey[]> {
  try {
    // Search for ProfileFaction accounts that reference this wallet
    const accounts = await connection.getProgramAccounts(
      PROFILE_FACTION_PROGRAM_ID,
      {
        filters: [
          {
            memcmp: {
              offset: 8, // After discriminator
              bytes: walletAddress.toBase58(),
            },
          },
        ],
      }
    );

    return accounts.map((acc) => acc.pubkey);
  } catch (error) {
    console.error("Error finding player profiles:", error);
    return [];
  }
}

/**
 * Get fleet status for a wallet address
 *
 * MVP Implementation:
 * - Discovers player profile existence on-chain
 * - Returns profile address for verification
 * - Full fleet data requires SAGE SDK integration (post-MVP spike)
 */
export async function getFleetStatus(
  args: Record<string, unknown>
): Promise<FleetStatusResult> {
  const parsed = inputSchema.safeParse(args);

  if (!parsed.success) {
    throw new ToolError(
      `Invalid arguments: ${parsed.error.message}`,
      "INVALID_ARGS"
    );
  }

  const { walletAddress } = parsed.data;

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
    // Find player profile accounts
    const profileAccounts = await findPlayerProfiles(publicKey);

    const hasProfile = profileAccounts.length > 0;
    const profileAddress = hasProfile ? profileAccounts[0].toBase58() : null;

    if (!hasProfile) {
      return {
        walletAddress,
        playerProfileAddress: null,
        fleetCount: 0,
        fleets: [],
        note:
          "No Star Atlas player profile found for this wallet. " +
          "Create a profile at https://sage.staratlas.com/ to play SAGE.",
      };
    }

    // MVP: Return profile verification
    // Full fleet enumeration requires SAGE SDK with proper IDL parsing
    return {
      walletAddress,
      playerProfileAddress: profileAddress,
      fleetCount: 0,
      fleets: [],
      note:
        "Player profile verified. Fleet enumeration requires SAGE SDK integration. " +
        "View fleet details at https://sage.staratlas.com/",
    };
  } catch (error) {
    if (error instanceof ToolError) throw error;

    throw new ToolError(
      `Failed to fetch fleet status: ${error instanceof Error ? error.message : "Unknown error"}`,
      "RPC_ERROR"
    );
  }
}
