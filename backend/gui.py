"""Desktop GUI for MLS Photo Processor."""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import logging
import threading


class MLSPhotoProcessorGUI:
    """Desktop GUI application for processing MLS photos."""
    
    def __init__(self, processor_func, parcel_matcher, classifier):
        """
        Initialize GUI.
        
        Args:
            processor_func: Function to call for processing (process_folder)
            parcel_matcher: ParcelMatcher instance
            classifier: ImageClassifier instance
        """
        self.processor_func = processor_func
        self.parcel_matcher = parcel_matcher
        self.classifier = classifier
        
        self.root = tk.Tk()
        self.root.title("MLS Photo Processor")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        self.selected_folder = None
        
        self._create_widgets()
        
        # Set up logging to GUI
        self._setup_logging()
        
        # Initialize button state
        self._update_process_button()
    
    def _create_widgets(self):
        """Create GUI widgets."""
        # Main container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="MLS Photo Processor",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Folder selection section
        folder_frame = tk.LabelFrame(main_frame, text="Select Folder", padx=10, pady=10)
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_label = tk.Label(
            folder_frame,
            text="No folder selected",
            wraplength=500,
            anchor="w"
        )
        self.folder_label.pack(fill=tk.X, pady=(0, 5))
        
        select_folder_btn = tk.Button(
            folder_frame,
            text="Select Folder",
            command=self._select_folder,
            width=20
        )
        select_folder_btn.pack()
        
        # Process button
        self.process_btn = tk.Button(
            main_frame,
            text="Process Images",
            command=self._process_images,
            state=tk.DISABLED,
            font=("Arial", 14, "bold"),
            bg="white",
            fg="black",
            width=20,
            height=2,
            relief=tk.RAISED,
            borderwidth=3,
            highlightthickness=2,
            highlightbackground="black"
        )
        self.process_btn.pack(pady=10)
        
        # Status/log area
        log_frame = tk.LabelFrame(main_frame, text="Status", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _setup_logging(self):
        """Set up logging to GUI text area."""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, msg + "\n")
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)
        
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger = logging.getLogger()
        logger.addHandler(gui_handler)
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message to GUI."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def _select_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title="Select folder containing MLS photos")
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=f"Selected: {folder}")
            self._log(f"Selected folder: {folder}")
            self._update_process_button()
    
    def _update_process_button(self):
        """Enable/disable process button based on selections."""
        if self.selected_folder:
            self.process_btn.config(
                state=tk.NORMAL,
                bg="white",
                fg="black",
                font=("Arial", 14, "bold"),
                activebackground="#E0E0E0",  # Light gray on hover
                activeforeground="black"
            )
        else:
            self.process_btn.config(
                state=tk.DISABLED,
                bg="white",
                fg="#808080",  # Gray text when disabled
                font=("Arial", 14, "bold")
            )
    
    def _process_images(self):
        """Process images in selected folder."""
        if not self.selected_folder:
            messagebox.showerror("Error", "Please select a folder first")
            return
        
        # Disable button during processing
        self.process_btn.config(
            state=tk.DISABLED,
            text="Processing...",
            bg="white",
            fg="black",
            font=("Arial", 14, "bold")
        )
        self._log("=" * 60)
        self._log("Starting image processing...")
        
        # Output to the same folder as input
        output_dir = str(Path(self.selected_folder) / "processed")
        
        # Run processing in separate thread to avoid blocking GUI
        def process_thread():
            try:
                result = self.processor_func(
                    self.selected_folder,
                    output_dir,
                    self.parcel_matcher,
                    self.classifier
                )
                
                # Update GUI in main thread
                self.root.after(0, self._processing_complete, result)
            except Exception as e:
                self.root.after(0, self._processing_error, str(e))
        
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def _processing_complete(self, result: dict):
        """Handle processing completion."""
        self.process_btn.config(
            state=tk.NORMAL,
            text="Process Images",
            bg="white",
            fg="black",
            font=("Arial", 14, "bold"),
            activebackground="#E0E0E0",
            activeforeground="black"
        )
        
        self._log("=" * 60)
        self._log("Processing complete!")
        self._log(f"Account Number: {result.get('account_no', 'UNKNOWN')}")
        if result.get('parcel_no'):
            self._log(f"Parcel Number: {result['parcel_no']}")
        self._log(f"Processed: {result.get('processed_count', 0)} images")
        
        if result.get('skipped_files'):
            self._log(f"Skipped {len(result['skipped_files'])} invalid files")
        
        if result.get('errors'):
            self._log(f"Errors: {len(result['errors'])}")
            for error in result['errors']:
                self._log(f"  - {error}")
        
        # Show completion message
        message = f"Processing complete!\n\n"
        message += f"Processed: {result.get('processed_count', 0)} images\n"
        message += f"Account: {result.get('account_no', 'UNKNOWN')}\n"
        if result.get('errors'):
            message += f"\n{len(result['errors'])} error(s) occurred. Check log for details."
        
        messagebox.showinfo("Processing Complete", message)
    
    def _processing_error(self, error_msg: str):
        """Handle processing error."""
        self.process_btn.config(
            state=tk.NORMAL,
            text="Process Images",
            bg="white",
            fg="black",
            font=("Arial", 14, "bold"),
            activebackground="#E0E0E0",
            activeforeground="black"
        )
        self._log(f"ERROR: {error_msg}")
        messagebox.showerror("Processing Error", f"An error occurred:\n\n{error_msg}")
    
    def run(self):
        """Start GUI main loop."""
        self.root.mainloop()

