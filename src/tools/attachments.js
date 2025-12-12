import { z } from 'zod';
import { zendeskClient } from '../zendesk-client.js';

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
  }
];
