import io
import mimetypes
import os

from flask import current_app, send_file
from flask_login import login_required

from . import itemstatic


@itemstatic.route('/img/<resource_id>/<path:path>', methods=['GET'])
@login_required
def item_img(resource_id, path):
    file_dir = os.path.join(current_app.config['STORAGE_DIR'], resource_id)
    file_dir = os.path.join(file_dir, 'itemContent/en-US')
    file_path = os.path.join(file_dir, path)
    if not os.path.exists(file_path):
        file_path = os.path.join(file_dir, 'items', resource_id, path)
    file_name = file_path.rsplit('/', 1)[1]
    content_type = mimetypes.guess_type(file_name)[0]
    with open(file_path, 'rb') as bites:
        return send_file(
            io.BytesIO(bites.read()),
            attachment_filename=file_name,
            mimetype=content_type
        )
