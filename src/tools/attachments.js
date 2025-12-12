import { z } from 'zod';
import { zendeskClient } from '../zendesk-client.js';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export const attachmentsTools = [
  {
    name: "get_attachment",
    description: "Get attachment metadata by ID, including the download URL",
    schema: {
      id: z.number().describe("Attachment ID")
    },
    handler: async ({ id }) => {
      try {
        const result = await zendeskClient.getAttachment(id);
        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error getting attachment: ${error.message}` }],
          isError: true
        };
      }
    }
  },
  {
    name: "download_attachment",
    description: "Download attachment content as base64-encoded data. Use get_attachment first to retrieve the content_url.",
    schema: {
      content_url: z.string().describe("The content_url from the attachment metadata")
    },
    handler: async ({ content_url }) => {
      try {
        const result = await zendeskClient.downloadAttachment(content_url);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              message: "Attachment downloaded successfully",
              contentType: result.contentType,
              size: result.size,
              data: result.data.substring(0, 100) + '...' // Show preview of base64 data
            }, null, 2) + '\n\nNote: Full base64 data is available but truncated in this preview. Use the data field programmatically.'
          }]
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error downloading attachment: ${error.message}` }],
          isError: true
        };
      }
    }
  },
  {
    name: "download_attachment_to_disk",
    description: "Download attachment and save to temporary directory on disk. Returns file path that can be read, searched, or extracted. Ideal for files that need analysis (logs, tarballs, etc.).",
    schema: {
      content_url: z.string().describe("The content_url from the attachment metadata"),
      filename: z.string().optional().describe("Optional filename. If not provided, will be inferred from the URL or content-disposition header")
    },
    handler: async ({ content_url, filename }) => {
      try {
        const result = await zendeskClient.downloadAttachment(content_url);

        // Create temp directory for zendesk attachments
        const tmpDir = path.join(os.tmpdir(), 'zendesk-attachments');
        await fs.mkdir(tmpDir, { recursive: true });

        // Determine filename
        let finalFilename = filename;
        if (!finalFilename) {
          try {
            const urlPath = new URL(content_url).pathname;
            finalFilename = path.basename(urlPath);
          } catch {
            // If URL parsing fails, generate a filename based on content type
            const ext = result.contentType?.split('/')[1] || 'bin';
            finalFilename = `attachment-${Date.now()}.${ext}`;
          }
        }

        const filePath = path.join(tmpDir, finalFilename);

        // Write the file
        await fs.writeFile(filePath, Buffer.from(result.data, 'base64'));

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              message: "Attachment downloaded to disk",
              path: filePath,
              filename: finalFilename,
              contentType: result.contentType,
              size: result.size,
              note: "You can now use Read, Grep, or other file tools to analyze this file"
            }, null, 2)
          }]
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error downloading attachment to disk: ${error.message}` }],
          isError: true
        };
      }
    }
  },
  {
    name: "download_and_extract_attachment",
    description: "Download attachment and automatically extract if it's a tarball (.tar, .tar.gz, .tgz) or zip file. Returns extraction directory path. Perfect for analyzing archived logs or code.",
    schema: {
      content_url: z.string().describe("The content_url from the attachment metadata"),
      filename: z.string().optional().describe("Optional filename. If not provided, will be inferred from the URL")
    },
    handler: async ({ content_url, filename }) => {
      try {
        const result = await zendeskClient.downloadAttachment(content_url);

        // Create temp directory for zendesk attachments
        const tmpDir = path.join(os.tmpdir(), 'zendesk-attachments');
        await fs.mkdir(tmpDir, { recursive: true });

        // Determine filename
        let finalFilename = filename;
        if (!finalFilename) {
          try {
            const urlPath = new URL(content_url).pathname;
            finalFilename = path.basename(urlPath);
          } catch {
            const ext = result.contentType?.split('/')[1] || 'bin';
            finalFilename = `attachment-${Date.now()}.${ext}`;
          }
        }

        const filePath = path.join(tmpDir, finalFilename);

        // Write the file
        await fs.writeFile(filePath, Buffer.from(result.data, 'base64'));

        // Check if it's an archive that should be extracted
        const isArchive = /\.(tar|tar\.gz|tgz|tar\.bz2|tbz2|zip)$/i.test(finalFilename);

        if (!isArchive) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                message: "Attachment downloaded (not an archive)",
                path: filePath,
                filename: finalFilename,
                contentType: result.contentType,
                size: result.size,
                extracted: false
              }, null, 2)
            }]
          };
        }

        // Create extraction directory
        const extractDir = path.join(tmpDir, `extracted-${Date.now()}`);
        await fs.mkdir(extractDir, { recursive: true });

        // Extract based on file type
        let extractCommand;
        if (finalFilename.match(/\.zip$/i)) {
          extractCommand = `unzip -q "${filePath}" -d "${extractDir}"`;
        } else if (finalFilename.match(/\.(tar\.gz|tgz)$/i)) {
          extractCommand = `tar -xzf "${filePath}" -C "${extractDir}"`;
        } else if (finalFilename.match(/\.(tar\.bz2|tbz2)$/i)) {
          extractCommand = `tar -xjf "${filePath}" -C "${extractDir}"`;
        } else if (finalFilename.match(/\.tar$/i)) {
          extractCommand = `tar -xf "${filePath}" -C "${extractDir}"`;
        }

        await execAsync(extractCommand);

        // List extracted contents
        const contents = await fs.readdir(extractDir, { recursive: true });

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              message: "Attachment downloaded and extracted",
              archivePath: filePath,
              extractionPath: extractDir,
              filename: finalFilename,
              contentType: result.contentType,
              size: result.size,
              extracted: true,
              fileCount: contents.length,
              note: "Use Read, Grep, or Glob tools on the extraction path to analyze contents"
            }, null, 2)
          }]
        };
      } catch (error) {
        return {
          content: [{ type: "text", text: `Error downloading/extracting attachment: ${error.message}` }],
          isError: true
        };
      }
    }
  }
];
