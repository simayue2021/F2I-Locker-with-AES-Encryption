import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import math
import numpy as np
from tqdm import tqdm
import zipfile
import os
import pyAesCrypt


class F2I(object):

    def lock(self, folder_path, lock_image_path, password, tile_size=256):
        # Zip the input folder
        folder_name = os.path.basename(folder_path)
        zip_path = folder_name + '.zip'
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_BZIP2) as zipf:
            # Add a text file with the folder name to the zip file
            zipf.writestr('folder_name.txt', folder_name)
            # Get the total number of files in the folder
            total_files = sum([len(files) for r, d, files in os.walk(folder_path)])
            # Create a tqdm progress bar
            with tqdm(total=total_files, desc="Zipping files") as pbar:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname=arcname)
                        # Update the progress bar
                        pbar.update(1)

        # Encrypt the zipped file using pyAesCrypt
        buffer_size = 64 * 1024
        encrypted_zip_path = zip_path + '.aes'
        with open(zip_path, 'rb') as fIn:
            with open(encrypted_zip_path, 'wb') as fOut:
                pyAesCrypt.encryptStream(fIn, fOut, password, buffer_size)

        # Calculate the size of the image
        size = int(math.sqrt(os.stat(encrypted_zip_path).st_size)) + 1

        # Calculate the number of tiles needed
        num_tiles = math.ceil(size / tile_size)

        # Create a new image with the calculated size
        image = Image.new('L', (size, size))

        # Read and process the encrypted zipped file in chunks
        x = y = 0
        with open(encrypted_zip_path, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                for b in chunk:
                    image.putpixel((x, y), b)
                    x += 1
                    if x == size:
                        x = 0
                        y += 1

        # Save the image in tiles
        for i in range(num_tiles):
            for j in range(num_tiles):
                tile = image.crop((i * tile_size, j * tile_size, (i + 1) * tile_size, (j + 1) * tile_size))
                tile.save(f"{lock_image_path}_{i}_{j}.png")

        # Combine the tiles to produce a single image
        combined_image = Image.new('L', (size, size))
        for i in range(num_tiles):
            for j in range(num_tiles):
                tile = Image.open(f"{lock_image_path}_{i}_{j}.png")
                combined_image.paste(tile, (i * tile_size, j * tile_size))
                os.remove(f"{lock_image_path}_{i}_{j}.png")

        combined_image.save(lock_image_path)

        os.remove(zip_path)
        os.remove(encrypted_zip_path)

        # Show progress using tqdm
        for _ in tqdm(range(size * size), desc="Processing data"):
            pass
    def unlock(self, lock_image_path, final_path, password):
        # Open the image
        image = Image.open(lock_image_path)
        # Get the pixel data from the image as a numpy array
        data = np.array(image)

        # Flatten the numpy array and convert it to binary data
        data = data.tobytes()

        # Write the encrypted data to a temporary file in chunks
        temp_file = 'temp.zip.aes'
        with open(temp_file, 'wb') as f:
            for i in tqdm(range(0, len(data), 1024), desc="Writing data"):
                f.write(data[i:i + 1024])

        # Decrypt the temporary file using pyAesCrypt
        buffer_size = 64 * 1024
        decrypted_zip_path = 'temp.zip'
        with open(temp_file, 'rb') as fIn:
            with open(decrypted_zip_path, 'wb') as fOut:
                try:
                    pyAesCrypt.decryptStream(fIn, fOut, password, buffer_size)
                except ValueError:
                    pass

        # Unzip the temporary file to recover the original file
        with zipfile.ZipFile(decrypted_zip_path, 'r') as zipf:
            # Read the folder name from the text file in the zip file
            with zipf.open('folder_name.txt') as f:
                folder_name = f.read().decode('utf-8')
                end_path = final_path + "/" + folder_name
                print(end_path)
            zipf.extractall(end_path)

        # Delete the temporary files
        os.remove(temp_file)
        os.remove(decrypted_zip_path)
        os.remove(final_path + "/" + folder_name + "/" + "folder_name.txt")


class F2IGUI(object):

    def __init__(self, root):
        self.root = root
        self.root.title("F2I Lock - Lock folder into image")

        # Add background image to the GUI
        self.background_image = Image.open("background_image.png")
        self.background_image = self.background_image.resize((800, 600), Image.LANCZOS)
        self.background_photo = ImageTk.PhotoImage(self.background_image)
        self.background_label = tk.Label(root, image=self.background_photo)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.folder_path = tk.StringVar()
        self.image_path = tk.StringVar()
        self.lock_image_path = tk.StringVar()

        # Set the window size and position it in the center of the screen
        self.window_width = 800
        self.window_height = 600
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.x_coordinate = int((self.screen_width / 2) - (self.window_width / 2))
        self.y_coordinate = int((self.screen_height / 2) - (self.window_height / 2))
        self.root.geometry(f"{self.window_width}x{self.window_height}+{self.x_coordinate}+{self.y_coordinate}")

        # Create a frame with a transparent background
        self.frame = tk.Frame(root, bg="white", bd=5)
        self.frame.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = tk.Label(self.frame, text="F2I Lock", bg="white", font=("Arial", 24))
        self.title_label.grid(row=0, column=0, padx=10, pady=5)

        self.key_label = tk.Label(self.frame, text="Password:", bg="white", font=("Arial", 15))
        self.key_label.grid(row=1, column=0, padx=10, pady=5)

        self.key_entry = tk.Entry(self.frame, show="*", font=("Arial", 15))
        self.key_entry.grid(row=1, column=1, padx=10, pady=5)

        self.secret_image_label = tk.Label(self.frame, text="Folder:", bg="white", font=("Arial", 15))
        self.secret_image_label.grid(row=2, column=0, padx=10, pady=5)

        self.secret_image_entry = tk.Entry(self.frame, textvariable=self.folder_path, state="disabled",
                                           font=("Arial", 15))
        self.secret_image_entry.grid(row=2, column=1, padx=10, pady=5)

        self.secret_image_button = tk.Button(self.frame, text="Browse", command=self.browse_folder,
                                             font=("Arial", 15))
        self.secret_image_button.grid(row=2, column=2, padx=10, pady=5)

        self.hide_button = tk.Button(self.frame, text="Lock into Image", command=self.lock, font=("Arial", 15))
        self.hide_button.grid(row=4, column=1, padx=10, pady=5)

        self.unhide_button = tk.Button(self.frame, text="Unlock into Folder", command=self.unlock, font=("Arial", 15))
        self.unhide_button.grid(row=6, column=1, padx=10, pady=5)

        self.stego_image_label = tk.Label(self.frame, text="Image:", bg="white", font=("Arial", 15))
        self.stego_image_label.grid(row=5, column=0, padx=10, pady=5)

        self.stego_image_button = tk.Button(self.frame, text="Browse", command=self.browse_lock_image,
                                            font=("Arial", 15))
        self.stego_image_button.grid(row=5, column=2, padx=10, pady=5)

        self.stego_image_entry = tk.Entry(self.frame, textvariable=self.lock_image_path, state="disabled",
                                          font=("Arial", 15))
        self.stego_image_entry.grid(row=5, column=1, padx=10, pady=5)

    def browse_folder(self):
        folder_path = tk.filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)

    def lock(self):
        folder_path = self.folder_path.get()
        image_path = filedialog.asksaveasfilename(title="Save Stego Image", defaultextension=".png",
                                                  filetypes=[("PNG Files", "*.png")])
        password = self.key_entry.get()
        if folder_path and image_path and password:
            f2i = F2I()
            f2i.lock(folder_path, image_path, password)
            self.lock_image_path.set(image_path)
            messagebox.showinfo("Success", "Folder locked successfully!")
        else:
            messagebox.showinfo("Error", "Please fill in all the required fields.")

    def unlock(self):
        lock_image_path = self.lock_image_path.get()
        final_path = filedialog.askdirectory(title="Save Stego Image")
        password = self.key_entry.get()
        if lock_image_path and final_path and password:
            f2i = F2I()
            f2i.unlock(lock_image_path, final_path, password)
            messagebox.showinfo("Success", "Folder unlocked successfully!")
        else:
            messagebox.showinfo("Error", "Please fill in all the required fields.")

    def browse_lock_image(self):
        lock_image_path = filedialog.askopenfilename(title="Select Locked Image",
                                                     filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if lock_image_path:
            self.lock_image_path.set(lock_image_path)


if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap("favicon.ico")
    gui = F2IGUI(root)
    gui.root.mainloop()
