"""AI Lab — EvoMemory browser, Transformer² expert stats, LoRA training, model merging."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import threading

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class AILabPage(BasePage):
    """AI research lab — memory browser, expert routing, LoRA fine-tuning, model merging."""

    def __init__(self):
        super().__init__("🧬 AI Lab")
        self.pod_gen = DataPod("Evo gen", "0", "cyan")
        self.pod_mem = DataPod("Memories", "0", "violet")
        self.pod_experts = DataPod("Experts", "7", "amber")
        for p in [self.pod_gen, self.pod_mem, self.pod_experts]:
            self.metric_strip.pack_start(p, True, True, 0)

        nb = Gtk.Notebook()
        nb.append_page(self._build_memory_tab(), Gtk.Label(label="EvoMemory"))
        nb.append_page(self._build_t2_tab(), Gtk.Label(label="Transformer²"))
        nb.append_page(self._build_evolver_tab(), Gtk.Label(label="ShinkaEvolve"))
        nb.append_page(self._build_lora_tab(), Gtk.Label(label="doc-to-LoRA"))
        nb.append_page(self._build_merge_tab(), Gtk.Label(label="Model Merge"))
        nb.append_page(self._build_drope_tab(), Gtk.Label(label="DroPE"))
        self.workspace.pack_start(nb, True, True, 0)

        GLib.timeout_add_seconds(5, self._refresh_stats)

    # ── EvoMemory tab ─────────────────────────────────────────────────────────

    def _build_memory_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>EvoMemory</b> — Evolutionary session memory\n"
            "<span color='#94a3b8' size='small'>High-fitness observations survive; near-duplicates merge. "
            "Relevant memories are auto-injected into AI context at dispatch time.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        # Stats row
        self._mem_status_lbl = Gtk.Label(xalign=0)
        self._mem_status_lbl.set_markup("<span color='#64748b'>Loading...</span>")
        box.pack_start(self._mem_status_lbl, False, False, 0)

        # Memory list
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(200)

        self._mem_store = Gtk.ListStore(str, str, str, str)  # source, age, fitness, content
        tv = Gtk.TreeView(model=self._mem_store)
        for i, (col, width) in enumerate([("Source", 80), ("Age", 70), ("Fit", 50), ("Content", 500)]):
            renderer = Gtk.CellRendererText()
            renderer.set_property("ellipsize", 3)  # PANGO_ELLIPSIZE_END
            col_obj = Gtk.TreeViewColumn(col, renderer, text=i)
            col_obj.set_fixed_width(width)
            tv.append_column(col_obj)
        sw.add(tv)
        box.pack_start(sw, True, True, 0)

        btn_row = Gtk.Box(spacing=8)
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda _: self._load_memories())
        btn_row.pack_start(refresh_btn, False, False, 0)

        clear_btn = Gtk.Button(label="Clear Episodic")
        clear_btn.connect("clicked", self._on_clear_episodic)
        btn_row.pack_start(clear_btn, False, False, 0)

        add_row = Gtk.Box(spacing=8)
        self._mem_add_entry = Gtk.Entry()
        self._mem_add_entry.set_placeholder_text("Manually add a memory...")
        add_row.pack_start(self._mem_add_entry, True, True, 0)
        add_btn = Gtk.Button(label="Add")
        add_btn.connect("clicked", self._on_add_memory)
        add_row.pack_start(add_btn, False, False, 0)

        box.pack_start(btn_row, False, False, 0)
        box.pack_start(add_row, False, False, 0)

        GLib.idle_add(self._load_memories)
        return box

    def _load_memories(self):
        try:
            from shadowcypher.ai.evo_memory import evo_memory
            self._mem_store.clear()
            all_mem = evo_memory._semantic + evo_memory._episodic[-20:]
            for e in sorted(all_mem, key=lambda x: x.fitness, reverse=True):
                age_h = e.age_seconds() / 3600
                age_str = f"{age_h:.1f}h" if age_h >= 1 else f"{int(e.age_seconds()/60)}m"
                self._mem_store.append([e.source, age_str, f"{e.fitness:.2f}", e.content[:200]])
            self._mem_status_lbl.set_markup(
                f"<span color='#94a3b8'>{evo_memory.status()}</span>"
            )
            self.pod_mem.set_value(str(len(evo_memory._semantic)))
        except Exception as ex:
            self._mem_status_lbl.set_markup(f"<span color='#f87171'>{ex}</span>")

    def _on_clear_episodic(self, btn):
        try:
            from shadowcypher.ai.evo_memory import evo_memory
            evo_memory.clear_episodic()
            self._load_memories()
        except Exception as e:
            self.log(str(e), "ERROR")

    def _on_add_memory(self, btn):
        text = self._mem_add_entry.get_text().strip()
        if not text:
            return
        try:
            from shadowcypher.ai.evo_memory import evo_memory
            evo_memory.add(text, source="manual")
            self._mem_add_entry.set_text("")
            self._load_memories()
        except Exception as e:
            self.log(str(e), "ERROR")

    # ── Transformer² tab ──────────────────────────────────────────────────────

    def _build_t2_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>Transformer²</b> — Self-adaptive expert routing\n"
            "<span color='#94a3b8' size='small'>Classifies each query into task types, mixes expert system prompts "
            "and temperature. Fitness-tracks which experts produce best results.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        # Expert fitness grid
        self._t2_grid = Gtk.Grid()
        self._t2_grid.set_column_spacing(20)
        self._t2_grid.set_row_spacing(6)
        box.pack_start(self._t2_grid, False, False, 0)

        # Test query
        test_frm = Gtk.Frame(label="Test Expert Routing")
        test_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        test_box.set_property("margin", 10)
        self._t2_test_entry = Gtk.Entry()
        self._t2_test_entry.set_placeholder_text("Enter a query to see which experts it routes to...")
        test_box.pack_start(self._t2_test_entry, False, False, 0)
        test_btn = Gtk.Button(label="Test Routing")
        test_btn.get_style_context().add_class("suggested-action")
        test_btn.connect("clicked", self._on_t2_test)
        test_box.pack_start(test_btn, False, False, 0)
        self._t2_result_lbl = Gtk.Label(xalign=0)
        self._t2_result_lbl.set_line_wrap(True)
        test_box.pack_start(self._t2_result_lbl, False, False, 0)
        test_frm.add(test_box)
        box.pack_start(test_frm, False, False, 0)

        refresh_btn = Gtk.Button(label="Refresh Stats")
        refresh_btn.connect("clicked", lambda _: self._load_t2_stats())
        box.pack_start(refresh_btn, False, False, 0)

        GLib.idle_add(self._load_t2_stats)
        return box

    def _load_t2_stats(self):
        try:
            from shadowcypher.ai.transformer2 import transformer2, EXPERTS
            for child in self._t2_grid.get_children():
                self._t2_grid.remove(child)
            header_labels = ["Expert", "Avg Fitness", "Samples", "Keywords"]
            for col, lbl in enumerate(header_labels):
                h = Gtk.Label(label=lbl, xalign=0)
                h.get_style_context().add_class("dim-label")
                self._t2_grid.attach(h, col, 0, 1, 1)

            for row, (name, cfg) in enumerate(EXPERTS.items(), start=1):
                hist = transformer2._fitness.get(name, [0.5])
                avg = sum(hist[-10:]) / len(hist[-10:])
                color = "#22c55e" if avg >= 0.6 else "#f59e0b" if avg >= 0.4 else "#f87171"
                bar = "█" * int(avg * 10) + "░" * (10 - int(avg * 10))

                name_lbl = Gtk.Label(label=name, xalign=0)
                fit_lbl = Gtk.Label(xalign=0)
                fit_lbl.set_markup(f"<span color='{color}'>{avg:.2f} {bar}</span>")
                samples_lbl = Gtk.Label(label=str(len(hist)), xalign=0)
                kw_lbl = Gtk.Label(label=", ".join(cfg["keywords"][:4]), xalign=0)
                kw_lbl.set_line_wrap(True)

                self._t2_grid.attach(name_lbl, 0, row, 1, 1)
                self._t2_grid.attach(fit_lbl, 1, row, 1, 1)
                self._t2_grid.attach(samples_lbl, 2, row, 1, 1)
                self._t2_grid.attach(kw_lbl, 3, row, 1, 1)

            self._t2_grid.show_all()
        except Exception as ex:
            self.log(str(ex), "ERROR")

    def _on_t2_test(self, btn):
        query = self._t2_test_entry.get_text().strip()
        if not query:
            return
        try:
            from shadowcypher.ai.transformer2 import transformer2
            cfg = transformer2.adapt(query, top_k=3)
            experts = ", ".join(cfg["experts_used"])
            temp = cfg["temperature"]
            self._t2_result_lbl.set_markup(
                f"<b>Experts:</b> {experts}\n"
                f"<b>Temperature:</b> {temp}\n"
                f"<b>System prompt:</b> <span color='#94a3b8'>{cfg['system_prompt'][:120]}...</span>"
            )
        except Exception as ex:
            self._t2_result_lbl.set_markup(f"<span color='#f87171'>{ex}</span>")

    # ── ShinkaEvolve tab ──────────────────────────────────────────────────────

    def _build_evolver_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>ShinkaEvolve</b> — Genetic algorithm for scan & prompt configs\n"
            "<span color='#94a3b8' size='small'>Evolves port ranges, tool ordering, and prompt templates. "
            "Configs that find more vulnerabilities survive to the next generation.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        self._evo_status_lbl = Gtk.Label(xalign=0)
        self._evo_status_lbl.set_markup("<span color='#64748b'>Loading...</span>")
        box.pack_start(self._evo_status_lbl, False, False, 0)

        self._evo_config_lbl = Gtk.Label(xalign=0)
        self._evo_config_lbl.set_line_wrap(True)
        self._evo_config_lbl.set_markup("<span color='#64748b'>—</span>")
        box.pack_start(self._evo_config_lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda _: self._load_evolver_stats())
        btn_row.pack_start(refresh_btn, False, False, 0)
        evolve_btn = Gtk.Button(label="Force Evolution Cycle")
        evolve_btn.connect("clicked", self._on_force_evolve)
        btn_row.pack_start(evolve_btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)

        GLib.idle_add(self._load_evolver_stats)
        return box

    def _load_evolver_stats(self):
        try:
            from shadowcypher.ai.shinka_evolver import shinka_evolver
            self._evo_status_lbl.set_markup(
                f"<span color='#94a3b8'>{shinka_evolver.status()}</span>"
            )
            best = shinka_evolver.best_scan_config()
            lines = "\n".join(f"  <b>{k}:</b> {v}" for k, v in best.items())
            self._evo_config_lbl.set_markup(f"<b>Best scan config:</b>\n{lines}")
            gen = shinka_evolver._store.get("generation", 0)
            self.pod_gen.set_value(str(gen))
        except Exception as ex:
            self._evo_status_lbl.set_markup(f"<span color='#f87171'>{ex}</span>")

    def _on_force_evolve(self, btn):
        try:
            from shadowcypher.ai.shinka_evolver import shinka_evolver
            shinka_evolver.evolve_async(
                on_complete=lambda sc, pc: GLib.idle_add(self._load_evolver_stats)
            )
            self._evo_status_lbl.set_markup("<span color='#f59e0b'>Evolving...</span>")
        except Exception as ex:
            self.log(str(ex), "ERROR")

    # ── doc-to-LoRA tab ───────────────────────────────────────────────────────

    def _build_lora_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>doc-to-LoRA</b> — Fine-tune local models on security documents\n"
            "<span color='#94a3b8' size='small'>Ingest CVE advisories, tool manuals, and pentest reports. "
            "Auto-generates Q&A training pairs and produces a LoRA adapter.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        grid.attach(Gtk.Label(label="Document dir:", xalign=0), 0, 0, 1, 1)
        self._lora_dir = Gtk.Entry()
        self._lora_dir.set_placeholder_text("/path/to/security-docs/")
        dir_btn = Gtk.Button(label="Browse")
        dir_btn.connect("clicked", self._on_lora_browse)
        dir_row = Gtk.Box(spacing=4)
        dir_row.pack_start(self._lora_dir, True, True, 0)
        dir_row.pack_start(dir_btn, False, False, 0)
        grid.attach(dir_row, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Base model:", xalign=0), 0, 1, 1, 1)
        self._lora_model = Gtk.Entry()
        self._lora_model.set_text("qwen3:8b")
        grid.attach(self._lora_model, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Max files:", xalign=0), 0, 2, 1, 1)
        self._lora_max = Gtk.SpinButton()
        self._lora_max.set_adjustment(Gtk.Adjustment(value=50, lower=1, upper=500, step_increment=10))
        grid.attach(self._lora_max, 1, 2, 1, 1)

        box.pack_start(grid, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        prep_btn = Gtk.Button(label="Prepare Dataset")
        prep_btn.get_style_context().add_class("suggested-action")
        prep_btn.connect("clicked", self._on_lora_prepare)
        btn_row.pack_start(prep_btn, False, False, 0)

        train_btn = Gtk.Button(label="Train LoRA")
        train_btn.connect("clicked", self._on_lora_train)
        btn_row.pack_start(train_btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)

        self._lora_status = Gtk.Label(xalign=0)
        self._lora_status.set_markup("<span color='#64748b'>—</span>")
        box.pack_start(self._lora_status, False, False, 0)

        self.build_terminal()
        box.pack_start(self.terminal, True, True, 0)
        return box

    def _on_lora_browse(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="Select Document Directory",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK),
        )
        if dialog.run() == Gtk.ResponseType.OK:
            self._lora_dir.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_lora_prepare(self, btn):
        src = self._lora_dir.get_text().strip()
        if not src:
            self.log("Set a document directory first.", "ERROR")
            return
        max_files = int(self._lora_max.get_value())
        self._lora_status.set_markup("<span color='#f59e0b'>Preparing dataset...</span>")
        try:
            from shadowcypher.ai.doc_lora import doc_lora
            def _run():
                try:
                    path = doc_lora.prepare_dataset(src, on_output=lambda m: GLib.idle_add(self.on_output, m), max_files=max_files)
                    GLib.idle_add(self._lora_status.set_markup, f"<span color='#22c55e'>Dataset ready: {path}</span>")
                except Exception as e:
                    GLib.idle_add(self._lora_status.set_markup, f"<span color='#f87171'>{e}</span>")
            threading.Thread(target=_run, daemon=True).start()
        except Exception as e:
            self.log(str(e), "ERROR")

    def _on_lora_train(self, btn):
        model = self._lora_model.get_text().strip() or "qwen3:8b"
        try:
            from shadowcypher.ai.doc_lora import doc_lora
            self._lora_status.set_markup("<span color='#f59e0b'>Training...</span>")
            doc_lora.train(model=model, on_output=lambda m: GLib.idle_add(self.on_output, m))
        except Exception as e:
            self.log(str(e), "ERROR")

    # ── Model Merge tab ───────────────────────────────────────────────────────

    def _build_merge_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>Evolutionary Model Merge</b> — Combine multiple Ollama models\n"
            "<span color='#94a3b8' size='small'>Ensemble, chain, or specialist-route across local models. "
            "Fitness-tracks which combination produces best results.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        self._merge_status_lbl = Gtk.Label(xalign=0)
        self._merge_status_lbl.set_markup("<span color='#64748b'>—</span>")
        box.pack_start(self._merge_status_lbl, False, False, 0)

        # Model selection
        models_frm = Gtk.Frame(label="Available Models")
        models_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        models_box.set_property("margin", 10)
        self._merge_model_checks: dict[str, Gtk.CheckButton] = {}
        self._merge_models_box = models_box
        models_frm.add(models_box)
        box.pack_start(models_frm, False, False, 0)

        strategy_row = Gtk.Box(spacing=8)
        strategy_row.pack_start(Gtk.Label(label="Strategy:"), False, False, 0)
        self._merge_strategy = Gtk.ComboBoxText()
        for s in ["ensemble", "chain", "specialist"]:
            self._merge_strategy.append(s, s.capitalize())
        self._merge_strategy.set_active(0)
        strategy_row.pack_start(self._merge_strategy, False, False, 0)
        box.pack_start(strategy_row, False, False, 0)

        test_row = Gtk.Box(spacing=8)
        self._merge_test_entry = Gtk.Entry()
        self._merge_test_entry.set_placeholder_text("Test query to run through merged model...")
        test_row.pack_start(self._merge_test_entry, True, True, 0)
        test_btn = Gtk.Button(label="Run")
        test_btn.get_style_context().add_class("suggested-action")
        test_btn.connect("clicked", self._on_merge_run)
        test_row.pack_start(test_btn, False, False, 0)
        box.pack_start(test_row, False, False, 0)

        refresh_btn = Gtk.Button(label="Refresh Models")
        refresh_btn.connect("clicked", lambda _: self._load_merge_models())
        box.pack_start(refresh_btn, False, False, 0)

        self.build_terminal()
        box.pack_start(self.terminal, True, True, 0)

        GLib.idle_add(self._load_merge_models)
        return box

    def _load_merge_models(self):
        try:
            from shadowcypher.ai.model_merger import model_merger
            models = model_merger.list_ollama_models()
            for child in self._merge_models_box.get_children():
                self._merge_models_box.remove(child)
            self._merge_model_checks.clear()
            if not models:
                self._merge_models_box.pack_start(Gtk.Label(label="No Ollama models found. Is Ollama running?", xalign=0), False, False, 0)
            for m in models:
                cb = Gtk.CheckButton(label=m)
                self._merge_models_box.pack_start(cb, False, False, 0)
                self._merge_model_checks[m] = cb
            self._merge_models_box.show_all()
            self._merge_status_lbl.set_markup(
                f"<span color='#94a3b8'>{model_merger.status()}</span>"
            )
        except Exception as ex:
            self._merge_status_lbl.set_markup(f"<span color='#f87171'>{ex}</span>")

    def _on_merge_run(self, btn):
        query = self._merge_test_entry.get_text().strip()
        if not query:
            return
        selected = [m for m, cb in self._merge_model_checks.items() if cb.get_active()]
        if not selected:
            self.log("Select at least one model.", "ERROR")
            return
        strategy = self._merge_strategy.get_active_id() or "ensemble"

        try:
            from shadowcypher.ai.model_merger import model_merger, MergeConfig
            cfg = MergeConfig(
                models=selected,
                strategy=strategy,
                weights=[1.0 / len(selected)] * len(selected),
            )
            self.log(f"Merge [{strategy}] across {selected}...", "INFO")
            threading.Thread(
                target=lambda: model_merger.merge(query, config=cfg, on_output=lambda m: GLib.idle_add(self.on_output, m)),
                daemon=True
            ).start()
        except Exception as ex:
            self.log(str(ex), "ERROR")

    # ── DroPE tab ─────────────────────────────────────────────────────────────

    def _build_drope_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_property("margin", 12)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup(
            "<b>DroPE</b> — Strategic context compression\n"
            "<span color='#94a3b8' size='small'>Preserves CVEs, IPs, severity markers, and credentials. "
            "Drops nmap boilerplate and blank lines. Lets long scan outputs fit in the AI context window.</span>"
        )
        hdr.set_line_wrap(True)
        box.pack_start(hdr, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)
        grid.attach(Gtk.Label(label="Target tokens:", xalign=0), 0, 0, 1, 1)
        self._drope_tokens = Gtk.SpinButton()
        self._drope_tokens.set_adjustment(Gtk.Adjustment(value=4000, lower=500, upper=32000, step_increment=500))
        grid.attach(self._drope_tokens, 1, 0, 1, 1)
        box.pack_start(grid, False, False, 0)

        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#94a3b8'>Paste long text below and compress it:</span>")
        box.pack_start(lbl, False, False, 0)

        sw_in = Gtk.ScrolledWindow()
        sw_in.set_min_content_height(150)
        self._drope_input = Gtk.TextView()
        self._drope_input.set_wrap_mode(Gtk.WrapMode.WORD)
        sw_in.add(self._drope_input)
        box.pack_start(sw_in, True, True, 0)

        compress_btn = Gtk.Button(label="Compress")
        compress_btn.get_style_context().add_class("suggested-action")
        compress_btn.connect("clicked", self._on_drope_compress)
        box.pack_start(compress_btn, False, False, 0)

        self._drope_result_lbl = Gtk.Label(xalign=0)
        self._drope_result_lbl.set_markup("<span color='#64748b'>—</span>")
        box.pack_start(self._drope_result_lbl, False, False, 0)

        sw_out = Gtk.ScrolledWindow()
        sw_out.set_min_content_height(150)
        self._drope_output = Gtk.TextView()
        self._drope_output.set_editable(False)
        self._drope_output.set_wrap_mode(Gtk.WrapMode.WORD)
        sw_out.add(self._drope_output)
        box.pack_start(sw_out, True, True, 0)

        return box

    def _on_drope_compress(self, btn):
        buf = self._drope_input.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        if not text.strip():
            return
        tokens = int(self._drope_tokens.get_value())
        try:
            from shadowcypher.ai.drope import drope
            compressed = drope.compress(text, target_tokens=tokens)
            ratio = len(compressed) / max(1, len(text))
            self._drope_result_lbl.set_markup(
                f"<span color='#22c55e'>{len(text)} → {len(compressed)} chars ({ratio:.0%})</span>"
            )
            out_buf = self._drope_output.get_buffer()
            out_buf.set_text(compressed)
        except Exception as ex:
            self._drope_result_lbl.set_markup(f"<span color='#f87171'>{ex}</span>")

    # ── Periodic stats refresh ─────────────────────────────────────────────────

    def _refresh_stats(self):
        self._load_memories()
        return True
