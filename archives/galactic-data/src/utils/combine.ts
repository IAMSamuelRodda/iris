// src\utils\combine.ts
import NodeCache from 'node-cache';
import { staratlasOrderAccountType } from '../types/staratlasOrderDataTypes';
import { coingeckoTokenType } from '../types/coingeckoDataTypes';

const cache = new NodeCache();

// Adjust the function to accept data objects directly
export function combineJsonData(staratlasData: staratlasOrderAccountType, coingeckoData: coingeckoTokenType): string {
  // Cache the data for future use
  cache.set("staratlasOrderAccountData", staratlasData);
  cache.set("coingeckoTokenData", coingeckoData);

  const combinedData = {
    coingeckoTokenData: coingeckoData || {},
    staratlasOrderAccountData: staratlasData || [],
  };

  return JSON.stringify(combinedData, null, 2);
}