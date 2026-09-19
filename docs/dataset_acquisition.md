# SpectraDerm Phase 1: Dataset Acquisition Checklist

This is an acquisition and verification checklist only. Do not download, redistribute, preprocess, or use a dataset until its official source, access terms, license, and citation requirements have been confirmed.

## Dataset A - Hyper-Skin

| Field | Verified information |
| --- | --- |
| Official dataset name | Hyper-Skin. |
| Official source | TO VERIFY. |
| Download/access method | TO VERIFY. |
| License | TO VERIFY. |
| Citation requirement | TO VERIFY. |
| Intended SpectraDerm module | Primary RGB-to-spectral reconstruction. |
| Image modality | Paired RGB and VIS spectral data. |
| RGB availability | 306 RGB samples. |
| Spectral/multispectral/hyperspectral availability | 306 VIS samples; 306 matched RGB/VIS pairs. |
| Spectral bands | 31 VIS bands. Wavelength metadata was not identified in the inspected files. |
| Image dimensions | Inspected VIS representation: `(31, 1024, 1024)`; internal pipeline convention: `(1024, 1024, 31)`. |
| Labels | TO VERIFY. |
| Subject/patient identifiers | 51 subject identifiers used for subject-aware splitting. |
| RGB/spectral pairing | 306 matched pairs; no unmatched pairs reported. |
| Metadata | TO VERIFY. |
| Known limitations | No wavelength metadata was identified in the inspected VIS files. |
| Skin-tone diversity information, if available | TO VERIFY. |
| Download status | Large raw archive remains outside the repository in Google Drive. Repository manifest and Phase 1 report are present. |

## Dataset B - Multispectral Skin Lesion Images / UMINHO-HSFD

| Field | Verified information |
| --- | --- |
| Official dataset name | University of Minho Hyperspectral Images of Faces Database (UMINHO-HSFD). |
| Official source | Figshare collection, documented in the local UMINHO-HSFD README. |
| Download/access method | TO VERIFY. |
| License | CC-BY 4.0. |
| Citation requirement | Cite Gomes, Linhares, and Nascimento (2024), *University of Minho Hyperspectral Faces Database: UMINHO-HSFD*, figshare collection. |
| Intended SpectraDerm module | Secondary spectral skin analysis and validation. Not disease/lesion classification. |
| Image modality | Hyperspectral facial reflectance with rendered RGB visual references. |
| RGB availability | 29 rendered RGB reference images; not independently captured RGB measurements. |
| Spectral/multispectral/hyperspectral availability | 29 reflectance MAT files; 29 matched RGB/reflectance pairs. |
| Spectral bands | 33 wavelengths from 400 to 720 nm at 10 nm intervals. |
| Image dimensions | Inspected sample reflectance shape: `(923, 618, 33)`; sample RGB shape: `(923, 618, 3)`. |
| Labels | TO VERIFY. The dataset is not a disease/lesion classification dataset. |
| Subject/patient identifiers | 29 face identifiers used for subject-aware splitting. |
| RGB/spectral pairing | 29 matched pairs; zero unmatched pairs reported. |
| Metadata | Sex, age, Fitzpatrick classification, von Luschan score, number of discernible colors, documented facial features, and image artifacts were analyzed. |
| Known limitations | Only 29 faces; skin-tone groups are strongly imbalanced; RGB images are rendered visual references; zero reflectance denotes artificial black background; reflectance must not be assumed to be limited to `[0,1]`. |
| Skin-tone diversity information, if available | Fitzpatrick and von Luschan metadata were analyzed. Distribution is strongly imbalanced. |
| Download status | Small documentation is stored in `docs/datasets/uminho_hsfd/`. Raw reflectance and RGB data remain outside the repository. |

## Verification Record

Before changing a dataset's status, record the official landing page, access date, applicable license version, required citation text, and any approved-use restrictions. Keep patient or subject identifiers out of notebooks, logs, reports, and derived filenames unless the dataset's governance documentation explicitly permits their use.
