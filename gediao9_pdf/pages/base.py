import os
from abc import ABC, abstractmethod

from ..core.template import load_template, fill_template, write_html, escape_text
from ..core.pdf_ops import render_pdf


class PageGenerator(ABC):
    template_file = ""
    html_name = ""
    pdf_name = ""

    def __init__(self, templates_dir, output_dir):
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        self.html_path = os.path.join(output_dir, self.html_name)
        self.pdf_path = os.path.join(output_dir, self.pdf_name)

    def load(self):
        return load_template(os.path.join(self.templates_dir, self.template_file))

    def fill(self, fields):
        return fill_template(self.load(), fields)

    def write(self, html):
        write_html(html, self.html_path)

    def render(self, pdf_path=None):
        render_pdf(self.html_path, pdf_path or self.pdf_path)

    @abstractmethod
    def generate(self, data, prev_pdfs):
        ...

    @staticmethod
    def _resolve_image(image_dir, image_name):
        for ext in (".jpg", ".png", ".JPG", ".PNG"):
            path = os.path.normpath(os.path.join(image_dir, image_name + ext))
            if os.path.exists(path):
                return f'<img src="file:///{path.replace(os.sep, "/")}" style="width:100%;height:500px;object-fit:cover;">'
        return '<div style="display:table-cell;width:100%;height:500px;background:#f0f0f0;border:1px dashed #ccc;vertical-align:middle;text-align:center;color:#999;">[图片位置预留]</div>'

    @staticmethod
    def _resolve_image_small(image_dir, image_name):
        for ext in (".jpg", ".png", ".JPG", ".PNG"):
            path = os.path.normpath(os.path.join(image_dir, image_name + ext))
            if os.path.exists(path):
                return f'<img src="file:///{path.replace(os.sep, "/")}" style="width:100%;height:200px;object-fit:cover;">'
        return '<div style="display:table-cell;width:100%;height:200px;background:#f0f0f0;border:1px dashed #ccc;vertical-align:middle;text-align:center;color:#999;">[图片位置预留]</div>'