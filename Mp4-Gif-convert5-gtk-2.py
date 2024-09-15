#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject
from moviepy.editor import VideoFileClip
import os
import threading
import time
from PIL import Image

# Monkey patch for the deprecated Image.ANTIALIAS in PIL
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # Ensure compatibility with Pillow 10.x
    
# Initialize GTK and check if it's available
if not Gtk.init_check():
    print("Failed to initialize GTK.")
    exit(1)    

class ConverterApp(Gtk.Window):

    def __init__(self):
        super().__init__(title="Mp4 <-> Gif")
        self.set_border_width(10)
        self.set_default_size(600, 165)

        # Default conversion settings
        self.bitrate = 500  # in kbps for GIF to MP4
        self.mp4_to_gif_fps = 30  # Default FPS for MP4 to GIF conversion
        self.gif_to_mp4_fps = 30  # Default FPS for GIF to MP4 conversion

        # Create main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Input file path row
        input_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(input_hbox, False, False, 0)

        input_label = Gtk.Label(label="Input Path:")
        input_hbox.pack_start(input_label, False, False, 0)

        self.input_entry = Gtk.Entry()
        input_hbox.pack_start(self.input_entry, True, True, 0)
        self.input_directory=""  #this variable stores the input file so that it can be automatically selected as the output folder

        input_file_button = Gtk.Button(label="Select Input File")
        input_file_button.connect("clicked", self.on_select_input_file)
        input_hbox.pack_start(input_file_button, False, False, 0)

        # Output file path row
        output_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(output_hbox, False, False, 0)

        output_label = Gtk.Label(label="Output Path:")
        output_hbox.pack_start(output_label, False, False, 0)

        self.output_entry = Gtk.Entry()
        output_hbox.pack_start(self.output_entry, True, True, 0)

        output_directory_button = Gtk.Button(label="Select Output Folder")
        output_directory_button.connect("clicked", self.on_select_output_directory)
        output_hbox.pack_start(output_directory_button, False, False, 0)

        # Settings button at the bottom
        settings_button = Gtk.Button(label="Settings")
        settings_button.connect("clicked", self.on_open_settings)
        vbox.pack_end(settings_button, False, False, 0)

        # Convert button
        convert_button = Gtk.Button(label="Convert")
        convert_button.connect("clicked", self.on_convert_file)
        vbox.pack_start(convert_button, False, False, 0)

        # Status label for progress updates
        self.status_label = Gtk.Label(label="")
        vbox.pack_start(self.status_label, False, False, 0)

        # Flag to control the animation
        self.animate = False
      
    ############################ This is the part where the buttons & menus functionality is coded #######################################  
    def on_select_input_file(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Input File", parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            input_file_path = dialog.get_filename()
            self.input_entry.set_text(input_file_path)
            self.input_directory = os.path.dirname(input_file_path)
            self.output_entry.set_text(self.input_directory) # Automatically set the output directory to the same folder as the input
            
        dialog.destroy()

    def on_select_output_directory(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Output Folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_entry.set_text(dialog.get_filename())
        if self.input_directory:
            dialog.set_current_folder(self.input_directory)
        response = dialog.run()    

        dialog.destroy()

    def update_status(self, message):
        GObject.idle_add(self.status_label.set_text, message)  # Update the label from the main thread

    def animate_dots(self):
        dots = ["", ".", "..", "..."]
        counter = 0
        while self.animate:
            GObject.idle_add(self.update_status, f"Processing{dots[counter]}")
            counter = (counter + 1) % len(dots)
            time.sleep(0.5)  # this controls the speed of the animation
    def mp4_to_gif(self, input_path, output_path):
        video = VideoFileClip(input_path)
        output_file = os.path.join(output_path, os.path.splitext(os.path.basename(input_path))[0] + ".gif")

        # Optimization: Resize and apply FPS based on settings
        video_resized = video.resize(width=1080)  # Resize to width of 1080 pixels
        video_resized.write_gif(output_file, fps=self.mp4_to_gif_fps, program='ffmpeg', opt="optimizeplus")

    def gif_to_mp4(self, input_path, output_path):
        clip = VideoFileClip(input_path)
        output_file = os.path.join(output_path, os.path.splitext(os.path.basename(input_path))[0] + ".mp4")

        # Optimization: Apply FPS and bitrate based on settings
        clip.write_videofile(output_file, codec='libx264', fps=self.gif_to_mp4_fps, bitrate=f"{self.bitrate}k")

    def conversion_thread(self, input_path, output_path):
        try:
            file_extension = os.path.splitext(input_path)[1].lower()

        # Handle MP4 to GIF conversion
            if file_extension == ".mp4":
                self.mp4_to_gif(input_path, output_path)
                conversion_successful = True  # Set flag if conversion is successful

        # Handle GIF to MP4 conversion
            elif file_extension == ".gif":
                self.gif_to_mp4(input_path, output_path)
                conversion_successful = True  # Set flag if conversion is successful

        # Unsupported file type
            else:
                self.update_status("Error: Unsupported file type. Please select either a .mp4 or .gif file.")
                dialog = Gtk.MessageDialog(
                    parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK, text="Input Error",
                )
                dialog.format_secondary_text("Error: Unsupported file type. Please select either a .mp4 or .gif file.")
                dialog.run()
                dialog.destroy()
                conversion_successful = False  # Set flag for unsuccessful conversion
                return  # Exit the function to prevent further execution

        except Exception as e:
            self.update_status(f"Error during conversion: {str(e)}")
            conversion_successful = False  # Set flag for unsuccessful conversion

        finally:
            self.animate = False
            GObject.idle_add(self.update_status, "")

        # Show "Conversion completed." only if the conversion was successful
            if conversion_successful:
                GObject.idle_add(self.update_status, "Conversion completed.")
    

    def on_convert_file(self, widget):
        input_path = self.input_entry.get_text()
        output_path = self.output_entry.get_text()

        if not input_path or not output_path:
            dialog = Gtk.MessageDialog(
                parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK, text="Input Error",
            )
            dialog.format_secondary_text("Please select both an input file and an output directory.")
            dialog.run()
            dialog.destroy()
            return

        # Start the animation in a new thread
        self.animate = True
        threading.Thread(target=self.animate_dots).start()

        # Start conversion in a new thread
        threading.Thread(target=self.conversion_thread, args=(input_path, output_path)).start()

    def on_open_settings(self, widget):
        # Create a dialog window for settings
        dialog = Gtk.Dialog(title="Settings", transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        # Get the content area of the dialog
        content_area = dialog.get_content_area()

        # Create sliders for bitrate and FPS settings
        bitrate_adjustment = Gtk.Adjustment(value=self.bitrate, lower=100, upper=1000, step_increment=10)
        fps_adjustment_mp4_to_gif = Gtk.Adjustment(value=self.mp4_to_gif_fps, lower=1, upper=60, step_increment=1)
        fps_adjustment_gif_to_mp4 = Gtk.Adjustment(value=self.gif_to_mp4_fps, lower=1, upper=60, step_increment=1)

        bitrate_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=bitrate_adjustment)
        fps_slider_mp4_to_gif = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=fps_adjustment_mp4_to_gif)
        fps_slider_gif_to_mp4 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=fps_adjustment_gif_to_mp4)

        bitrate_slider.set_digits(0)
        fps_slider_mp4_to_gif.set_digits(0)
        fps_slider_gif_to_mp4.set_digits(0)

        content_area.pack_start(Gtk.Label(label="GIF to MP4 Bitrate (kbps):"), False, False, 0)
        content_area.pack_start(bitrate_slider, False, False, 0)
        content_area.pack_start(Gtk.Label(label="MP4 to GIF FPS:"), False, False, 0)
        content_area.pack_start(fps_slider_mp4_to_gif, False, False, 0)
        content_area.pack_start(Gtk.Label(label="GIF to MP4 FPS:"), False, False, 0)
        content_area.pack_start(fps_slider_gif_to_mp4, False, False, 0)

        dialog.show_all()

        # Handle OK button click
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.bitrate = int(bitrate_adjustment.get_value())
            self.mp4_to_gif_fps = int(fps_adjustment_mp4_to_gif.get_value())
            self.gif_to_mp4_fps = int(fps_adjustment_gif_to_mp4.get_value())

        dialog.destroy()

def main():
    app = ConverterApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()