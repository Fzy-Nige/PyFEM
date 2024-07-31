import sys
import subprocess
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QFileDialog, QVBoxLayout, QWidget, QToolBar, QMessageBox, QStyle
from PySide6.QtCore import QProcess, Qt, QThread, Signal, QObject
from PySide6.QtGui import QIcon, QAction, QKeySequence

from pyfem.io.InputReader   import InputRead
from pyfem.io.OutputManager import OutputManager
from pyfem.solvers.Solver   import Solver

class EmittingStream(QObject):
    text_written = Signal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass 
        
# Worker thread class
class WorkerThread(QThread):
    output_signal = Signal(str)

    def __init__(self, input_file):
        super().__init__()
        self.input_file = input_file

    def run(self):

        #sys.stdout = EmittingStream(text_written=self.output_signal.emit)
        #sys.stderr = EmittingStream(text_written=self.output_signal.emit)
        
        self.props,self.globdat = InputRead( self.input_file )
        
        self.solver = Solver        ( self.props , self.globdat )
        self.output = OutputManager ( self.props , self.globdat )

        while self.globdat.active:
            self.solver.run( self.props , self.globdat )
            self.output.run( self.props , self.globdat )

        self.globdat.close()        

        #sys.stdout = sys.__stdout__
        #sys.stderr = sys.__stderr__
                
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Python Script Executor")
        
        self.create_menu()
        self.create_toolbar()

        self.layout = QVBoxLayout()

        self.output_terminal = QTextEdit()
        self.output_terminal.setReadOnly(True)
        self.output_terminal.setStyleSheet("background-color: black; color: white; font-family: 'Courier New', monospace;")
        self.layout.addWidget(self.output_terminal)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.input_file = None
        #self.process = QProcess(self)
        #self.process.readyReadStandardOutput.connect(self.update_output)
        #self.process.readyReadStandardError.connect(self.update_output)
        
        self.emitting_stream = EmittingStream()
        self.emitting_stream.text_written.connect(self.handle_output)
        sys.stdout = self.emitting_stream
        sys.stderr = self.emitting_stream        

    def create_menu(self):
        menu_bar = self.menuBar()
        
        file_menu  = menu_bar.addMenu("File")
        edit_menu  = menu_bar.addMenu("Edit")
        run_menu   = menu_bar.addMenu("Run")
        about_menu = menu_bar.addMenu("About")

        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), 'New', self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))        
        new_action.triggered.connect(self.load_file)
        file_menu.addAction(new_action)

        open_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), 'Open', self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))        
        open_action.triggered.connect(self.load_file)
        file_menu.addAction(open_action)

        save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), 'Save', self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))        
        save_action.triggered.connect(self.load_file)
        file_menu.addAction(save_action)
        
        exit_action = QAction(QIcon.fromTheme("application-exit"), "Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        execute_action = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Execute", self)
        execute_action.setShortcut(QKeySequence("Ctrl+R"))  
        execute_action.triggered.connect(self.execute_script)
        run_menu.addAction(execute_action)

        abort_action = QAction(self.style().standardIcon(QStyle.SP_BrowserStop), "Abort", self)
        abort_action.setShortcut(QKeySequence("Ctrl+C"))          
        abort_action.triggered.connect(self.execute_script)
        run_menu.addAction(abort_action)
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), 'New', self)        
        new_action.triggered.connect(self.load_file)
        toolbar.addAction(new_action)

        open_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), 'Open', self)        
        open_action.triggered.connect(self.load_file)
        toolbar.addAction(open_action)

        save_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save_action.triggered.connect(self.execute_script)
        toolbar.addAction(save_action)        

        execute_action = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Execute", self)        
        execute_action.triggered.connect(self.execute_script)
        toolbar.addAction(execute_action)

        abort_action = QAction(self.style().standardIcon(QStyle.SP_BrowserStop), "Abort", self)
        abort_action.triggered.connect(self.execute_script)
        toolbar.addAction(abort_action)

    def load_file(self):
        file_dialog = QFileDialog()
        self.input_file, _ = file_dialog.getOpenFileName(self, 
            caption = "Open Input File", 
            dir     = "examples", 
            filter  = "PyFEM Input Files (*.pro);;All Files (*.*)")
        if self.input_file:
            self.output_terminal.append(f"Loaded file: {self.input_file}")

    def execute_script(self):
        if not self.input_file:
            self.output_terminal.append("Please load an input file first.")
            return

        #self.output_terminal.append("Executing script...")
        #self.process.start("python", ["PyFEM.py", self.input_file])
        
        self.worker = WorkerThread(self.input_file)
        self.worker.output_signal.connect(self.handle_output)
        self.worker.start()   
        
    def handle_output(self, text):
        self.output_terminal.append( text.rstrip() )
        #self.output_terminal.append(result)             

    def update_output(self):
        output = self.process.readAllStandardOutput().data().decode()
        error = self.process.readAllStandardError().data().decode()
        self.output_terminal.append(output)
        #self.output_terminal.append(error)        
        #if error:
        #    self.output_terminal.append(f"Error: {error}")

    def show_about(self):
        QMessageBox.about(self, "About", "Python Script Executor\n\nDeveloped with PySide6.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())

