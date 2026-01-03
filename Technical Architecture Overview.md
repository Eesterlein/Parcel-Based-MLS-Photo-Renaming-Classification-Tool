# Parcel-Based MLS Photo Renaming & Classification Tool  
## Technical Architecture Overview

---

## Application Type

This application is a local desktop utility built with Python and `tkinter`. It runs entirely on the user’s machine and performs all processing locally using files already present on the filesystem. The application does not rely on a web server or cloud-based runtime services.

The only external network interaction occurs during the initial download of the CLIP model, which is retrieved via the Hugging Face Hub and cached locally. After this initial setup, the application operates fully offline.

The application combines parcel-to-account resolution, scene-based image classification, and deterministic file renaming into a single end-to-end workflow designed for MLS photo processing.

---

## High-Level Subsystems

The application consists of four coordinated subsystems:

1. **Parcel Matching Subsystem**  
   Resolves parcel identifiers to account numbers using CSV-based mapping data.

2. **Scene-Based Image Classification Subsystem**  
   Assigns room labels to images using a vision-language model.

3. **File Validation and Renaming Subsystem**  
   Safely loads, validates, renames, and copies image and PDF files.

4. **Desktop GUI and Orchestration Layer**  
   Coordinates user interaction and manages execution flow.

---

## Execution Model

The application follows a single-process, event-driven architecture.

### On Startup

- Logging is initialized for both console and file output.
- A session ID and runtime timer are created for traceability.
- Core components are initialized:
  - **ParcelMatcher** loads CSV mapping data used to resolve parcel numbers to account numbers.
  - **ImageClassifier** loads a CLIP-based vision-language model used for scene classification.

The user interface is provided by a `tkinter` GUI running on the main thread. All user interactions (folder selection, process initiation) are handled synchronously through the GUI.

### When Processing Is Initiated

1. The selected folder is parsed to extract parcel identifiers.  
2. Parcel numbers are resolved to account numbers using CSV mapping data.  
3. Image and PDF files are discovered.  
4. Each image is validated using a permissive Pillow-based validator.  
5. Images are classified using scene-based semantic similarity.  
6. Files are renamed according to a strict naming convention.  
7. Files are copied into a `processed/` output directory.

Image processing runs in a separate daemon thread, ensuring the GUI remains responsive during long-running operations.

Original files are never modified or overwritten.

---

## Scene-Based Image Classification

### Model and Approach

The application uses the **CLIP (Contrastive Language–Image Pretraining)** vision-language model via the Hugging Face Transformers library. Classification is performed using zero-shot **scene understanding** rather than object detection or heuristic rules.

Each image is evaluated holistically against a fixed set of predefined room scenes. The model computes semantic similarity scores and selects the highest-confidence scene.

No model fine-tuning or retraining is performed.

---

## Confidence Thresholds and Conservative Defaults

Scene classifications are accepted only when the model’s confidence exceeds a defined minimum threshold. If no scene label meets this threshold, the image is conservatively classified as **OTHER**.

This design intentionally favors under-classification over forced labeling, reducing false positives and ensuring stable behavior across ambiguous, transitional, or unconventional MLS images.

---

## Final Allowed Room Categories

The system enforces a constrained set of canonical room labels:

- KITCHEN  
- LIVING ROOM  
- BEDROOM  
- OFFICE  
- DINING ROOM  
- DECK  
- EXTERIOR  
- BATHROOM  
- OTHER  

All labels are normalized to uppercase.

---

## Rationale for a Small Label Set

The label set is intentionally limited to reduce ambiguity, improve consistency, and simplify downstream workflows. Avoiding rarely used or highly subjective categories minimizes edge cases and prevents unstable classification behavior.

---

## File Validation and Safety

Image validation is intentionally permissive. If Pillow can successfully open and decode an image, it is considered valid.

Robust image loading includes:

- Support for truncated or malformed MLS images  
- Forced decode attempts  
- Memory re-encoding as a fallback  

If an image cannot be loaded safely, it is skipped.

---

## File Renaming and Output Handling

Files are renamed using a deterministic format:


PDF files are also renamed and copied using account-number-based naming.

---

## Determinism and Reproducibility

Given the same input files and model version, classification results are deterministic. No randomness or stochastic sampling is used during inference.

Each processing run is stateless and independent.

---

## Core Dependencies

- **pandas**  
  Used by the parcel matching subsystem to load and query CSV mapping data that associates parcel numbers with account numbers.

- **Pillow**  
  Used for image loading, validation, conversion, and robust handling of malformed or truncated MLS images.

- **transformers**  
  Used to load and interact with the CLIP vision-language model for scene-based image classification.

- **torch**  
  Used as the deep learning backend required by the Transformers library. Handles tensor operations and model inference.

- **tkinter**  
  Used as the desktop GUI framework. Provides native windowing, buttons, dialogs, and event handling.

- **pyinstaller**  
  Used to package the application into a standalone executable for Windows deployment.

---

## Supporting Dependencies

- **huggingface-hub**  
  Used internally by the Transformers library to download and cache model files locally.

- **tqdm**  
  Listed as a potential dependency for progress reporting but not currently used in the active codebase.

---

## Overall Design Philosophy

The application prioritizes predictable behavior, conservative classification, and operational safety over aggressive automation. Scene-based semantic understanding is used where it provides clear advantages, while deterministic file handling and explicit confidence thresholds prevent silent failure or forced misclassification.

Ambiguous cases are intentionally surfaced as **OTHER**, allowing for quick manual review when needed without compromising automated output quality.

---

# How the MLS Photo Processor Evolved

## Overview

The MLS Photo Processor evolved through several distinct phases, shaped by technical constraints, legal considerations, and direct feedback from its primary user. What began as an ambitious attempt to automate photo acquisition ultimately became a focused, reliable local tool optimized for real-world assessor workflows.

Rather than centering on automation at all costs, the final design reflects a series of deliberate decisions prioritizing legality, stability, and usability over fragile or high-risk approaches.

---

## The Original Problem

The project initially began as a Zillow photo scraping and classification tool. The original goal was to automatically retrieve property photos from Zillow, associate them with account numbers, and classify images by room type to reduce manual processing time.

Several approaches were explored to retrieve Zillow images programmatically:

- API-based scraping services, including **Amplify** and **ScraperAPI**
  - Amplify was unable to retrieve usable image data due to Zillow’s restrictions and protections.
  - ScraperAPI successfully retrieved HTML content but was limited to only the first few preview images exposed in Zillow’s interface.

- Browser automation using **Playwright** and **Chromium**
  - This approach successfully retrieved all images loaded on Zillow pages, but introduced new problems:
    - large numbers of irrelevant images (logos, UI assets, linked properties)
    - difficulty reliably filtering only the correct property photos
    - increased complexity and fragility
    - significant maintenance overhead

While further refinement of browser automation could potentially reduce noise, the approach was increasingly brittle and misaligned with the actual workflow of the intended user.

---

## A Key Insight: Understanding the Real Workflow

After discussing the problem directly with the primary user, a critical insight emerged:

> The majority of the user’s time was not spent scraping Zillow — it was spent manually downloading MLS photos from the CREN system using credentialed access.

Further investigation revealed that:

- CREN requires authenticated access  
- bulk downloading via developer tools had been intentionally disabled  
- scraping CREN under another user’s credentials would introduce legal and ethical risks  

At that point, it became clear that fully automated photo acquisition was neither practical nor appropriate.

The project pivoted accordingly.

---

## Revised Scope: Assisting, Not Replacing, the User

Rather than attempting to automate photo acquisition, the system was redesigned to support the user’s existing workflow:

- The user manually downloads MLS photos from CREN  
- Photos can be downloaded in any structure or format  
- The only requirement is that the folder name corresponds to a parcel number  

From there, the application handles everything downstream:

- parcel number resolution  
- image validation and normalization  
- classification  
- deterministic renaming  
- RealWare-compatible output  

This shift dramatically simplified the system while improving reliability and trust.

---

## User Requirements

Based on direct user feedback, the following core requirements were established:

- Folder names use parcel numbers to enable account matching  
- All output filenames use uppercase lettering  
- Photos are converted to JPEG format compatible with RealWare drag-and-drop uploads  
- Images are classified by room type  
- Original files are never modified or overwritten  

Additional requirements were added to support future upgrades and debugging:

- detailed logging for traceability and diagnostics  

---

## Research and Development

### Realities of MLS Photo Data

MLS photos present unique challenges:

- inconsistent staging  
- poor framing  
- partial or cropped views  
- mixed-use or transitional spaces  
- malformed or truncated image files  

Any classification system had to be robust to these conditions and avoid brittle assumptions.

---

### Early Classification Approaches

Initial classification attempts relied on heuristics and object-based logic. While intuitive in theory, these approaches proved fragile in practice:

- objects appear across multiple room types  
- partial views confused object detectors  
- rule complexity increased rapidly  
- small changes in framing produced inconsistent results  

This approach became increasingly difficult to maintain and reason about.

---

### The Shift to Scene-Based Understanding

The key realization was that rooms are better understood as **scenes**, not collections of objects.

Humans classify rooms based on:

- spatial layout  
- context  
- lighting  
- composition  

The system adopted this same perspective by transitioning to scene-based classification using a vision-language model.

---

### Adopting CLIP for Scene-Based Classification

The application now uses the CLIP (Contrastive Language–Image Pretraining) model via the Hugging Face Transformers library.

CLIP enables:

- holistic evaluation of images  
- zero-shot classification against predefined room scenes  
- no custom training or fine-tuning  
- fully local inference after initial download  

Classification is constrained by:

- a small, controlled label set  
- confidence thresholds  
- conservative defaults  

This approach significantly improved stability across real MLS photo sets.

---

## Why the System Is Fully Local

All processing occurs locally on the user’s machine.

This decision was driven by:

- privacy considerations  
- legal constraints  
- offline usability  
- ease of deployment in institutional environments  

After the initial model download, the application performs no runtime network calls and can be packaged as a standalone executable.

---

## Resulting Design Philosophy

The final system reflects a set of deliberate engineering values:

- prioritize stability over cleverness  
- treat uncertainty as a valid outcome  
- favor under-classification over false positives  
- separate data resolution, vision inference, and file handling  
- support real workflows rather than forcing automation  

The MLS Photo Processor is not designed to replace human judgment. Instead, it reduces repetitive work, enforces consistency, and surfaces uncertainty honestly — allowing users to remain in control while benefiting from automation where it is most reliable.


