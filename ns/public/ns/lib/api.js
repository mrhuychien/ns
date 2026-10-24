// Gọi whitelisted method của Frappe bằng fetch (không cần frappe.call của Desk).
const CTX = () => window.NS_CONTEXT || {};

function parseServerMessages(json) {
    try {
        const arr = JSON.parse(json._server_messages || '[]');
        const msgs = arr.map((s) => { try { return JSON.parse(s).message || s; } catch { return s; } });
        if (msgs.length) return msgs.map((m) => String(m).replace(/<[^>]+>/g, '')).join('\n');
    } catch { /* ignore */ }
    if (json.exception) {
        const line = String(json.exception).split('\n').pop();
        return line.replace(/^[\w.]+Error:\s*/, '') || json.exception;
    }
    if (json._error_message) return json._error_message;
    return null;
}

export class ApiError extends Error {
    constructor(message, status, raw) { super(message); this.status = status; this.raw = raw; }
}

export async function call(method, args = {}) {
    const res = await fetch(`/api/method/${method}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            'X-Frappe-CSRF-Token': CTX().csrfToken || (window.frappe && window.frappe.csrf_token) || '',
        },
        body: JSON.stringify(args),
    });
    let json = {};
    try { json = await res.json(); } catch { /* non-json */ }
    if (!res.ok || json.exc_type || json.exception) {
        if (res.status === 403 && String(json.exc_type || '').includes('Permission')) {
            throw new ApiError(parseServerMessages(json) || 'Không có quyền.', 403, json);
        }
        if (res.status === 401 || res.status === 417 && String(json.exc_type || '').includes('CSRF')) {
            throw new ApiError('Phiên đăng nhập hết hạn — tải lại trang.', res.status, json);
        }
        throw new ApiError(parseServerMessages(json) || `Lỗi máy chủ (${res.status})`, res.status, json);
    }
    return json.message;
}

export async function download(method, args = {}) {
    const res = await fetch(`/api/method/${method}`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': CTX().csrfToken || '' },
        body: JSON.stringify(args),
    });
    if (!res.ok) {
        let json = {}; try { json = await res.json(); } catch { /* */ }
        throw new ApiError(parseServerMessages(json) || `Không tải được file (${res.status})`, res.status, json);
    }
    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    const filename = m ? decodeURIComponent(m[1]) : 'download.xlsx';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
    return filename;
}

export async function upload(file, { doctype = 'Employee', docname = null, isPrivate = 1 } = {}) {
    const fd = new FormData();
    fd.append('file', file, file.name);
    fd.append('is_private', String(isPrivate));
    if (doctype) fd.append('doctype', doctype);
    if (docname) fd.append('docname', docname);
    const res = await fetch('/api/method/upload_file', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'X-Frappe-CSRF-Token': CTX().csrfToken || '', Accept: 'application/json' },
        body: fd,
    });
    let json = {}; try { json = await res.json(); } catch { /* */ }
    if (!res.ok) throw new ApiError(parseServerMessages(json) || `Không tải lên được (${res.status})`, res.status, json);
    return json.message; // { file_url, name, ... }
}

export const ns = {
    nhanVien: {
        danhSach: (a) => call('ns.api.nhan_vien.danh_sach', a),
        chiTiet: (name) => call('ns.api.nhan_vien.chi_tiet', { name }),
        luu: (name, data) => call('ns.api.nhan_vien.luu', { name, data }),
        tao: (data) => call('ns.api.nhan_vien.tao', { data }),
    },
    suKien: {
        them: (a) => call('ns.api.su_kien.them', a),
        suaNoiDung: (name, noi_dung, tieu_de) => call('ns.api.su_kien.sua_noi_dung', { name, noi_dung, tieu_de }),
        xoa: (name) => call('ns.api.su_kien.xoa', { name }),
    },
    lichSu: (employee) => call('ns.api.lich_su.get', { employee }),
    congLuong: (employee, thang, nam) => call('ns.api.cong_luong.thang', { employee, thang, nam }),
    luong: {
        bang: (a) => call('ns.api.luong.bang', a),
        xuatExcel: (a) => download('ns.api.luong.xuat_excel', a),
        chuyenKhoan: (a) => download('ns.api.luong.chuyen_khoan', a),
    },
    viec: () => call('ns.api.viec.tong_hop'),
    boSung: {
        tongQuan: (department) => call('ns.api.bo_sung.tong_quan', { department }),
        luoi: (department, chi_thieu) => call('ns.api.bo_sung.luoi', { department, chi_thieu: chi_thieu ? 1 : 0 }),
        luuO: (employee, field, gia_tri) => call('ns.api.bo_sung.luu_o', { employee, field, gia_tri }),
        mauExcel: (department) => download('ns.api.bo_sung.mau_excel', { department }),
        xemTruoc: (file_url) => call('ns.api.bo_sung.xem_truoc_excel', { file_url }),
        apDung: (file_url, chi_dong) => call('ns.api.bo_sung.ap_dung_excel', { file_url, chi_dong }),
    },
};
