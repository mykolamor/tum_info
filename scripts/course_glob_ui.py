from PySide6.QtCore import QSize, Qt, QMimeData, QUrl
from PySide6.QtGui import QDrag, QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QLabel, QLineEdit, QCheckBox, QGridLayout, QPlainTextEdit, QFileDialog
import sys
import os
import webbrowser
import json
import course_functions
import course_glob_resources

try:
  from ctypes import windll  # Only exists on Windows.
  myappid = 'mykolamor.tum_info.grades.1'
  windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
  pass

def logger(message):
  window.log_label.appendPlainText(str(message))
  window.log_label.repaint()
  print(message)

class FileButton(QPushButton):
  def __init__(self, title=None, parent=None):
    super(FileButton, self).__init__(title, parent)

  def mouseMoveEvent(self, e):
    if e.buttons() != Qt.LeftButton:
      return
    
    mimeData = QMimeData()
    mimeData.setUrls([QUrl('file:{}'.format(self.fileName))])

    drag = QDrag(self)
    drag.setMimeData(mimeData)

    pixmap = QPixmap(self.size())
    self.render(pixmap)
    drag.setPixmap(pixmap)

    #drag.setHotSpot(e.position() - self.rect().topLeft())

    dropAction = drag.exec(Qt.CopyAction)
  
  def saveFile(self):
    dialog = QFileDialog(parent=self, caption='Save grades')
    dialog.setFileMode(QFileDialog.AnyFile)
    dialog.setNameFilter("JSON (*.json)")
    dialog.setViewMode(QFileDialog.List)
    dialog.setAcceptMode(QFileDialog.AcceptSave)
    fileNames = []
    succ = False
    while not succ:
      if dialog.exec():
        fileNames = dialog.selectedFiles()
        if len(fileNames) != 0:
          self.fileName = fileNames[0]
          succ = True


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.setWindowTitle('Download grades')
    self.setMinimumSize(QSize(400, 300))

    self.setWindowIcon(QIcon(':/assets/icons/grade.ico'))

    username_label = QLabel('Username:')
    self.username_label = username_label
    username_entry = QLineEdit()
    self.username_entry = username_entry

    password_label = QLabel('Password:')
    self.password_label = password_label
    password_entry = QLineEdit()
    password_entry.setEchoMode(QLineEdit.Password)
    self.password_entry = password_entry

    advanced_check = QCheckBox('Advanced')
    advanced_check.stateChanged.connect(self.advanced)
    self.advanced_check = advanced_check

    passshow_check = QCheckBox('Show passes')
    passshow_check.stateChanged.connect(self.advanced)
    self.passshow_check = passshow_check

    verbose_check = QCheckBox('Verbose logs')
    self.verbose_check = verbose_check

    button = QPushButton('Download')
    button.setCheckable(True)
    button.clicked.connect(self.download)
    self.button = button

    info_label = QLabel('Press download after entering login info')
    self.info_label = info_label

    log_label = QPlainTextEdit()
    log_label.setLineWrapMode(QPlainTextEdit.NoWrap)
    log_label.setReadOnly(True)
    self.log_label = log_label
    
    source_label = QLabel('<a href="https://github.com/mykolamor/tum_info/tree/main/scripts">The app is open-source and doesn\'t steal data! Click here to browse code.</a>')
    source_label.setOpenExternalLinks(True)
    self.source_label = source_label

    layout = QGridLayout()
    layout.addWidget(username_label, 0, 0)
    layout.addWidget(username_entry, 0, 1)
    layout.addWidget(password_label, 1, 0)
    layout.addWidget(password_entry, 1, 1)
    layout.addWidget(advanced_check, 2, 0)
    layout.addWidget(passshow_check, 2, 1)
    layout.addWidget(verbose_check, 3, 0)
    layout.addWidget(button, 3, 1)
    layout.addWidget(info_label, 4, 0, 1, -1)
    layout.addWidget(log_label, 5, 0, 1, -1)
    layout.addWidget(source_label, 6, 0, 1, -1)
    self.layout = layout

    container = QWidget()
    container.setLayout(layout)

    self.setCentralWidget(container)

  def advanced(self):
    if self.advanced_check.checkState() == Qt.Checked:
      self.username_label.setText('Access token:')
      self.password_label.setText('Cookie:')
      self.username_entry.setEchoMode(QLineEdit.Normal if self.passshow_check.checkState() == Qt.Checked else QLineEdit.Password)
      self.password_entry.setEchoMode(QLineEdit.Normal if self.passshow_check.checkState() == Qt.Checked else QLineEdit.Password)
    else:
      self.username_label.setText('Username:')
      self.password_label.setText('Password:')
      self.username_entry.setEchoMode(QLineEdit.Normal)
      self.password_entry.setEchoMode(QLineEdit.Normal if self.passshow_check.checkState() == Qt.Checked else QLineEdit.Password)

  def removedrag(self):
    if getattr(self, 'drag_button', None) != None:
      self.layout.removeWidget(self.drag_button)
      self.drag_button.deleteLater()
      self.drag_button = None
  
  def download(self):
    try:
      self.log_label.setPlainText('')
      self.removedrag()
      verbose = self.verbose_check.checkState() == Qt.Checked
      auth = None
      
      if self.advanced_check.checkState() == Qt.Checked:
        auth = course_functions.AuthModel(self.password_entry.text(), self.username_entry.text())
      else:
        logger('Performing login...')
        auth = course_functions.perform_login(self.username_entry.text(), self.password_entry.text(), logger, verbose)
        logger('Performing profile lookup...')
        auth = course_functions.perform_profile(auth, logger, verbose)
      
      logger('Performing achievements lookup...')
      achievements = course_functions.perform_achievements(auth, logger, verbose)
      logger('Performing grade stats lookup...')
      achievements = [y for x in achievements for y in course_functions.perform_exam(auth, x, logger, verbose)]

      drag_button = FileButton('Grades')
      drag_button.saveFile()

      with open(drag_button.fileName, 'w') as file_object:
        json.dump(achievements, file_object)
      logger('grades.json was saved to {}.'.format(drag_button.fileName))
      logger('Drag grades button into your favorite messanger.')
      logger('Or find the created grades.json file yourself.')
      logger('Email: contact@mykolamor.com')
      logger('Telegram: @mykolamor')
      logger('Facebook: mykolamor')
      logger('Matrix: @mykolamor:matrix.org')
      logger('Mastodon: @mykolamor@mastodon.social')
      logger('Website: https://mykolamor.com/#contact')
      self.info_label.setText('Drag grades into your favorite messanger')

      self.drag_button = drag_button
      self.layout.addWidget(drag_button, 4, 1, Qt.AlignRight)
    except Exception as e:
      self.info_label.setText(str(e))
      self.removedrag()

if __name__ == '__main__':
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  app.exec()
