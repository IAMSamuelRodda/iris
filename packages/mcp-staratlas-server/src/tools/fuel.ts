/**
 * Fuel prediction tools for Star Atlas SAGE fleets
 *
 * Calculates fuel depletion time based on current fuel and consumption rates.
 * MVP: Works with user-provided data
 * Post-MVP: Auto-fetch from SAGE accounts after SDK integration
 */

import { z } from "zod";
import { ToolError } from "../errors.js";

// Input schema for predictFuelDepletion
const inputSchema = z.object({
  currentFuel: z
    .number()
    .min(0)
    .describe("Current fuel amount in the fleet's fuel tank"),
  fuelCapacity: z
    .number()
    .min(0)
    .describe("Maximum fuel capacity of the fleet"),
  consumptionRate: z
    .number()
    .min(0)
    .describe("Fuel consumption rate per hour (based on current activity)"),
  activity: z
    .enum(["idle", "mining", "subwarp", "warp"])
    .optional()
    .default("idle")
    .describe("Current fleet activity (affects consumption context)"),
  fleetName: z
    .string()
    .optional()
    .describe("Optional fleet name for identification in response"),
});

export const predictFuelDepletionSchema = {
  type: "object" as const,
  properties: {
    currentFuel: {
      type: "number",
      description: "Current fuel amount in the fleet's fuel tank",
    },
    fuelCapacity: {
      type: "number",
      description: "Maximum fuel capacity of the fleet",
    },
    consumptionRate: {
      type: "number",
      description: "Fuel consumption rate per hour (based on current activity)",
    },
    activity: {
      type: "string",
      enum: ["idle", "mining", "subwarp", "warp"],
      description: "Current fleet activity (affects consumption context)",
      default: "idle",
    },
    fleetName: {
      type: "string",
      description: "Optional fleet name for identification in response",
    },
  },
  required: ["currentFuel", "fuelCapacity", "consumptionRate"],
};

export interface FuelPrediction {
  fleetName: string;
  currentFuel: number;
  fuelCapacity: number;
  fuelPercentage: number;
  consumptionRate: number;
  activity: string;
  hoursUntilEmpty: number | null;
  depletionTime: string | null;
  status: "critical" | "low" | "moderate" | "good" | "full";
  recommendation: string;
}

/**
 * Get fuel status category based on percentage
 */
function getFuelStatus(
  percentage: number,
  hoursRemaining: number | null
): "critical" | "low" | "moderate" | "good" | "full" {
  if (percentage >= 95) return "full";
  if (percentage >= 50) return "good";
  if (percentage >= 25) return "moderate";
  if (percentage >= 10 || (hoursRemaining !== null && hoursRemaining > 2))
    return "low";
  return "critical";
}

/**
 * Generate recommendation based on fuel status and activity
 */
function getRecommendation(
  status: string,
  activity: string,
  hoursRemaining: number | null
): string {
  if (status === "critical") {
    if (activity === "warp" || activity === "subwarp") {
      return "URGENT: Return to starbase immediately for refueling. Risk of stranding.";
    }
    if (activity === "mining") {
      return "URGENT: Stop mining and return to starbase. Fuel critically low.";
    }
    return "URGENT: Refuel immediately. Fleet at risk of becoming stranded.";
  }

  if (status === "low") {
    if (activity === "mining") {
      return "Consider ending mining session soon. Plan refuel trip.";
    }
    return "Plan refueling soon. Avoid long-distance travel.";
  }

  if (status === "moderate") {
    if (hoursRemaining !== null && hoursRemaining < 24) {
      return "Fuel adequate for current activity. Monitor consumption.";
    }
    return "Fuel levels acceptable. Continue operations.";
  }

  if (status === "good" || status === "full") {
    return "Fuel levels healthy. Operations can continue normally.";
  }

  return "Monitor fuel levels regularly.";
}

/**
 * Format duration in human-readable form
 */
function formatDuration(hours: number): string {
  if (hours < 1) {
    const minutes = Math.round(hours * 60);
    return `${minutes} minute${minutes !== 1 ? "s" : ""}`;
  }
  if (hours < 24) {
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (m === 0) return `${h} hour${h !== 1 ? "s" : ""}`;
    return `${h}h ${m}m`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = Math.round(hours % 24);
  if (remainingHours === 0) return `${days} day${days !== 1 ? "s" : ""}`;
  return `${days}d ${remainingHours}h`;
}

/**
 * Predict when a fleet will run out of fuel
 *
 * MVP: Uses user-provided fuel data
 * Post-MVP: Will auto-fetch from SAGE accounts
 */
export async function predictFuelDepletion(
  args: Record<string, unknown>
): Promise<FuelPrediction> {
  const parsed = inputSchema.safeParse(args);

  if (!parsed.success) {
    throw new ToolError(
      `Invalid arguments: ${parsed.error.message}`,
      "INVALID_ARGS"
    );
  }

  const {
    currentFuel,
    fuelCapacity,
    consumptionRate,
    activity,
    fleetName,
  } = parsed.data;

  // Validate logical constraints
  if (currentFuel > fuelCapacity) {
    throw new ToolError(
      `Current fuel (${currentFuel}) cannot exceed capacity (${fuelCapacity})`,
      "INVALID_ARGS"
    );
  }

  // Calculate fuel percentage
  const fuelPercentage =
    fuelCapacity > 0 ? (currentFuel / fuelCapacity) * 100 : 0;

  // Calculate time until empty
  let hoursUntilEmpty: number | null = null;
  let depletionTime: string | null = null;

  if (consumptionRate > 0 && currentFuel > 0) {
    hoursUntilEmpty = currentFuel / consumptionRate;
    depletionTime = formatDuration(hoursUntilEmpty);
  } else if (consumptionRate === 0) {
    // No consumption = infinite time (idle or docked)
    hoursUntilEmpty = null;
    depletionTime = "N/A (no consumption)";
  } else {
    // No fuel
    hoursUntilEmpty = 0;
    depletionTime = "Already empty";
  }

  // Determine status and recommendation
  const status = getFuelStatus(fuelPercentage, hoursUntilEmpty);
  const recommendation = getRecommendation(status, activity, hoursUntilEmpty);

  return {
    fleetName: fleetName ?? "Unnamed Fleet",
    currentFuel,
    fuelCapacity,
    fuelPercentage: Math.round(fuelPercentage * 10) / 10,
    consumptionRate,
    activity,
    hoursUntilEmpty:
      hoursUntilEmpty !== null
        ? Math.round(hoursUntilEmpty * 100) / 100
        : null,
    depletionTime,
    status,
    recommendation,
  };
}
