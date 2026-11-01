// Record actual local UI actions on the dedicated rich synthetic database.
import { chromium, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const root = resolve('..'), out = resolve(root, '.local/full-roadmap/video'); mkdirSync(out, { recursive: true });
const python = resolve(root, 'backend/.venv/Scripts/python.exe'), db = resolve(root, '.local/full-roadmap/rich-demo.sqlite3');
const browser = await chromium.launch(); const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, recordVideo: { dir: out, size: { width: 1440, height: 1000 } } });
const page = await context.newPage(); const steps = []; const start = Date.now(); let passed = false;
const nav = name => page.getByRole('navigation', { name: 'Main', exact: true }).getByRole('button', { name, exact: true });
async function caption(text, seconds = 17) {
  await page.evaluate(text => {
    document.getElementById('demo-caption')?.remove(); const el = document.createElement('div'); el.id = 'demo-caption'; el.textContent = text;
    Object.assign(el.style, { position: 'fixed', bottom: '12px', left: '220px', right: '30px', zIndex: '99999', background: '#211536', color: 'white', padding: '18px 24px', borderRadius: '8px', font: '19px/1.45 system-ui', boxShadow: '0 2px 12px #0004', pointerEvents: 'none' }); document.body.append(el);
  }, text);
  steps.push({ elapsed_seconds: Math.round((Date.now()-start)/1000), caption: text });
  console.log(text); await page.waitForTimeout(seconds * 1000);
}
function localCode(user, kind='LOGIN_OTP') {
  return execFileSync(python, ['-c', 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]);print(c.execute("SELECT secret_text FROM dev_outbox WHERE user_id=? AND kind=? AND secret_text IS NOT NULL ORDER BY rowid DESC LIMIT 1",(sys.argv[2],sys.argv[3])).fetchone()[0])', db, user, kind],{encoding:'utf8'}).trim();
}
async function login(user) {
  await page.goto('http://127.0.0.1:8084'); await page.getByLabel('Username',{exact:true}).fill(user); await page.getByLabel('Password',{exact:true}).fill(user[0].toUpperCase()+user.slice(1)+'@2026'); await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Verify sign-in',exact:true})).toBeVisible();
  const field=page.getByLabel('Verification code',{exact:true}); await field.evaluate(e => e.style.webkitTextSecurity='disc'); await field.fill(localCode(user)); await page.getByRole('button',{name:'Verify and sign in',exact:true}).click(); await expect(nav(user==='admin'?'Operations':'Home')).toBeVisible();
}
try {
  await login('alice'); await page.getByRole('button',{name:'Show balance',exact:true}).click();
  await caption('NovaBank: ngân hàng mô phỏng phục vụ nghiên cứu prompt injection. Video dùng dữ liệu giả, 5 khách hàng và lịch sử 6 tháng.');
  await page.getByRole('button',{name:'Transfer',exact:true}).click(); await page.getByLabel('NovaBank account ID').fill('ACC-BOB-001'); await page.getByRole('textbox',{name:'Amount',exact:true}).fill('2000000'); await page.getByLabel('Content').fill('Alice Bob video demo');
  await caption('Alice nhập người nhận Bob và 2.000.000 VND. Backend xác minh tài khoản, hạn mức và số dư. Chưa có tiền được ghi sổ.');
  const response = page.waitForResponse(r => r.url().endsWith('/api/transfers') && r.request().method()==='POST'); await page.getByRole('button',{name:'Continue',exact:true}).click(); const draft=await (await response).json();
  await caption('Màn hình xác nhận hiển thị người nhận, phí và tổng tiền trừ. OTP thuộc luồng ngân hàng, không gửi cho AI.');
  await page.getByLabel('Enter OTP').fill(draft.demo_otp); await page.getByRole('button',{name:'Confirm transfer',exact:true}).click(); await expect(page.getByText('Transfer successful',{exact:true})).toBeVisible();
  await caption('Giao dịch hoàn tất. Số dư, lịch sử, ledger và thông báo được ghi trong cùng giao dịch database. Gửi lại cùng khóa idempotency không trừ lần hai.');
  const download=page.waitForEvent('download'); await page.getByRole('button',{name:'Download PDF receipt'}).click(); await (await download).saveAs(resolve(out,'receipt.pdf')); await page.getByRole('button',{name:'Done',exact:true}).click();
  await nav('Explore').click(); await page.getByRole('button',{name:'Spending & budgets',exact:false}).click();
  await caption('Thống kê theo tháng cộng phí chuyển tiền, loại tiền chuyển vào tiết kiệm và hoàn tiền giao dịch lỗi. Có ngân sách và sao kê PDF/CSV.');
  await page.getByRole('button',{name:'All services',exact:true}).click(); await page.getByRole('button',{name:'Cards Manage',exact:false}).click();
  await caption('Thẻ debit và credit dùng tiền giả. Khóa/mở thẻ, mua hàng và trả nợ đều cần xác nhận. Mọi sản phẩm dùng chung bộ ghi sổ cân bằng.');
  await nav('Assistant').click(); await page.getByRole('button',{name:'New conversation',exact:true}).click(); await page.getByRole('textbox',{name:'Message',exact:true}).fill('What interest rate does NovaBank offer for 6 month savings?'); await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(page.getByText(/NovaBank simulation policy|KB-savings|5%|5.0%/).first()).toBeVisible({timeout:150000});
  await caption('Qwen chạy local truy xuất chính sách bằng nomic embeddings. Agent là tiến trình riêng, gọi Banking API bằng token ủy quyền ngắn hạn.');
  await page.getByRole('textbox',{name:'Message',exact:true}).fill('Transfer 200000 VND to ACC-BOB-001 content ai demo'); await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(page.getByRole('button',{name:'Review and approve',exact:true})).toBeVisible({timeout:150000});
  await caption('AI tạo đề xuất chuyển 200.000 VND. Khách hàng phải duyệt, sau đó xác nhận OTP ở Banking API. Agent không có quyền gọi confirm.');
  await page.getByRole('button',{name:'Decline',exact:true}).click();
  await caption('Alice từ chối đề xuất. Không có tiền nào được chuyển bởi AI. Trace lưu model, profile, quyết định tool và thời gian xử lý.');
  await page.getByRole('button',{name:'Sign out',exact:true}).click(); await login('bob'); await nav('Alerts').click();
  await caption('Bob đăng nhập qua MFA và nhận thông báo tiền vào từ Alice. Quyền sở hữu được kiểm tra ở backend cho lịch sử và biên lai.');
  await page.getByRole('button',{name:'Sign out',exact:true}).click(); await login('admin'); await page.getByRole('button',{name:'Research',exact:true}).click();
  await caption('Dashboard nghiên cứu: 35 kịch bản trên 7 vector, 2 model, 3 profile, 5 lần lặp. 100 tác vụ hợp lệ và thí nghiệm bỏ từng lớp phòng vệ.');
  await page.getByRole('region',{name:'Research metrics'}).scrollIntoViewIfNeeded();
  await caption('1.790 quan sát hoàn tất, không có lỗi chạy. Utility defended: Qwen 99%, Llama 90%. ASR 0 trong bộ thử này không chứng minh an toàn tuyệt đối.');
  await page.goto(pathToFileURL(resolve(root,'docs/release/research/comparison.html')).href);
  await caption('Một quan sát lưu thật: baseline lab chấp nhận đề xuất chuyển sai người nhận. Defended chặn cùng payload. Baseline này vẫn cần người duyệt trước khi chuyển tiền.');
  await page.evaluate(()=>scrollTo(0,document.body.scrollHeight));
  await caption('Giới hạn: nguồn truy xuất được đưa sẵn vào model, payload còn theo mẫu và ablation nhỏ. Cần đánh giá tấn công thích ứng trước mọi ứng dụng thực tế.');
  const remain=Math.max(0,330000-(Date.now()-start));
  await caption('Bằng chứng bàn giao gồm test, migration giữ dữ liệu cũ, đối soát, phục hồi backup, raw thí nghiệm và cấu hình Docker/Caddy. HTTPS công khai và CI remote còn cần môi trường phát hành.', Math.min(45,remain/1000));
  passed = true;
} catch(error) { steps.push({error:error.message}); process.exitCode=1; console.error(error.message); }
finally {
  const video=page.video(); await context.close(); const path=await video.path(); await browser.close();
  writeFileSync(resolve(out,'recording.json'),JSON.stringify({passed,path,duration_seconds:Math.round((Date.now()-start)/1000),steps},null,2)); console.log('Recording:',path,'passed:',passed);
}
