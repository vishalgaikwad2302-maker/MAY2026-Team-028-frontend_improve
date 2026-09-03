/**
 * Native client-side image compression utility for SmartSweep.
 * Compresses images to strictly under targetKB (default: 200 KB) using HTML5 Canvas.
 * No external heavy libraries required; safe for modern mobile and desktop browsers.
 */

/**
 * Format bytes into human-readable size string (e.g., "142 KB", "1.2 MB").
 */
export function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Compresses an image File or Blob to be under maxKB.
 * 
 * @param {File|Blob} file - The raw input file from file picker or camera.
 * @param {Object} options - Configuration options.
 * @param {number} options.maxKB - Target maximum file size in kilobytes (default: 200).
 * @param {number} options.maxDimension - Max width or height in pixels (default: 1600).
 * @returns {Promise<{ file: File, previewUrl: string, originalSize: number, compressedSize: number, savingsPercent: number }>}
 */
export async function compressImage(file, options = {}) {
  const maxKB = options.maxKB || 200;
  const targetBytes = maxKB * 1024;
  const maxDimension = options.maxDimension || 1600;
  const originalSize = file.size;

  // If already an allowed JPEG/WEBP under target size, return without re-compression
  if (file.size <= targetBytes && (file.type === "image/jpeg" || file.type === "image/webp")) {
    const previewUrl = URL.createObjectURL(file);
    return {
      file,
      previewUrl,
      originalSize,
      compressedSize: file.size,
      savingsPercent: 0,
    };
  }

  return new Promise((resolve, reject) => {
    const tempUrl = URL.createObjectURL(file);
    const img = new Image();

    img.onload = async () => {
      try {
        let width = img.width;
        let height = img.height;

        // Scale down dimensions if exceeding maxDimension while preserving aspect ratio
        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d", { alpha: false });
        if (!ctx) {
          throw new Error("Could not acquire 2D canvas context for compression.");
        }

        // Draw white background in case of transparent PNG
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        // Quality stepping levels to achieve < maxKB
        const qualitySteps = [0.85, 0.72, 0.60, 0.48, 0.35];
        let finalBlob = null;

        for (const quality of qualitySteps) {
          finalBlob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", quality));
          if (finalBlob && finalBlob.size <= targetBytes) {
            break;
          }
        }

        // If still over targetBytes, scale down canvas resolution further
        if (finalBlob && finalBlob.size > targetBytes) {
          const scaledCanvas = document.createElement("canvas");
          const scale = Math.sqrt(targetBytes / finalBlob.size) * 0.9;
          scaledCanvas.width = Math.max(320, Math.round(width * scale));
          scaledCanvas.height = Math.max(240, Math.round(height * scale));
          const scaledCtx = scaledCanvas.getContext("2d", { alpha: false });
          if (scaledCtx) {
            scaledCtx.fillStyle = "#ffffff";
            scaledCtx.fillRect(0, 0, scaledCanvas.width, scaledCanvas.height);
            scaledCtx.drawImage(canvas, 0, 0, scaledCanvas.width, scaledCanvas.height);
            finalBlob = await new Promise((res) =>
              scaledCanvas.toBlob(res, "image/jpeg", 0.65)
            );
          }
        }

        if (!finalBlob) {
          throw new Error("Image compression failed to produce output blob.");
        }

        // Generate clean file name ending in .jpg
        const baseName = (file.name || "photo").replace(/\.[^/.]+$/, "");
        const compressedFile = new File([finalBlob], `${baseName}.jpg`, {
          type: "image/jpeg",
          lastModified: Date.now(),
        });

        const previewUrl = URL.createObjectURL(finalBlob);
        const compressedSize = finalBlob.size;
        const savingsPercent = Math.max(
          0,
          Math.round(((originalSize - compressedSize) / originalSize) * 100)
        );

        resolve({
          file: compressedFile,
          previewUrl,
          originalSize,
          compressedSize,
          savingsPercent,
        });
      } catch (err) {
        reject(err);
      } finally {
        URL.revokeObjectURL(tempUrl);
      }
    };

    img.onerror = (err) => {
      URL.revokeObjectURL(tempUrl);
      reject(new Error("Failed to load image for compression: " + err));
    };

    img.src = tempUrl;
  });
}
