# Licenses and Data Use

## RVL-CDIP

This project uses a classifier trained on the RVL-CDIP document image dataset.

- Source: http://www.cs.cmu.edu/~aharley/rvl-cdip/
- Alternate/public project page: https://adamharley.com/rvl-cdip/
- Intended use note: RVL-CDIP is commonly used for academic and research work.
- Commercial use note: users should verify the dataset license and usage terms before using this model or derived artifacts commercially.

The full RVL-CDIP dataset is not committed to this repository. Training was performed in Colab. This repository ships only the derived project artifacts needed for local inference validation:

- trained classifier artifact
- model card
- 50 golden TIFF replay images
- golden expected outputs

Because the model was trained on RVL-CDIP, it may inherit dataset limitations, label ambiguity, document-domain bias, and other dataset-specific behavior.
