import { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, ScanLine, LoaderCircle } from 'lucide-react';
import { createQrReader } from './qrReader';

export function QrCamera({ paused, onRead }: { paused: boolean; onRead: (payload: string) => Promise<void> }) {
  const [requested, setRequested] = useState(false);
  const [state, setState] = useState<'idle' | 'starting' | 'scanning' | 'error'>('idle');
  const [error, setError] = useState('');
  const video = useRef<HTMLVideoElement>(null);
  const read = useRef(onRead);
  read.current = onRead;

  useEffect(() => {
    if (paused) setRequested(false);
  }, [paused]);

  useEffect(() => {
    if (!requested || paused) return;
    let cancelled = false, stream: MediaStream | undefined, timer: ReturnType<typeof setTimeout> | undefined;
    function stop() { stream?.getTracks().forEach(track => track.stop()); if (timer) clearTimeout(timer); }
    setState('starting'); setError('');
    void (async () => {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Không thể mở camera. Hãy dùng HTTPS hoặc mở ứng dụng trên localhost.');
      const detect = await createQrReader();
      if (cancelled) return;
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } }, audio: false });
      if (cancelled) { stop(); return; }
      const target = video.current;
      if (!target) { stop(); return; }
      target.srcObject = stream;
      await target.play();
      if (cancelled) { stop(); return; }
      setState('scanning');
      async function scan() {
        if (cancelled || !target) return;
        try {
          const value = await detect(target);
          if (cancelled) return;
          if (value) { stop(); setRequested(false); setState('idle'); await read.current(value); return; }
          timer = setTimeout(() => void scan(), 240);
        } catch {
          if (!cancelled) { stop(); setState('error'); setError('Camera không đọc được hình ảnh. Hãy thử lại hoặc tải ảnh QR lên.'); }
        }
      }
      await scan();
    })().catch((reason: unknown) => {
      stop();
      if (cancelled) return;
      const failure = reason as Error;
      setState('error');
      setError(failure.name === 'NotAllowedError' ? 'Chưa có quyền camera. Hãy cho phép camera trong trình duyệt, rồi thử lại.'
        : failure.name === 'NotFoundError' ? 'Không tìm thấy camera trên thiết bị. Bạn có thể tải ảnh QR lên.'
          : failure.name === 'NotReadableError' ? 'Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng đó rồi thử lại.' : failure.message);
    });
    const hide = () => { if (document.hidden) { stop(); setRequested(false); setState('idle'); } };
    document.addEventListener('visibilitychange', hide);
    return () => { cancelled = true; stop(); document.removeEventListener('visibilitychange', hide); if (video.current) video.current.srcObject = null; };
  }, [requested, paused]);

  const active = requested && !paused && state === 'scanning';
  const starting = requested && !paused && state === 'starting';
  return <section className={`qr-camera${active ? ' is-live' : ''}`} aria-label="Quét mã QR">
    <div className="qr-camera-top"><span className="qr-live-status"><i />{active ? 'CAMERA ĐANG BẬT' : 'QUÉT MÃ QR'}</span><ScanLine size={19} aria-hidden="true" /></div>
    <video ref={video} className="qr-camera-video" muted playsInline aria-label="Hình ảnh từ camera" hidden={!active} />
    <div className="qr-scan-target" aria-hidden="true"><i /><i /><i /><i />{active ? <span className="qr-scan-beam" /> : <ScanLine className="qr-camera-symbol" strokeWidth={1} />}</div>
    <div className="qr-camera-content">
      {active ? <><p role="status">Đưa mã QR vào trong khung</p><button className="qr-camera-button is-quiet" onClick={() => { setRequested(false); setState('idle'); }}><CameraOff size={17} />Tắt camera</button></>
        : <><p>{starting ? 'Đang mở camera…' : 'Đặt mã QR trong khung để bắt đầu'}</p><button className="qr-camera-button" disabled={starting || paused} onClick={() => { setRequested(false); setState('idle'); requestAnimationFrame(() => setRequested(true)); }}>
          {starting ? <LoaderCircle className="qr-spin" size={18} /> : <Camera size={18} />}{starting ? 'Đang kết nối' : state === 'error' ? 'Thử lại camera' : 'Bật camera'}</button></>}
    </div>
    {error && !paused && <p className="qr-camera-error" role="alert">{error}</p>}
  </section>;
}
