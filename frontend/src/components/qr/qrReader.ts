type Source = HTMLVideoElement | ImageBitmap;
type NativeDetector = { detect(source: Source): Promise<{ rawValue: string }[]> };
type NativeConstructor = { new(options: { formats: string[] }): NativeDetector; getSupportedFormats(): Promise<string[]> };

export async function createQrReader(preferNative = true) {
  let native: NativeDetector | undefined;
  const Constructor = (window as unknown as { BarcodeDetector?: NativeConstructor }).BarcodeDetector;
  if (preferNative && Constructor) {
    try { if ((await Constructor.getSupportedFormats()).includes('qr_code')) native = new Constructor({ formats: ['qr_code'] }); } catch { /* Use the portable decoder. */ }
  }
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) throw new Error('Không thể đọc hình ảnh trên trình duyệt này.');
  let decode = native ? undefined : (await import('jsqr')).default;
  return async (source: Source): Promise<string | null> => {
    if (native) {
      try { return (await native.detect(source)).find(item => item.rawValue)?.rawValue ?? null; }
      catch { native = undefined; }
    }
    decode ??= (await import('jsqr')).default;
    const width = 'videoWidth' in source ? source.videoWidth : source.width;
    const height = 'videoHeight' in source ? source.videoHeight : source.height;
    if (!width || !height) return null;
    const scale = Math.min(1, 1600 / Math.max(width, height));
    canvas.width = Math.max(1, Math.round(width * scale)); canvas.height = Math.max(1, Math.round(height * scale));
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
    return decode(pixels.data, pixels.width, pixels.height, { inversionAttempts: 'attemptBoth' })?.data ?? null;
  };
}

export async function readQrFile(file: File) {
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) throw new Error('Choose a NovaBank QR image (PNG, JPG or WebP).');
  if (file.size > 8 * 1024 * 1024) throw new Error('Choose an image smaller than 8 MB.');
  const bitmap = await createImageBitmap(file).catch(() => { throw new Error('Không mở được ảnh. Hãy chọn một ảnh PNG, JPG hoặc WebP hợp lệ.'); });
  try {
    if (bitmap.width * bitmap.height > 24_000_000) throw new Error('Ảnh quá lớn. Hãy chọn ảnh dưới 24 megapixel.');
    const read = await createQrReader(false);
    const payload = await read(bitmap);
    if (!payload) throw new Error('Không tìm thấy mã QR. Hãy chọn ảnh rõ nét và chứa trọn mã.');
    return payload;
  } finally { bitmap.close(); }
}
