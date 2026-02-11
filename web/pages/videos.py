"""
影片回放頁面

瀏覽測試錄影檔案，支援播放和下載。
"""

from pathlib import Path

from nicegui import ui

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VIDEOS_DIR = PROJECT_ROOT / "reports" / "videos"


def videos_page():
    """影片回放頁面主體"""

    videos_container = ui.column().classes("w-full")

    def refresh():
        videos_container.clear()
        with videos_container:
            _render_videos()

    with ui.row().classes("w-full items-center justify-between q-mb-md"):
        ui.label("測試錄影").classes("text-h6")
        ui.button("重新整理", icon="refresh", on_click=refresh).props("flat")

    with videos_container:
        _render_videos()


def _render_videos():
    """渲染影片列表"""
    if not VIDEOS_DIR.exists():
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    videos = sorted(VIDEOS_DIR.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not videos:
        with ui.card().classes("w-full"):
            with ui.column().classes("items-center q-pa-xl w-full"):
                ui.icon("videocam_off", size="4rem").classes("text-grey")
                ui.label("尚無錄影檔案").classes("text-h6 text-grey q-mt-md")
                ui.label("使用 video_recorder fixture 開始錄影").classes("text-caption text-grey")

                with ui.expansion("使用範例", icon="code").classes("w-full q-mt-md"):
                    ui.code("""
def test_login(self, driver, video_recorder):
    video_recorder.start()
    # ... 測試操作 ...
    video_recorder.stop_and_save("test_login")
                    """, language="python")
        return

    ui.label(f"共 {len(videos)} 個錄影檔案").classes("text-subtitle2 text-grey q-mb-md")

    # 篩選
    search = ui.input("搜尋檔名", placeholder="輸入關鍵字篩選...").classes("w-64 q-mb-md").props("outlined dense")

    cards_container = ui.row().classes("w-full gap-4")

    def filter_videos():
        cards_container.clear()
        keyword = search.value.lower()
        with cards_container:
            for video in videos:
                if keyword and keyword not in video.name.lower():
                    continue
                _render_video_card(video)

    search.on("change", filter_videos)

    # 初始渲染
    with cards_container:
        for video in videos[:20]:  # 最多顯示 20 個
            _render_video_card(video)

    if len(videos) > 20:
        ui.label(f"僅顯示最近 20 個，共 {len(videos)} 個").classes("text-caption text-grey q-mt-md")


def _render_video_card(video: Path):
    """渲染單一影片卡片"""
    stat = video.stat()
    size_mb = stat.st_size / (1024 * 1024)

    from datetime import datetime
    mtime = datetime.fromtimestamp(stat.st_mtime)

    # 從檔名解析測試名稱
    name = video.stem
    # 移除時間戳後綴 (如 test_login_1234567890)
    parts = name.rsplit("_", 1)
    test_name = parts[0] if len(parts) > 1 and parts[1].isdigit() else name

    # 判斷是否為失敗測試
    is_fail = "FAIL" in name.upper() or "fail" in name.lower()

    with ui.card().classes("w-80"):
        # 標題
        with ui.row().classes("items-center gap-2 q-mb-sm"):
            ui.icon(
                "error" if is_fail else "videocam",
                color="red" if is_fail else "primary",
            )
            ui.label(test_name).classes("text-subtitle2 font-bold ellipsis").style(
                "max-width: 250px"
            ).tooltip(name)

        # 影片播放器
        video_url = f"/videos/{video.name}"
        ui.video(video_url).classes("w-full rounded").props("controls")

        # 資訊
        ui.separator().classes("q-my-sm")
        with ui.row().classes("justify-between w-full"):
            ui.label(mtime.strftime("%Y-%m-%d %H:%M")).classes("text-caption text-grey")
            ui.label(f"{size_mb:.1f} MB").classes("text-caption text-grey")

        # 狀態標籤
        if is_fail:
            ui.badge("FAIL", color="negative").classes("q-mt-xs")
