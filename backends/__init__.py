import base64, io


def qr_data_url(text):
    import qrcode
    img = qrcode.QRCode(border=1, box_size=8)
    img.add_data(text)
    img.make(fit=True)
    buf = io.BytesIO()
    img.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# Backend interface (MockBackend and WPPBackend both implement it):
#   status()                       -> {"state": starting|qr|authenticated|ready|error, "qr": dataurl?, "me": {name, pic}?, "error": str?}
#   list_chats()                   -> [{"id", "name"}]
#   list_photos(chat_id, start_ms, end_ms) -> [{"id", "ts"(seconds), "sender", "ext"}]
#   fetch_photo(chat_id, meta)     -> bytes
#   logout(), shutdown()
