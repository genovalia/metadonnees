
BEGIN_REFERENCE_MATERIAL
******************************************************************
OCA_READ_ME/1.0
This is a human-readable schema, based on the OCA schema standard.

Reference for Overlays Capture Architecture (OCA):
https://doi.org/10.5281/zenodo.7707467

Reference for OCA_READ_ME/1.0:
https://github.com/agrifooddatacanada/OCA_README

A schema describes details about a dataset.
In OCA, a schema consists of a capture_base which documents the attributes and their most basic features.
A schema may also contain overlays which add details to the capture_base.
For each overlay and capture_base, a hash of their original contents has been calculated and is reported here as the SAID value.

This README format documents the capture_base and overlays that were associated together in a single OCA Bundle.
OCA_MANIFEST lists all components of the OCA Bundle.
For the OCA_BUNDLE, each section between rows of ****'s contains the details of one "layer type/version" of the OCA Bundle.
******************************************************************
END_REFERENCE_MATERIAL

BEGIN_OCA_MANIFEST
******************************************************************
Package SAID/digest: EL15GXx4E7_WBXlowqIIAtuitJ0XGpYqSsEfAw0EWE8l
Bundle SAID/digest: EN7yF5Bf8kusfh2IZwBJAr1ufGtZ-tfsEGbKhtT7BDL6

spec/capture_base/1.1 SAID/digest: "ELJIPGIN2rA6CotyYqLtnXyODkux61GBDNup81Vc-mCt"
spec/overlays/meta/1.1 (eng) SAID/digest: "EIvbStNLK2byw53-k6GWqimQqWle8VDxAG7NoUcMVohT"
spec/overlays/label/1.1 (eng) SAID/digest: "EK6bZdYBwPiv9T5uviYBiaLxCP2NIDEx5Ap26RpYLI2s"
spec/overlays/information/1.1 (eng) SAID/digest: "EAKCiuB_auHj2CFmuOkPeX9wMhbpLQkdVvzaeRqS96D7"
spec/overlays/entry_code/1.1 SAID/digest: "EAG7o6L_fQv-5_njbhFtybZW_lOjbUA6K8YxJSyGXIeX"
spec/overlays/entry/1.1 (eng) SAID/digest: "EERUnm78T88XG_8v8YnAXppihsN5xX1fb1OXzX5RuukF"

community/overlays/adc/ordering/1.1 SAID/digest: "ECaLsWX4ps60gZ4ck1kWb-6lghhXya3Z3QGWBCYkbmhI"
******************************************************************
END_OCA_MANIFEST

BEGIN_OCA_BUNDLE
******************************************************************
Layer name: spec/capture_base/1.1
SAID/digest: ELJIPGIN2rA6CotyYqLtnXyODkux61GBDNup81Vc-mCt
Classification: RDF401

Schema attributes: data type
    id: Text
    organism: Text
    sex: Text
    latitude: Numeric
    longitude: Numeric
    subspecies: Text
    population: Text
    sampled_tissue: Text
    sequenced_molecule: Text
    genotyping_technology: Text
    sampling_year: DateTime

******************************************************************
Layer name: spec/overlays/meta/1.1
SAID/digest: EIvbStNLK2byw53-k6GWqimQqWle8VDxAG7NoUcMVohT
Language: eng
Description: This is a data set of spongy moths from all around the species distribution

******************************************************************
Layer name: spec/overlays/label/1.1
SAID/digest: EK6bZdYBwPiv9T5uviYBiaLxCP2NIDEx5Ap26RpYLI2s
Language: eng
Schema attributes: spec/overlays/label/1.1
    id: id
    organism: organism
    sex: sex
    latitude: latitude
    longitude: longitude
    subspecies: subspecies
    population: population
    sampled_tissue: sampled_tissue
    sequenced_molecule: sequenced_molecule
    genotyping_technology: genotyping_technology
    sampling_year: sampling_year

******************************************************************
Layer name: spec/overlays/information/1.1
SAID/digest: EAKCiuB_auHj2CFmuOkPeX9wMhbpLQkdVvzaeRqS96D7
Language: eng
Schema attributes: spec/overlays/information/1.1
    id: unique id for the individual
    organism: species name according to Linean classification
    sex: sex of the individual: M (male) or F (female)
    latitude: decimal latitude of sampling for this individual
    longitude: decimal longitude of sampling for this individual
    subspecies: subspecies, either : Lymantria, asiatica, japonica
    population: population name
    sampled_tissue: sampled tissue
    sequenced_molecule: sequenced molecule: DNA, RNA, ... etc...
    genotyping_technology: genotyping technology: GBS, Ampliseq, sequencing
    sampling_year: year the individual been sampled

******************************************************************
Layer name: spec/overlays/entry_code/1.1
SAID/digest: EAG7o6L_fQv-5_njbhFtybZW_lOjbUA6K8YxJSyGXIeX

Schema attributes: spec/overlays/entry_code/1.1
    sex: [M,F]
    subspecies: [Lymantria,Asiatica,Japonica]

******************************************************************
Layer name: spec/overlays/entry/1.1
SAID/digest: EERUnm78T88XG_8v8YnAXppihsN5xX1fb1OXzX5RuukF
Schema attributes: spec/overlays/entry/1.1
    sex: male, female
    subspecies: European, Asian, Japan

******************************************************************
END_OCA_BUNDLE

BEGIN_OCA_PACKAGE_EXTENSIONS
******************************************************************
Layer name: community/overlays/adc/ordering/1.1
SAID/digest: ECaLsWX4ps60gZ4ck1kWb-6lghhXya3Z3QGWBCYkbmhI
Attribute ordering: id, organism, sex, latitude, longitude, subspecies, population, sampled_tissue, sequenced_molecule, genotyping_technology, sampling_year
Entry code ordering:
    sex: M, F
    subspecies: Lymantria, Asiatica, Japonica

******************************************************************
END_OCA_PACKAGE_EXTENSIONS
