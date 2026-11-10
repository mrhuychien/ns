// Giao diện phiếu lương + công nhân tự xem + tài khoản — Chromium THẬT, CSS thật, API Python THẬT trên Frappe giả
// (scripts/server-thu.py), trang dựng từ CHÍNH www/*.html (import map, NS_CONTEXT, build handshake là bản thật).
//
// Vì sao: đây là chỗ công nhân tự đọc lương của mình — hỏng là hỏng im lặng theo mấy hướng:
//   · cột lệch, giờ lẻ làm tròn, dòng chưa có giá hiện "0" như giá thật, cộng ngày không khớp phiếu (port D234 sx);
//   · bảng rộng hơn màn điện thoại 360px; cuộn xuống cuối tháng mất đầu cột;
//   · tên hàng lạ chèn HTML; tháng nháp lọt ra; trình duyệt gửi mã nhân viên (đoán mã đọc lương người khác);
//   · màn tài khoản: mật khẩu không hiện / thẻ in không có QR; HR User thấy nút tạo.
// Chạy: node scripts/test-giaodien.mjs   (verify.sh gọi sẵn). NS_SHOT=<thư mục> để chụp ảnh xem bằng mắt.
import { existsSync, mkdirSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const GOC = resolve(dirname(fileURLToPath(import.meta.url)), '..');
let hong = 0;
const kiem = (ten, dk, ct = '') => {
    if (!dk) hong += 1;
    console.log(`  ${dk ? 'ok  ' : 'HỎNG'} ${ten}${ct && !dk ? ` — ${ct}` : ''}`);
};
const CHROME = ['/opt/pw-browsers/chromium', '/opt/pw-browsers/chromium-1243/chrome-linux/chrome']
    .find((f) => existsSync(f));
const PW = '/opt/node22/lib/node_modules/playwright/index.js';
if (!CHROME || !existsSync(PW)) {
    console.log('-- trình duyệt thật: BỎ QUA (máy này không có Chromium / Playwright) --');
    console.log('GIAODIEN-OK (bỏ qua)');
    process.exit(0);
}
const SHOT = process.env.NS_SHOT || '';
if (SHOT) mkdirSync(SHOT, { recursive: true });

// ── server thử ──
const PORT = 8200 + Math.floor(Math.random() * 600);
const srv = spawn('python3', ['-B', join(GOC, 'scripts/server-thu.py'), String(PORT)], { cwd: GOC });
let srvLog = '';
srv.stdout.on('data', (d) => { srvLog += d; });
srv.stderr.on('data', (d) => { srvLog += d; });
const GOCURL = `http://127.0.0.1:${PORT}`;
for (let i = 0; i < 100 && !srvLog.includes('server-thu:'); i++) await new Promise((r) => setTimeout(r, 100));
if (!srvLog.includes('server-thu:')) { console.log(srvLog); console.log('GIAODIEN: server không lên'); process.exit(1); }
const seed = () => fetch(`${GOCURL}/__test/seed`);
const goi = async () => (await fetch(`${GOCURL}/__test/goi`)).json();

const pw = (await import(PW)).default;
const browser = await pw.chromium.launch({ executablePath: CHROME });
const loiTrang = [];
async function moTrang(user, { w = 360, h = 740 } = {}) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
    if (user) await ctx.addCookies([{ name: 'sid', value: user, url: GOCURL }]);
    const p = await ctx.newPage();
    p.on('pageerror', (e) => loiTrang.push(`${user}: ${e.message}`));
    p.on('response', (r) => { if (r.status() >= 500) loiTrang.push(`${user}: HTTP ${r.status()} ${r.url()}`); });
    return { ctx, p };
}
const gon = (s) => (s || '').replace(/\s+/g, ' ').trim();
const bangNgay = (p, sel = '.ns-pl-ngay') => p.$$eval(`${sel} tbody`, (tb) => tb.map((t) => [...t.rows]
    .map((r) => [...r.cells].map((c) => c.textContent.replace(/\s+/g, ' ').trim()))));
const tranNgang = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const chup = async (p, ten) => { if (SHOT) await p.screenshot({ path: join(SHOT, `${ten}.png`), fullPage: true }); };

try {
    await seed();
    console.log('-- công nhân: đăng nhập --');
    {
        const { ctx, p } = await moTrang(null);
        await p.goto(`${GOCURL}/phieuluong`, { waitUntil: 'domcontentloaded' });
        kiem('chưa đăng nhập → trang đăng nhập, quay lại đúng /phieuluong',
            p.url().endsWith('/login?redirect-to=/phieuluong') && !!(await p.$('#login')), p.url());
        await ctx.close();
    }

    console.log('\n-- công nhân khoán (An), điện thoại 360px --');
    {
        const { ctx, p } = await moTrang('an@x');
        await p.goto(`${GOCURL}/phieuluong`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('#cn-phieu .ns-pl');
        kiem('chào đúng người: tên + mã NV + bộ phận', gon(await p.textContent('.ns-cn-chao'))
            === 'Nguyễn Thị An HR-EMP-00001 · Công khoán - HGC', gon(await p.textContent('.ns-cn-chao')));
        const opts = await p.$$eval('#cn-chon option', (o) => o.map((x) => x.textContent));
        kiem('chỉ tháng có phiếu ĐÃ DUYỆT, mới nhất trước (nháp T12 không hiện)', JSON.stringify(opts)
            === JSON.stringify(['Tháng 11/2026', 'Tháng 10/2026']), JSON.stringify(opts));
        kiem('mặc định tháng mới nhất; › tắt, ‹ bật', (await p.$eval('#cn-toi', (b) => b.disabled))
            && !(await p.$eval('#cn-lui', (b) => b.disabled)));
        kiem('thực nhận to, đúng số phiếu', gon(await p.textContent('.ns-pl-tong-chinh b')) === '15.822.400 đ');
        kiem('nhãn Đã duyệt', gon(await p.textContent('.ns-pl-nhan-tt')) === 'Đã duyệt');
        kiem('báo dòng chưa có giá (lời cho công nhân)', gon(await p.textContent('.ns-pl')).includes(
            '⚠ 1 dòng sản phẩm chưa có đơn giá (đang tính 0 đồng) — phòng lương đang cập nhật.'));

        const dau = await p.$$eval('.ns-pl-ngay thead th', (th) => th.map((x) => x.textContent.trim()));
        kiem('bảng từng ngày: Sản phẩm · SL · Đơn giá · Thành tiền', JSON.stringify(dau)
            === JSON.stringify(['Sản phẩm', 'SL', 'Đơn giá', 'Thành tiền']), JSON.stringify(dau));
        const ng = await bangNgay(p);
        kiem('mỗi ngày một nhóm dòng, đúng thứ tự ngày', ng.map((t) => t[0][0].slice(0, 5)).join() === '01/11,02/11,03/11,04/11',
            JSON.stringify(ng.map((t) => t[0])));
        const [cn, t2, t3, t4] = ng;
        kiem('Chủ nhật: đầu ngày ghi thứ + chấm ăn', JSON.stringify(cn[0]) === JSON.stringify(['01/11 · Chủ nhật · ăn ca']), JSON.stringify(cn[0]));
        kiem('sản phẩm: tên · cách làm | SL | đơn giá | thành tiền — đúng cột',
            JSON.stringify(cn[1]) === JSON.stringify(['Bánh đậu xanh sen · Máy', '110', '1.200', '132.000']), JSON.stringify(cn[1]));
        kiem('làm theo giờ: SL là số GIỜ, giờ lẻ không làm tròn (2,5 giờ × 33.000)',
            JSON.stringify(cn[2]) === JSON.stringify(['Làm theo giờ', '2,5 giờ', '33.000', '82.500']), JSON.stringify(cn[2]));
        kiem('cộng ngày ghi phép tính (lương SP × 1,2 + tiền ăn) = thu nhập ngày của phiếu',
            JSON.stringify(cn[3]) === JSON.stringify(['Cộng ngày (lương SP 214.500 × 1,2 + tiền ăn 20.000)', '277.400']), JSON.stringify(cn[3]));
        kiem('dòng CHƯA CÓ GIÁ: "⚠ chưa có giá", không phải "0" như giá thật',
            JSON.stringify(t2[1]) === JSON.stringify(['Bánh TT · Tay', '5', '⚠ chưa có giá', '0']), JSON.stringify(t2[1]));
        kiem('giờ mức 30.000 hiện rõ đơn giá', JSON.stringify(t2[2]) === JSON.stringify(['Làm theo giờ', '3 giờ', '30.000', '90.000']), JSON.stringify(t2[2]));
        kiem('không hệ số, không tiền ăn → cộng ngày không phép tính', JSON.stringify(t2[3]) === JSON.stringify(['Cộng ngày', '90.000']), JSON.stringify(t2[3]));
        kiem('ngày chỉ chấm ăn: không dòng sản phẩm; cộng ngày = tiền ăn', JSON.stringify(t3)
            === JSON.stringify([['03/11 · Thứ 3 · ăn ca · ăn đêm'], ['Cộng ngày (tiền ăn 30.000)', '30.000']]), JSON.stringify(t3));
        kiem('số lớn có dấu chấm nghìn (1.234 × 12.500 = 15.425.000)',
            JSON.stringify(t4[1].slice(1)) === JSON.stringify(['1.234', '12.500', '15.425.000']), JSON.stringify(t4[1]));
        kiem('tên hàng lạ không chèn HTML (hiện nguyên chữ)', t4[2][0] === 'Bánh <i>lạ</i>' && !(await p.$('.ns-pl i')), JSON.stringify(t4[2]));
        kiem('bảng vừa màn 360px: không kéo ngang', (await tranNgang(p)) <= 0, String(await tranNgang(p)));
        kiem('cột số căn phải', (await p.$eval('.ns-pl-ngay tbody tr:nth-child(2) td:nth-child(4)', (td) => getComputedStyle(td).textAlign)) === 'right');
        const dinh = await p.evaluate(() => {
            const bang = document.querySelector('.ns-pl-ngay');
            window.scrollTo(0, bang.getBoundingClientRect().top + window.scrollY + bang.offsetHeight - 120);
            const th = document.querySelector('.ns-pl-ngay thead th').getBoundingClientRect();
            const hd = document.querySelector('.ns-header').getBoundingClientRect();
            return { th: Math.round(th.top), hd: Math.round(hd.bottom) };
        });
        kiem('cuộn tới cuối tháng: đầu cột dính ngay dưới thanh tiêu đề', Math.abs(dinh.th - dinh.hd) <= 1, JSON.stringify(dinh));
        await chup(p, 'cn-khoan-t11');

        await p.click('#cn-lui');
        await p.waitForFunction(() => location.hash === '#2026-10' && document.querySelector('.ns-pl-tong-chinh b')?.textContent.includes('7.260.000'));
        const t10 = gon(await p.textContent('#cn-phieu'));
        kiem('‹ sang T10: địa chỉ ghi #2026-10, phạt + bảo hiểm trong khấu trừ',
            t10.includes('Hộp móp') && t10.includes('− 20.000 đ') && t10.includes('Bảo hiểm − 500.000 đ'), t10.slice(0, 300));
        kiem('… T10 là tháng cũ nhất: ‹ tắt, › bật', (await p.$eval('#cn-lui', (b) => b.disabled)) && !(await p.$eval('#cn-toi', (b) => b.disabled)));
        await p.reload({ waitUntil: 'domcontentloaded' });
        await p.waitForSelector('#cn-phieu .ns-pl');
        kiem('tải lại vẫn đúng tháng đang xem (#2026-10)', (await p.$eval('#cn-chon', (s) => s.selectedOptions[0].textContent)).startsWith('Tháng 10/2026'));
        await p.waitForTimeout(3300);
        kiem('không có banner "bản CŨ" (BUILD trang khớp server)', !(await p.$('text=bản CŨ')));

        const ds = (await goi()).filter((x) => x.method.startsWith('ns.api.cong_nhan.'));
        kiem('trình duyệt KHÔNG gửi mã nhân viên (server tự suy từ phiên)', ds.length >= 3 && ds.every((x) => !('employee' in x.args)), JSON.stringify(ds.map((x) => x.args)));
        kiem('… mọi lượt gọi kèm CSRF token', ds.every((x) => x.csrf === 'csrf-test'));
        await p.click('#cn-menu-btn');
        kiem('menu: đổi mật khẩu → /update-password', (await p.getAttribute('.ns-acct-menu a', 'href')) === '/update-password');
        await Promise.all([p.waitForURL(/\/login\?redirect-to=%2Fphieuluong$/), p.click('#cn-logout')]);
        const lo = (await goi()).filter((x) => x.method === 'logout');
        kiem('đăng xuất: POST /api/method/logout kèm CSRF rồi về trang đăng nhập', lo.length === 1 && lo[0].csrf === 'csrf-test' && lo[0].user === 'an@x');
        await ctx.close();
    }

    console.log('\n-- công nhân công nhật (Bình) --');
    {
        const { ctx, p } = await moTrang('binh@x');
        await p.goto(`${GOCURL}/phieuluong`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('#cn-phieu .ns-pl');
        const txt = gon(await p.textContent('#cn-phieu'));
        kiem('các khoản → tổng thu nhập → trừ → thực nhận, kèm phần chuyển khoản',
            /Lương ngày công 6\.000\.000 đ.*Tổng thu nhập 7\.530\.000 đ.*Tiền phạt − 30\.000 đ.*Bảo hiểm − 550\.000 đ.*Thực nhận 6\.950\.000 đ.*Trong đó chuyển khoản 5\.000\.000 đ/.test(txt), txt.slice(0, 400));
        const cc = await p.$$eval('.ns-pl-cc tbody tr', (r) => r.map((x) => [x.className, [...x.cells].map((c) => c.textContent.replace(/\s+/g, ' ').trim())]));
        kiem('bảng chấm công: đủ 26 ngày, ngày · thứ | công | thêm giờ', cc.length === 26
            && JSON.stringify(cc[0][1]) === JSON.stringify(['01/10 · Thứ 5', '1', '2,5 giờ']) && JSON.stringify(cc[2][1]) === JSON.stringify(['03/10 · Thứ 7', '0,5', '–']), JSON.stringify(cc.slice(0, 3)));
        kiem('Chủ nhật tô nền (04, 11, 18, 25/10)', cc.filter((x) => x[0].includes('ns-pl-cn')).map((x) => x[1][0].slice(0, 2)).join() === '04,11,18,25');
        const phat = gon(await p.innerText('#cn-phieu .ns-pl-list:last-of-type'));
        kiem('lý do phạt + phép tính (số lượng × giá) + số tiền trừ', phat === 'Đi muộn 3 × 10.000 đ − 30.000 đ', phat);
        kiem('không kéo ngang ở 360px', (await tranNgang(p)) <= 0);
        await chup(p, 'cn-nhat-t10');
        await ctx.close();
    }

    console.log('\n-- tài khoản chưa gắn hồ sơ --');
    {
        const { ctx, p } = await moTrang('lac@x');
        await p.goto(`${GOCURL}/phieuluong`, { waitUntil: 'domcontentloaded' });
        await p.waitForTimeout(400);
        kiem('báo "chưa gắn với hồ sơ", không có phiếu', gon(await p.textContent('.ns-cn-main')).includes('Tài khoản chưa gắn với hồ sơ nhân viên') && !(await p.$('.ns-pl')));
        kiem('… và không gọi API lương', !(await goi()).some((x) => x.user === 'lac@x' && x.method.startsWith('ns.api.cong_nhan')));
        await ctx.close();
    }

    console.log('\n-- phòng nhân sự: màn Tài khoản (HR Manager) --');
    await seed();
    {
        const { ctx, p } = await moTrang('ql@x', { w: 390, h: 800 });
        await p.goto(`${GOCURL}/ns#/tai-khoan`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('.ns-tk-row');
        const dong = await p.$$eval('.ns-tk-row', (r) => r.map((x) => x.textContent.replace(/\s+/g, ' ').trim()));
        kiem('4 người đang làm; An tài khoản dùng chung (có vai sx), Cường chưa có',
            dong.length === 4 && dong.find((x) => x.includes('Nguyễn Thị An')).includes('dùng chung')
            && dong.find((x) => x.includes('Lê Văn Cường')).includes('Chưa có tài khoản'), JSON.stringify(dong));
        kiem('An (dùng chung): không có nút cấp lại / khoá, chỉ Gỡ', await p.$$eval('[data-emp="HR-EMP-00001"] button', (b) => b.map((x) => x.textContent.trim()).join('|')) === 'Gỡ');
        await p.click('#tk-chon-het');
        await p.click('#tk-tao-chon');
        await p.click('.ns-modal-content [data-ok]');
        await p.waitForSelector('.ns-modal-title:has-text("Đã cấp 1/2 tài khoản")');
        const kq = gon(await p.textContent('.ns-modal-content'));
        const mk = gon(await p.textContent('.ns-tk-mk'));
        kiem('tạo hàng loạt: Cường được cấp (SĐT chuẩn hoá), người chưa có SĐT được liệt kê để làm riêng',
            kq.includes('Lê Văn Cường') && kq.includes('0901234567') && kq.includes('Phạm Không Số: Hồ sơ chưa có số điện thoại'), kq);
        kiem('mật khẩu hiện MỘT lần, 8 ký tự', /^[A-Za-z2-9]{8}$/.test(mk), mk);
        const [the] = await Promise.all([ctx.waitForEvent('page'), p.click('#tk-in')]);
        await the.waitForLoadState();
        const theTxt = gon(await the.textContent('body'));
        kiem('in thẻ: QR (SVG) + SĐT + mật khẩu + địa chỉ /phieuluong', !!(await the.$('svg.qr path'))
            && theTxt.includes('0901234567') && theTxt.includes(mk) && theTxt.includes('/phieuluong'), theTxt.slice(0, 300));
        if (SHOT) await the.screenshot({ path: join(SHOT, 'the-dang-nhap.png') });
        await the.close();
        await p.click('.ns-modal-content [data-ns-close]');
        await p.waitForSelector('[data-emp="HR-EMP-00003"] .ns-badge-success');
        kiem('danh sách tải lại: Cường đã có tài khoản', gon(await p.textContent('[data-emp="HR-EMP-00003"]')).includes('Đang dùng'));
        // Một người: nhập SĐT trong hộp thoại
        await p.click('[data-tk-tao="HR-EMP-00004"]');
        await p.fill('#tk-sdt', '0977 000 111');
        await p.click('#tk-ok');
        await p.waitForSelector('.ns-modal-title:has-text("Đã cấp tài khoản")');
        kiem('tạo một người bằng SĐT gõ tay', gon(await p.textContent('.ns-modal-content')).includes('0977000111'));
        await p.click('.ns-modal-content [data-ns-close]');
        await p.waitForSelector('[data-emp="HR-EMP-00004"] .ns-badge-success');
        // Cấp lại mật khẩu (tài khoản riêng của app)
        await p.click('[data-tk-caplai="HR-EMP-00004"]');
        await p.click('.ns-modal-content [data-ok]');
        await p.waitForSelector('.ns-modal-title:has-text("Đã cấp lại mật khẩu")');
        kiem('cấp lại mật khẩu: mật khẩu mới hiện để in thẻ', /^[A-Za-z2-9]{8}$/.test(gon(await p.textContent('.ns-tk-mk'))));
        await p.click('.ns-modal-content [data-ns-close]');
        kiem('không kéo ngang ở 390px', (await tranNgang(p)) <= 0);
        await chup(p, 'hr-tai-khoan');

        console.log('\n-- phòng nhân sự: bảng lương → Xem phiếu, hồ sơ → Công & lương --');
        await p.setViewportSize({ width: 360, height: 560 });   // bảng từng ngày cao hơn khung modal → phải cuộn
        await p.goto(`${GOCURL}/ns#/luong?t=11&n=2026&loai=khoan`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('[data-xem]');
        await p.click('[data-xem="PL-2026-11-HR-EMP-00001"]');
        await p.waitForSelector('.ns-modal-content .ns-pl-ngay');
        await p.waitForTimeout(500);                             // modal trượt lên xong mới đo
        kiem('Xem phiếu từ bảng lương: modal có từng ngày + tên người',
            gon(await p.textContent('.ns-modal-content .ns-pl-dau')).includes('Nguyễn Thị An · HR-EMP-00001'));
        const m = await p.evaluate(() => { const c = document.querySelector('.ns-modal-content'); return c.scrollWidth - c.clientWidth; });
        kiem('modal phiếu vừa màn điện thoại (không kéo ngang)', m <= 0, String(m));
        const dinhM = await p.evaluate(() => {
            const c = document.querySelector('.ns-modal-content');
            const bang = c.querySelector('.ns-pl-ngay');
            const tren = () => c.getBoundingClientRect().top;
            c.scrollTop += bang.getBoundingClientRect().top - tren() + 200;   // đầu bảng đã trôi lên khỏi khung 200px
            const th = c.querySelector('.ns-pl-ngay thead th').getBoundingClientRect();
            return { th: Math.round(th.top - tren()), bang: Math.round(bang.getBoundingClientRect().top - tren()), cao: bang.offsetHeight, khung: c.clientHeight };
        });
        kiem('cuộn giữa bảng trong modal: đầu cột dính SÁT mép khung (không lộ dòng qua khe lề)', dinhM.bang < -150 && Math.abs(dinhM.th) <= 1, JSON.stringify(dinhM));
        kiem('modal có nút mở Desk để sửa / duyệt', !!(await p.$('.ns-modal-content a[href="/app/sx-phieu-luong/PL-2026-11-HR-EMP-00001"]')));
        await chup(p, 'hr-modal-phieu');
        await p.click('.ns-modal-content [data-ns-close]');

        await p.goto(`${GOCURL}/ns#/nv/HR-EMP-00002?tab=luong&t=10&n=2026`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('#cl-body .ns-pl');
        await p.waitForSelector('#cl-tk .ns-badge');
        kiem('hồ sơ → Công & lương: phiếu dựng bằng component chung + In / Mở ERPNext',
            !!(await p.$('#cl-body .ns-pl-cc')) && !!(await p.$('#cl-body a[href^="/printview?doctype=SalaryDay"]')));
        kiem('… ô tài khoản: Đang dùng + Xem như công nhân', gon(await p.textContent('#cl-tk')).includes('Đang dùng')
            && !!(await p.$('#cl-tk a[href="/phieuluong?nv=HR-EMP-00002"]')));
        await ctx.close();
    }

    console.log('\n-- HR User (không phải quản lý) --');
    {
        const { ctx, p } = await moTrang('hr@x', { w: 1280, h: 900 });
        await p.goto(`${GOCURL}/ns#/tai-khoan`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('.ns-tk-row');
        kiem('xem được danh sách nhưng KHÔNG có nút tạo / cấp lại / khoá / gỡ', !(await p.$('[data-tk-tao],[data-tk-caplai],[data-tk-khoa],[data-tk-go],#tk-tao-chon')));
        kiem('desktop: thanh điều hướng có mục Tài khoản', !!(await p.$('.ns-desktop-nav a[href="#/tai-khoan"]')));
        await p.goto(`${GOCURL}/phieuluong?nv=HR-EMP-00001`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('#cn-phieu .ns-pl');
        const x = (await goi()).filter((g) => g.user === 'hr@x' && g.method.startsWith('ns.api.cong_nhan.'));
        kiem('xem như công nhân: thanh báo + gọi API kèm mã nhân viên', gon(await p.textContent('.ns-info-bar')).includes('xem như công nhân')
            && x.length && x.every((g) => g.args.employee === 'HR-EMP-00001'));
        await ctx.close();
    }
    {
        const { ctx, p } = await moTrang('hr@x', { w: 360, h: 740 });
        await p.goto(`${GOCURL}/ns#/tai-khoan`, { waitUntil: 'domcontentloaded' });
        await p.waitForSelector('.ns-tk-row');
        kiem('điện thoại: thanh dưới vẫn 5 ô (Tài khoản vào từ menu 👤)', (await p.$$('.ns-bottom-nav .ns-nav-item')).length === 5);
        await p.click('#ns-acct');
        kiem('… menu 👤 có lối vào Tài khoản xem lương', !!(await p.$('.ns-acct-menu a[href="#/tai-khoan"]')));
        await ctx.close();
    }
} catch (e) {
    hong += 1;
    console.log(`  HỎNG kịch bản dừng giữa chừng: ${e.message.split('\n')[0]}`);
} finally {
    await browser.close();
    srv.kill();
}
kiem('không lỗi JS / HTTP 5xx trên trang', loiTrang.length === 0, loiTrang.join(' | '));
if (hong && srvLog.includes('Traceback')) console.log(srvLog.slice(-3000));
console.log(hong ? `GIAODIEN: ${hong} HỎNG` : 'GIAODIEN-OK');
process.exit(hong ? 1 : 0);
