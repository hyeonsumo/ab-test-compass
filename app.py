from datetime import datetime
from pathlib import Path
import sys
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import ai_assistant
import storage
import theme as t
from analysis import analyze_experiment, check_srm, required_sample_size
from assignment import assign_variant, generate_salt
from simulator import simulate_traffic


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

storage.init_storage()


def resource_path(relative_path):
    """Resolve bundled assets in local runs and PyInstaller one-file builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


class ABTestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AB Compass")
        self.geometry("1180x760")
        self.minsize(1000, 640)
        self.configure(fg_color=t.BG_BASE)

        try:
            icon_path = resource_path("docs/icon.ico")
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self.refresh_experiments()

        self.after(300, self._show_welcome_if_needed)

    # ============================================================
    # 사이드바
    # ============================================================
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=0,
            fg_color=t.BG_SURFACE,
            border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=80)
        logo_frame.pack(fill="x", padx=t.SPACE_6, pady=(t.SPACE_6, t.SPACE_8))
        logo_frame.pack_propagate(False)

        logo_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_row.pack(anchor="w", pady=(t.SPACE_2, 0))

        try:
            logo_path = resource_path("docs/logo_small.png")
            if logo_path.exists():
                self._logo_img = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(36, 36),
                )
                ctk.CTkLabel(logo_row, image=self._logo_img, text="").pack(
                    side="left", padx=(0, t.SPACE_2)
                )
        except Exception:
            pass

        text_wrap = ctk.CTkFrame(logo_row, fg_color="transparent")
        text_wrap.pack(side="left")

        ctk.CTkLabel(
            text_wrap,
            text="AB Compass",
            font=(t.FONT_FAMILY, 18, "bold"),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_wrap,
            text="EXPERIMENT TOOLKIT",
            font=(t.FONT_FAMILY, 9, "bold"),
            text_color=t.PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        self._sidebar_section_label(sidebar, "EXPERIMENT")
        self._sidebar_button(sidebar, "+  새 실험", self.on_open_create_dialog, "primary")
        self._sidebar_button(sidebar, "✨  AI로 설계", self.on_open_ai_designer, "secondary")

        self._sidebar_section_label(sidebar, "TOOLS", top_pad=t.SPACE_6)
        self._sidebar_button(sidebar, "AI 설정", self.on_open_ai_settings, "ghost")
        self._sidebar_button(sidebar, "🗑  전체 초기화", self.on_reset_all, "ghost")

        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            bottom,
            text="v0.1.0",
            font=t.f_tiny(),
            text_color=t.TEXT_TERTIARY,
        ).pack(anchor="w")

    def _sidebar_section_label(self, parent, text, top_pad=0):
        ctk.CTkLabel(
            parent,
            text=text,
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w", padx=t.SPACE_6, pady=(top_pad, t.SPACE_2))

    def _sidebar_button(self, parent, text, command, variant="ghost"):
        if variant == "primary":
            fg = t.PRIMARY
            hover = t.PRIMARY_HOVER
            text_c = "white"
        elif variant == "secondary":
            fg = t.BG_ELEVATED
            hover = t.BG_SUBTLE
            text_c = t.TEXT_PRIMARY
        else:
            fg = "transparent"
            hover = t.BG_ELEVATED
            text_c = t.TEXT_SECONDARY

        btn = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=fg,
            hover_color=hover,
            text_color=text_c,
            font=t.f_button(),
            height=38,
            corner_radius=t.RADIUS_MD,
            anchor="w",
        )
        btn.pack(fill="x", padx=t.SPACE_4, pady=2)
        return btn

    # ============================================================
    # 메인 콘텐츠
    # ============================================================
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=t.BG_BASE, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent", height=88)
        header.grid(row=0, column=0, sticky="ew", padx=t.SPACE_8, pady=(t.SPACE_8, 0))
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="실험 목록",
            font=t.f_title(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_3, 0))

        ctk.CTkLabel(
            header,
            text="실험을 만들고 시뮬레이션 결과를 확인합니다",
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        list_wrap = ctk.CTkFrame(main, fg_color="transparent")
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=t.SPACE_8, pady=t.SPACE_6)
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self.experiments_frame = ctk.CTkScrollableFrame(
            list_wrap,
            fg_color="transparent",
            scrollbar_button_color=t.BG_SUBTLE,
            scrollbar_button_hover_color=t.BORDER_STRONG,
        )
        self.experiments_frame.grid(row=0, column=0, sticky="nsew")

    # ============================================================
    # 실험 카드
    # ============================================================
    def refresh_experiments(self):
        for child in self.experiments_frame.winfo_children():
            child.destroy()

        df = storage.load_experiments()
        if len(df) == 0:
            self._render_empty_state()
            return

        for _, exp in df.iterrows():
            self._build_experiment_card(exp.to_dict())

    def _render_empty_state(self):
        wrap = ctk.CTkFrame(
            self.experiments_frame,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            height=320,
        )
        wrap.pack(fill="x", pady=t.SPACE_4)
        wrap.pack_propagate(False)

        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="🧪", font=(t.FONT_FAMILY, 40)).pack(
            pady=(0, t.SPACE_3)
        )
        ctk.CTkLabel(
            inner,
            text="아직 실험이 없습니다",
            font=t.f_section(),
            text_color=t.TEXT_PRIMARY,
        ).pack()
        ctk.CTkLabel(
            inner,
            text="새 실험을 만들거나 AI로 설계안을 작성하세요",
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
        ).pack(pady=(t.SPACE_1, t.SPACE_4))

        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack()
        ctk.CTkButton(
            btn_row,
            text="+ 새 실험",
            command=self.on_open_create_dialog,
            fg_color=t.PRIMARY,
            hover_color=t.PRIMARY_HOVER,
            font=t.f_button(),
            height=38,
            width=120,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", padx=t.SPACE_1)
        ctk.CTkButton(
            btn_row,
            text="✨ AI로 설계",
            command=self.on_open_ai_designer,
            fg_color=t.BG_ELEVATED,
            hover_color=t.BG_SUBTLE,
            text_color=t.TEXT_PRIMARY,
            font=t.f_button(),
            height=38,
            width=120,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", padx=t.SPACE_1)

    def _build_experiment_card(self, exp: dict):
        card = ctk.CTkFrame(
            self.experiments_frame,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        card.pack(fill="x", pady=t.SPACE_2)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=t.SPACE_6, pady=t.SPACE_5)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        title_wrap = ctk.CTkFrame(top, fg_color="transparent")
        title_wrap.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_wrap,
            text=str(exp["name"]),
            font=t.f_section(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        created_at = str(exp.get("created_at", ""))[:10]
        ctk.CTkLabel(
            title_wrap,
            text=f"#{exp['id']}  ·  생성 {created_at}",
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="right")

        ctk.CTkButton(
            right,
            text="✕",
            width=28,
            height=28,
            command=lambda e=exp: self.on_delete_experiment(e),
            fg_color="transparent",
            hover_color=t.DANGER_BG,
            text_color=t.TEXT_TERTIARY,
            font=(t.FONT_FAMILY, 13, "bold"),
            corner_radius=t.RADIUS_SM,
        ).pack(side="right", padx=(t.SPACE_2, 0))

        self._status_badge(right, "Running", t.SUCCESS).pack(side="right")

        hypothesis = str(exp.get("hypothesis") or "").strip()
        if hypothesis:
            ctk.CTkLabel(
                inner,
                text=f"가설: {hypothesis}",
                font=t.f_caption(),
                text_color=t.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=760,
            ).pack(anchor="w", pady=(t.SPACE_3, 0))

        duration_days = self._int_value(exp.get("duration_days"), 14)
        meta_text = (
            f"A {exp['variant_a_ratio']:.0%} / B {1 - exp['variant_a_ratio']:.0%}"
            f"     ·     기준 {exp['baseline_rate']:.1%}"
            f"     ·     예상 효과 +{exp['treatment_effect']:.1%}"
            f"     ·     기간 {duration_days}일"
        )
        ctk.CTkLabel(
            inner,
            text=meta_text,
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_3, 0))

        summary = storage.get_summary(exp["id"])
        total_exposures = summary["A"]["exposures"] + summary["B"]["exposures"]
        if total_exposures == 0:
            indicator_text = "● 데이터 없음"
            indicator_color = t.TEXT_TERTIARY
        elif total_exposures < 1000:
            indicator_text = f"● {total_exposures:,} 노출 (표본 부족)"
            indicator_color = t.WARNING
        else:
            indicator_text = f"● {total_exposures:,} 노출"
            indicator_color = t.SUCCESS

        ctk.CTkLabel(
            inner,
            text=indicator_text,
            font=t.f_caption(),
            text_color=indicator_color,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_1, 0))

        metrics_row = ctk.CTkFrame(inner, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(t.SPACE_4, 0))

        self._metric_block(
            metrics_row,
            label="A 그룹 노출",
            value=f"{summary['A']['exposures']:,}",
            sub=f"전환 {summary['A']['conversions']:,}",
        ).pack(side="left", fill="x", expand=True)

        self._metric_block(
            metrics_row,
            label="A 전환율",
            value=f"{summary['A']['rate']:.2%}",
            sub="대조군",
        ).pack(side="left", fill="x", expand=True)

        self._metric_block(
            metrics_row,
            label="B 그룹 노출",
            value=f"{summary['B']['exposures']:,}",
            sub=f"전환 {summary['B']['conversions']:,}",
        ).pack(side="left", fill="x", expand=True)

        self._metric_block(
            metrics_row,
            label="B 전환율",
            value=f"{summary['B']['rate']:.2%}",
            sub="실험군",
            highlight=summary["B"]["rate"] > summary["A"]["rate"]
            and summary["A"]["rate"] > 0,
        ).pack(side="left", fill="x", expand=True)

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(t.SPACE_5, 0))

        num_entry = ctk.CTkEntry(
            actions,
            placeholder_text="유저 수",
            width=110,
            height=36,
            fg_color=t.BG_ELEVATED,
            border_color=t.BORDER,
            border_width=1,
            corner_radius=t.RADIUS_MD,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
        )
        num_entry.pack(side="left")
        num_entry.insert(0, "5000")

        ctk.CTkButton(
            actions,
            text="시뮬레이션",
            width=110,
            height=36,
            command=lambda e=exp, ne=num_entry: self.on_simulate(e, ne),
            fg_color=t.BG_ELEVATED,
            hover_color=t.BG_SUBTLE,
            text_color=t.TEXT_PRIMARY,
            font=t.f_button(),
            corner_radius=t.RADIUS_MD,
            border_width=1,
            border_color=t.BORDER,
        ).pack(side="left", padx=(t.SPACE_2, 0))

        ctk.CTkButton(
            actions,
            text="결과 분석 →",
            width=120,
            height=36,
            command=lambda e=exp: self.on_analyze(e),
            fg_color=t.PRIMARY,
            hover_color=t.PRIMARY_HOVER,
            text_color="white",
            font=t.f_button(),
            corner_radius=t.RADIUS_MD,
        ).pack(side="right")

    def _status_badge(self, parent, text, color):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            wrap,
            text="●",
            font=(t.FONT_FAMILY, 12),
            text_color=color,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            wrap,
            text=text,
            font=t.f_caption_bold(),
            text_color=t.TEXT_SECONDARY,
        ).pack(side="left")
        return wrap

    def _metric_block(self, parent, label, value, sub="", highlight=False):
        block = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(
            block,
            text=label,
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w")

        value_color = t.SUCCESS if highlight else t.TEXT_PRIMARY
        ctk.CTkLabel(
            block,
            text=value,
            font=(t.FONT_FAMILY, 20, "bold"),
            text_color=value_color,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        if sub:
            ctk.CTkLabel(
                block,
                text=sub,
                font=t.f_tiny(),
                text_color=t.TEXT_TERTIARY,
                anchor="w",
            ).pack(anchor="w")

        return block

    # ============================================================
    # 생성 / 시뮬레이션 / 분석
    # ============================================================
    def on_delete_experiment(self, experiment: dict):
        summary = storage.get_summary(experiment["id"])
        total_events = (
            summary["A"]["exposures"]
            + summary["B"]["exposures"]
            + summary["A"]["conversions"]
            + summary["B"]["conversions"]
        )

        dialog = ctk.CTkToplevel(self)
        dialog.title("실험 삭제")
        dialog.geometry("440x260")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(fg_color=t.BG_SURFACE)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 220
        y = self.winfo_y() + (self.winfo_height() // 2) - 130
        dialog.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            frame,
            text="실험을 삭제하시겠어요?",
            font=t.f_section(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text=str(experiment["name"]),
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(2, t.SPACE_4))

        if total_events > 0:
            warn = ctk.CTkFrame(frame, fg_color=t.DANGER_BG, corner_radius=t.RADIUS_MD)
            warn.pack(fill="x", pady=(0, t.SPACE_4))
            ctk.CTkLabel(
                warn,
                text=(
                    f"이 실험에 쌓인 {total_events:,}개의 이벤트도 함께 삭제됩니다.\n"
                    "이 작업은 되돌릴 수 없습니다."
                ),
                font=t.f_body(),
                text_color=t.TEXT_PRIMARY,
                wraplength=380,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=t.SPACE_4, pady=t.SPACE_3)
        else:
            ctk.CTkLabel(
                frame,
                text="이 작업은 되돌릴 수 없습니다.",
                font=t.f_body(),
                text_color=t.TEXT_SECONDARY,
            ).pack(anchor="w", pady=(0, t.SPACE_4))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x")

        def confirm_delete():
            storage.delete_experiment(experiment["id"])
            dialog.destroy()
            self.refresh_experiments()

        ctk.CTkButton(
            btn_row,
            text="취소",
            command=dialog.destroy,
            fg_color=t.BG_ELEVATED,
            hover_color=t.BG_SUBTLE,
            text_color=t.TEXT_PRIMARY,
            font=t.f_button(),
            height=40,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))

        ctk.CTkButton(
            btn_row,
            text="삭제",
            command=confirm_delete,
            fg_color=t.DANGER,
            hover_color=t.DANGER_TEXT,
            text_color="white",
            font=t.f_button(),
            height=40,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", fill="x", expand=True, padx=(t.SPACE_2, 0))

    def on_reset_all(self):
        confirmed = messagebox.askyesno(
            "전체 초기화",
            "모든 실험과 이벤트 데이터가 삭제됩니다.\n계속하시겠어요?",
            icon="warning",
        )
        if confirmed:
            storage.reset_all()
            self.refresh_experiments()

    def on_open_create_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("새 실험 만들기")
        win.geometry("520x680")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=t.BG_SURFACE)
        win.resizable(False, False)

        frame = ctk.CTkScrollableFrame(win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            frame,
            text="새 실험 만들기",
            font=t.f_section(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, t.SPACE_1))
        ctk.CTkLabel(
            frame,
            text="가설과 사전 종료 기준을 함께 입력하세요",
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, t.SPACE_5))

        name_entry = self._styled_field(frame, "실험 이름", "예: 결제 버튼 색상 테스트")
        hypothesis_box = self._styled_textbox(
            frame,
            "가설 (필수)",
            "예: 결제 버튼 색상을 바꾸면 결제 전환율이 높아질 것이다",
        )
        ratio_entry = self._styled_field(frame, "A 그룹 비율 (0~1)", "0.5")
        baseline_entry = self._styled_field(frame, "기준 전환율", "0.10")
        effect_entry = self._styled_field(frame, "예상 효과 (B의 lift)", "0.05")
        duration_entry = self._styled_field(frame, "실험 기간 (일)", "14")

        status = ctk.CTkLabel(frame, text="", font=t.f_caption(), text_color=t.DANGER)
        status.pack(anchor="w", pady=(t.SPACE_2, 0))

        def submit():
            name = name_entry.get().strip()
            hypothesis = hypothesis_box.get("1.0", "end").strip()
            if not name:
                status.configure(text="실험 이름은 필수입니다.")
                return
            if not hypothesis:
                status.configure(text="가설은 필수입니다.")
                return

            try:
                ratio = float(ratio_entry.get() or "0.5")
                baseline = float(baseline_entry.get() or "0.10")
                effect = float(effect_entry.get() or "0.05")
                duration = int(duration_entry.get() or "14")
            except ValueError:
                status.configure(text="숫자 입력값을 확인하세요.")
                return

            if not 0.05 <= ratio <= 0.95:
                status.configure(text="A 그룹 비율은 0.05 ~ 0.95 사이여야 합니다.")
                return
            if not 0 < baseline < 1:
                status.configure(text="기준 전환율은 0과 1 사이여야 합니다. (예: 0.10)")
                return
            if not -0.99 <= effect <= 5:
                status.configure(text="예상 효과는 -0.99 ~ 5 사이여야 합니다.")
                return
            if duration < 1:
                status.configure(text="실험 기간은 1일 이상이어야 합니다.")
                return

            exp_id = storage.create_experiment(
                name,
                generate_salt(),
                ratio,
                baseline,
                effect,
                hypothesis=hypothesis,
                duration_days=duration,
            )
            required = required_sample_size(baseline, effect)
            required_text = f"{required:,}명" if required is not None else "계산 불가 (효과 0%)"
            win.destroy()
            self.refresh_experiments()
            messagebox.showinfo(
                "실험 생성 완료",
                (
                    f"실험 #{exp_id}을 만들었습니다.\n\n"
                    f"권장 표본 크기: 그룹당 {required_text}\n"
                    f"실험 기간: {duration}일\n\n"
                    "p-value를 보고 조기 중단하지 마세요.\n"
                    "미리 정한 기간/표본을 채우는 것이 중요합니다."
                ),
            )

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(t.SPACE_5, 0))

        ctk.CTkButton(
            btn_row,
            text="취소",
            command=win.destroy,
            fg_color=t.BG_ELEVATED,
            hover_color=t.BG_SUBTLE,
            text_color=t.TEXT_PRIMARY,
            font=t.f_button(),
            height=40,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))

        ctk.CTkButton(
            btn_row,
            text="실험 생성",
            command=submit,
            fg_color=t.PRIMARY,
            hover_color=t.PRIMARY_HOVER,
            text_color="white",
            font=t.f_button(),
            height=40,
            corner_radius=t.RADIUS_MD,
        ).pack(side="left", fill="x", expand=True, padx=(t.SPACE_2, 0))

    def _styled_field(self, parent, label, placeholder, show=None):
        ctk.CTkLabel(
            parent,
            text=label,
            font=t.f_label(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_3, 4))
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show=show,
            height=40,
            fg_color=t.BG_ELEVATED,
            border_color=t.BORDER,
            border_width=1,
            corner_radius=t.RADIUS_MD,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
        )
        entry.pack(fill="x")
        return entry

    def _styled_textbox(self, parent, label, placeholder):
        ctk.CTkLabel(
            parent,
            text=label,
            font=t.f_label(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_3, 4))
        box = ctk.CTkTextbox(
            parent,
            height=80,
            fg_color=t.BG_ELEVATED,
            border_color=t.BORDER,
            border_width=1,
            corner_radius=t.RADIUS_MD,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
        )
        box.pack(fill="x")
        box.insert("1.0", placeholder)

        def clear_placeholder(_event):
            if box.get("1.0", "end").strip() == placeholder:
                box.delete("1.0", "end")

        box.bind("<FocusIn>", clear_placeholder)
        return box

    def on_simulate(self, experiment, num_entry):
        raw = num_entry.get().strip()
        try:
            n = int(raw or "5000")
        except ValueError:
            messagebox.showerror("오류", "유저 수는 정수여야 합니다.")
            return

        if n < 100:
            messagebox.showwarning(
                "표본이 너무 작습니다",
                "최소 100명 이상을 권장합니다.\n표본이 작으면 분석 결과의 변동이 클 수 있습니다.",
            )
            return
        if n > 1_000_000:
            messagebox.showwarning(
                "표본이 너무 큽니다",
                "최대 1,000,000명까지만 시뮬레이션할 수 있습니다.",
            )
            return

        progress_win = ctk.CTkToplevel(self)
        progress_win.title("시뮬레이션")
        progress_win.geometry("440x150")
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.configure(fg_color=t.BG_SURFACE)

        frame = ctk.CTkFrame(progress_win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            frame,
            text="시뮬레이션 실행 중",
            font=t.f_subsection(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text=str(experiment["name"]),
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, t.SPACE_3))

        bar = ctk.CTkProgressBar(
            frame,
            height=8,
            progress_color=t.PRIMARY,
            fg_color=t.BG_ELEVATED,
        )
        bar.pack(fill="x")
        bar.set(0)

        self.update()

        def cb(ratio):
            bar.set(ratio)
            progress_win.update()

        result = simulate_traffic(experiment, n, progress_callback=cb)
        progress_win.destroy()
        self.refresh_experiments()
        messagebox.showinfo(
            "완료",
            (
                f"{result['exposures']:,}명의 노출 이벤트를 만들었습니다.\n"
                f"A 전환: {result['conversions_a']:,}명\n"
                f"B 전환: {result['conversions_b']:,}명"
            ),
        )

    def on_analyze(self, experiment):
        summary = storage.get_summary(experiment["id"])
        a_total = summary["A"]["exposures"]
        b_total = summary["B"]["exposures"]

        if a_total == 0 or b_total == 0:
            messagebox.showwarning("데이터 부족", "먼저 시뮬레이션을 실행하세요.")
            return

        result = analyze_experiment(
            a_total,
            summary["A"]["conversions"],
            b_total,
            summary["B"]["conversions"],
        )
        if "error" in result:
            messagebox.showwarning("분석 불가", result["error"])
            return

        srm = check_srm(a_total, b_total, experiment["variant_a_ratio"])
        required = required_sample_size(
            experiment["baseline_rate"],
            experiment["treatment_effect"],
        )
        self._show_analysis_window(experiment, summary, result, srm, required)

    def _show_analysis_window(self, experiment, summary, result, srm, required):
        win = ctk.CTkToplevel(self)
        win.title(f"결과 분석 - {experiment['name']}")
        win.geometry("680x760")
        win.transient(self)
        win.configure(fg_color=t.BG_BASE)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            scroll,
            text=str(experiment["name"]),
            font=t.f_title(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            scroll,
            text=f"실험 #{experiment['id']}",
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
        ).pack(anchor="w", pady=(2, t.SPACE_5))

        self._show_peeking_warning(scroll, experiment, summary, required)

        is_sig = result["significant"]
        conclusion = "통계적으로 유의한 차이" if is_sig else "통계적으로 유의하지 않음"
        color = t.SUCCESS if is_sig else t.WARNING
        self._notice_card(scroll, conclusion, self._interpret_result(result), color)

        self._section(scroll, "그룹별 성과")
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, t.SPACE_4))
        self._stat_card(
            row,
            (
                f"A 그룹 (대조군)\n"
                f"노출: {summary['A']['exposures']:,}명\n"
                f"전환: {summary['A']['conversions']:,}명\n"
                f"전환율: {result['rate_a']:.3%}"
            ),
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))
        self._stat_card(
            row,
            (
                f"B 그룹 (실험군)\n"
                f"노출: {summary['B']['exposures']:,}명\n"
                f"전환: {summary['B']['conversions']:,}명\n"
                f"전환율: {result['rate_b']:.3%}"
            ),
        ).pack(side="left", fill="x", expand=True, padx=(t.SPACE_2, 0))

        self._section(scroll, "효과 크기")
        self._stat_card(
            scroll,
            (
                f"절대 차이 (B - A): {result['diff']:+.3%}\n"
                f"상대적 개선 (Lift): {result['lift']:+.2%}\n"
                f"95% 신뢰구간: [{result['ci_lower']:+.3%}, {result['ci_upper']:+.3%}]"
            ),
        ).pack(fill="x", pady=(0, t.SPACE_4))

        self._section(scroll, "통계 검정")
        enough_sample = (
            summary["A"]["exposures"] >= required
            and summary["B"]["exposures"] >= required
        )
        self._stat_card(
            scroll,
            (
                f"p-value: {result['p_value']:.4f}\n"
                f"z-score: {result['z_score']:.3f}\n"
                f"유의수준: {result['alpha']}\n"
                f"필요 표본 (그룹당): {required:,}명 "
                f"({'충족' if enough_sample else '미달'})"
            ),
        ).pack(fill="x", pady=(0, t.SPACE_4))

        self._section(scroll, "데이터 품질 (SRM)")
        srm_title = "SRM 감지됨" if srm["has_srm"] else "정상"
        srm_color = t.DANGER if srm["has_srm"] else t.INFO
        self._notice_card(
            scroll,
            srm_title,
            (
                f"실제 A 비율: {srm['actual_a_ratio']:.4f} "
                f"(기대: {srm['expected_a_ratio']:.4f})\n"
                f"카이제곱 p-value: {srm['p_value']:.4f}"
            ),
            srm_color,
        )

    def _show_peeking_warning(self, parent, experiment, summary, required):
        created_at = self._parse_datetime(experiment.get("created_at"))
        days_elapsed = (datetime.now() - created_at).days if created_at else 0
        duration_days = self._int_value(experiment.get("duration_days"), 14)
        total_samples = summary["A"]["exposures"] + summary["B"]["exposures"]
        required_total = required * 2

        if days_elapsed < duration_days or total_samples < required_total:
            self._notice_card(
                parent,
                "실험이 아직 완료되지 않았습니다",
                (
                    f"경과: {days_elapsed}/{duration_days}일, "
                    f"표본: {total_samples:,}/{required_total:,}명\n"
                    "지금 결정을 내리면 엿보기 편향으로 결과가 왜곡될 수 있습니다."
                ),
                t.WARNING,
            )

    def _section(self, parent, title):
        ctk.CTkLabel(
            parent,
            text=title,
            font=t.f_subsection(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(t.SPACE_4, t.SPACE_2))

    def _stat_card(self, parent, text):
        frame = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_MD,
            border_width=1,
            border_color=t.BORDER,
        )
        ctk.CTkLabel(
            frame,
            text=text,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
            justify="left",
        ).pack(padx=t.SPACE_4, pady=t.SPACE_4, anchor="w")
        return frame

    def _notice_card(self, parent, title, text, color):
        frame = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_MD,
            border_width=1,
            border_color=t.BORDER,
        )
        frame.pack(fill="x", pady=(0, t.SPACE_4))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=t.SPACE_4, pady=t.SPACE_4)
        ctk.CTkLabel(row, text="●", text_color=color, font=(t.FONT_FAMILY, 12)).pack(
            side="left", padx=(0, t.SPACE_2)
        )
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            content,
            text=title,
            font=t.f_subsection(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            content,
            text=text,
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", pady=(t.SPACE_1, 0))
        return frame

    def _interpret_result(self, result):
        p = result["p_value"]
        diff = result["diff"]
        lift = result["lift"]

        if result["significant"] and diff > 0:
            return (
                f"B 그룹이 A 그룹보다 {lift:+.1%} 더 높은 전환율을 보였습니다. "
                f"p-value는 {p:.4f}입니다."
            )
        if result["significant"] and diff < 0:
            return (
                f"B 그룹이 A 그룹보다 {lift:+.1%} 낮은 전환율을 보였습니다. "
                f"p-value는 {p:.4f}입니다."
            )
        return (
            f"두 그룹의 차이({diff:+.3%})가 통계적으로 의미있는 차이라고 보기 어렵습니다. "
            f"p-value는 {p:.4f}입니다."
        )

    # ============================================================
    # AI / 설정 / 환영
    # ============================================================
    def _show_analysis_window(self, experiment, summary, result, srm, required):
        win = ctk.CTkToplevel(self)
        win.title(f"결과 분석 - {experiment['name']}")
        win.geometry("720x820")
        win.transient(self)
        win.configure(fg_color=t.BG_BASE)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            scroll,
            text=str(experiment["name"]),
            font=t.f_title(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            scroll,
            text=f"실험 #{experiment['id']}  ·  생성 {str(experiment['created_at'])[:10]}",
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w", pady=(2, t.SPACE_5))

        self._show_peeking_warning(scroll, experiment, summary, required)

        if result["significant"] and result["diff"] > 0:
            conclusion = "통계적으로 유의함 · B 그룹 우세"
            conclusion_color = t.SUCCESS
        elif result["significant"]:
            conclusion = "통계적으로 유의함 · B 그룹 열세"
            conclusion_color = t.DANGER
        else:
            conclusion = "통계적으로 유의하지 않음"
            conclusion_color = t.WARNING

        self._render_warning_card(
            scroll,
            conclusion,
            (
                f"p-value {result['p_value']:.4f}  ·  "
                f"절대 차이 {result['diff']:+.3%}  ·  "
                f"상대 개선 {result['lift']:+.2%}"
            ),
            color=conclusion_color,
        )

        self._section_header(scroll, "시각화")
        from charts import make_comparison_chart, make_trend_chart

        chart_card_1 = ctk.CTkFrame(
            scroll,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        chart_card_1.pack(fill="x", pady=(0, t.SPACE_3))
        ctk.CTkLabel(
            chart_card_1,
            text="그룹별 전환율 비교",
            font=t.f_caption_bold(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", padx=t.SPACE_5, pady=(t.SPACE_4, 0))
        comparison_widget = make_comparison_chart(chart_card_1, result)
        comparison_widget.pack(fill="x", padx=t.SPACE_3, pady=(t.SPACE_2, t.SPACE_3))

        chart_card_2 = ctk.CTkFrame(
            scroll,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        chart_card_2.pack(fill="x", pady=(0, t.SPACE_5))
        ctk.CTkLabel(
            chart_card_2,
            text="누적 전환율 추이",
            font=t.f_caption_bold(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", padx=t.SPACE_5, pady=(t.SPACE_4, 0))
        ctk.CTkLabel(
            chart_card_2,
            text="노출 수가 늘어날 때 두 그룹의 누적 전환율이 어떻게 변하는지 확인합니다",
            font=t.f_tiny(),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w", padx=t.SPACE_5)
        exposures_df = storage.load_exposures(experiment["id"])
        conversions_df = storage.load_conversions(experiment["id"])
        trend_widget = make_trend_chart(chart_card_2, exposures_df, conversions_df)
        trend_widget.pack(fill="x", padx=t.SPACE_3, pady=(t.SPACE_2, t.SPACE_3))

        self._section_header(scroll, "그룹별 성과")
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, t.SPACE_5))
        self._big_metric_card(
            row,
            "A 그룹 · 대조군",
            result["rate_a"],
            summary["A"]["exposures"],
            summary["A"]["conversions"],
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))
        self._big_metric_card(
            row,
            "B 그룹 · 실험군",
            result["rate_b"],
            summary["B"]["exposures"],
            summary["B"]["conversions"],
            highlight=result["rate_b"] > result["rate_a"],
        ).pack(side="left", fill="x", expand=True, padx=(t.SPACE_2, 0))

        self._section_header(scroll, "효과 크기")
        self._stat_table(
            scroll,
            [
                ("절대 차이 (B - A)", f"{result['diff']:+.3%}"),
                ("상대적 개선 (Lift)", f"{result['lift']:+.2%}"),
                (
                    "95% 신뢰구간",
                    f"[{result['ci_lower']:+.3%}, {result['ci_upper']:+.3%}]",
                ),
            ],
        )

        enough_sample = (
            required is not None
            and summary["A"]["exposures"] >= required
            and summary["B"]["exposures"] >= required
        )
        required_text = f"{required:,}명" if required is not None else "계산 불가"
        self._section_header(scroll, "통계 검정")
        self._stat_table(
            scroll,
            [
                ("p-value", f"{result['p_value']:.4f}"),
                ("z-score", f"{result['z_score']:.3f}"),
                ("유의수준", f"{result['alpha']:.2f}"),
                (
                    "필요 표본 · 그룹당",
                    required_text,
                    "충족" if enough_sample else "미달",
                    t.SUCCESS if enough_sample else t.WARNING,
                ),
            ],
        )

        self._section_header(scroll, "데이터 품질 · SRM")
        self._stat_table(
            scroll,
            [
                ("실제 A 비율", f"{srm['actual_a_ratio']:.4f}"),
                ("기대 A 비율", f"{srm['expected_a_ratio']:.4f}"),
                ("카이제곱 p-value", f"{srm['p_value']:.4f}"),
                (
                    "SRM 상태",
                    "배정 비율 검사",
                    "점검 필요" if srm["has_srm"] else "정상",
                    t.DANGER if srm["has_srm"] else t.SUCCESS,
                ),
            ],
        )

        self._section_header(scroll, "결과 해석")
        self._render_interpretation(scroll, result)

    def _show_peeking_warning(self, parent, experiment, summary, required):
        created_at = self._parse_datetime(experiment.get("created_at"))
        days_elapsed = (datetime.now() - created_at).days if created_at else 0
        duration_days = self._int_value(experiment.get("duration_days"), 14)
        total_samples = summary["A"]["exposures"] + summary["B"]["exposures"]

        if required is None:
            self._render_warning_card(
                parent,
                "사전 표본 크기를 계산할 수 없습니다",
                (
                    "예상 효과가 0%인 대조 시나리오입니다. 통계 결과를 연습용으로만 "
                    "해석하고, 실제 실험에서는 감지하려는 최소 효과를 먼저 정하세요."
                ),
            )
            return

        required_total = required * 2
        progress = min(total_samples / required_total, 1) if required_total else 0
        if days_elapsed < duration_days or total_samples < required_total:
            self._render_warning_card(
                parent,
                "표본이 아직 부족합니다",
                (
                    f"경과 기간: {days_elapsed}/{duration_days}일\n"
                    f"표본 도달률: {progress:.1%}  ·  "
                    f"{total_samples:,}/{required_total:,}명\n"
                    "지금 결정을 내리면 엿보기 편향으로 결과가 왜곡될 수 있습니다."
                ),
            )

    def _section_header(self, parent, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=t.f_subsection(),
            text_color=t.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_4, t.SPACE_2))

    def _big_metric_card(self, parent, label, rate, exposures, conversions, highlight=False):
        card = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=t.SPACE_5, pady=t.SPACE_5)

        ctk.CTkLabel(
            inner,
            text=label,
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w")

        rate_color = t.SUCCESS if highlight else t.TEXT_PRIMARY
        ctk.CTkLabel(
            inner,
            text=f"{rate:.2%}",
            font=(t.FONT_FAMILY, 28, "bold"),
            text_color=rate_color,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_1, 0))

        ctk.CTkLabel(
            inner,
            text=f"노출 {exposures:,}  ·  전환 {conversions:,}",
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_1, 0))
        return card

    def _stat_table(self, parent, rows):
        card = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        card.pack(fill="x", pady=(0, t.SPACE_5))

        for i, row in enumerate(rows):
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.pack(
                fill="x",
                padx=t.SPACE_5,
                pady=(t.SPACE_3 if i == 0 else 0, t.SPACE_3),
            )

            ctk.CTkLabel(
                line,
                text=row[0],
                font=t.f_caption(),
                text_color=t.TEXT_SECONDARY,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                line,
                text=row[1],
                font=t.f_body_medium(),
                text_color=t.TEXT_PRIMARY,
                anchor="e",
            ).pack(side="right")

            if len(row) >= 4:
                ctk.CTkLabel(
                    line,
                    text=f"  ● {row[2]}",
                    font=t.f_caption_bold(),
                    text_color=row[3],
                ).pack(side="right")

            if i < len(rows) - 1:
                ctk.CTkFrame(card, fg_color=t.BORDER, height=1).pack(
                    fill="x", padx=t.SPACE_5
                )

    def _render_warning_card(self, parent, title, text, color=t.WARNING):
        if color == t.SUCCESS:
            bg = t.SUCCESS_BG
            accent = t.SUCCESS_TEXT
        elif color == t.DANGER:
            bg = t.DANGER_BG
            accent = t.DANGER_TEXT
        elif color == t.INFO:
            bg = t.INFO_BG
            accent = t.INFO_TEXT
        else:
            bg = t.WARNING_BG
            accent = t.WARNING_TEXT

        card = ctk.CTkFrame(
            parent,
            fg_color=bg,
            corner_radius=t.RADIUS_LG,
        )
        card.pack(fill="x", pady=(0, t.SPACE_5))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=t.SPACE_5, pady=t.SPACE_4)

        ctk.CTkLabel(
            inner,
            text=f"●  {title}",
            font=t.f_subsection(),
            text_color=accent,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text=text,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
            wraplength=620,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(t.SPACE_2, 0))

    def _render_interpretation(self, parent, result):
        p = result["p_value"]
        diff = result["diff"]
        lift = result["lift"]

        if result["significant"] and diff > 0:
            text = (
                f"B 그룹의 전환율이 A 그룹보다 {lift:+.1%} 높습니다. "
                f"p-value는 {p:.4f}이며, 신뢰구간에 0이 포함되지 않습니다. "
                "현재 표본에서는 B 그룹의 개선 효과가 확인됩니다."
            )
        elif result["significant"] and diff < 0:
            text = (
                f"B 그룹의 전환율이 A 그룹보다 {lift:+.1%} 낮습니다. "
                f"p-value는 {p:.4f}이며, 통계적으로 유의한 차이입니다. "
                "현재 표본에서는 B안이 전환율을 낮춘 것으로 보입니다."
            )
        else:
            text = (
                f"관측된 차이는 {diff:+.3%}, p-value는 {p:.4f}입니다. "
                "현재 표본에서는 유의한 차이를 확인하지 못했습니다. "
                "표본 수와 신뢰구간을 함께 확인하세요."
            )

        card = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_LG,
            border_width=1,
            border_color=t.BORDER,
        )
        card.pack(fill="x")
        ctk.CTkLabel(
            card,
            text=text,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
            wraplength=620,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=t.SPACE_5, pady=t.SPACE_4)

    def on_open_ai_designer(self):
        key = ai_assistant.get_api_key()
        if not key:
            messagebox.showinfo(
                "AI 설정 필요",
                "AI 실험 설계 기능을 사용하려면 Gemini API 키를 먼저 저장하세요.",
            )
            self.on_open_ai_settings()
            return

        win = ctk.CTkToplevel(self)
        win.title("AI로 실험 설계")
        win.geometry("680x720")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=t.BG_BASE)

        frame = ctk.CTkScrollableFrame(win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            frame,
            text="AI로 실험 설계",
            font=t.f_title(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text="아이디어를 입력하면 가설, 지표, 표본 계획이 포함된 초안을 만듭니다.",
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, t.SPACE_5))

        prompt_box = ctk.CTkTextbox(
            frame,
            height=120,
            fg_color=t.BG_ELEVATED,
            border_color=t.BORDER,
            border_width=1,
            corner_radius=t.RADIUS_MD,
            font=t.f_body(),
            text_color=t.TEXT_PRIMARY,
        )
        prompt_box.pack(fill="x")
        prompt_box.insert(
            "1.0",
            "예: 결제 버튼 색상을 파란색에서 초록색으로 바꾸면 결제 전환율이 올라갈 것 같다.",
        )

        status = ctk.CTkLabel(frame, text="", font=t.f_caption(), text_color=t.TEXT_SECONDARY)
        status.pack(anchor="w", pady=(t.SPACE_3, 0))

        result_holder = {"design": None}
        result_frame = ctk.CTkFrame(
            frame,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_MD,
            border_width=1,
            border_color=t.BORDER,
        )

        def render_design(design: dict):
            for child in result_frame.winfo_children():
                child.destroy()
            if not result_frame.winfo_ismapped():
                result_frame.pack(fill="x", pady=(t.SPACE_5, 0))

            rows = [
                ("실험 이름", design["name"]),
                ("가설", design["hypothesis"]),
                ("A안", design["variant_a"]),
                ("B안", design["variant_b"]),
                ("핵심 지표", design["primary_metric"]),
                ("A 비율", f"{design['variant_a_ratio']:.0%}"),
                ("기준 전환율", f"{design['baseline_rate']:.1%}"),
                ("예상 효과", f"+{design['treatment_effect']:.1%}"),
                ("권장 기간", f"{design['duration_days']}일"),
            ]

            for label, value in rows:
                ctk.CTkLabel(
                    result_frame,
                    text=label,
                    font=t.f_caption_bold(),
                    text_color=t.TEXT_TERTIARY,
                ).pack(anchor="w", padx=t.SPACE_4, pady=(t.SPACE_3, 0))
                ctk.CTkLabel(
                    result_frame,
                    text=str(value),
                    font=t.f_body(),
                    text_color=t.TEXT_PRIMARY,
                    justify="left",
                    wraplength=580,
                ).pack(anchor="w", padx=t.SPACE_4, pady=(2, 0))

            if design.get("risk_notes"):
                ctk.CTkLabel(
                    result_frame,
                    text="실무 주의점",
                    font=t.f_caption_bold(),
                    text_color=t.TEXT_TERTIARY,
                ).pack(anchor="w", padx=t.SPACE_4, pady=(t.SPACE_3, 0))
                ctk.CTkLabel(
                    result_frame,
                    text="\n".join(f"• {note}" for note in design["risk_notes"]),
                    font=t.f_caption(),
                    text_color=t.TEXT_SECONDARY,
                    justify="left",
                    wraplength=580,
                ).pack(anchor="w", padx=t.SPACE_4, pady=(2, t.SPACE_4))

        button_row = ctk.CTkFrame(frame, fg_color="transparent")
        button_row.pack(fill="x", pady=(t.SPACE_5, 0))

        def generate():
            prompt = prompt_box.get("1.0", "end").strip()
            if not prompt:
                status.configure(text="아이디어를 입력하세요.", text_color=t.DANGER)
                return

            status.configure(text="설계안을 만드는 중입니다...", text_color=t.TEXT_SECONDARY)
            win.update()

            try:
                design = ai_assistant.design_experiment(prompt)
            except Exception as exc:
                status.configure(text="AI 설계 실패. 터미널 로그를 확인하세요.", text_color=t.DANGER)
                messagebox.showerror("AI 설계 실패", str(exc))
                return

            result_holder["design"] = design
            status.configure(text="설계안을 만들었습니다.", text_color=t.SUCCESS)
            render_design(design)

        def create_from_design():
            design = result_holder["design"]
            if not design:
                status.configure(text="먼저 설계안을 만드세요.", text_color=t.DANGER)
                return

            exp_id = storage.create_experiment(
                design["name"],
                generate_salt(),
                design["variant_a_ratio"],
                design["baseline_rate"],
                design["treatment_effect"],
                hypothesis=design["hypothesis"],
                duration_days=design["duration_days"],
            )
            win.destroy()
            self.refresh_experiments()
            messagebox.showinfo("실험 생성 완료", f"설계안으로 실험 #{exp_id}을 만들었습니다.")

        ctk.CTkButton(
            button_row,
            text="취소",
            command=win.destroy,
            fg_color=t.BG_ELEVATED,
            hover_color=t.BG_SUBTLE,
            text_color=t.TEXT_PRIMARY,
            font=t.f_button(),
            height=40,
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))

        ctk.CTkButton(
            button_row,
            text="설계안 만들기",
            command=generate,
            fg_color=t.PRIMARY,
            hover_color=t.PRIMARY_HOVER,
            font=t.f_button(),
            height=40,
        ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))

        ctk.CTkButton(
            button_row,
            text="이 설계로 실험 만들기",
            command=create_from_design,
            fg_color=t.SUCCESS,
            hover_color=t.SUCCESS_BG,
            font=t.f_button(),
            height=40,
        ).pack(side="left", fill="x", expand=True)

    def on_open_ai_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("AI 설정")
        win.geometry("480x260")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=t.BG_SURFACE)
        win.resizable(False, False)

        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        ctk.CTkLabel(
            frame,
            text="AI 설정",
            font=t.f_section(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text="키는 data/config.json에 저장되며, AI 요청 시 Google Gemini로 전송됩니다.",
            font=t.f_caption(),
            text_color=t.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(2, t.SPACE_5))

        key_entry = self._styled_field(frame, "Gemini API 키", "AIza...", show="*")
        current_key = ai_assistant.get_api_key()
        if current_key:
            key_entry.insert(0, current_key)

        status = ctk.CTkLabel(frame, text="", font=t.f_caption(), text_color=t.DANGER)
        status.pack(anchor="w", pady=(t.SPACE_2, 0))

        def save():
            key = key_entry.get().strip()
            if not key.startswith("AIza"):
                status.configure(text="Gemini 키는 보통 'AIza'로 시작합니다.")
                return
            ai_assistant.save_api_key(key)
            ai_assistant.mark_setup_done()
            win.destroy()
            messagebox.showinfo("저장 완료", "API 키가 저장되었습니다.")

        ctk.CTkButton(
            frame,
            text="저장",
            command=save,
            fg_color=t.PRIMARY,
            hover_color=t.PRIMARY_HOVER,
            font=t.f_button(),
            height=40,
            corner_radius=t.RADIUS_MD,
        ).pack(fill="x", pady=(t.SPACE_5, 0))

    def _show_welcome_if_needed(self):
        if ai_assistant.is_setup_done():
            return
        self._open_welcome_window()

    def _open_welcome_window(self):
        win = ctk.CTkToplevel(self)
        win.title("환영합니다")
        win.geometry("620x680")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        win.configure(fg_color=t.BG_BASE)

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 310
        y = self.winfo_y() + (self.winfo_height() // 2) - 340
        win.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=t.SPACE_6, pady=t.SPACE_6)

        progress_label = ctk.CTkLabel(
            container,
            text="1 / 2",
            font=t.f_caption(),
            text_color=t.TEXT_TERTIARY,
        )
        progress_label.pack(anchor="e")

        body = ctk.CTkScrollableFrame(container, fg_color="transparent", height=480)
        body.pack(fill="both", expand=True, pady=(t.SPACE_2, t.SPACE_3))

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(fill="x")

        def reset():
            for child in body.winfo_children():
                child.destroy()
            for child in button_row.winfo_children():
                child.destroy()

        def render_step1():
            reset()
            progress_label.configure(text="1 / 2")

            ctk.CTkLabel(
                body,
                text="🧭 AB Compass",
                font=t.f_display(),
                text_color=t.TEXT_PRIMARY,
            ).pack(anchor="w", pady=(0, t.SPACE_1))
            ctk.CTkLabel(
                body,
                text="가상 트래픽으로 A/B 테스트 흐름을 확인하는 데스크톱 도구",
                font=t.f_body(),
                text_color=t.TEXT_SECONDARY,
            ).pack(anchor="w", pady=(0, t.SPACE_5))

            self._welcome_card(
                body,
                "이 도구에서 할 수 있는 일",
                (
                    "실험을 만들고 가상 사용자를 배정한 뒤 전환 이벤트를 생성합니다.\n\n"
                    "수집된 표본으로 전환율, p-value, 신뢰구간, SRM 결과를 확인할 수 있습니다."
                ),
            )
            self._welcome_card(
                body,
                "주요 기능",
                (
                    "• 결정적 해싱 기반 사용자 그룹 배정\n"
                    "• 가상 트래픽 시뮬레이션\n"
                    "• p-value, 신뢰구간, SRM 자동 분석\n"
                    "• AI 실험 설계 어시스턴트 (선택)"
                ),
            )
            self._welcome_card(
                body,
                "활용 예시",
                (
                    "• A/B 테스트의 배정 로직을 확인할 때\n"
                    "• 표본 수에 따른 결과 변화를 비교할 때\n"
                    "• 통계 검정 결과를 읽는 연습을 할 때"
                ),
            )

            ctk.CTkButton(
                button_row,
                text="다음 →",
                command=render_step2,
                height=44,
                fg_color=t.PRIMARY,
                hover_color=t.PRIMARY_HOVER,
                font=t.f_button(),
            ).pack(fill="x")

        def render_step2():
            reset()
            progress_label.configure(text="2 / 2")

            ctk.CTkLabel(
                body,
                text="AI 설계 설정",
                font=t.f_title(),
                text_color=t.TEXT_PRIMARY,
            ).pack(anchor="w", pady=(0, t.SPACE_1))
            ctk.CTkLabel(
                body,
                text="필요한 경우에만 설정하세요. 건너뛰어도 시뮬레이션과 분석을 사용할 수 있습니다.",
                font=t.f_caption(),
                text_color=t.TEXT_SECONDARY,
            ).pack(anchor="w", pady=(0, t.SPACE_4))

            self._welcome_card(
                body,
                "API 키 용도",
                (
                    "입력한 아이디어를 Google Gemini로 보내고, "
                    "가설과 실험 조건이 담긴 초안을 받습니다."
                ),
            )
            self._welcome_card(
                body,
                "발급 안내",
                (
                    "Google AI Studio에서 API 키를 발급받을 수 있습니다. "
                    "사용 한도와 과금 정책은 Google 안내를 확인하세요."
                ),
            )
            self._welcome_card(
                body,
                "저장 위치",
                (
                    "키는 이 PC의 data/config.json 파일에 저장됩니다. "
                    "AI 설계 요청 시 Google Gemini로 전송됩니다. "
                    "data/ 폴더는 .gitignore에 포함돼 있습니다."
                ),
            )

            ctk.CTkLabel(
                body,
                text="발급 방법: https://aistudio.google.com/apikey 접속 → Create API key",
                font=t.f_caption(),
                text_color=t.TEXT_SECONDARY,
                wraplength=520,
            ).pack(anchor="w", pady=(t.SPACE_2, t.SPACE_2))

            key_entry = self._styled_field(body, "Gemini API 키", "AIza...", show="*")
            status_label = ctk.CTkLabel(body, text="", font=t.f_caption(), text_color=t.DANGER)
            status_label.pack(anchor="w", pady=(t.SPACE_2, 0))

            def save_and_close():
                key = key_entry.get().strip()
                if not key:
                    status_label.configure(text="키를 입력하거나 '나중에 설정'을 선택하세요.")
                    return
                if not key.startswith("AIza"):
                    status_label.configure(text="Gemini 키는 보통 'AIza'로 시작합니다.")
                    return
                ai_assistant.save_api_key(key)
                ai_assistant.mark_setup_done()
                storage.seed_sample_data()
                win.destroy()
                self.refresh_experiments()
                messagebox.showinfo("설정 완료", "API 키가 저장되었습니다.")

            def skip_setup():
                ai_assistant.mark_setup_done()
                storage.seed_sample_data()
                win.destroy()
                self.refresh_experiments()

            ctk.CTkButton(
                button_row,
                text="← 이전",
                command=render_step1,
                fg_color=t.BG_ELEVATED,
                hover_color=t.BG_SUBTLE,
                text_color=t.TEXT_PRIMARY,
                height=44,
                width=80,
            ).pack(side="left", padx=(0, t.SPACE_2))
            ctk.CTkButton(
                button_row,
                text="나중에 설정",
                command=skip_setup,
                fg_color=t.BG_ELEVATED,
                hover_color=t.BG_SUBTLE,
                text_color=t.TEXT_PRIMARY,
                height=44,
            ).pack(side="left", fill="x", expand=True, padx=(0, t.SPACE_2))
            ctk.CTkButton(
                button_row,
                text="저장하고 시작",
                command=save_and_close,
                fg_color=t.PRIMARY,
                hover_color=t.PRIMARY_HOVER,
                height=44,
                font=t.f_button(),
            ).pack(side="right", fill="x", expand=True)

        render_step1()

    def _welcome_card(self, parent, title, body):
        card = ctk.CTkFrame(
            parent,
            fg_color=t.BG_SURFACE,
            corner_radius=t.RADIUS_MD,
            border_width=1,
            border_color=t.BORDER,
        )
        card.pack(fill="x", pady=(0, t.SPACE_3))
        ctk.CTkLabel(
            card,
            text=title,
            font=t.f_subsection(),
            text_color=t.TEXT_PRIMARY,
        ).pack(anchor="w", padx=t.SPACE_4, pady=(t.SPACE_4, t.SPACE_2))
        ctk.CTkLabel(
            card,
            text=body,
            font=t.f_body(),
            text_color=t.TEXT_SECONDARY,
            justify="left",
            wraplength=520,
        ).pack(anchor="w", padx=t.SPACE_4, pady=(0, t.SPACE_4))

    def on_test_assignment(self):
        # Legacy hook kept for older callbacks, if any.
        pass

    def _parse_datetime(self, value):
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def _int_value(self, value, default):
        try:
            if value == "" or value is None:
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default


if __name__ == "__main__":
    app = ABTestApp()
    app.mainloop()
