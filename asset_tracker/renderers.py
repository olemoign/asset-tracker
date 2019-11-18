"""CSV Renderer https://docs.pylonsproject.org/projects/pyramid-cookbook/en/latest/templates/customrenderers.html"""

import csv
from io import StringIO


class CSVRenderer(object):
    def __init__(self, _info):
        pass

    def __call__(self, value, system):
        """Return a plain CSV-encoded string with content-type ``text/csv``. The content-type may be overridden by
        setting ``request.response.content_type``.
        """
        request = system.get('request')
        if request is not None:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'text/csv'

        fout = StringIO()
        writer = csv.writer(fout, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(value.get('header', []))
        writer.writerows(value.get('rows', []))

        return fout.getvalue()
