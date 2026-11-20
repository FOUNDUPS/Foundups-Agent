"""Offline HPC phone-flow check with the actual member shell and synthetic public HTTP."""
import json
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from mall_scoped_video_browser import public, provider, route_local


def run():
    origin = "https://hpc.foundups.com"
    calls = []

    def route_guest(route):
        path = urlsplit(route.request.url).path
        if route.request.url == origin + "/member/":
            html = (public / "member/index.html").read_text(encoding="utf-8")
            config = '<meta name="reddog-public-api-root" content="/api/reddog/public">'
            route.fulfill(content_type="text/html", body=html.replace("</head>", config + "</head>"))
            return
        if not path.startswith("/api/reddog/public/"):
            route_local(route)
            return
        operation = path.rsplit("/", 1)[1]
        assert route.request.url == origin + "/api/reddog/public/foundups/" + operation
        body = route.request.post_data_json
        calls.append(operation)
        session = dict(revision=0, nonce="0" * 64, remaining_turns=10,
                       expires_at=2100000600, idle_expires_at=2100000120)
        if operation == "encounter":
            assert body["consent"] is True
            result = dict(session, token="e" * 64)
        elif operation == "turn":
            assert body == {"message": "What is this?", "foundup_id": "hpc",
                            "revision": 0, "nonce": session["nonce"]}
            result = dict(session, revision=1, nonce="1" * 64, remaining_turns=9,
                          reply="Hasan Piker Coalition", disclosure="public", effect_ceiling="NONE")
        else:
            assert operation == "withdraw"
            result = {"withdrawn": True}
        route.fulfill(content_type="application/json", body=json.dumps(result))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844},
                                          is_mobile=True, has_touch=True, service_workers="block")
            context.add_init_script(provider)
            context.route("**/*", route_guest)
            page = context.new_page()
            page.set_default_timeout(8000)
            page.goto(origin + "/member/", wait_until="domcontentloaded")
            page.locator("#videoScopePhoneDock .mall-search-dog").click()
            dialog = page.get_by_role("dialog", name="Red Dog guest conversation")
            expect(dialog).to_be_visible()
            assert calls == []
            dialog.get_by_role("checkbox").check()
            dialog.get_by_role("button", name="Start guest session").click()
            focus = dialog.get_by_role("group", name="Fractal Mall focus")
            expect(focus).to_be_visible()
            expect(focus.locator("[data-reddog-fractal-path]")).to_have_text("Mall › hpc")
            ask = focus.locator("[data-reddog-fractal-ask]")
            expect(ask).to_be_visible()
            ask.click()
            question = dialog.get_by_role("textbox")
            expect(question).to_have_value("What should I know about hpc?")
            assert question.evaluate("element => document.activeElement === element") is True
            assert calls == ["encounter"], calls
            question.fill("Keep this local draft")
            ask.click()
            expect(question).to_have_value("Keep this local draft")
            assert calls == ["encounter"], calls
            question.fill("What is this?")
            dialog.get_by_role("button", name="Send", exact=True).click()
            expect(dialog.get_by_text("Hasan Piker Coalition", exact=True)).to_be_visible()
            dialog.get_by_role("button", name="End session").click()
            expect(dialog.get_by_text("Hasan Piker Coalition", exact=True)).to_have_count(0)
            expect(focus).to_be_hidden()
            assert calls == ["encounter", "turn", "withdraw"], calls
        finally:
            browser.close()


if __name__ == "__main__":
    run()
    print("HPC guest conversation passed in Chromium at 390x844 (offline fixtures).")
