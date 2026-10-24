import frappe
from frappe import _
from frappe.model.document import Document


class NSSuKien(Document):
    """Sự kiện nhân sự (timeline). Sự kiện nguồn "Tự động" do hook sinh ra;
    sau khi tạo không được đổi loai/ngay (chỉ bổ sung noi_dung)."""

    def validate(self):
        if not self.nguon:
            self.nguon = "Tay"
        if not self.tieu_de:
            self.tieu_de = self.loai
        if self.is_new() or frappe.flags.ns_backfill or frappe.flags.in_install or frappe.flags.in_migrate:
            return
        truoc = self.get_doc_before_save()
        if truoc and truoc.nguon == "Tự động":
            if (truoc.loai, str(truoc.ngay)) != (self.loai, str(self.ngay)):
                frappe.throw(_("Sự kiện tự động không được đổi loại/ngày — chỉ bổ sung nội dung."))
