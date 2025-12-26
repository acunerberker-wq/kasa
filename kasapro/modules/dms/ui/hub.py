# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import queue
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from ..constants import DOC_TYPES, DMS_STATUSES


class DmsHubFrame(ttk.Frame):
    def __init__(self, master: ttk.Frame, app: object):
        super().__init__(master)
        self.app = app
        self.db = app.db
        self.services = app.services.dms
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._poll_queue()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_library_tab()
        self._build_approvals_tab()
        self._build_tasks_tab()

        self._refresh_documents()
        self._refresh_approvals()
        self._refresh_tasks()
        self._schedule_reminder_check()

    def _company_id(self) -> int:
        return int(getattr(self.app, "active_company_id", None) or 1)

    def _actor_id(self) -> Optional[int]:
        return getattr(self.app, "data_owner_user_id", None) or getattr(self.app, "user", {}).get("id")

    def _build_library_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Kütüphane")

        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(toolbar, text="Arama:").pack(side=tk.LEFT)
        self.txt_search = ttk.Entry(toolbar, width=24)
        self.txt_search.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(toolbar, text="Tip:").pack(side=tk.LEFT)
        self.cmb_type = ttk.Combobox(toolbar, values=[""] + DOC_TYPES, width=14, state="readonly")
        self.cmb_type.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(toolbar, text="Durum:").pack(side=tk.LEFT)
        self.cmb_status = ttk.Combobox(toolbar, values=[""] + DMS_STATUSES, width=16, state="readonly")
        self.cmb_status.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Button(toolbar, text="Ara", command=self._refresh_documents).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Button(toolbar, text="CSV Export", command=self._export_documents_csv).pack(side=tk.LEFT)

        actions = ttk.Frame(tab)
        actions.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Button(actions, text="Yeni Doküman", command=self._create_document).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Düzenle", command=self._edit_document).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Arşivle", command=self._archive_document).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Sürüm Yükle", command=self._upload_version).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Workflow Başlat", command=self._start_workflow).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Detay", command=self._open_detail).pack(side=tk.LEFT, padx=4)

        columns = ("id", "title", "doc_type", "status", "current_version", "updated_at")
        self.tree_docs = ttk.Treeview(tab, columns=columns, show="headings", height=16)
        for col, title, width in [
            ("id", "ID", 60),
            ("title", "Başlık", 260),
            ("doc_type", "Tip", 120),
            ("status", "Durum", 150),
            ("current_version", "Sürüm", 80),
            ("updated_at", "Güncelleme", 160),
        ]:
            self.tree_docs.heading(col, text=title)
            self.tree_docs.column(col, width=width, anchor="w")
        self.tree_docs.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    def _build_approvals_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Onay Kutusu")

        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(toolbar, text="Yenile", command=self._refresh_approvals).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Onayla", command=lambda: self._act_workflow("approve")).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Revize İste", command=lambda: self._act_workflow("revise")).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Reddet", command=lambda: self._act_workflow("reject")).pack(side=tk.LEFT, padx=4)

        columns = ("id", "doc_title", "template_name", "status", "updated_at")
        self.tree_approvals = ttk.Treeview(tab, columns=columns, show="headings", height=16)
        for col, title, width in [
            ("id", "ID", 60),
            ("doc_title", "Doküman", 240),
            ("template_name", "Şablon", 200),
            ("status", "Durum", 150),
            ("updated_at", "Güncelleme", 160),
        ]:
            self.tree_approvals.heading(col, text=title)
            self.tree_approvals.column(col, width=width, anchor="w")
        self.tree_approvals.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    def _build_tasks_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Görevlerim")

        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(toolbar, text="Yenile", command=self._refresh_tasks).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Tamamlandı", command=self._complete_task).pack(side=tk.LEFT, padx=4)

        columns = ("id", "doc_title", "title", "due_at", "status")
        self.tree_tasks = ttk.Treeview(tab, columns=columns, show="headings", height=12)
        for col, title, width in [
            ("id", "ID", 60),
            ("doc_title", "Doküman", 220),
            ("title", "Görev", 260),
            ("due_at", "Bitiş", 150),
            ("status", "Durum", 120),
        ]:
            self.tree_tasks.heading(col, text=title)
            self.tree_tasks.column(col, width=width, anchor="w")
        self.tree_tasks.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        reminder_frame = ttk.LabelFrame(tab, text="Yaklaşan/Geciken Hatırlatmalar")
        reminder_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.lst_reminders = tk.Listbox(reminder_frame, height=6)
        self.lst_reminders.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _poll_queue(self) -> None:
        try:
            msg = self._queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_queue)
            return

        kind = msg[0]
        if kind == "documents":
            self._render_documents(msg[1])
        elif kind == "approvals":
            self._render_approvals(msg[1])
        elif kind == "tasks":
            self._render_tasks(msg[1], msg[2])
        elif kind == "error":
            messagebox.showerror("Dokümanlar", msg[1])
        elif kind == "info":
            messagebox.showinfo("Dokümanlar", msg[1])
        self.after(120, self._poll_queue)

    def _refresh_documents(self) -> None:
        q = (self.txt_search.get() or "").strip()
        doc_type = (self.cmb_type.get() or "").strip()
        status = (self.cmb_status.get() or "").strip()
        company_id = self._company_id()

        def worker():
            try:
                rows = self.db.dms.list_documents(company_id, q=q, status=status, doc_type=doc_type)
                self._queue.put(("documents", rows))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _render_documents(self, rows: List[Any]) -> None:
        self.tree_docs.delete(*self.tree_docs.get_children())
        for row in rows:
            current_version = row["current_version_id"] or ""
            self.tree_docs.insert(
                "",
                "end",
                values=(row["id"], row["title"], row["doc_type"], row["status"], current_version, row["updated_at"]),
            )

    def _selected_document_id(self) -> Optional[int]:
        sel = self.tree_docs.selection()
        if not sel:
            return None
        values = self.tree_docs.item(sel[0], "values")
        if not values:
            return None
        return int(values[0])

    def _create_document(self) -> None:
        dlg = _DocumentDialog(self, title="Yeni Doküman")
        if not dlg.result:
            return
        data = dlg.result
        try:
            doc_id = self.services.create_document(
                self._company_id(),
                data["title"],
                data["doc_type"],
                data["status"],
                data["tags"],
                self._actor_id(),
            )
            self._queue.put(("info", f"Doküman oluşturuldu (ID: {doc_id})"))
            self._refresh_documents()
        except Exception as exc:
            messagebox.showerror("Dokümanlar", str(exc))

    def _edit_document(self) -> None:
        doc_id = self._selected_document_id()
        if not doc_id:
            messagebox.showwarning("Dokümanlar", "Düzenlemek için doküman seçin.")
            return
        doc = self.db.dms.get_document(self._company_id(), doc_id)
        if not doc:
            messagebox.showerror("Dokümanlar", "Doküman bulunamadı.")
            return
        tags = ",".join(self.db.dms.list_tags(self._company_id(), doc_id))
        dlg = _DocumentDialog(
            self,
            title="Doküman Düzenle",
            initial={
                "title": doc["title"],
                "doc_type": doc["doc_type"],
                "status": doc["status"],
                "tags": tags,
            },
        )
        if not dlg.result:
            return
        data = dlg.result
        self.services.update_document(
            self._company_id(),
            doc_id,
            data["title"],
            data["doc_type"],
            data["status"],
            data["tags"],
            self._actor_id(),
        )
        self._refresh_documents()

    def _archive_document(self) -> None:
        doc_id = self._selected_document_id()
        if not doc_id:
            messagebox.showwarning("Dokümanlar", "Arşivlemek için doküman seçin.")
            return
        if not messagebox.askyesno("Dokümanlar", "Doküman arşivlensin mi?"):
            return
        self.services.archive_document(self._company_id(), doc_id, self._actor_id())
        self._refresh_documents()

    def _upload_version(self) -> None:
        doc_id = self._selected_document_id()
        if not doc_id:
            messagebox.showwarning("Dokümanlar", "Sürüm eklemek için doküman seçin.")
            return
        filepath = filedialog.askopenfilename(title="Dosya Seç")
        if not filepath:
            return
        note = simpledialog.askstring("Sürüm Notu", "Değişiklik notu", parent=self)
        company_id = self._company_id()

        def worker():
            try:
                version_id = self.services.upload_version(
                    company_id,
                    doc_id,
                    filepath,
                    os.path.basename(filepath),
                    note or "",
                    self._actor_id(),
                )
                self._queue.put(("info", f"Yeni sürüm eklendi (ID: {version_id})"))
                self._refresh_documents()
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _export_documents_csv(self) -> None:
        company_id = self._company_id()
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not filepath:
            return
        try:
            rows = self.db.dms.list_documents(company_id)
            headers = ["ID", "Başlık", "Tip", "Durum", "Güncelleme"]
            data = [[r["id"], r["title"], r["doc_type"], r["status"], r["updated_at"]] for r in rows]
            self.app.services.exporter.export_table_csv(headers, data, filepath)
            messagebox.showinfo("Dokümanlar", "CSV export tamamlandı.")
        except Exception as exc:
            messagebox.showerror("Dokümanlar", str(exc))

    def _open_detail(self) -> None:
        doc_id = self._selected_document_id()
        if not doc_id:
            messagebox.showwarning("Dokümanlar", "Detay için doküman seçin.")
            return
        DetailWindow(self, self.app, doc_id)

    def _ensure_default_template(self) -> int:
        company_id = self._company_id()
        templates = self.db.dms.list_workflow_templates(company_id, "document")
        if templates:
            return int(templates[0]["id"])
        template_id = self.db.dms.create_workflow_template(company_id, "Standart Onay", "document")
        self.db.dms.add_workflow_step(company_id, template_id, 1, "Yönetici Onayı", "admin", None)
        return template_id

    def _start_workflow(self) -> None:
        doc_id = self._selected_document_id()
        if not doc_id:
            messagebox.showwarning("Dokümanlar", "Workflow için doküman seçin.")
            return
        template_id = self._ensure_default_template()
        try:
            instance_id = self.services.start_workflow(self._company_id(), doc_id, template_id, self._actor_id())
            messagebox.showinfo("Dokümanlar", f"Workflow başlatıldı (ID: {instance_id})")
            self._refresh_approvals()
        except Exception as exc:
            messagebox.showerror("Dokümanlar", str(exc))

    def _refresh_approvals(self) -> None:
        company_id = self._company_id()
        user_id = int(self._actor_id() or 0)
        user = getattr(self.app, "user", None)
        if user is None:
            role = "user"
        elif hasattr(user, "get"):
            role = str(user.get("role") or "user")
        else:
            role = str(user["role"] if "role" in user.keys() else "user")

        def worker():
            try:
                rows = self.db.dms.list_pending_approvals(company_id, user_id, role)
                self._queue.put(("approvals", rows))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _render_approvals(self, rows: List[Any]) -> None:
        self.tree_approvals.delete(*self.tree_approvals.get_children())
        for row in rows:
            self.tree_approvals.insert(
                "",
                "end",
                values=(row["id"], row["doc_title"], row["template_name"], row["status"], row["updated_at"]),
            )

    def _selected_approval_id(self) -> Optional[int]:
        sel = self.tree_approvals.selection()
        if not sel:
            return None
        values = self.tree_approvals.item(sel[0], "values")
        if not values:
            return None
        return int(values[0])

    def _act_workflow(self, action: str) -> None:
        instance_id = self._selected_approval_id()
        if not instance_id:
            messagebox.showwarning("Onay", "İşlem için kayıt seçin.")
            return
        comment = simpledialog.askstring("Yorum", "Yorum (opsiyonel)") or ""
        try:
            if action == "approve":
                self.services.workflow_approve(self._company_id(), instance_id, self._actor_id(), comment)
            elif action == "reject":
                self.services.workflow_reject(self._company_id(), instance_id, self._actor_id(), comment)
            else:
                self.services.workflow_request_revision(self._company_id(), instance_id, self._actor_id(), comment)
            self._refresh_approvals()
            self._refresh_documents()
        except Exception as exc:
            messagebox.showerror("Onay", str(exc))

    def _refresh_tasks(self) -> None:
        company_id = self._company_id()
        user_id = int(self._actor_id() or 0)
        now_iso = datetime.now().isoformat()

        def worker():
            try:
                tasks = self.db.dms.list_tasks_by_assignee(company_id, user_id)
                reminders = self.db.dms.list_due_reminders(company_id, now_iso)
                self._queue.put(("tasks", tasks, reminders))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _render_tasks(self, tasks: List[Any], reminders: List[Any]) -> None:
        self.tree_tasks.delete(*self.tree_tasks.get_children())
        for row in tasks:
            self.tree_tasks.insert(
                "",
                "end",
                values=(row["id"], row["doc_title"], row["title"], row["due_at"], row["status"]),
            )
        self.lst_reminders.delete(0, tk.END)
        for row in reminders:
            self.lst_reminders.insert(tk.END, f"{row['remind_at']} - {row['doc_title']}")

    def _selected_task_id(self) -> Optional[int]:
        sel = self.tree_tasks.selection()
        if not sel:
            return None
        values = self.tree_tasks.item(sel[0], "values")
        if not values:
            return None
        return int(values[0])

    def _complete_task(self) -> None:
        task_id = self._selected_task_id()
        if not task_id:
            messagebox.showwarning("Görevler", "Tamamlamak için görev seçin.")
            return
        try:
            self.services.complete_task(self._company_id(), task_id, self._actor_id())
            self._refresh_tasks()
        except Exception as exc:
            messagebox.showerror("Görevler", str(exc))

    def _schedule_reminder_check(self) -> None:
        self._refresh_tasks()
        self.after(60000, self._schedule_reminder_check)


class _DocumentDialog(tk.Toplevel):
    def __init__(self, master: ttk.Frame, title: str, initial: Optional[Dict[str, str]] = None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[Dict[str, Any]] = None
        initial = initial or {}

        ttk.Label(self, text="Başlık:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.ent_title = ttk.Entry(self, width=40)
        self.ent_title.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(self, text="Tip:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.cmb_type = ttk.Combobox(self, values=DOC_TYPES, state="readonly", width=37)
        self.cmb_type.grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(self, text="Durum:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.cmb_status = ttk.Combobox(self, values=DMS_STATUSES, state="readonly", width=37)
        self.cmb_status.grid(row=2, column=1, padx=8, pady=6)

        ttk.Label(self, text="Etiketler (virgülle):").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.ent_tags = ttk.Entry(self, width=40)
        self.ent_tags.grid(row=3, column=1, padx=8, pady=6)

        self.ent_title.insert(0, initial.get("title", ""))
        self.cmb_type.set(initial.get("doc_type", DOC_TYPES[0]))
        self.cmb_status.set(initial.get("status", DMS_STATUSES[0]))
        self.ent_tags.insert(0, initial.get("tags", ""))

        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(actions, text="Kaydet", command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="İptal", command=self._cancel).pack(side=tk.LEFT, padx=4)

        self.grab_set()
        self.ent_title.focus()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _save(self) -> None:
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Doküman", "Başlık zorunlu.")
            return
        tags = [t.strip() for t in self.ent_tags.get().split(",") if t.strip()]
        self.result = {
            "title": title,
            "doc_type": self.cmb_type.get().strip() or DOC_TYPES[0],
            "status": self.cmb_status.get().strip() or DMS_STATUSES[0],
            "tags": tags,
        }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class DetailWindow(tk.Toplevel):
    def __init__(self, master: ttk.Frame, app: object, document_id: int):
        super().__init__(master)
        self.app = app
        self.db = app.db
        self.services = app.services.dms
        self.document_id = document_id
        self.title("Doküman Detayı")
        self.geometry("860x520")

        self._build_ui()
        self._refresh()

    def _company_id(self) -> int:
        return int(getattr(self.app, "active_company_id", None) or 1)

    def _actor_id(self) -> Optional[int]:
        return getattr(self.app, "data_owner_user_id", None) or getattr(self.app, "user", {}).get("id")

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)
        self.lbl_title = ttk.Label(top, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_title.pack(side=tk.LEFT)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=10)
        ttk.Button(btns, text="Link Ekle", command=self._add_link).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Görev Ata", command=self._add_task).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Hatırlatma", command=self._add_reminder).pack(side=tk.LEFT, padx=4)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self._build_versions_tab()
        self._build_links_tab()
        self._build_workflows_tab()
        self._build_tasks_tab()
        self._build_audit_tab()

    def _build_versions_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Sürümler")
        cols = ("version_no", "original_name", "mime", "size", "status", "created_at")
        self.tree_versions = ttk.Treeview(tab, columns=cols, show="headings")
        for col, title, width in [
            ("version_no", "No", 60),
            ("original_name", "Dosya", 240),
            ("mime", "MIME", 160),
            ("size", "Boyut", 80),
            ("status", "Durum", 120),
            ("created_at", "Tarih", 160),
        ]:
            self.tree_versions.heading(col, text=title)
            self.tree_versions.column(col, width=width, anchor="w")
        self.tree_versions.pack(fill=tk.BOTH, expand=True)

    def _build_links_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Linkler")
        cols = ("entity_type", "entity_id", "created_at")
        self.tree_links = ttk.Treeview(tab, columns=cols, show="headings")
        for col, title, width in [
            ("entity_type", "Tip", 160),
            ("entity_id", "ID", 160),
            ("created_at", "Tarih", 160),
        ]:
            self.tree_links.heading(col, text=title)
            self.tree_links.column(col, width=width, anchor="w")
        self.tree_links.pack(fill=tk.BOTH, expand=True)

    def _build_workflows_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Workflow")
        cols = ("template_name", "status", "current_step_no", "updated_at")
        self.tree_workflows = ttk.Treeview(tab, columns=cols, show="headings")
        for col, title, width in [
            ("template_name", "Şablon", 220),
            ("status", "Durum", 160),
            ("current_step_no", "Adım", 80),
            ("updated_at", "Güncelleme", 160),
        ]:
            self.tree_workflows.heading(col, text=title)
            self.tree_workflows.column(col, width=width, anchor="w")
        self.tree_workflows.pack(fill=tk.BOTH, expand=True)

    def _build_tasks_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Görevler")
        cols = ("title", "assignee_id", "due_at", "status")
        self.tree_tasks = ttk.Treeview(tab, columns=cols, show="headings")
        for col, title, width in [
            ("title", "Görev", 240),
            ("assignee_id", "Atanan", 120),
            ("due_at", "Bitiş", 160),
            ("status", "Durum", 120),
        ]:
            self.tree_tasks.heading(col, text=title)
            self.tree_tasks.column(col, width=width, anchor="w")
        self.tree_tasks.pack(fill=tk.BOTH, expand=True)

    def _build_audit_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Audit")
        cols = ("action", "actor_id", "details", "created_at")
        self.tree_audit = ttk.Treeview(tab, columns=cols, show="headings")
        for col, title, width in [
            ("action", "İşlem", 160),
            ("actor_id", "Kullanıcı", 100),
            ("details", "Detay", 240),
            ("created_at", "Tarih", 160),
        ]:
            self.tree_audit.heading(col, text=title)
            self.tree_audit.column(col, width=width, anchor="w")
        self.tree_audit.pack(fill=tk.BOTH, expand=True)

    def _refresh(self) -> None:
        company_id = self._company_id()
        doc = self.db.dms.get_document(company_id, self.document_id)
        if doc:
            self.lbl_title.config(text=f"{doc['title']} ({doc['doc_type']})")

        self._fill_tree(self.tree_versions, self.db.dms.list_versions(company_id, self.document_id))
        self._fill_tree(self.tree_links, self.db.dms.list_document_links(company_id, self.document_id))
        self._fill_tree(self.tree_workflows, self.db.dms.list_workflows_for_document(company_id, self.document_id))
        self._fill_tree(self.tree_tasks, self.db.dms.list_tasks_for_document(company_id, self.document_id))
        self._fill_tree(self.tree_audit, self.db.dms.list_audit(company_id, "document", self.document_id))

    def _fill_tree(self, tree: ttk.Treeview, rows: List[Any]) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            values = [row[col] for col in tree["columns"]]
            tree.insert("", "end", values=values)

    def _add_link(self) -> None:
        entity_type = simpledialog.askstring("Link", "Entity tipi (invoice/contract/quote vb.)", parent=self)
        if not entity_type:
            return
        entity_id = simpledialog.askstring("Link", "Entity ID", parent=self)
        if not entity_id:
            return
        self.services.add_document_link(
            self._company_id(),
            self.document_id,
            entity_type,
            entity_id,
            self._actor_id(),
        )
        self._refresh()

    def _add_task(self) -> None:
        title = simpledialog.askstring("Görev", "Görev başlığı", parent=self)
        if not title:
            return
        assignee_id = simpledialog.askinteger("Görev", "Atanan kullanıcı ID", parent=self)
        if not assignee_id:
            return
        due_at = simpledialog.askstring("Görev", "Bitiş tarihi (YYYY-MM-DD)", parent=self)
        if not due_at:
            return
        self.services.create_task(
            self._company_id(),
            self.document_id,
            title,
            assignee_id,
            due_at,
            self._actor_id(),
        )
        self._refresh()

    def _add_reminder(self) -> None:
        remind_at = simpledialog.askstring("Hatırlatma", "Hatırlatma zamanı (YYYY-MM-DD)", parent=self)
        if not remind_at:
            return
        self.services.create_reminder(self._company_id(), self.document_id, remind_at, self._actor_id())
        self._refresh()
