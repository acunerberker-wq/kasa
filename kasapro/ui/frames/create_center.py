# -*- coding: utf-8 -*-
"""Create Center UI frame."""

from __future__ import annotations

import queue
import threading
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

from ..base import BaseView
from ..create_form_registry import CATEGORY_ORDER, FormSpec, get_form_registry
from ..ui_logging import log_ui_event


class CreateCenterFrame(BaseView):
    def __init__(self, master: tk.Misc, app: Any):
        self.app = app
        self._registry = get_form_registry()
        self._forms_by_id: Dict[str, FormSpec] = {spec.form_id: spec for spec in self._registry}
        self._form_instances: Dict[str, ttk.Frame] = {}
        self._current_form_id: Optional[str] = None
        self._search_queue: queue.Queue = queue.Queue()
        super().__init__(master, app)
        self.build_ui()

    def build_ui(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="Kayıt Oluştur (Merkez)", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Yeni kayıtlar tek merkezden yönetilir. Favoriler ve son kullanılanlar hızlı erişim sağlar.",
            style="SidebarSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        self.left_panel = ttk.Frame(body)
        self.right_panel = ttk.Frame(body)
        body.add(self.left_panel, weight=1)
        body.add(self.right_panel, weight=4)

        self._build_left_panel()
        self._build_right_panel()

        self._populate_categories()
        self._select_first_category()

    def _build_left_panel(self) -> None:
        cat_box = ttk.LabelFrame(self.left_panel, text="Kategoriler")
        cat_box.pack(fill=tk.BOTH, expand=True, padx=(0, 6))
        self.category_list = tk.Listbox(cat_box, height=12)
        self.category_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.category_list.bind("<<ListboxSelect>>", lambda _e: self._on_category_change())

    def _build_right_panel(self) -> None:
        top = ttk.Frame(self.right_panel)
        top.pack(fill=tk.X)

        search_row = ttk.Frame(top)
        search_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(search_row, text="Hızlı Arama:").pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT)
        self.search_var.trace_add("write", lambda *_args: self._schedule_search())
        self.fav_btn = ttk.Button(search_row, text="☆ Favori", command=self._toggle_favorite)
        self.fav_btn.pack(side=tk.LEFT, padx=8)

        lists_row = ttk.Frame(top)
        lists_row.pack(fill=tk.X, pady=(0, 6))

        fav_box = ttk.LabelFrame(lists_row, text="Favoriler")
        fav_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.fav_list = tk.Listbox(fav_box, height=4)
        self.fav_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.fav_list.bind("<<ListboxSelect>>", lambda _e: self._open_selected_list(self.fav_list))

        recent_box = ttk.LabelFrame(lists_row, text="Son Kullanılanlar")
        recent_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.recent_list = tk.Listbox(recent_box, height=4)
        self.recent_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.recent_list.bind("<<ListboxSelect>>", lambda _e: self._open_selected_list(self.recent_list))

        actions = ttk.Frame(self.right_panel)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="Kaydet", style="Primary.TButton", command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Kaydet + Yeni", command=self._save_and_new).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Taslak", command=self._save_draft).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="İptal", style="Secondary.TButton", command=self._cancel).pack(side=tk.LEFT, padx=4)

        mid = ttk.Frame(self.right_panel)
        mid.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(mid, text="Form Listesi")
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.form_list = tk.Listbox(list_frame, height=12)
        self.form_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.form_list.bind("<<ListboxSelect>>", lambda _e: self._on_form_select())

        self.form_container = ttk.Frame(mid, style="Panel.TFrame")
        self.form_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bind_all("<Control-s>", self._on_ctrl_s)
        self.bind_all("<Escape>", self._on_escape)

    def _on_ctrl_s(self, _event: tk.Event) -> str:
        if getattr(self.app, "active_screen_key", "") != "create_center":
            return "break"
        self._save()
        return "break"

    def _on_escape(self, _event: tk.Event) -> str:
        if getattr(self.app, "active_screen_key", "") != "create_center":
            return "break"
        self._cancel()
        return "break"

    def _schedule_search(self) -> None:
        query = self.search_var.get()

        def worker() -> None:
            results = self._filter_forms(query)
            self._search_queue.put(results)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll_search)

    def _poll_search(self) -> None:
        try:
            results = self._search_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_search)
            return
        self._render_form_list(results)

    def _filter_forms(self, query: str) -> List[FormSpec]:
        query = (query or "").strip().lower()
        allowed = self._allowed_forms()
        if not query:
            return allowed
        return [spec for spec in allowed if query in spec.label.lower()]

    def _allowed_forms(self) -> List[FormSpec]:
        user = getattr(self.app, "user", None)
        if user is None:
            role = ""
        elif hasattr(user, "get"):
            role = str(user.get("role", "")).lower()
        else:
            role = str(user["role"] if "role" in user.keys() else "").lower()
        allowed = []
        for spec in self._registry:
            if not spec.roles_allowed:
                allowed.append(spec)
                continue
            if role in [r.lower() for r in spec.roles_allowed]:
                allowed.append(spec)
        return allowed

    def _populate_categories(self) -> None:
        categories = self._categories_for_role()
        self.category_list.delete(0, tk.END)
        for cat in categories:
            self.category_list.insert(tk.END, cat)

    def _categories_for_role(self) -> List[str]:
        allowed = self._allowed_forms()
        available = {spec.category for spec in allowed}
        ordered = [cat for cat in CATEGORY_ORDER if cat in available]
        extra = sorted(available.difference(CATEGORY_ORDER))
        return ordered + extra

    def _select_first_category(self) -> None:
        if self.category_list.size() == 0:
            return
        self.category_list.selection_set(0)
        self._on_category_change()

    def _on_category_change(self) -> None:
        idx = self.category_list.curselection()
        if not idx:
            return
        category = self.category_list.get(idx[0])
        self._render_form_list([spec for spec in self._allowed_forms() if spec.category == category])

    def _render_form_list(self, specs: List[FormSpec]) -> None:
        self.form_list.delete(0, tk.END)
        self._list_labels: List[str] = []
        for spec in specs:
            label = spec.label
            self.form_list.insert(tk.END, label)
            self._list_labels.append(spec.form_id)
        if specs:
            self.form_list.selection_set(0)
            self._on_form_select()

    def _on_form_select(self) -> None:
        idx = self.form_list.curselection()
        if not idx:
            return
        form_id = self._list_labels[idx[0]]
        self.select_form(form_id)

    def select_form(self, form_id: str, context: Optional[Dict[str, Any]] = None) -> None:
        spec = self._forms_by_id.get(form_id)
        if not spec:
            return
        form = self._form_instances.get(form_id)
        if form is None:
            form = spec.factory(self.form_container, self.app)
            self._form_instances[form_id] = form
        for child in self.form_container.winfo_children():
            child.pack_forget()
        form.pack(fill=tk.BOTH, expand=True)
        self._current_form_id = form_id
        self._sync_favorite_button()
        self._record_recent(form_id)
        try:
            if hasattr(form, "set_context"):
                form.set_context(context)
            if hasattr(form, "on_show"):
                form.on_show()
            if hasattr(form, "focus_first"):
                form.focus_first()
        except Exception:
            pass
        log_ui_event("create_form_selected", form=form_id)

    def _sync_favorite_button(self) -> None:
        favs = self._get_favorites()
        is_fav = self._current_form_id in favs
        self.fav_btn.config(text=("★ Favori" if is_fav else "☆ Favori"))
        self._render_favorites()

    def _get_favorites(self) -> List[str]:
        if not hasattr(self.app, "_create_center_favorites"):
            self.app._create_center_favorites = []
        return list(self.app._create_center_favorites)

    def _toggle_favorite(self) -> None:
        if not self._current_form_id:
            return
        favs = self._get_favorites()
        if self._current_form_id in favs:
            favs.remove(self._current_form_id)
        else:
            favs.append(self._current_form_id)
        self.app._create_center_favorites = favs
        self._sync_favorite_button()

    def _record_recent(self, form_id: str) -> None:
        if not hasattr(self.app, "_create_center_recent_forms"):
            self.app._create_center_recent_forms = []
        recents: List[str] = list(self.app._create_center_recent_forms)
        if form_id in recents:
            recents.remove(form_id)
        recents.insert(0, form_id)
        del recents[6:]
        self.app._create_center_recent_forms = recents
        self._render_recent()

    def _render_favorites(self) -> None:
        self.fav_list.delete(0, tk.END)
        for form_id in self._get_favorites():
            spec = self._forms_by_id.get(form_id)
            if spec:
                self.fav_list.insert(tk.END, spec.label)

    def _render_recent(self) -> None:
        self.recent_list.delete(0, tk.END)
        if not hasattr(self.app, "_create_center_recent_forms"):
            return
        for form_id in list(self.app._create_center_recent_forms):
            spec = self._forms_by_id.get(form_id)
            if spec:
                self.recent_list.insert(tk.END, spec.label)

    def _open_selected_list(self, listbox: tk.Listbox) -> None:
        idx = listbox.curselection()
        if not idx:
            return
        label = listbox.get(idx[0])
        for form_id, spec in self._forms_by_id.items():
            if spec.label == label:
                self.select_form(form_id)
                break

    def _get_current_form(self) -> Optional[Any]:
        if not self._current_form_id:
            return None
        return self._form_instances.get(self._current_form_id)

    def _save(self) -> None:
        form = self._get_current_form()
        if form is None:
            return
        if hasattr(form, "save") and form.save():
            log_ui_event("create_form_save", form=self._current_form_id)

    def _save_and_new(self) -> None:
        form = self._get_current_form()
        if form is None:
            return
        if hasattr(form, "save") and form.save():
            if hasattr(form, "reset_form"):
                form.reset_form()
            log_ui_event("create_form_save_new", form=self._current_form_id)

    def _save_draft(self) -> None:
        form = self._get_current_form()
        if form is None:
            return
        if hasattr(form, "save_draft"):
            form.save_draft()

    def _cancel(self) -> None:
        form = self._get_current_form()
        if form is None:
            return
        if hasattr(form, "reset_form"):
            form.reset_form()

    def refresh(self, data: Optional[Any] = None) -> None:
        self._populate_categories()
        self._render_favorites()
        self._render_recent()
