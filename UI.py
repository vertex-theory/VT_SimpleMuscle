import maya.cmds as cmds

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore

try:
    from shiboken2 import wrapInstance  # Maya 2024 and earlier
except ImportError:
    from shiboken6 import wrapInstance  # Maya 2025 and later

import maya.OpenMayaUI as omui
import importlib
import VT_SimpleMuscle.lib as sm
importlib.reload(sm)

'''
TODO

'''


# Function to get the main Maya window
def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


# Main UI class
class VTSimpleMuscleUI(QtWidgets.QWidget):
    def __init__(self):
        super(VTSimpleMuscleUI, self).__init__(parent=get_maya_main_window())

        self.setObjectName("VTSimpleMuscleUI")
        self.setWindowTitle("VT_SimpleMuscle 1.0")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setMinimumWidth(300)

        # Create the tab widget
        self.tab_widget = QtWidgets.QTabWidget(self)

        self.create_muscle_tab()

        self.create_push_joint_tab()

        # Main layout
        muscle_layout = QtWidgets.QVBoxLayout(self)
        muscle_layout.addWidget(self.tab_widget)

    def create_muscle_tab(self):
        muscle_tab = QtWidgets.QWidget()
        muscle_layout = QtWidgets.QVBoxLayout(muscle_tab)

        # First Section: Create Muscle Rig Guides
        section_1_layout = QtWidgets.QVBoxLayout()
        section_1_title = QtWidgets.QLabel("1. Create Muscle Rig Guides")
        section_1_title.setAlignment(QtCore.Qt.AlignLeft)
        section_1_layout.addWidget(section_1_title)

        muscle_name_label = QtWidgets.QLabel("Muscle Name (Use _L/_l, _M/_m, _R/_r):")
        section_1_layout.addWidget(muscle_name_label)

        muscle_name_layout = QtWidgets.QHBoxLayout()
        self.muscle_name_input = QtWidgets.QLineEdit()
        muscle_name_layout.addWidget(self.muscle_name_input)

        section_1_layout.addLayout(muscle_name_layout)

        set_parent_lable = QtWidgets.QLabel("Set Muscle Parent (should be a skin joint)")
        section_1_layout.addWidget(set_parent_lable)

        set_parent_layout = QtWidgets.QHBoxLayout()
        self.muscle_parent_input = QtWidgets.QLineEdit()
        set_parent_layout.addWidget(self.muscle_parent_input)
        rig_parent_button = QtWidgets.QPushButton("<<Use Selected")
        set_parent_layout.addWidget(rig_parent_button)
        section_1_layout.addLayout(set_parent_layout)

        number_joints_label = QtWidgets.QLabel("Number Of Deformation Joints\n(you can change this later):")
        section_1_layout.addWidget(number_joints_label)
        self.joint_number_input = QtWidgets.QSpinBox()
        self.joint_number_input.setMinimum(0)  # Set minimum value
        self.joint_number_input.setMaximum(100)  # Set maximum value
        self.joint_number_input.setValue(3)  # Default value
        section_1_layout.addWidget(self.joint_number_input)

        surf_type_label = QtWidgets.QLabel("Linear or Cubic\nCubic for twisting sections like a bicep\n(you can change this later):")
        section_1_layout.addWidget(surf_type_label)
        self.type_dropdown = QtWidgets.QComboBox()
        self.type_dropdown.addItems(["Linear", "Cubic"])
        section_1_layout.addWidget(self.type_dropdown)

        create_muscle_button = QtWidgets.QPushButton("Create Muscle Guide")
        section_1_layout.addWidget(create_muscle_button)


        #section_1_layout.addWidget(muscle_name_label)


        muscle_layout.addLayout(section_1_layout)

        # Horizontal line
        muscle_layout.addWidget(self.create_horizontal_line())

        # Second Section: Set Guide Attributes
        section_2_layout = QtWidgets.QVBoxLayout()
        section_2_title = QtWidgets.QLabel(
            "2. Mirror Muscle Guides\nLeft to Right\nMuscle names must use (_L/_l, _M/_m, _R/_r)\nIf guides are selected it will mirror just those guides.\nIf no guides are selected it will mirror all the _L guides")
        section_2_title.setAlignment(QtCore.Qt.AlignLeft)
        section_2_layout.addWidget(section_2_title)

        guide_mirror_layout = QtWidgets.QHBoxLayout()
        mirror_guide_button = QtWidgets.QPushButton("Mirror Guides")
        guide_mirror_layout.addWidget(mirror_guide_button)

        section_2_layout.addLayout(guide_mirror_layout)

        muscle_layout.addLayout(section_2_layout)

        # Horizontal line
        muscle_layout.addWidget(self.create_horizontal_line())

        # Third Section: Build Muscle Rig
        section_3_layout = QtWidgets.QVBoxLayout()
        section_3_title = QtWidgets.QLabel(
            "3. Build Muscle Rigs\nEither builds selected guides or all guides")
        section_3_title.setAlignment(QtCore.Qt.AlignLeft)
        section_3_layout.addWidget(section_3_title)

        build_layout = QtWidgets.QHBoxLayout()
        build_button = QtWidgets.QPushButton("Build")
        build_layout.addWidget(build_button)

        section_3_layout.addLayout(build_layout)

        muscle_layout.addLayout(section_3_layout)

        # Horizontal line
        muscle_layout.addWidget(self.create_horizontal_line())

        # Fourth Section: Build Muscle Rig
        section_4_layout = QtWidgets.QVBoxLayout()
        section_4_title = QtWidgets.QLabel(
            "4. Export/Import Guides")
        section_4_title.setAlignment(QtCore.Qt.AlignLeft)
        section_4_layout.addWidget(section_4_title)

        export_layout = QtWidgets.QHBoxLayout()
        export_button = QtWidgets.QPushButton("Export")
        export_layout.addWidget(export_button)
        import_button = QtWidgets.QPushButton('Import')
        export_layout.addWidget(import_button)
        bake_button = QtWidgets.QPushButton("Bake Settings To Guides")

        section_4_layout.addWidget(bake_button)
        section_4_layout.addLayout(export_layout)

        muscle_layout.addLayout(section_4_layout)

        # Horizontal line
        muscle_layout.addWidget(self.create_horizontal_line())

        # Fith Section: Build Muscle Rig
        section_5_layout = QtWidgets.QVBoxLayout()
        section_5_title = QtWidgets.QLabel(
            "Utilities")
        section_5_title.setAlignment(QtCore.Qt.AlignLeft)
        section_5_layout.addWidget(section_5_title)

        utility_layout = QtWidgets.QHBoxLayout()
        disconnect_button = QtWidgets.QPushButton("Unparent Joints")
        utility_layout.addWidget(disconnect_button)
        connect_button = QtWidgets.QPushButton("Parent Joints")
        utility_layout.addWidget(connect_button)
        delete_button=QtWidgets.QPushButton("Delete Muscle Rigs")
        utility_layout.addWidget(delete_button)

        utility2_layout = QtWidgets.QHBoxLayout()
        select_jnts_button = QtWidgets.QPushButton("Select Skin Joints")
        utility2_layout.addWidget(select_jnts_button)
        mirror_settings_button = QtWidgets.QPushButton('Mirror Rig Settings')
        utility2_layout.addWidget(mirror_settings_button)

        section_5_layout.addLayout(utility_layout)
        section_5_layout.addLayout(utility2_layout)

        muscle_layout.addLayout(section_5_layout)

        # Footer Section: Author and Contact Info
        footer_widget = QtWidgets.QWidget()  # Create a QWidget for styling
        footer_layout = QtWidgets.QVBoxLayout(footer_widget)
        footer_layout.setAlignment(QtCore.Qt.AlignCenter)

        author_label = QtWidgets.QLabel("Author: Jeff Brodsky")
        contact_label = QtWidgets.QLabel("vertexTheory.com")

        # Set text color to white for visibility on black background
        author_label.setStyleSheet("color: white;")
        contact_label.setStyleSheet("color: white;")

        footer_layout.addWidget(author_label)
        footer_layout.addWidget(contact_label)

        # Set background color of the footer to black
        footer_widget.setStyleSheet("background-color: black;")

        muscle_layout.addWidget(footer_widget)

        # Connect button signals to functions
        rig_parent_button.clicked.connect(self.set_rig_parent)
        create_muscle_button.clicked.connect(self.create_muscle)
        mirror_guide_button.clicked.connect(self.mirror_click)
        build_button.clicked.connect(self.build_all_click)
        connect_button.clicked.connect(self.parent_click)
        disconnect_button.clicked.connect(self.unparent_click)
        delete_button.clicked.connect(self.delete_all)
        export_button.clicked.connect(self.show_save_dialog)
        import_button.clicked.connect(self.show_import_dialog)
        bake_button.clicked.connect(self.bake_click)
        select_jnts_button.clicked.connect(self.select_joints)
        mirror_settings_button.clicked.connect(self.mirror_settings)

        self.tab_widget.addTab(muscle_tab, 'Simple Muscles')

    def create_push_joint_tab(self):
        pushjoint_tab = QtWidgets.QWidget()
        pushjoint_layout = QtWidgets.QVBoxLayout(pushjoint_tab)

        push_layout = QtWidgets.QVBoxLayout()
        push_title = QtWidgets.QLabel(
            "Build push joint rigs for selected joint.\nUse names like: Elbow_L, Index_01_L")
        push_title.setAlignment(QtCore.Qt.AlignLeft)
        push_layout.addWidget(push_title)

        # push_name_layout = QtWidgets.QHBoxLayout()
        self.push_name_input = QtWidgets.QLineEdit()
        push_layout.addWidget(self.push_name_input)

        push_build_button = QtWidgets.QPushButton('Build Push Joint Rig')
        push_layout.addWidget(push_build_button)

        # Connect button signals to functions
        push_build_button.clicked.connect(self.push_build_click)

        pushjoint_layout.addLayout(push_layout)

        self.tab_widget.addTab(pushjoint_tab, 'Push Joints')

    def create_horizontal_line(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        return line

    def mirror_click(self):
        sm.mirror_guides()

    def build_all_click(self):
        sm.build_all_rigs()

    def parent_click(self):
        sm.parent_def_joints()

    def unparent_click(self):
        sm.unparent_def_joints()

    def bake_click(self):
        sm.bake_to_guides()

    def delete_all(self):
        sm.delete_all_rigs()

    def select_joints(self):
        sm.select_def_joints()

    def mirror_settings(self):
        sm.mirror_rig_settings()

    def create_muscle(self):
        muscle_name = self.muscle_name_input.text()
        parent = self.muscle_parent_input.text()
        number_jnts = self.joint_number_input.value()
        type = self.type_dropdown.currentText()
        sm.create_muscle(muscle_name, parent, number_jnts, type)

    def set_rig_parent(self):
        try:
            self.muscle_parent_input.setText(cmds.ls(sl=True)[0])
        except:
            cmds.error('You need to have a valid rig parent selected. It should be a deformation joint')

    def show_save_dialog(self):
        # Show save file dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Muscle Guides",
            "",
            "Maya ASCII (*.ma)"
        )
        sm.export_guides(file_path)

    def show_import_dialog(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Muscle Guides",
            "",
            "Maya ASCII (*.ma)"
        )
        sm.import_guides(file_path)

    ######################################

    def push_build_click(self):
        name = self.push_name_input.text()
        sm.create_push_joints(cmds.ls(sl=True)[0], name)

# Function to show the UI
def show_ui():
    if cmds.window("VTSimpleMuscleUI", exists=True):
        cmds.deleteUI("VTSimpleMuscleUI", wnd=True)

    try:
        ui = VTSimpleMuscleUI()
        ui.show()
        print("UI displayed successfully.")
    except Exception as e:
        print(f"Failed to show UI: {e}")


