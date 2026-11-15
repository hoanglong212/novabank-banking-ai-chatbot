"""Assemble unaltered actual browser screenshots; not a continuous recording."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent


def assemble(folder, names, target):
    frames = [Image.open(ROOT / folder / name).convert('RGB') for name in names]
    if len({frame.size for frame in frames}) != 1:
        raise ValueError('Screenshot dimensions differ; preserve originals and recapture.')
    frames[0].save(ROOT / target, save_all=True, append_images=frames[1:],
        duration=2400, loop=0, optimize=False)


if __name__ == '__main__':
    assemble('mfa', ['01-login-totp.png', '02-recipient-stepup.png', '03-stepup-passed.png',
        '04-separate-email-otp.png', '05-confirmed-receipt.png'], 'mfa.gif')
    assemble('quishing', ['malicious-qr-blocked.png', 'genuine-qr-review.png',
        'genuine-qr-verification.png'], 'quishing.gif')
