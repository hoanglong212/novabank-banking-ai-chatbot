import { createWorker, OEM, PSM } from 'tesseract.js';

// A disposable supervisor lets the caller stop Tesseract and its child worker
// even before createWorker finishes initializing the recognition engine.
self.onmessage = async (event: MessageEvent<Blob>) => {
  try {
    const worker = await createWorker('eng+vie', OEM.LSTM_ONLY, {
      workerPath: '/ocr/runtime/worker.min.js', corePath: '/ocr/runtime/core', langPath: '/ocr/lang',
      workerBlobURL: false, gzip: false, cacheMethod: 'none',
      logger: message => {
        if (message.status === 'recognizing text') self.postMessage({ progress: Math.round(message.progress * 100) });
      },
      errorHandler: () => self.postMessage({ error: 'Không tải được bộ đọc ảnh. Hãy thử lại hoặc nhập thông tin bên dưới.' }),
    });
    try {
      await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT, preserve_interword_spaces: '1' });
      const { data } = await worker.recognize(event.data);
      self.postMessage({ result: { text: data.text, confidence: data.confidence } });
    } finally { await worker.terminate(); }
  } catch {
    self.postMessage({ error: 'Không đọc được ảnh. Hãy thử ảnh rõ hơn hoặc nhập thông tin bên dưới.' });
  }
};
