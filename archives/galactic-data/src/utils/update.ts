// src\utils\update.ts
// Utility function to check if the JSON file needs updating
import { promises as fs } from 'fs';

export async function needsUpdate(filePath: string, interval: number): Promise<boolean> {
    try {
        const stats = await fs.stat(filePath);
        const now = new Date();
        const lastModified = new Date(stats.mtime);
        const diff = now.getTime() - lastModified.getTime();
        return diff > interval;
    } catch (error: unknown) { // Note the change here to annotate the error type as unknown
        // Assert error as NodeJS.ErrnoException to access the 'code' property
        if (error instanceof Error && (error as NodeJS.ErrnoException).code === 'ENOENT') {
            console.log(`File ${filePath} does not exist, needs creation.`);
            return true; // File doesn't exist, needs update (and creation)
        }
        console.error('Error checking file update need:', error);
        throw error; // Rethrow unexpected errors
    }
}