# Ethics & Data Governance Statement

OpenSurgicalVision adheres to the highest ethical and regulatory standards for biomedical data handling.

## 1. Institutional Review Board (IRB) & Ethics Status
- **Scenario A (Default):** The project aggregates and standardizes existing open-access public datasets that were collected under their respective institutional ethics approvals. Re-annotation of fully de-identified public data does not constitute human subjects research.
- **Scenario B (New Partner Data):** Any primary clinical video collected in partnership with clinics/universities MUST obtain formal IRB approval from the contributing hospital/institution prior to data transfer. OpenSurgicalVision does NOT accept raw patient data directly.

## 2. 4-Layer De-identification Protocol
Before any dataset sample is ingested or referenced:
1. **PS3.15 Standard:** All direct 18 HIPAA Safe Harbor identifiers are purged.
2. **Private Vendor Tags:** All DICOM tags in odd group numbers are systematically stripped.
3. **Burned-In Annotations:** Every single video frame/slice is scanned with OCR (Tesseract / EasyOCR) to detect and mask burned-in patient names, timestamps, hospital IDs, and ultrasound/CT overlay text.
4. **3D Defacing:** Facial features in cranial CT/MRI volumes are defaced to prevent facial recognition reconstruction.
