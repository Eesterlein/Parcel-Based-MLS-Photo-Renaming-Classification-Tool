- Double-click the executable to launch the app

The app opens as a small desktop window.

> **First launch note:**  
> The first time the app runs, it may take slightly longer while the image classification model is downloaded and cached locally. No user action is required.

---

### 2. Download MLS Photos from CREN

- Sign in to CREN using your **own authorized credentials**
- Navigate to the property listing you are working with
- Download the MLS photos for that property

**Folder requirement:**
- Save the photos into a folder named **exactly after the parcel number**

Example:
123456789123


Photos may be in any naming format or structure.

---

### 3. Select the Folder in the App

- Click **Select Folder**
- Choose the parcel-number-named folder containing the MLS photos

---

### 4. Process Photos

- Click **Process Photos**

The application will:
- Resolve the parcel number to an account number
- Validate and normalize images
- Classify images by room type
- Rename files using a consistent naming convention
- Copy processed files into an output folder

---

### 5. View Output

- A new folder named:
processed

will appear inside the selected parcel folder

- This folder contains:
- Renamed JPEG images
- Uppercase filenames
- Files ready for RealWare drag-and-drop upload

Original photos remain unchanged.

---

## Always Verify Results

This tool assists with automation but **final review remains the user’s responsibility**.

Before using processed files:
- Verify the **account number** in filenames is correct
- Review room classifications for reasonableness
- Manually rename any images that need adjustment

Images classified as `OTHER` are expected in ambiguous or low-confidence cases.

---

## Known Limitations & Status

- This application is **early-stage and limited-tested**
- It has been validated against a small number of real MLS photo sets
- Additional refinements will be driven by real user feedback and usage patterns

### Known Issue: Error Message on Exit

You may see an error message when **closing the application**.

- This occurs during application shutdown
- It does **not** affect processed files
- It is related to logging cleanup during GUI teardown
- It can be safely ignored

This is a known, non-critical issue and will be addressed in a future update.

---

## Data Handling & Security

- All files remain on the local machine
- No photos or data are uploaded
- No MLS or CREN credentials are stored or used by the app
- No telemetry or tracking
- After the initial model download, the app runs fully offline

---

## Summary

The MLS Photo Processor is designed to:
- reduce repetitive manual work
- enforce consistent naming conventions
- assist with photo organization and classification
- surface uncertainty honestly rather than forcing labels

It is **not** intended to replace user judgment, but to support it with safe, conservative automation.

---

For technical details, see:
- `TECHNICAL_OVERVIEW.md` (Windows-specific architecture)
