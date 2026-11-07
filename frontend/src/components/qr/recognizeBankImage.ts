type Recognition = { text: string; confidence: number };

export async function recognizeBankImage(file: File, signal: AbortSignal, progress: (value: number) => void): Promise<Recognition> {
  signal.throwIfAborted();
  const bitmap = await createImageBitmap(file).catch(() => { throw new Error('Không mở được ảnh. Hãy chọn ảnh PNG, JPG hoặc WebP hợp lệ.'); });
  const canvas = document.createElement('canvas');
  try {
    signal.throwIfAborted();
    if (bitmap.width * bitmap.height > 24_000_000) throw new Error('Ảnh quá lớn. Hãy chọn ảnh dưới 24 megapixel.');
    const scale = Math.min(2, 2400 / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Không thể đọc ảnh trên thiết bị này.');
    context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  } finally { bitmap.close(); }
  const image = await new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Không xử lý được ảnh này.'))));
  signal.throwIfAborted();
  return new Promise<Recognition>((resolve, reject) => {
    const worker = new Worker(new URL('./bankImage.worker.ts', import.meta.url), { type: 'module' });
    const stop = () => { clearTimeout(timeout); signal.removeEventListener('abort', abort); worker.terminate(); };
    const abort = () => { stop(); reject(new DOMException('Cancelled', 'AbortError')); };
    const timeout = setTimeout(() => { stop(); reject(new Error('Đọc ảnh mất quá lâu. Hãy thử ảnh rõ hơn hoặc nhập thông tin bên dưới.')); }, 90_000);
    signal.addEventListener('abort', abort, { once: true });
    worker.onmessage = ({ data }: MessageEvent<{ progress?: number; result?: Recognition; error?: string }>) => {
      if (signal.aborted) return;
      if (data.result) { stop(); resolve(data.result); }
      else if (data.error) { stop(); reject(new Error(data.error)); }
      else if (data.progress !== undefined) progress(data.progress);
    };
    worker.onerror = event => { event.preventDefault(); stop(); reject(new Error('Không tải được bộ đọc ảnh. Hãy thử lại.')); };
    worker.postMessage(image);
  });
}