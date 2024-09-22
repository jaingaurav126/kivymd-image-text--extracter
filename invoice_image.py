from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window
import os

class UploadApp(MDApp):
    def build(self):
        # Set the theme colors and window background color
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = (1, 1, 1, 1)  # White background

        # Create main layout
        layout = MDBoxLayout(orientation='vertical', padding=30, spacing=20)

        # Add a title at the top
        title_label = MDLabel(
            text="Image Analyzer",
            halign="center",
            font_style="H4",
            theme_text_color="Primary",
            size_hint_y=None,
            height=50
        )
        layout.add_widget(title_label)

        # Add a short description below the title
        description_label = MDLabel(
            text="Extract content from images in a structured format.",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=40
        )
        layout.add_widget(description_label)

        # Add a status label for updates
        self.status_label = MDLabel(
            text="Press 'Select File' to choose a file",
            halign="center",
            theme_text_color="Hint",
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.status_label)

        # Add 'Select File' button
        file_select_button = MDRaisedButton(
            text="Select File",
            size_hint=(1, 0.2),
            md_bg_color=self.theme_cls.primary_color,
            pos_hint={'center_x': 0.5}
        )
        file_select_button.bind(on_press=self.open_file_chooser)
        layout.add_widget(file_select_button)

        # Add 'Upload' button
        upload_button = MDRaisedButton(
            text="Upload",
            size_hint=(1, 0.2),
            md_bg_color=self.theme_cls.primary_color,
            pos_hint={'center_x': 0.5}
        )
        upload_button.bind(on_press=self.upload_file)
        layout.add_widget(upload_button)

        self.selected_file = None
        return layout

    def open_file_chooser(self, instance):
        content = MDBoxLayout(orientation='vertical')
        self.file_chooser = FileChooserIconView(filters=['*.jpg', '*.png', '*.pdf'])
        content.add_widget(self.file_chooser)

        close_button = MDRaisedButton(text="Select", size_hint=(1, 0.2))
        close_button.bind(on_press=self.select_file)
        content.add_widget(close_button)

        self.popup = Popup(title="Choose a file", content=content, size_hint=(0.9, 0.9))
        self.popup.open()

    def select_file(self, instance):
        selected = self.file_chooser.selection
        if selected:
            self.selected_file = selected[0]
            self.status_label.text = f"Selected file: {os.path.basename(self.selected_file)}"
        else:
            self.status_label.text = "No file selected"

        self.popup.dismiss()

    def upload_file(self, instance):
        if not self.selected_file:
            self.status_label.text = "No file selected to upload"
            return

        self.status_label.text = "Extracting tables from image..."
        # Show a loading popup with white text
        self.loading_popup = Popup(
            title="Processing",
            content=MDLabel(
                text="Hang tight as we process and organize the content into a clear, structured format for you...",
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1)  # White text
            ),
            size_hint=(0.8, 0.5),
            background_color=(0, 0, 0, 1)  # Black background
        )
        self.loading_popup.open()

        def on_success(req, result):
            self.loading_popup.dismiss()
            table_names = result.get("table_names", [])
            if table_names:
                self.status_label.text = "Tables extracted successfully!"
                self.show_download_button()
            else:
                self.status_label.text = "No tables found."

        def on_failure(req, result):
            self.loading_popup.dismiss()
            self.status_label.text = f"Failed to upload: {result}"

        UrlRequest(
            url='http://127.0.0.1:5000/upload',
            on_success=on_success,
            on_failure=on_failure,
            req_body=open(self.selected_file, 'rb').read(),
            req_headers={'Content-Type': 'application/octet-stream'},
            method='POST'
        )

    def show_download_button(self):
        download_button = MDRaisedButton(
            text="Download Data", size_hint=(1, 0.2), md_bg_color=self.theme_cls.primary_color, pos_hint={'center_x': 0.5}
        )
        download_button.bind(on_press=self.download_data)

        content = MDBoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(MDLabel(
            text="Download the extracted data",
            halign='center',
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1)  # White text
        ))
        content.add_widget(download_button)

        # Create the download popup with a black background
        self.download_popup = Popup(
            title="Download Options",
            content=content,
            size_hint=(0.8, 0.4),
            background_color=(0, 0, 0, 1)  # Black background
        )
        self.download_popup.open()

    def download_data(self, instance):
        self.download_popup.dismiss()
        UrlRequest(
            url='http://127.0.0.1:5000/download',
            on_success=self.on_download_success,
            on_failure=self.on_download_failure
        )

    def on_download_success(self, req, result):
        self.status_label.text = "Download successful!"

    def on_download_failure(self, req, result):
        self.status_label.text = f"Failed to download data: {result}"

if __name__ == '__main__':
    UploadApp().run()
