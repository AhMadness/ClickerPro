from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QMessageBox, QRadioButton, QShortcut, QProgressBar)
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QKeySequence
import sys
import pyautogui
from pynput.mouse import Listener as MouseListener
import threading
import time


class AutomationThread(QThread):
    update_progress = pyqtSignal(int)
    update_loop_indicator = pyqtSignal(int, int)  # New signal for loop indicator
    automation_completed = pyqtSignal()

    def __init__(self, positions, num_loops):
        super().__init__()
        self.positions = positions
        self.num_loops = num_loops
        self.paused = False
        self.running = True
        self.current_loop = 0  # Initialize current_loop


    def run(self):
        try:
            for self.current_loop in range(1, self.num_loops + 1):
                for position, interval, click_type in self.positions:
                    while self.paused or not self.running:
                        if not self.running:
                            return
                        QThread.msleep(100)

                    if click_type == 'single':
                        pyautogui.click(position)
                    elif click_type == 'double':
                        pyautogui.doubleClick(position)
                    elif click_type == 'right':
                        pyautogui.rightClick(position)
                    elif click_type is None:
                        pyautogui.moveTo(position)

                    QThread.msleep(int(interval * 1000))
                    if not self.running:
                        return

                # Use self.current_loop here
                self.update_progress.emit(int(self.current_loop / self.num_loops * 100))
                self.update_loop_indicator.emit(self.current_loop, self.num_loops)

            self.automation_completed.emit()

        except Exception as e:
            print(f"Error during automation: {e}")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        # No change to paused state
        while self.isRunning():
            QThread.msleep(100)

class ClickAutomationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.paused = False  # Initialize paused attribute

        self.positions = []  # List to hold positions and intervals
        self.num_loops = 0
        self.running = False
        self.automation_thread = None

        self.estimated_time_timer = QTimer(self)
        self.estimated_time_timer.timeout.connect(self.updateEstimatedTime)
        self.estimated_time_seconds = 0

    def initUI(self):
        # Main layout
        self.layout = QVBoxLayout()  # Store layout as an attribute
        layout = QVBoxLayout()

        self.setFixedWidth(400)

        # Row for position input
        self.position_input = QLineEdit(self)
        self.get_position_button = QPushButton('Get Position', self)
        self.get_position_button.clicked.connect(self.getPosition)

        position_layout = QHBoxLayout()
        position_layout.addWidget(self.position_input)
        position_layout.addWidget(self.get_position_button)

        # Row for interval input
        self.interval_input = QLineEdit(self)
        self.interval_label = QLabel('Interval')
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(self.interval_label)
        interval_layout.addWidget(self.interval_input)

        # Row for number of loops input
        self.num_loops_input = QLineEdit(self)
        self.loops_label = QLabel('Number of loops')
        loops_layout = QHBoxLayout()
        loops_layout.addWidget(self.loops_label)
        loops_layout.addWidget(self.num_loops_input)

        # Add More and Start buttons
        self.add_more_button = QPushButton('Add', self)
        self.add_more_button.clicked.connect(self.addMore)
        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.startAutomation)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_more_button)
        buttons_layout.addWidget(self.start_button)

        # List to display positions
        self.positions_list = QListWidget(self)

        # Click type selection
        self.no_action_radio = QRadioButton("None")
        self.single_click_radio = QRadioButton("Single Click")
        self.double_click_radio = QRadioButton("Double Click")
        self.right_click_radio = QRadioButton("Right Click")
        self.no_action_radio.setChecked(True)  # Set "None" as the default selected option

        click_type_layout = QHBoxLayout()
        click_type_layout.addWidget(self.single_click_radio)
        click_type_layout.addWidget(self.double_click_radio)
        click_type_layout.addWidget(self.right_click_radio)
        click_type_layout.addWidget(self.no_action_radio)  # Add the "None" radio button to the layout

        # Add all rows to main layout
        layout.addLayout(position_layout)
        layout.addLayout(interval_layout)
        layout.addLayout(loops_layout)
        layout.addLayout(click_type_layout)
        layout.addWidget(self.positions_list)
        layout.addLayout(buttons_layout)

        self.control_buttons_layout = QHBoxLayout()  # New horizontal layout for control buttons

        self.pause_resume_button = QPushButton('Pause', self)
        self.pause_resume_button.clicked.connect(self.togglePauseResume)
        self.pause_resume_button.hide()
        self.control_buttons_layout.addWidget(self.pause_resume_button)

        self.stop_button = QPushButton('Stop', self)  # New stop button
        self.stop_button.clicked.connect(self.stopAutomation)
        self.stop_button.hide()
        self.control_buttons_layout.addWidget(self.stop_button)

        layout.addLayout(self.control_buttons_layout)

        # Loop indicator and Estimated Time layout11
        status_layout = QHBoxLayout()
        self.loop_indicator_label = QLabel('Loop: 0/0', self)
        self.loop_indicator_label.setAlignment(Qt.AlignLeft)
        self.loop_indicator_label.hide()

        self.estimated_time_label = QLabel('Estimated Time: 00:00:00', self)
        self.estimated_time_label.setAlignment(Qt.AlignRight)
        self.estimated_time_label.hide()

        status_layout.addWidget(self.loop_indicator_label)
        status_layout.addStretch()  # This will push the labels to the opposite ends
        status_layout.addWidget(self.estimated_time_label)

        # Add status_layout above the progress bar
        layout.addLayout(status_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)  # Hide the text
        self.progress_bar.hide()  # Hide initially
        layout.addWidget(self.progress_bar)

        # Create Edit and Remove buttons but hide them initially
        self.edit_button = QPushButton('Edit', self)
        self.edit_button.clicked.connect(self.editCommand)
        self.edit_button.hide()

        self.remove_button = QPushButton('Remove', self)
        self.remove_button.clicked.connect(self.removeCommand)
        self.remove_button.hide()

        self.back_button = QPushButton('Back', self)
        self.back_button.clicked.connect(self.onBackClicked)
        self.back_button.hide()

        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.back_button)

        # Setting up keyboard shortcut for pause/resume
        self.pause_resume_shortcut = QShortcut(QKeySequence('P'), self)
        self.pause_resume_shortcut.activated.connect(self.togglePauseResume)

        # Reset button
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.resetList)

        # Add the reset button to the buttons layout
        buttons_layout.addWidget(self.reset_button)

        self.setLayout(layout)
        self.setWindowTitle('Clicker')

        # Connect item clicked signal
        self.positions_list.itemClicked.connect(self.onCommandSelected)
        self.positions_list.itemSelectionChanged.connect(self.onSelectionChanged)

    @pyqtSlot()
    def getPosition(self):
        # Only show the message box if the list of positions is empty
        if not self.positions:
            QMessageBox.information(self, 'Get Position',
                                    'Move your cursor to the desired position. The position will be captured in 5 seconds.')
        threading.Thread(target=self.delayedGetPosition).start()

    def delayedGetPosition(self):
        time.sleep(5)
        x, y = pyautogui.position()
        self.position_input.setText(f'{x}, {y}')

    @pyqtSlot()
    def addMore(self):
        try:
            position = tuple(map(int, self.position_input.text().split(',')))
            interval = float(self.interval_input.text())
            click_type = None  # Default to None (no action)
            if self.single_click_radio.isChecked():
                click_type = 'single'
            elif self.double_click_radio.isChecked():
                click_type = 'double'
            elif self.right_click_radio.isChecked():
                click_type = 'right'
            if not self.num_loops:
                self.num_loops = int(self.num_loops_input.text())
                self.num_loops_input.setDisabled(True)
            self.positions.append((position, interval, click_type))
            self.positions_list.addItem(f'Position: {position}, Interval: {interval}s, Click: {click_type}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Invalid input: {e}')

    def setNonAutomationUIEnabled(self, enabled=True):
        # Enable or disable all components except pause/resume button and progress bar
        self.position_input.setEnabled(enabled)
        self.get_position_button.setEnabled(enabled)
        self.interval_input.setEnabled(enabled)
        self.num_loops_input.setEnabled(enabled)
        self.add_more_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.positions_list.setEnabled(enabled)
        self.single_click_radio.setEnabled(enabled)
        self.double_click_radio.setEnabled(enabled)
        self.right_click_radio.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)

    @pyqtSlot()
    def startAutomation(self):
        if self.running:
            QMessageBox.information(self, 'Already running', 'Automation is already running.')
            return
        elif not self.positions:
            QMessageBox.warning(self, 'No positions', 'Please add at least one position before starting.')
            return

        # Update num_loops based on the input field value
        self.num_loops = int(self.num_loops_input.text())

        self.running = True
        self.automation_thread = AutomationThread(self.positions, self.num_loops)
        self.automation_thread.update_loop_indicator.connect(self.updateLoopIndicator)
        self.automation_thread.update_progress.connect(self.updateProgressBar)
        self.automation_thread.automation_completed.connect(self.autoClearList)

        self.automation_thread.start()
        self.pause_resume_button.show()
        self.stop_button.show()
        self.progress_bar.show()
        self.loop_indicator_label.setText(f'Loop: 0/{self.num_loops}')  # Initialize loop indicator
        self.loop_indicator_label.show()  # Show loop indicator
        self.setNonAutomationUIEnabled(False)

        # Hide the elements that are not needed during processing
        self.position_input.hide()
        self.get_position_button.hide()
        self.interval_input.hide()
        self.num_loops_input.hide()
        self.add_more_button.hide()
        self.start_button.hide()
        self.reset_button.hide()
        self.single_click_radio.hide()
        self.double_click_radio.hide()
        self.right_click_radio.hide()
        self.no_action_radio.hide()
        self.interval_label.hide()
        self.loops_label.hide()
        self.edit_button.hide()
        self.remove_button.hide()
        self.back_button.hide()

        # Initialize the estimated time and start the timer
        self.estimated_time_seconds = sum(interval for _, interval, _ in self.positions) * self.num_loops
        self.displayEstimatedTime(self.estimated_time_seconds)  # Display the initial estimated time
        self.estimated_time_label.show()  # Show the estimated time label
        self.estimated_time_timer.start(1000)  # Update every second

        # Start the mouse movement listener
        self.startMouseListener()

    def runAutomation(self):
        total_steps = self.num_loops * len(self.positions)
        current_step = 0
        for _ in range(self.num_loops):
            for position, interval, click_type in self.positions:
                if not self.running:
                    return  # Exit if not running
                while self.paused:  # Pause loop
                    time.sleep(0.1)
                if click_type == 'single':
                    pyautogui.click(position)
                elif click_type == 'double':
                    pyautogui.doubleClick(position)
                elif click_type == 'right':
                    pyautogui.rightClick(position)
                elif click_type is None:
                    pyautogui.moveTo(position)
                time.sleep(interval)
                current_step += 1
                self.updateProgressBar(current_step / total_steps * 100)
        self.running = False
        self.start_button.setText('Start')
        self.updateProgressBar(0)
        self.pause_resume_button.hide()  # Hide the button
        self.progress_bar.hide()  # Hide the progress bar

    @pyqtSlot()
    def togglePauseResume(self):
        if self.paused:
            self.automation_thread.resume()
            self.estimated_time_timer.start(1000)  # Resume the estimated time countdown
            self.mouse_listener.stop()
            self.mouse_listener_thread.join()
            self.pause_resume_button.setText('Pause')
            self.paused = False
        else:
            self.automation_thread.pause()
            self.estimated_time_timer.stop()  # Pause the estimated time countdown
            self.startMouseListener()
            self.pause_resume_button.setText('Resume')
            self.paused = True

    def startMouseListener(self):
        self.mouse_listener = MouseListener(on_move=self.on_mouse_move)
        self.mouse_listener_thread = threading.Thread(target=self.mouse_listener.start)
        self.mouse_listener_thread.start()

    def on_mouse_move(self, x, y):
        if self.running and not self.paused:
            self.togglePauseResume()

    @pyqtSlot()
    def stopAutomation(self):
        if self.automation_thread and self.automation_thread.isRunning():
            current_loop = self.automation_thread.current_loop
            remaining_loops = self.num_loops - current_loop + 1
            self.num_loops = max(0, remaining_loops)

            # Update the number of loops input field
            self.num_loops_input.setText(str(self.num_loops))

            self.automation_thread.stop()
            # Wait for the thread to finish in a non-blocking way
            while self.automation_thread.isRunning():
                QApplication.processEvents()

            self.running = False
            self.setNonAutomationUIEnabled(True)
            self.updateProgressBar(0)
            self.loop_indicator_label.hide()
            self.pause_resume_button.setText('Pause')
            self.paused = False
            self.pause_resume_button.hide()
            self.stop_button.hide()
            self.progress_bar.hide()
            self.estimated_time_label.hide()  # Show the estimated time label

            # Show the elements that were hidden during processing
            self.position_input.show()
            self.get_position_button.show()
            self.interval_input.show()
            self.interval_label.show()
            self.num_loops_input.show()
            self.num_loops_input.setDisabled(True)
            self.loops_label.show()
            self.add_more_button.show()
            self.start_button.show()
            self.reset_button.show()
            self.single_click_radio.show()
            self.double_click_radio.show()
            self.right_click_radio.show()
            self.no_action_radio.show()

        if self.running or len(self.positions) > 1:
            self.num_loops_input.setDisabled(True)

        if self.mouse_listener.running:
            self.mouse_listener.stop()
            self.mouse_listener_thread.join()

    def closeEvent(self, event):
        # ... [existing closeEvent functionality]
        if hasattr(self, 'mouse_listener') and self.mouse_listener.running:
            self.mouse_listener.stop()
            self.mouse_listener_thread.join()

    def updateProgressBar(self, value):
        self.progress_bar.setValue(int(value))

    def updateLoopIndicator(self, current_loop, total_loops):
        self.loop_indicator_label.setText(f'Loop: {current_loop}/{total_loops}')
        self.loop_indicator_label.show()

    def getCurrentLoop(self):
        return self.loop_num

    def updateEstimatedTime(self):
        if self.estimated_time_seconds > 0:
            self.estimated_time_seconds -= 1
        self.displayEstimatedTime(self.estimated_time_seconds)

    def displayEstimatedTime(self, seconds):
        # Format and display the estimated time
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        self.estimated_time_label.setText(f'Estimated Time: {time_str}')

    def onCommandSelected(self, item):
        # This method is called when an item in the list is clicked
        if item:
            # Hide all buttons first
            self.add_more_button.hide()
            self.start_button.hide()
            self.reset_button.hide()

            # Now show the buttons in the desired order
            self.edit_button.show()
            self.remove_button.show()
            self.back_button.show()
        else:
            self.onSelectionChanged()

    def onSelectionChanged(self):
        if not self.positions_list.selectedItems():
            # Reset UI to original state with Add, Start, Reset
            self.add_more_button.setText('Add')
            self.add_more_button.clicked.disconnect()
            self.add_more_button.clicked.connect(self.addMore)
            self.add_more_button.show()

            self.start_button.show()

            self.reset_button.setText('Reset')
            self.reset_button.clicked.disconnect()
            self.reset_button.clicked.connect(self.resetList)
            self.reset_button.show()

            self.edit_button.hide()
            self.remove_button.hide()
            self.back_button.hide()

    def editCommand(self):
        selected_item = self.positions_list.currentItem()
        if selected_item:
            index = self.positions_list.row(selected_item)
            position, interval, click_type = self.positions[index]

            # Set the input fields with selected item's values
            self.position_input.setText(f'{position[0]}, {position[1]}')
            self.interval_input.setText(str(interval))

            # Set the radio buttons according to the click_type
            if click_type == 'single':
                self.single_click_radio.setChecked(True)
            elif click_type == 'double':
                self.double_click_radio.setChecked(True)
            elif click_type == 'right':
                self.right_click_radio.setChecked(True)
            else:
                self.no_action_radio.setChecked(True)

            # Enable editing of num_loops_input if the first item is selected
            if index == 0:
                self.num_loops_input.setEnabled(True)
            else:
                self.num_loops_input.setDisabled(True)

            # Change the Add button to Update
            self.add_more_button.setText('Update')
            self.add_more_button.clicked.disconnect()
            self.add_more_button.clicked.connect(lambda: self.updateCommand(index))

            # Change the Reset button to Cancel
            self.reset_button.setText('Cancel')
            self.reset_button.clicked.disconnect()
            self.reset_button.clicked.connect(self.cancelEdit)

            # UI Adjustments
            self.edit_button.hide()
            self.start_button.hide()
            self.add_more_button.show()
            self.reset_button.show()
            self.remove_button.hide()
            self.back_button.hide()

    def onBackClicked(self):
        # Clear selection and reset UI to original state
        self.positions_list.clearSelection()
        self.onSelectionChanged()
        self.back_button.hide()  # Hide the Back button

    def updateCommand(self, index):
        try:
            position = tuple(map(int, self.position_input.text().split(',')))
            interval = float(self.interval_input.text())
            click_type = self.getCurrentClickType()

            self.positions[index] = (position, interval, click_type)
            self.positions_list.item(index).setText(f'Position: {position}, Interval: {interval}s, Click: {click_type}')

            self.resetUIAfterEditOrRemove()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Invalid input: {e}')

    def getCurrentClickType(self):
        if self.single_click_radio.isChecked():
            return 'single'
        elif self.double_click_radio.isChecked():
            return 'double'
        elif self.right_click_radio.isChecked():
            return 'right'
        else:
            return None

    def cancelEdit(self):
        self.resetUIAfterEditOrRemove()

    def clearInputFields(self):
        self.position_input.clear()
        self.interval_input.clear()
        self.single_click_radio.setChecked(False)
        self.double_click_radio.setChecked(False)
        self.right_click_radio.setChecked(False)
        self.no_action_radio.setChecked(True)

    def removeCommand(self):
        selected_item = self.positions_list.currentItem()
        if selected_item:
            index = self.positions_list.row(selected_item)
            if index == 0:
                reply = QMessageBox.question(self, 'Reset Confirmation',
                                             'Removing the first item will reset everything. Proceed?',
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.resetList()
            else:
                self.positions.pop(index)
                self.positions_list.takeItem(index)
                self.resetUIAfterEditOrRemove()
        else:
            QMessageBox.information(self, 'No selection', 'Please select an item to remove.')

    def autoClearList(self):
        # self.clearList()
        self.running = False
        self.setNonAutomationUIEnabled(True)
        self.updateProgressBar(0)
        self.loop_indicator_label.hide()  # Hide loop indicator
        self.pause_resume_button.hide()
        self.progress_bar.hide()
        self.stop_button.hide()
        self.estimated_time_label.hide()  # Show the estimated time label
        self.start_button.setText('Start')

        self.pause_resume_button.setText('Pause')
        self.paused = False

        # Show elements after processing is done
        self.position_input.show()
        self.get_position_button.show()
        self.interval_input.show()
        self.interval_label.show()
        self.num_loops_input.show()
        self.loops_label.show()
        self.add_more_button.show()
        self.start_button.show()
        self.reset_button.show()
        self.single_click_radio.show()
        self.double_click_radio.show()
        self.right_click_radio.show()
        self.no_action_radio.show()

    def clearList(self):
        # Clear the positions list and the QListWidget
        self.positions.clear()
        self.positions_list.clear()
        self.num_loops_input.setDisabled(False)
        self.num_loops = 0
        self.position_input.clear()
        self.interval_input.clear()
        self.num_loops_input.clear()
        self.pause_resume_button.hide()
        self.progress_bar.hide()
        self.estimated_time_label.hide()  # Show the estimated time label
        self.start_button.setText('Start')

    def resetUIAfterEditOrRemove(self):
        # Reset the button text and connections
        self.add_more_button.setText('Add')
        self.add_more_button.clicked.disconnect()
        self.add_more_button.clicked.connect(self.addMore)
        self.add_more_button.show()

        self.reset_button.setText('Reset')
        self.reset_button.clicked.disconnect()
        self.reset_button.clicked.connect(self.resetList)
        self.reset_button.show()

        self.start_button.show()

        self.edit_button.hide()
        self.remove_button.hide()
        self.back_button.hide()

        if self.running or len(self.positions) > 1:
            self.num_loops_input.setDisabled(True)

        # Clear the input fields
        self.clearInputFields()

    @pyqtSlot()
    def resetList(self):
        # Stop the thread if it's running
        if self.running and self.automation_thread and self.automation_thread.isRunning():
            self.automation_thread.stop()
            self.automation_thread.wait()  # Wait for the thread to finish
        self.clearList()

    def closeEvent(self, event):
        if self.automation_thread and self.automation_thread.isRunning():
            self.automation_thread.stop()
        event.accept()  # Ensure the event is accepted to close the window

    def mousePressEvent(self, event):
        if self.running:
            # Do nothing if the automation is running
            return

        widget_at_click = QApplication.widgetAt(event.globalPos())
        if widget_at_click != self.positions_list:
            self.positions_list.clearSelection()
            self.onSelectionChanged()

        super().mousePressEvent(event)

def main():
    app = QApplication(sys.argv)

    # Set the global stylesheet for the application
    app.setStyleSheet("""
    QWidget {
        background-color: #323232;
        color: #EEEEEE;
    }
    QLineEdit, QListWidget {
        background-color: #424242;
        border: 1px solid #555555;
    }
    QPushButton {
        background-color: #EEEEEE;
        color: #000000;
    }
    """)

    ex = ClickAutomationApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


# import pyautogui
# import time
# import keyboard  # you might need to install this package
#
# # Define the coordinates for positions a and b
# position_a = (1845, 593)  # Replace x1, y1 with the actual coordinates for position a
# position_b = (1856, 136)  # Replace x2, y2 with the actual coordinates for position b
#
# # Number of times to repeat the process
# repeat_count = 806
#
# # 10-second delay before starting
# print("Starting in 10 seconds...")
# time.sleep(10)
#
# for _ in range(repeat_count):
#     if keyboard.is_pressed('q'):  # If 'q' is pressed, break the loop
#         print("Exiting...")
#         break
#
#     # Move to position a and click
#     pyautogui.click(position_a)
#
#     # Wait for 2 seconds
#     time.sleep(3)
#
#     # Move to position b and click
#     pyautogui.click(position_b)
#
#     # Wait for 0.5 seconds
#     time.sleep(0.5)
#
#     # Return to position a
#     pyautogui.moveTo(position_a)
#
# print("Process completed or exited.")