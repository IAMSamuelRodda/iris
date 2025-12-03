/**
 * Text Chunker for Streaming TTS
 *
 * Buffers streaming text and yields complete chunks for TTS synthesis.
 * Supports two modes:
 * - "sentence": Yields each sentence (faster first audio, potentially choppier)
 * - "paragraph": Yields each paragraph (slower first audio, more natural prosody)
 *
 * Trade-off: Sentence mode reduces latency but may sound more robotic.
 * Paragraph mode gives Chatterbox more context for natural intonation.
 */

export type ChunkMode = "sentence" | "paragraph";

export interface ChunkerOptions {
  mode: ChunkMode;
  /** Minimum characters before yielding (avoids tiny chunks) */
  minChunkSize?: number;
  /** Maximum characters before forcing a yield (prevents huge chunks) */
  maxChunkSize?: number;
}

const DEFAULT_OPTIONS: ChunkerOptions = {
  mode: "sentence",
  minChunkSize: 10,
  maxChunkSize: 500,
};

/**
 * Common abbreviations that shouldn't trigger sentence breaks.
 * The period after these is NOT a sentence boundary.
 */
const ABBREVIATIONS = new Set([
  "mr",
  "mrs",
  "ms",
  "dr",
  "prof",
  "sr",
  "jr",
  "vs",
  "etc",
  "inc",
  "ltd",
  "co",
  "corp",
  "dept",
  "est",
  "approx",
  "govt",
  "vol",
  "no",
  "fig",
  "e.g",
  "i.e",
  "viz",
  "cf",
  "al", // et al.
]);

/**
 * Text chunker that accumulates streaming text and yields complete chunks.
 *
 * Usage:
 * ```typescript
 * const chunker = new TextChunker({ mode: "sentence" });
 *
 * for await (const textDelta of stream) {
 *   const chunks = chunker.add(textDelta);
 *   for (const chunk of chunks) {
 *     voiceClient.synthesize(chunk);
 *   }
 * }
 *
 * // Don't forget remaining text at end
 * const final = chunker.flush();
 * if (final) voiceClient.synthesize(final);
 * ```
 */
export class TextChunker {
  private buffer = "";
  private options: Required<ChunkerOptions>;

  constructor(options: Partial<ChunkerOptions> = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options } as Required<ChunkerOptions>;
  }

  /**
   * Add text to the buffer and return any complete chunks.
   */
  add(text: string): string[] {
    this.buffer += text;
    return this.extractChunks();
  }

  /**
   * Flush any remaining text in the buffer.
   * Call this when the stream ends.
   */
  flush(): string | null {
    const remaining = this.buffer.trim();
    this.buffer = "";
    return remaining.length >= this.options.minChunkSize ? remaining : null;
  }

  /**
   * Reset the chunker state.
   */
  reset(): void {
    this.buffer = "";
  }

  /**
   * Get current buffer contents (for debugging).
   */
  getBuffer(): string {
    return this.buffer;
  }

  private extractChunks(): string[] {
    const chunks: string[] = [];

    while (true) {
      const chunk = this.options.mode === "sentence"
        ? this.extractSentence()
        : this.extractParagraph();

      if (!chunk) break;

      // Only yield if meets minimum size (unless forced by max size)
      if (chunk.length >= this.options.minChunkSize) {
        chunks.push(chunk);
      } else {
        // Put it back if too small
        this.buffer = chunk + this.buffer;
        break;
      }
    }

    // Force yield if buffer exceeds max size
    if (this.buffer.length > this.options.maxChunkSize) {
      const forcedChunk = this.forceExtract();
      if (forcedChunk) {
        chunks.push(forcedChunk);
      }
    }

    return chunks;
  }

  /**
   * Extract a complete sentence from the buffer.
   * Returns null if no complete sentence is found.
   */
  private extractSentence(): string | null {
    // Look for sentence-ending punctuation followed by space or newline
    // But avoid false positives from abbreviations
    const sentenceEndRegex = /[.!?][\s\n]/g;
    let match: RegExpExecArray | null;

    while ((match = sentenceEndRegex.exec(this.buffer)) !== null) {
      const endPos = match.index + 1; // Include the punctuation
      const potentialSentence = this.buffer.slice(0, endPos);

      // Check if this is a false positive (abbreviation)
      if (this.isAbbreviation(potentialSentence)) {
        continue;
      }

      // Extract the sentence
      this.buffer = this.buffer.slice(endPos).trimStart();
      return potentialSentence.trim();
    }

    return null;
  }

  /**
   * Extract a complete paragraph from the buffer.
   * Returns null if no complete paragraph is found.
   */
  private extractParagraph(): string | null {
    // Look for double newline (paragraph break)
    const paragraphBreak = this.buffer.indexOf("\n\n");
    if (paragraphBreak !== -1) {
      const paragraph = this.buffer.slice(0, paragraphBreak);
      this.buffer = this.buffer.slice(paragraphBreak + 2).trimStart();
      return paragraph.trim();
    }

    // Also check for single newline followed by blank-ish content
    // (some systems use single \n for paragraphs)
    const singleNewline = this.buffer.indexOf("\n");
    if (singleNewline !== -1) {
      const afterNewline = this.buffer.slice(singleNewline + 1);
      // If what follows starts with another newline or significant whitespace
      if (afterNewline.startsWith("\n") || afterNewline.match(/^\s{2,}/)) {
        const paragraph = this.buffer.slice(0, singleNewline);
        this.buffer = afterNewline.trimStart();
        return paragraph.trim();
      }
    }

    return null;
  }

  /**
   * Force extract a chunk when buffer exceeds max size.
   * Tries to break at a natural point (space, comma, etc.)
   */
  private forceExtract(): string | null {
    if (this.buffer.length === 0) return null;

    // Try to find a good break point near max size
    const searchStart = Math.max(0, this.options.maxChunkSize - 50);
    const searchEnd = this.options.maxChunkSize;
    const searchRegion = this.buffer.slice(searchStart, searchEnd);

    // Prefer breaking at: sentence end > comma > space
    const sentenceBreak = searchRegion.lastIndexOf(". ");
    if (sentenceBreak !== -1) {
      const breakPoint = searchStart + sentenceBreak + 1;
      const chunk = this.buffer.slice(0, breakPoint);
      this.buffer = this.buffer.slice(breakPoint).trimStart();
      return chunk.trim();
    }

    const commaBreak = searchRegion.lastIndexOf(", ");
    if (commaBreak !== -1) {
      const breakPoint = searchStart + commaBreak + 1;
      const chunk = this.buffer.slice(0, breakPoint);
      this.buffer = this.buffer.slice(breakPoint).trimStart();
      return chunk.trim();
    }

    const spaceBreak = searchRegion.lastIndexOf(" ");
    if (spaceBreak !== -1) {
      const breakPoint = searchStart + spaceBreak;
      const chunk = this.buffer.slice(0, breakPoint);
      this.buffer = this.buffer.slice(breakPoint).trimStart();
      return chunk.trim();
    }

    // No good break point, just split at max
    const chunk = this.buffer.slice(0, this.options.maxChunkSize);
    this.buffer = this.buffer.slice(this.options.maxChunkSize);
    return chunk.trim();
  }

  /**
   * Check if the text ends with a common abbreviation.
   */
  private isAbbreviation(text: string): boolean {
    // Get the last word before the period
    const words = text.trim().split(/\s+/);
    if (words.length === 0) return false;

    const lastWord = words[words.length - 1].toLowerCase();
    // Remove trailing punctuation for comparison
    const wordWithoutPunc = lastWord.replace(/[.!?]+$/, "");

    return ABBREVIATIONS.has(wordWithoutPunc);
  }
}

/**
 * Create a chunker with the specified mode.
 */
export function createChunker(mode: ChunkMode = "sentence"): TextChunker {
  return new TextChunker({ mode });
}
