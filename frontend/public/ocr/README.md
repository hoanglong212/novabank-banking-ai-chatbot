# Local OCR assets

English and Vietnamese trained data are from tesseract-ocr/tessdata_fast,
commit `87416418657359cb625c412a48b6e1d6d41c29bd`, under Apache-2.0 (see lang/LICENSE).

`npm run prepare:ocr` copies the locked Tesseract.js worker and its LSTM WASM cores
from installed packages into runtime/. The dev/build scripts run this step.
These generated runtime files are not hand-edited. OCR loads only from this app's
origin; user images are neither uploaded to an OCR service nor sent to the assistant.
