"""Track an existing evaluation and package its completed evidence. No model calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'docs/release/week7-evidence')
    args = parser.parse_args()
    directory = args.run.resolve()
    if not directory.is_relative_to(ROOT / '.local/week7-live'):
        parser.error('Expected an existing isolated Week 7 run directory')
    if not directory.is_dir():
        parser.error('Run directory does not exist')
    output = args.out.resolve(); output.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 4 * 60 * 60

    def status(state, count, errors, detail):
        stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
        data = {'state': state, 'updated_at_utc': stamp, 'observations': count,
                'execution_errors': errors, 'run_directory': str(directory), 'detail': detail}
        (output / 'evaluation-status.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
        (output / 'EVALUATION_STATUS.md').write_text(
            f'# Week 7 — trạng thái bộ đo Qwen\n\n**{state}** · {stamp}\n\n'
            f'Đã ghi {count} quan sát; {errors} lỗi thực thi (không tính NOT_APPLICABLE).\n\n'
            + detail + '\n\nTrạng thái này chỉ dành cho bộ đo; không thay thế nghiệm thu Caido/VM, lint hoặc review độc lập.\n', encoding='utf-8')

    while True:
        rows = []
        observations = directory / 'observations.jsonl'
        if observations.exists():
            for line in observations.read_text(encoding='utf-8').splitlines():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: pass  # The writer may be appending its last line.
        errors = sum(bool(r['error']) and not r['error'].startswith('NOT_APPLICABLE') for r in rows)
        summary_file = directory / 'summary.json'
        try:
            summary = json.loads(summary_file.read_text(encoding='utf-8')) if summary_file.exists() else None
        except json.JSONDecodeError:
            summary = None
        if summary:
            status('PACKAGING', len(rows), errors, 'Bộ đo đã kết thúc; đang tạo bảng và kiểm tra bố cục slide.')
            commands = [([sys.executable, str(ROOT / 'scripts/week7-report.py'), '--source', str(directory), '--out', str(output)], ROOT),
                        (['node', 'scripts/render-week7-slides.mjs', str(output)], ROOT / 'frontend')]
            for command, cwd in commands:
                completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8')
                with (output / 'packaging.log').open('a', encoding='utf-8') as log:
                    log.write(completed.stdout + completed.stderr)
                if completed.returncode:
                    status('PACKAGING_FAILED', len(rows), errors, 'Xem packaging.log; không coi bộ evidence là đã hoàn tất.')
                    return 1
            state = 'COMPLETED_WITH_ERRORS' if errors else 'COMPLETED_SUBSET' if summary['subset'] else 'COMPLETED'
            status(state, len(rows), errors, 'Đã xuất results.csv, summary.json, asr-table.md và 7 slide. Layout tự động đã kiểm tra; slide kết quả mới vẫn cần người xem lại. Xem completion.md để biết các phần nghiệm thu còn thiếu.')
            return 0
        if time.monotonic() >= deadline:
            status('MONITOR_TIMEOUT', len(rows), errors, 'Theo dõi đã hết 4 giờ; chưa có summary hoàn tất. Không dừng bộ đo hoặc ứng dụng.')
            return 1
        status('RUNNING', len(rows), errors, 'Bộ đo tiếp tục ở nền trên DB riêng. Báo cáo chính chỉ được thay thế sau khi bộ đo kết thúc.')
        time.sleep(15)


if __name__ == '__main__':
    raise SystemExit(main())
