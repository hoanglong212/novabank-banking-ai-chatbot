"""Bounded PDF/UTF-8 extraction; no OCR and no original-file persistence."""
import io
import logging
import unicodedata
from pypdf import PdfReader, apply_configuration

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 140100
logging.getLogger('pypdf').addHandler(logging.NullHandler())
logging.getLogger('pypdf').propagate = False


class Rejected(ValueError):
    pass


def filename(value):
    value = (value or 'document').replace('\\', '/').split('/')[-1]
    return ''.join(c for c in value if ord(c) >= 32 and c not in '<>')[:160] or 'document'


@apply_configuration(zlib_maximum_output_length=2 * 1024 * 1024,
                     array_based_stream_maximum_output_length=2 * 1024 * 1024,
                     lzw_maximum_output_length=2 * 1024 * 1024,
                     run_length_maximum_output_length=2 * 1024 * 1024,
                     stream_decoding_work_maximum_length=8 * 1024 * 1024,
                     page_tree_maximum_entries=1000, xform_maximum_invocations_per_extraction=100)
def extract(data):
    if len(data) > MAX_BYTES:
        raise Rejected('FILE_TOO_LARGE')
    if data.startswith(b'%PDF-'):
        mime = 'application/pdf'
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise Rejected('ENCRYPTED_PDF')
            if len(reader.pages) > 50:
                raise Rejected('TOO_MANY_PAGES')
            parts = []
            for page in reader.pages:
                stream = page.get_contents()
                if stream and len(stream.get_data()) > 2 * 1024 * 1024:
                    raise Rejected('PDF_CONTENT_LIMIT')
                parts.append(page.extract_text() or '')
                if sum(map(len, parts)) > MAX_TEXT:
                    raise Rejected('TOO_MANY_CHUNKS')
            text = '\n'.join(parts)
        except Rejected:
            raise
        except Exception:
            raise Rejected('INVALID_PDF') from None
    else:
        mime = 'text/plain'
        if data.startswith((b'MZ', b'PK', b'\x89PNG', b'\xff\xd8', b'GIF8', b'\x7fELF')):
            raise Rejected('UNSUPPORTED_FILE')
        try:
            text = data.decode('utf-8-sig', errors='strict')
        except UnicodeError:
            raise Rejected('UNSUPPORTED_FILE') from None
        if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
            raise Rejected('UNSUPPORTED_FILE')
    text = unicodedata.normalize('NFKC', text).replace('\r\n', '\n')
    if not text.strip():
        raise Rejected('NO_TEXT')
    pieces = [text[i:i+800] for i in range(0, len(text), 700)]
    if len(pieces) > 200:
        raise Rejected('TOO_MANY_CHUNKS')
    return mime, pieces
