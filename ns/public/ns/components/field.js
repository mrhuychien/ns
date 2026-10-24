// Editor theo fieldtype — dùng chung cho form hồ sơ và lưới bổ sung
import { escapeHtml } from '../lib/format.js';

export function inputFor({ field, fieldtype = 'Data', options = null, value = null, placeholder = '', attrs = '' }) {
    const name = escapeHtml(field);
    const v = value == null ? '' : value;
    const a = `name="${name}" data-field="${name}" data-fieldtype="${escapeHtml(fieldtype)}" ${attrs}`;
    switch (fieldtype) {
        case 'Date':
            return `<input class="ns-input" type="date" ${a} value="${escapeHtml(String(v).slice(0, 10))}">`;
        case 'Check':
            return `<label class="ns-switch"><input type="checkbox" ${a} ${Number(v) ? 'checked' : ''}><span></span></label>`;
        case 'Currency': case 'Float': case 'Int':
            return `<input class="ns-input ns-input-num" type="text" inputmode="numeric" ${a} value="${v === '' ? '' : escapeHtml(formatNum(v))}" placeholder="${escapeHtml(placeholder)}">`;
        case 'Select': case 'Link': {
            const opts = (options || []).map((o) => `<option value="${escapeHtml(o)}" ${String(o) === String(v) ? 'selected' : ''}>${escapeHtml(o)}</option>`).join('');
            if (fieldtype === 'Link' && (!options || options.length > 60)) {
                return `<input class="ns-input" type="text" ${a} value="${escapeHtml(v)}" list="ns-dl-${name}"><datalist id="ns-dl-${name}">${(options || []).map((o) => `<option value="${escapeHtml(o)}">`).join('')}</datalist>`;
            }
            return `<select class="ns-input" ${a}><option value="">—</option>${opts}</select>`;
        }
        case 'Small Text': case 'Text': case 'Long Text':
            return `<textarea class="ns-input ns-textarea" rows="2" ${a} placeholder="${escapeHtml(placeholder)}">${escapeHtml(v)}</textarea>`;
        default:
            return `<input class="ns-input" type="text" ${a} value="${escapeHtml(v)}" placeholder="${escapeHtml(placeholder)}">`;
    }
}
function formatNum(v) { const n = Number(v); return Number.isNaN(n) ? v : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 }).format(n); }

export function readValue(input) {
    const ft = input.dataset.fieldtype || input.type;
    if (ft === 'Check' || input.type === 'checkbox') return input.checked ? 1 : 0;
    const v = input.value;
    if (ft === 'Currency' || ft === 'Float' || ft === 'Int') {
        if (v === '' || v == null) return null;
        const s = String(v).replace(/[.\s]/g, '').replace(',', '.');
        const n = Number(s);
        return Number.isNaN(n) ? v : n;
    }
    return v === '' ? null : v;
}
export function displayValue(fieldtype, v) {
    if (v === null || v === undefined || v === '') return '';
    if (fieldtype === 'Date') { const s = String(v).slice(0, 10); const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/); return m ? `${m[3]}/${m[2]}/${m[1]}` : s; }
    if (fieldtype === 'Check') return Number(v) ? 'Có' : 'Không';
    if (fieldtype === 'Currency' || fieldtype === 'Float' || fieldtype === 'Int') return formatNum(v);
    return String(v);
}
