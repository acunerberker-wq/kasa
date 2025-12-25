# -*- coding: utf-8 -*-
"""KasaPro v3 - Şirket içi mesajlaşma ekranı."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ..base import BaseView
from ..ui_logging import wrap_callback
from ...config import APP_TITLE

if TYPE_CHECKING:
    from ...app import App


class MessagesFrame(BaseView):
    def __init__(self, master, app: "App"):
        self.app = app
        super().__init__(master, app)
        self.page = 0
        self.limit = 50
        self._rows: List[Dict[str, object]] = []
        self._active_message_id: Optional[int] = None
        self.build_ui()

    def build_ui(self) -> None:
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=10)

        ttk.Label(top, text="Klasör:").pack(side=tk.LEFT)
        self.folder_var = tk.StringVar(value="Gelen")
        self.cmb_folder = ttk.Combobox(
            top,
            textvariable=self.folder_var,
            values=["Gelen", "Giden", "Taslak"],
            width=10,
            state="readonly",
        )
        self.cmb_folder.pack(side=tk.LEFT, padx=6)
        self.cmb_folder.bind(
            "<<ComboboxSelected>>",
            wrap_callback("messages_folder_change", lambda _e: self._on_folder_change()),
        )

        ttk.Label(top, text="Ara:").pack(side=tk.LEFT, padx=(10, 0))
        self.search_var = tk.StringVar()
        self.ent_search = ttk.Entry(top, textvariable=self.search_var, width=24)
        self.ent_search.pack(side=tk.LEFT, padx=6)
        self.ent_search.bind("<Return>", wrap_callback("messages_search", lambda _e: self.refresh()))

        self.only_unread_var = tk.IntVar(value=0)
        self.chk_unread = ttk.Checkbutton(
            top,
            text="Sadece okunmamış",
            variable=self.only_unread_var,
            command=self.refresh,
        )
        self.chk_unread.pack(side=tk.LEFT, padx=8)

        ttk.Button(top, text="🔄 Yenile", command=wrap_callback("messages_refresh", self.refresh)).pack(side=tk.RIGHT)
        ttk.Button(top, text="➕ Yeni Mesaj", command=wrap_callback("messages_compose", self.compose_new)).pack(
            side=tk.RIGHT, padx=6
        )

        pager = ttk.Frame(self)
        pager.pack(fill=tk.X, padx=12, pady=(0, 6))
        ttk.Button(pager, text="◀ Önceki", command=wrap_callback("messages_prev", self.prev_page)).pack(side=tk.LEFT)
        ttk.Button(pager, text="Sonraki ▶", command=wrap_callback("messages_next", self.next_page)).pack(
            side=tk.LEFT, padx=6
        )
        self.lbl_page = ttk.Label(pager, text="Sayfa 1")
        self.lbl_page.pack(side=tk.LEFT, padx=10)

        cols = ("message_id", "from_to", "subject", "created_at", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self.tree.heading("from_to", text="Kimden")
        self.tree.heading("subject", text="Konu")
        self.tree.heading("created_at", text="Tarih")
        self.tree.heading("status", text="Durum")
        self.tree.column("message_id", width=0, stretch=False)
        self.tree.column("from_to", width=200)
        self.tree.column("subject", width=400)
        self.tree.column("created_at", width=150)
        self.tree.column("status", width=90, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_selected_message())
        self.tree.bind("<Double-1>", lambda _e: self._open_selected())

        detail = ttk.LabelFrame(self, text="Mesaj Detayı")
        detail.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.lbl_subject = ttk.Label(detail, text="Konu: -")
        self.lbl_subject.pack(anchor="w", padx=10, pady=(8, 0))

        self.txt_body = tk.Text(detail, height=8, wrap="word")
        self.txt_body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.txt_body.config(state="disabled")

        attach_bar = ttk.Frame(detail)
        attach_bar.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(attach_bar, text="Ekler:").pack(side=tk.LEFT)
        self.lst_attachments = tk.Listbox(attach_bar, height=4)
        self.lst_attachments.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(attach_bar, text="💾 Kaydet", command=self.save_attachment).pack(side=tk.RIGHT)

        self.refresh()

    def _on_folder_change(self):
        self.page = 0
        folder = self.folder_var.get()
        if folder == "Gelen":
            self.tree.heading("from_to", text="Kimden")
            self.chk_unread.config(state="normal")
        elif folder == "Giden":
            self.tree.heading("from_to", text="Kime")
            self.chk_unread.config(state="disabled")
        else:
            self.tree.heading("from_to", text="Kime")
            self.chk_unread.config(state="disabled")
        self.refresh()

    def _current_user(self) -> Tuple[Optional[int], str]:
        uid = self.app.get_active_user_id() if hasattr(self.app, "get_active_user_id") else None
        uname = self.app.get_active_username() if hasattr(self.app, "get_active_username") else ""
        return uid, uname

    def refresh(self, data=None):
        uid, _uname = self._current_user()
        if not uid:
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        self._rows = []
        self._active_message_id = None
        self.lbl_subject.config(text="Konu: -")
        self._set_body("")
        self.lst_attachments.delete(0, tk.END)

        q = self.search_var.get().strip()
        folder = self.folder_var.get()
        offset = self.page * self.limit
        if folder == "Gelen":
            rows = self.app.db.message_inbox_list(uid, q=q, only_unread=bool(self.only_unread_var.get()), limit=self.limit, offset=offset)
        elif folder == "Giden":
            rows = self.app.db.message_sent_list(uid, q=q, limit=self.limit, offset=offset)
        else:
            rows = self.app.db.message_drafts_list(uid, q=q, limit=self.limit, offset=offset)

        for r in rows:
            message_id = int(r["message_id"])
            if folder == "Gelen":
                from_to = str(r["sender_username"] or "")
                status = "Yeni" if int(r["is_read"]) == 0 else "Okundu"
            else:
                from_to = str(r["recipients"] or "")
                status = "Taslak" if folder == "Taslak" else "Gönderildi"
            subject = str(r["subject"] or "")
            created_at = str(r["created_at"] or "")
            self.tree.insert("", tk.END, values=(message_id, from_to, subject, created_at, status))
            self._rows.append({
                "message_id": message_id,
                "folder": folder,
            })

        try:
            unread = self.app.db.message_unread_count(uid)
            if hasattr(self.app, "update_messages_badge"):
                self.app.update_messages_badge(unread)
        except Exception:
            pass

        self._update_page_label(len(rows))

    def _update_page_label(self, row_count: int):
        page_no = self.page + 1
        extra = "" if row_count == self.limit else " (son)"
        self.lbl_page.config(text=f"Sayfa {page_no}{extra}")

    def prev_page(self):
        if self.page <= 0:
            return
        self.page -= 1
        self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    def _get_selected_message_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return None
        try:
            return int(vals[0])
        except Exception:
            return None

    def _show_selected_message(self):
        msg_id = self._get_selected_message_id()
        if not msg_id:
            return
        self._active_message_id = msg_id
        folder = self.folder_var.get()
        uid, _uname = self._current_user()
        if not uid:
            return
        if folder == "Gelen":
            row = self.app.db.message_get_for_recipient(msg_id, uid)
            if row and int(row["is_read"]) == 0:
                try:
                    self.app.services.messages.mark_read(msg_id, uid)
                except Exception:
                    pass
        else:
            row = self.app.db.message_get_for_sender(msg_id, uid)

        if not row:
            return
        subject = str(row["subject"] or "")
        self.lbl_subject.config(text=f"Konu: {subject}")
        self._set_body(str(row["body"] or ""))
        self._load_attachments(msg_id)

    def _open_selected(self):
        folder = self.folder_var.get()
        msg_id = self._get_selected_message_id()
        if not msg_id:
            return
        if folder == "Taslak":
            self.compose_new(draft_id=msg_id)
        else:
            self._show_selected_message()

    def _set_body(self, text: str):
        self.txt_body.config(state="normal")
        self.txt_body.delete("1.0", tk.END)
        self.txt_body.insert(tk.END, text)
        self.txt_body.config(state="disabled")

    def _load_attachments(self, message_id: int):
        self.lst_attachments.delete(0, tk.END)
        try:
            rows = self.app.db.message_attachments_list(message_id)
        except Exception:
            rows = []
        for r in rows:
            name = str(r["filename"] or "")
            self.lst_attachments.insert(tk.END, name)

    def save_attachment(self):
        msg_id = self._active_message_id
        if not msg_id:
            messagebox.showinfo(APP_TITLE, "Önce bir mesaj seçin.")
            return
        sel = self.lst_attachments.curselection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Önce bir ek seçin.")
            return
        idx = sel[0]
        rows = self.app.db.message_attachments_list(msg_id)
        if idx >= len(rows):
            return
        row = rows[idx]
        filename = str(row["filename"])
        stored_name = str(row["stored_name"])
        target = filedialog.asksaveasfilename(title="Eki Kaydet", initialfile=filename)
        if not target:
            return
        try:
            source = self.app.services.messages.get_attachment_path(stored_name)
            shutil.copy2(source, target)
            messagebox.showinfo(APP_TITLE, "Ek kaydedildi.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def compose_new(self, draft_id: Optional[int] = None):
        ComposeMessageWindow(self, self.app, draft_id=draft_id, on_done=self.refresh)


class ComposeMessageWindow(tk.Toplevel):
    def __init__(self, master, app: "App", draft_id: Optional[int] = None, on_done=None):
        super().__init__(master)
        self.app = app
        self.draft_id = draft_id
        self.on_done = on_done
        self.new_attachments: List[str] = []
        self.existing_attachments: List[Tuple[str, str]] = []
        self.title("Yeni Mesaj" if not draft_id else "Taslak Düzenle")
        self.geometry("640x560")
        self._build()
        if self.draft_id:
            self._load_draft()

    def _build(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Alıcılar:").pack(anchor="w")
        self.lst_users = tk.Listbox(frm, selectmode=tk.MULTIPLE, height=6)
        self.lst_users.pack(fill=tk.X, pady=(0, 8))
        self.user_map: List[Tuple[int, str]] = self.app.services.messages.list_users()
        for _uid, uname in self.user_map:
            self.lst_users.insert(tk.END, uname)

        ttk.Label(frm, text="Konu:").pack(anchor="w")
        self.ent_subject = ttk.Entry(frm)
        self.ent_subject.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(frm, text="Mesaj:").pack(anchor="w")
        self.txt_body = tk.Text(frm, height=10, wrap="word")
        self.txt_body.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        attach_box = ttk.LabelFrame(frm, text="Ekler")
        attach_box.pack(fill=tk.BOTH, expand=False, pady=(0, 8))
        self.lst_attach = tk.Listbox(attach_box, height=5)
        self.lst_attach.pack(fill=tk.X, padx=8, pady=(6, 4))
        btns = ttk.Frame(attach_box)
        btns.pack(fill=tk.X, padx=8, pady=(0, 6))
        ttk.Button(btns, text="➕ Ekle", command=self.add_attachment).pack(side=tk.LEFT)
        ttk.Button(btns, text="🗑 Kaldır", command=self.remove_attachment).pack(side=tk.LEFT, padx=6)

        actions = ttk.Frame(frm)
        actions.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(actions, text="Taslak Kaydet", command=self.save_draft).pack(side=tk.LEFT)
        ttk.Button(actions, text="Gönder", command=self.send).pack(side=tk.RIGHT)
        ttk.Button(actions, text="İptal", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def _selected_recipients(self) -> List[Tuple[int, str]]:
        recipients: List[Tuple[int, str]] = []
        for idx in self.lst_users.curselection():
            if idx < len(self.user_map):
                recipients.append(self.user_map[idx])
        return recipients

    def _load_draft(self):
        uid = self.app.get_active_user_id()
        if not uid:
            return
        row = self.app.db.message_get_for_sender(self.draft_id, uid)
        if not row:
            return
        self.ent_subject.insert(0, str(row["subject"] or ""))
        self.txt_body.insert("1.0", str(row["body"] or ""))

        try:
            recs = self.app.db.message_list_recipients(self.draft_id)
        except Exception:
            recs = []
        wanted = {int(r["recipient_id"]) for r in recs if r and r["recipient_id"] is not None}
        for idx, (rid, _uname) in enumerate(self.user_map):
            if rid in wanted:
                self.lst_users.selection_set(idx)

        try:
            rows = self.app.db.message_attachments_list(self.draft_id)
        except Exception:
            rows = []
        for r in rows:
            name = str(r["filename"] or "")
            stored = str(r["stored_name"] or "")
            self.existing_attachments.append((name, stored))
            self.lst_attach.insert(tk.END, f"{name} (mevcut)")

    def add_attachment(self):
        paths = filedialog.askopenfilenames(title="Ek Dosya Seç")
        if not paths:
            return
        for path in paths:
            if path and os.path.exists(path):
                self.new_attachments.append(path)
                self.lst_attach.insert(tk.END, os.path.basename(path))

    def remove_attachment(self):
        sel = self.lst_attach.curselection()
        if not sel:
            return
        idx = sel[0]
        label = self.lst_attach.get(idx)
        if label.endswith("(mevcut)"):
            messagebox.showinfo(APP_TITLE, "Mevcut ekler silinemez.")
            return
        try:
            del self.new_attachments[idx - len(self.existing_attachments)]
        except Exception:
            pass
        self.lst_attach.delete(idx)

    def _get_message_payload(self):
        subject = self.ent_subject.get().strip()
        body = self.txt_body.get("1.0", tk.END).strip()
        recipients = self._selected_recipients()
        return subject, body, recipients

    def send(self):
        uid = self.app.get_active_user_id()
        uname = self.app.get_active_username()
        if not uid:
            return
        subject, body, recipients = self._get_message_payload()
        if not recipients:
            messagebox.showwarning(APP_TITLE, "En az bir alıcı seçmelisiniz.")
            return
        try:
            if self.draft_id:
                self.app.services.messages.update_draft_and_send(
                    self.draft_id, uid, uname, recipients, subject, body, self.new_attachments
                )
            else:
                self.app.services.messages.send_message(
                    uid, uname, recipients, subject, body, self.new_attachments
                )
            messagebox.showinfo(APP_TITLE, "Mesaj gönderildi.")
            if self.on_done:
                self.on_done()
            self.destroy()
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def save_draft(self):
        uid = self.app.get_active_user_id()
        uname = self.app.get_active_username()
        if not uid:
            return
        subject, body, recipients = self._get_message_payload()
        try:
            if self.draft_id:
                self.app.services.messages.update_draft(
                    self.draft_id, uid, recipients, subject, body, self.new_attachments
                )
            else:
                self.app.services.messages.save_draft(
                    uid, uname, recipients, subject, body, self.new_attachments
                )
            messagebox.showinfo(APP_TITLE, "Taslak kaydedildi.")
            if self.on_done:
                self.on_done()
            self.destroy()
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))
