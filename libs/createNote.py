
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from libs.utils import new_icon, label_validator, trimmed

BB = QDialogButtonBox

import logging

class CreateNote(QDialog):

    def __init__(self, text="", parent=None ):
        super(CreateNote, self).__init__(parent)

        self.setWindowTitle("Add Note")
        self.resize(500,300)

        layout = QVBoxLayout()

        label = QLabel()
        label.setText("Attach a note to bounding box")
        layout.addWidget(label)

        self.edit = QTextEdit()
        self.edit.setHtml("<h1>Type Here!</h1>")
        layout.addWidget(self.edit)

        self.button_box = bb = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)
        bb.button(BB.Ok).setIcon(new_icon('done'))
        bb.button(BB.Cancel).setIcon(new_icon('undo'))
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)

        layout.addWidget(bb)
        self.setLayout(layout)

    def validate(self):
        if self.edit.toPlainText():
            self.accept()

    def post_process(self):
        pass

    def pop_up(self, text='', move=True):
        """
        Shows the dialog, setting the current text to `text`, and blocks the caller until the user has made a choice.
        If the user entered a label, that label is returned, otherwise (i.e. if the user cancelled the action)
        `None` is returned.
        """
        logging.debug(f"pop_up note with text = {text}")
        self.edit.setPlainText(text)
        self.edit.setFocus(Qt.PopupFocusReason)
        if move:
            cursor_pos = QCursor.pos()
            parent_bottom_right = self.parentWidget().geometry()
            max_x = parent_bottom_right.x() + parent_bottom_right.width() - self.sizeHint().width()
            max_y = parent_bottom_right.y() + parent_bottom_right.height() - self.sizeHint().height()
            max_global = self.parentWidget().mapToGlobal(QPoint(max_x, max_y))
            if cursor_pos.x() > max_global.x():
                cursor_pos.setX(max_global.x())
            if cursor_pos.y() > max_global.y():
                cursor_pos.setY(max_global.y())
            self.move(cursor_pos)
        return trimmed(self.edit.toPlainText()) if self.exec_() else None

