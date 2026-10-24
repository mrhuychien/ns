// #/viec — Việc cần làm theo nhóm §6
import { ns } from '../lib/api.js';
import { html, raw, skeleton, emptyState } from '../lib/dom.js';
import { escapeHtml } from '../lib/format.js';
import { icon } from '../components/canh_bao.js';

export async function render({ container, setHeader }) {
    setHeader('Việc cần làm');
    container.innerHTML = skeleton(90, 4);
    let data;
    try { data = await ns.viec(); } catch (e) { container.innerHTML = `<div class="ns-risk-bar">${escapeHtml(e.message)}</div>`; return; }
    const nhom = data.nhom || [];
    const tongDo = nhom.filter((g) => g.muc === 'do').reduce((s, g) => s + g.dong.filter((d) => d.muc === 'do').length, 0);
    const tongVang = nhom.reduce((s, g) => s + g.dong.filter((d) => d.muc === 'vang').length, 0);
    container.innerHTML = html`
        <div class="ns-view-banner"><div><div class="ns-view-banner-title">Việc cần làm</div>
            <div class="ns-view-banner-subtitle">${tongDo} việc đỏ · ${tongVang} việc vàng · ${nhom.length} nhóm</div></div>
            <div class="ns-view-banner-badge">${(window.NS_CONTEXT || {}).today}</div></div>
        ${nhom.length ? '' : raw(emptyState('🎉', 'Không có việc nào', 'Hồ sơ và lương đều ổn.'))}
        <div class="ns-viec-grid">${raw(nhom.map(card).join(''))}</div>`;
    container.querySelectorAll('[data-toggle]').forEach((h) => { h.onclick = () => { const l = h.parentElement.querySelector('.ns-viec-list'); l.hidden = !l.hidden; }; });
    container.querySelectorAll('[data-more]').forEach((b) => { b.onclick = () => { b.parentElement.querySelectorAll('[hidden].ns-queue-row').forEach((r) => { r.hidden = false; }); b.remove(); }; });
}
function card(g) {
    const sorted = [...g.dong].sort((a, b) => ({ do: 0, vang: 1, xanh: 2 }[a.muc] - { do: 0, vang: 1, xanh: 2 }[b.muc]));
    const MAX = 8;
    return html`<div class="ns-card ns-viec-card ns-${g.muc}">
        <div class="ns-viec-head" data-toggle><div><div class="ns-viec-title">${icon(g.ma)} ${g.ten}</div><div class="ns-sub">${g.ma}</div></div><div class="ns-viec-count">${g.so_luong}</div></div>
        <div class="ns-viec-list">${raw(sorted.map((d, i) => html`<a class="ns-queue-row" href="#/nv/${d.name}${g.ma.startsWith('luong') ? '?tab=luong' : g.ma.endsWith('het_han') ? '?tab=giayto' : ''}" ${i >= MAX ? 'hidden' : ''}>
            <span class="ns-queue-name">${d.employee_name} <span class="ns-sub">${d.department || ''}</span></span>
            <span class="ns-queue-val"><span class="ns-badge ns-badge-${d.muc === 'do' ? 'danger' : d.muc === 'vang' ? 'warning' : 'success'}">${d.chi_tiet || (d.muc === 'do' ? 'đỏ' : d.muc === 'vang' ? 'vàng' : '')}</span></span></a>`).join(''))}
        ${sorted.length > MAX ? raw(`<button class="ns-btn ns-btn-sm ns-mt-2 ns-w-full" data-more>Xem thêm ${sorted.length - MAX}</button>`) : ''}</div></div>`;
}
