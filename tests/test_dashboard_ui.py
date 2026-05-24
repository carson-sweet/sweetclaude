"""
Dashboard UI regression tests — Playwright-based structural and functional assertions.

Protects:
  - Detail panel is a flex sidebar, not a fixed overlay
  - Resize handle exists and works
  - Accordions use native <details>/<summary>, expanded by default
  - Eyebrow layout: type + ID + status/source/priority badges
  - Date fields include times and timezone
  - Completion time shown for done items
  - Drag handles present on roadmap story rows and detail panel issue rows
  - SortableJS loaded and initialized on drag containers
  - Close button and Escape key dismiss sidebar
"""
import http.server
import os
import subprocess
import sys
import threading
import time

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_PORT = 18411


@pytest.fixture(scope="module")
def dashboard_server():
    cache_script = os.path.join(SCRIPTS_DIR, "cache.py")
    subprocess.run(
        [sys.executable, cache_script, "--project-dir", PROJECT_DIR, "--rebuild"],
        capture_output=True,
    )

    from dashboard import DashboardHandler, build_api_data

    DashboardHandler.project_dir = PROJECT_DIR

    server = http.server.HTTPServer(("127.0.0.1", TEST_PORT), DashboardHandler)
    server.allow_reuse_address = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    for _ in range(20):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/api/data", timeout=1)
            break
        except Exception:
            time.sleep(0.25)

    yield f"http://127.0.0.1:{TEST_PORT}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser_page(dashboard_server):
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(dashboard_server)
    page.wait_for_function("window.DATA !== null", timeout=10000)
    yield page
    browser.close()
    pw.stop()


# ---------------------------------------------------------------------------
# Structural: app layout is flex, not overlay
# ---------------------------------------------------------------------------

class TestLayoutStructure:
    def test_app_layout_is_flex(self, browser_page):
        display = browser_page.locator(".app-layout").evaluate(
            "el => getComputedStyle(el).display"
        )
        assert display == "flex"

    def test_detail_panel_not_fixed_position(self, browser_page):
        position = browser_page.locator("#detail-overlay").evaluate(
            "el => getComputedStyle(el).position"
        )
        assert position != "fixed", "Detail panel must be a sidebar, not a fixed overlay"

    def test_detail_panel_is_relative(self, browser_page):
        position = browser_page.locator("#detail-overlay").evaluate(
            "el => getComputedStyle(el).position"
        )
        assert position == "relative"

    def test_resize_handle_exists(self, browser_page):
        assert browser_page.locator("#detail-resize-handle").count() == 1

    def test_resize_handle_cursor_is_col_resize(self, browser_page):
        cursor = browser_page.locator("#detail-resize-handle").evaluate(
            "el => getComputedStyle(el).cursor"
        )
        assert cursor == "col-resize"

    def test_body_is_flex_column(self, browser_page):
        display = browser_page.evaluate("getComputedStyle(document.body).display")
        direction = browser_page.evaluate(
            "getComputedStyle(document.body).flexDirection"
        )
        assert display == "flex"
        assert direction == "column"


# ---------------------------------------------------------------------------
# Structural: detail panel content contract
# ---------------------------------------------------------------------------

class TestDetailPanelStructure:
    @pytest.fixture(autouse=True)
    def open_epic_detail(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        yield
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)

    def test_eyebrow_exists(self, browser_page):
        eyebrow = browser_page.locator("#detail-eyebrow")
        assert eyebrow.count() == 1
        text = eyebrow.inner_text()
        assert "EP-" in text or "ISSUE-" in text or "MS-" in text

    def test_eyebrow_contains_status_badge(self, browser_page):
        badges = browser_page.locator("#detail-eyebrow .status-badge")
        assert badges.count() >= 1

    def test_eyebrow_contains_source_badge(self, browser_page):
        badges = browser_page.locator("#detail-eyebrow .source-badge")
        assert badges.count() >= 1

    def test_title_exists(self, browser_page):
        title = browser_page.locator("#detail-title")
        assert title.count() == 1
        assert len(title.inner_text().strip()) > 0

    def test_accordions_use_native_details(self, browser_page):
        sections = browser_page.locator("#detail-body details.detail-section")
        assert sections.count() >= 2, "Expected at least 2 accordion sections"

    def test_accordions_use_summary(self, browser_page):
        summaries = browser_page.locator(
            "#detail-body details.detail-section > summary"
        )
        assert summaries.count() >= 2

    def test_accordions_expanded_by_default(self, browser_page):
        sections = browser_page.locator("#detail-body details.detail-section")
        count = sections.count()
        for i in range(count):
            assert sections.nth(i).get_attribute("open") is not None, (
                f"Accordion section {i} should be expanded by default"
            )

    def test_details_section_has_dates(self, browser_page):
        details_section = browser_page.locator(
            "details.detail-section:has(summary:text('Details'))"
        )
        assert details_section.count() == 1
        text = details_section.inner_text()
        assert "CREATED" in text.upper()
        assert "UPDATED" in text.upper()

    def test_dates_include_timezone(self, browser_page):
        details_section = browser_page.locator(
            "details.detail-section:has(summary:text('Details'))"
        )
        text = details_section.inner_text()
        assert "UTC" in text, "Date fields must include timezone"


# ---------------------------------------------------------------------------
# Structural: done items show completion time
# ---------------------------------------------------------------------------

class TestCompletionTime:
    @pytest.fixture(autouse=True)
    def open_done_epic(self, browser_page):
        browser_page.locator(".epic-node:has(.status-badge:text('done'))").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        yield
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)

    def test_completion_time_shown(self, browser_page):
        details_section = browser_page.locator(
            "details.detail-section:has(summary:text('Details'))"
        )
        text = details_section.inner_text()
        assert "COMPLETION TIME" in text.upper(), (
            "Done items must show completion time"
        )


# ---------------------------------------------------------------------------
# Structural: drag handles
# ---------------------------------------------------------------------------

class TestDragHandles:
    def test_roadmap_stories_have_drag_handles(self, browser_page):
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(200)
        toggles = browser_page.locator("#panel-roadmap .story-toggle")
        if toggles.count() > 0:
            toggles.first.click()
            browser_page.wait_for_timeout(300)
            handles = browser_page.locator(
                "#panel-roadmap .dnd-stories .story-row .drag-handle"
            )
            assert handles.count() > 0, "Roadmap story rows must have drag handles"

    def test_detail_panel_issues_have_drag_handles(self, browser_page):
        active_epic = browser_page.locator(
            "#panel-roadmap .epic-node:has(.status-badge:text('active'))"
        )
        if active_epic.count() == 0:
            pytest.skip("No active epic with open issues to test")
        active_epic.first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        handles = browser_page.locator("#detail-stories .drag-handle")
        if browser_page.locator("#detail-stories").count() > 0:
            assert handles.count() > 0, (
                "Detail panel issue rows must have drag handles"
            )
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)

    def test_dnd_stories_containers_have_epic_data_attr(self, browser_page):
        containers = browser_page.locator("#panel-roadmap .dnd-stories")
        count = containers.count()
        for i in range(count):
            epic_id = containers.nth(i).get_attribute("data-epic")
            assert epic_id and epic_id.startswith("EP-"), (
                f"dnd-stories container {i} must have data-epic attribute"
            )


# ---------------------------------------------------------------------------
# Structural: SortableJS loaded
# ---------------------------------------------------------------------------

class TestSortableJS:
    def test_sortablejs_script_tag_exists(self, browser_page):
        scripts = browser_page.locator("script[src*='sortablejs']")
        assert scripts.count() == 1

    def test_sortable_global_available(self, browser_page):
        result = browser_page.evaluate("typeof Sortable")
        assert result == "function", "SortableJS must be loaded as global"


# ---------------------------------------------------------------------------
# Functional: sidebar open/close
# ---------------------------------------------------------------------------

class TestSidebarInteraction:
    def test_clicking_epic_opens_sidebar(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        display = browser_page.locator("#detail-overlay").evaluate(
            "el => getComputedStyle(el).display"
        )
        assert display == "flex"

    def test_close_button_dismisses_sidebar(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        browser_page.locator(".detail-close").click()
        browser_page.wait_for_timeout(300)
        classes = browser_page.locator("#detail-overlay").get_attribute("class")
        assert "open" not in classes

    def test_escape_key_dismisses_sidebar(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)
        classes = browser_page.locator("#detail-overlay").get_attribute("class")
        assert "open" not in classes

    def test_sidebar_pushes_content_not_overlaps(self, browser_page):
        main_width_before = browser_page.locator(".main").evaluate(
            "el => el.getBoundingClientRect().width"
        )
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        main_width_after = browser_page.locator(".main").evaluate(
            "el => el.getBoundingClientRect().width"
        )
        assert main_width_after < main_width_before, (
            "Opening sidebar must shrink main content area (flex), not overlap it"
        )
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)


# ---------------------------------------------------------------------------
# Functional: accordion toggle
# ---------------------------------------------------------------------------

class TestAccordionToggle:
    @pytest.fixture(autouse=True)
    def open_detail(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        yield
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)

    def test_clicking_summary_collapses_section(self, browser_page):
        section = browser_page.locator(
            "#detail-body details.detail-section"
        ).first
        summary = section.locator("> summary")
        assert section.get_attribute("open") is not None
        summary.click()
        browser_page.wait_for_timeout(200)
        assert section.get_attribute("open") is None, (
            "Clicking summary should collapse the accordion"
        )
        summary.click()
        browser_page.wait_for_timeout(200)
        assert section.get_attribute("open") is not None, (
            "Clicking summary again should re-expand the accordion"
        )


# ---------------------------------------------------------------------------
# Functional: resize handle
# ---------------------------------------------------------------------------

class TestResizeHandle:
    def test_resize_changes_panel_width(self, browser_page):
        browser_page.locator("#panel-roadmap .epic-node").first.click()
        browser_page.locator("#detail-overlay.open").wait_for(timeout=3000)
        panel = browser_page.locator("#detail-overlay")
        handle = browser_page.locator("#detail-resize-handle")
        width_before = panel.evaluate("el => el.getBoundingClientRect().width")
        box = handle.bounding_box()
        browser_page.mouse.move(box["x"] + 2, box["y"] + box["height"] / 2)
        browser_page.mouse.down()
        browser_page.mouse.move(box["x"] - 100, box["y"] + box["height"] / 2)
        browser_page.mouse.up()
        width_after = panel.evaluate("el => el.getBoundingClientRect().width")
        assert width_after > width_before, (
            "Dragging resize handle left must widen the panel"
        )
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(300)


# ---------------------------------------------------------------------------
# Functional: backlog drag handles
# ---------------------------------------------------------------------------

class TestBacklogDragHandles:
    def test_backlog_rows_have_drag_handles(self, browser_page):
        browser_page.locator("text=Backlog").first.click()
        browser_page.wait_for_timeout(500)
        handles = browser_page.locator(
            "#panel-backlog .dnd-container .backlog-row .drag-handle"
        )
        assert handles.count() > 0, "Backlog rows must have drag handles"

    def test_backlog_dnd_containers_exist(self, browser_page):
        browser_page.locator("text=Backlog").first.click()
        browser_page.wait_for_timeout(500)
        containers = browser_page.locator("#panel-backlog .dnd-container")
        assert containers.count() > 0, "Backlog must have dnd-container elements"


# ---------------------------------------------------------------------------
# Structural: source badge rendering
# ---------------------------------------------------------------------------

class TestSourceBadge:
    def test_roadmap_epics_show_source_badge(self, browser_page):
        browser_page.locator("text=Roadmap").first.click()
        browser_page.wait_for_timeout(500)
        badges = browser_page.locator("#panel-roadmap .source-badge")
        assert badges.count() > 0, "Roadmap epics must show source badges"

    def test_source_badge_values_are_auto_or_manual(self, browser_page):
        browser_page.locator("text=Roadmap").first.click()
        browser_page.wait_for_timeout(500)
        badges = browser_page.locator("#panel-roadmap .source-badge")
        count = badges.count()
        for i in range(count):
            text = badges.nth(i).inner_text().strip()
            assert text in ("auto", "manual"), (
                f"Source badge must be 'auto' or 'manual', got '{text}'"
            )
