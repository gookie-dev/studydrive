import asyncio
import os

import reflex as rx
from rxconfig import config
from fastapi import Response
from fastapi.responses import FileResponse
from studydrive_downloader import StudydriveDownloader

# Constants
NOT_CACHED = "Not cached"

# Studydrive downloader
sd_downloader = StudydriveDownloader()


# State classes
class StatsState(rx.State):
    @rx.var
    def download_counter(self) -> str:
        return sd_downloader.counter()


class IndexState(rx.State):
    url: str
    empty_url: bool = False
    invalid_url: bool = False

    def update_url(self, url: str):
        self.url = url
        self.empty_url = False
        self.invalid_url = False

    def redirect(self):
        if not self.url or self.url == "":
            self.empty_url = True
            return

        if not sd_downloader.validate_url(self.url):
            self.invalid_url = True
            return

        return rx.redirect(sd_downloader.get_url_path(self.url))


class DocumentState(rx.State):
    preview: bool = None
    file: bool = None
    uid: str = ""
    document: str = ""
    course: str = ""
    user: str = ""
    description: str = ""
    upload_daytime: str = ""
    type: str = ""
    pages: str = ""
    cached: str = NOT_CACHED
    oops: bool = False
    link: str = ""
    file_name: str = ""

    @rx.var
    def slug(self) -> str:
        return self.router.page.params.get("slug")

    @rx.var
    def id(self) -> int:
        return int(self.router.page.params.get("id"))

    def download(self):
        sd_downloader.increment_counter()
        return rx.download(url=f"/download/{self.link}/{self.file_name}")

    @rx.background
    async def fetch_files(self):
        async with self:
            while self.cached == NOT_CACHED:
                try:
                    self.cached = sd_downloader.check_cached(self.uid)
                    preview = sd_downloader.check_preview(self.uid)
                    if preview is not None:
                        self.preview = preview
                    file = sd_downloader.check_file(self.uid)
                    if file is not None:
                        self.file = file
                    await asyncio.sleep(0.5)
                    return DocumentState.fetch_files
                except Exception as e:
                    print(f"Failed to fetch files for document {self.id}: {e}")
                    self.oops = True

    @rx.background
    async def fetch_stats(self):
        async with self:
            try:
                self.uid, self.document, self.course, self.user, self.description, self.upload_daytime, self.pages, self.type, preview, file, self.cached, self.link, self.file_name = await sd_downloader.load(self.slug, self.id)
                if self.cached == NOT_CACHED:
                    if preview is not None:
                        self.preview = preview
                    if file is not None:
                        self.file = file
                    return DocumentState.fetch_files
            except Exception as e:
                print(f"Failed to fetch stats for document {self.id}: {e}")
                self.oops = True

    def on_load(self):
        if self.uid != self.id:
            self.reset()
        return DocumentState.fetch_stats


# Metadata
def get_metadata():
    return {
        "title": "Studydrive Downloader",
        "description": "Download from Studydrive for free.",
        "image": "/icon.png",
        "meta": [
            {"property": "og:title", "content": "Studydrive Downloader"},
            {"property": "og:description", "content": "Download from Studydrive for free."},
            {"property": "og:type", "content": "article"},
            {"property": "og:image", "content": "/icon.png"},
            {"property": "og:image:type", "content": "image/png"},
            {"property": "og:site", "content": "studydrive.gookie.dev"},
            {"property": "theme-color", "content": "#3E63DD"}
        ]
    }


# Routes
@rx.page(
    route="/",
    **get_metadata()
)
def index() -> rx.Component:
    return rx.flex(
        github_icon(),
        rx.center(
            rx.vstack(
                heading(),
                rx.hstack(
                    rx.box(
                        rx.input(placeholder=sd_downloader.placeholder_url, on_change=IndexState.update_url, size="3"),
                        flex_grow=1),
                    rx.box(rx.button(rx.icon("file-down"), "Download", on_click=IndexState.redirect, size="3")),
                    spacing="6",
                    width="100%"
                ),
                rx.cond(
                    IndexState.empty_url,
                    rx.callout("The URL can't be empty", icon="triangle_alert", width="100%", color_scheme="red")
                ),
                rx.cond(
                    IndexState.invalid_url,
                    rx.callout("That's an invalid URL", icon="triangle_alert", width="100%", color_scheme="red")
                ),
                margin="2rem",
                margin_top="8%"
            )
        ),
        direction="column"
    )


@rx.page(
    route="/document/[slug]/[id]",
    on_load=DocumentState.on_load,
    **get_metadata()
)
def document() -> rx.Component:
    return rx.flex(
        github_icon(),
        rx.center(
            rx.vstack(
                heading(),
                rx.cond(
                    DocumentState.oops,
                    rx.callout("Oops, something went wrong", icon="triangle_alert", width="100%", color_scheme="red"),
                    rx.card(
                        rx.text(DocumentState.document, size="5", padding_bottom="0.5rem"),
                        rx.divider(),
                        stat(DocumentState.course, "graduation-cap", 1.1, 1.1),
                        stat(DocumentState.user, "user", 1.1),
                        stat(DocumentState.description, "info", 1.1),
                        stat(DocumentState.upload_daytime, "calendar", 1.1),
                        stat(DocumentState.type, "book-type", 1.1),
                        stat(DocumentState.pages, "file", 1.1),
                        stat(DocumentState.uid, "hash"),
                        rx.hstack(
                            rx.icon("database-zap", flex_shrink=0, size=20),
                            rx.text(DocumentState.cached, size="2"),
                            rx.box(flex_grow=1),
                            rx.flex(
                                rx.cond(
                                    DocumentState.cached == NOT_CACHED,
                                    rx.chakra.button("Loading...", is_loading=True, loading_text="Please wait", spinner_placement="start"),
                                    rx.box(rx.button(rx.icon("file-down"), "Download", on_click=DocumentState.download, size="3"))
                                ),
                                justify_content="end"
                            ),
                            align_items="end",
                            padding_top="0rem"
                        ),
                        width="100%",
                        max_width="100%",
                        padding="1rem"
                    ),
                ),
                rx.flex(height="0.5rem"),
                rx.cond(
                    DocumentState.preview,
                    rx.card(
                        rx.image(src=f"/download/preview/{DocumentState.id}",
                                 width="100%",
                                 background="#FFF"
                                 ),
                        padding="0",
                        width="100%"
                    )
                ),
                margin="2rem",
                margin_top="8%",
                max_width="46rem"
            )
        ),
        direction="column"
    )


# API route
async def download_endpoint(download_id: str, file_name: str) -> Response:
    file = sd_downloader.get_file(download_id)
    if file:
        return FileResponse(path=f"./cache/{file}.pdf", filename=file_name)
    return Response(content="Download not found or expired.", status_code=404)


async def download_preview_endpoint(file_name: str) -> Response:
    file_path = f"./assets/preview/{file_name}.png"
    if os.path.isfile(file_path):
        return FileResponse(path=file_path, filename=f"{file_name}.png")
    else:
        return Response(content="File not found.", status_code=404)


# Components
def github_icon() -> rx.flex:
    return rx.flex(
        rx.link(
            rx.icon("github", size=40, color="#3e63dd"),
            href=f"https://github.com/gookie-dev/{config.app_name}",
            is_external=True
        ),
        justify_content="end",
        width="100%",
        position="fixed",
        padding="2rem"
    )


def heading():
    return (
        rx.heading("Free Studydrive Downloader", size="9", margin_right="1rem", on_click=rx.redirect("/")),
        rx.text(f"Studydrive downloader for offline access with a total of {StatsState.download_counter} downloads.", size="5",
                font_size=["1rem", "1.2rem"]),
        rx.flex(height="0.3rem")
    )


def stat(text, icon: str, bottom: float = 0, top: float = 0) -> rx.hstack:
    return rx.cond(
        (text != ""),
        rx.hstack(
            rx.icon(icon, flex_shrink=0, size=20),
            rx.text(text, size="2"),
            padding_bottom=f"{bottom}rem",
            padding_top=f"{top}rem"
        )
    )


# App setup
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        has_background=False,
        radius="medium",
        accent_color="indigo",
    ),
    stylesheets=["/styles.css"]
)
app.api.add_api_route("/preview/{file_name}", download_preview_endpoint)
app.api.add_api_route("/{download_id}/{file_name}", download_endpoint)