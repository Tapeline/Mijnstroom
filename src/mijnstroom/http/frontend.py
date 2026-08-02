from litestar.static_files import create_static_files_router

frontend_router = create_static_files_router(
    path="/",
    directories=["frontend"],
    html_mode=True,
)
